"""
歌词查询相关API，用于在线歌曲的歌词获取

歌词源策略（按优先级）：
1. QQ 音乐  —— 中文曲库最全，歌词本身是简体，覆盖周杰伦等版权曲目
2. LRCLIB  —— 开源社区库，中文覆盖不全且繁简混杂，作为兜底
两条路径都统一过一遍 OpenCC(t2s)，保证最终一定是简体。
"""
import base64
import difflib
import re

import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from opencc import OpenCC

# OpenCC 初始化要加载词典，做成模块级单例，避免每次请求重复加载
_cc = OpenCC('t2s')

QQ_SEARCH_URL = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp'
QQ_LYRIC_URL = 'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg'
# QQ 音乐接口必须带 Referer，否则返回空或错误码
QQ_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://y.qq.com/',
}

LRCLIB_SEARCH_URL = 'https://lrclib.net/api/search'

# 匹配度阈值：低于此分视为没搜到（宁可不给歌词，也不给错歌词）
MIN_MATCH_SCORE = 0.5
# 歌词最短长度：挡住"纯音乐，请欣赏"这类占位文本和错配的残句
MIN_LYRIC_LENGTH = 50
# 有逐行时间轴的结果优先，给一点加权
SYNCED_BONUS = 0.05

# 用于归一化的正则：去掉括号内容（Live/Remastered/伴奏等版本标注）、标点与空白
_BRACKET_RE = re.compile(r'[\(\（\[\【][^\)\）\]\】]*[\)\）\]\】]')
_NON_WORD_RE = re.compile(r'[^\w]+', re.UNICODE)
# 多歌手分隔符：周杰伦/费玉清、A & B、feat. 等
_ARTIST_SPLIT_RE = re.compile(r'[/、,，&;；]|\bfeat\.?\b|\bft\.?\b', re.IGNORECASE)

# B站标题里常见的非歌手噪声词：解析出的"歌手"含这些词说明抓错了段落
_NOISE_WORDS = (
    '完整版', '滚动歌词', '动态歌词', '歌词版', '无损', '高音质', '纯享',
    '原唱', '翻唱', '伴奏', '现场版', '官方', 'MV', '音频', '合集',
)


def _normalize(text: str) -> str:
    """归一化：转简体 + 小写 + 去括号内容 + 去标点空白，用于相似度比较"""
    if not text:
        return ''
    s = _cc.convert(str(text)).lower()
    s = _BRACKET_RE.sub('', s)
    s = _NON_WORD_RE.sub('', s)
    return s


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _artist_ratio(artist: str, candidate: str) -> float:
    """歌手相似度：候选可能是多歌手串，取其中最高的一项"""
    if not artist or not candidate:
        return 0.0
    want = _normalize(artist)
    parts = [_normalize(p) for p in _ARTIST_SPLIT_RE.split(str(candidate))]
    parts = [p for p in parts if p]
    if not parts:
        return 0.0
    return max(_ratio(want, p) for p in parts)


def _score(title: str, artist: str, cand_title: str, cand_artist: str, synced: bool = False) -> float:
    """综合匹配分：歌名 65% + 歌手 35%；没有歌手信息时只看歌名"""
    title_score = _ratio(_normalize(title), _normalize(cand_title))
    if artist and cand_artist:
        score = title_score * 0.65 + _artist_ratio(artist, cand_artist) * 0.35
    else:
        score = title_score
    if synced:
        score += SYNCED_BONUS
    return min(score, 1.0)


def _pick_best(candidates, title, artist):
    """从候选里挑综合分最高的一条，返回 (候选, 分数)"""
    best = None
    best_score = 0.0
    for item in candidates:
        score = _score(title, artist, item.get('title', ''), item.get('artist', ''), item.get('synced', False))
        if score > best_score:
            best, best_score = item, score
    return best, best_score


def clean_bilibili_title(title: str):
    """
    从B站歌曲标题中提取歌名和歌手名
    
    处理逻辑：
    1. 砍去尾部：移除换行符后面的内容（通常是UP主名字）
    2. 去标签：移除【】、[]等括号及其内部内容
    3. 去修饰：移除引号内部的情感抒发文案（英文引号与中文引号都要处理）
    4. 提取核心：优先寻找书名号《》提取歌名，紧跟在其后的文本作为歌手名
    
    返回: dict with keys: song_name (str), artist_name (str), original_title (str)
    """
    if not title:
        return {'song_name': '', 'artist_name': '', 'original_title': ''}
    
    original_title = title.strip()
    
    cleaned = original_title.split('\n')[0]
    
    cleaned = cleaned.strip()
    
    import re
    
    cleaned = re.sub(r'【[^】]*】', '', cleaned)
    
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    
    # 英文双引号内的情感文案
    cleaned = re.sub(r'"[^"]*"', '', cleaned)
    # 中文单/双引号、直角引号内的情感文案。
    # B站标题常见写法：《歌名》- 歌手 -‘一句歌词’，不剥掉这段会把歌手名污染成
    # “周杰伦 -‘你发如雪 纷飞了眼泪…’”，导致歌词搜索完全匹配不上。
    cleaned = re.sub(r'[‘“「『][^’”」』]*[’”」』]', '', cleaned)
    
    cleaned = cleaned.strip()
    
    song_name = ''
    artist_name = ''
    
    guhao_match = re.search(r'《([^》]+)》', cleaned)
    if guhao_match:
        song_name = guhao_match.group(1).strip()
        
        before_guhao = cleaned[:guhao_match.start()].strip()
        after_guhao = cleaned[guhao_match.end():].strip()
        
        possible_tags = ['无损音质', '4K', '高清', 'HQ', 'SQ', 'flac', 'mp3', 'wav', '录音', '现场', 'live', 'LIVE', '翻唱', 'cover', 'COVER']
        
        if after_guhao:
            dash_match = re.match(r'[-–—~]\s*(.+)', after_guhao)
            if dash_match:
                possible_after_artist = dash_match.group(1).strip()
                if not any(tag in possible_after_artist for tag in possible_tags):
                    artist_name = possible_after_artist
            elif not any(tag in after_guhao for tag in possible_tags):
                if not before_guhao or before_guhao and len(after_guhao) > 3:
                    artist_name = after_guhao
        
        # 解析出的"歌手"若含"完整版/滚动歌词"这类噪声词，说明抓错了段落，
        # 丢弃后回退到书名号之前的文本（那里往往才是真正的演唱者）
        if artist_name and any(w in artist_name for w in _NOISE_WORDS):
            artist_name = ''
        if not artist_name and before_guhao:
            artist_name = before_guhao
    
    if not song_name:
        dash_match = re.match(r'"?(.+?)"?\s*[-–—~]\s*(.+)', cleaned)
        if dash_match:
            song_name = dash_match.group(1).strip()
            artist_name = dash_match.group(2).strip()
        else:
            parts = re.split(r'[-–—~]', cleaned)
            if len(parts) >= 2:
                song_name = parts[0].strip()
                artist_name = parts[1].strip()
            else:
                song_name = cleaned
    
    song_name = re.sub(r'\s+', ' ', song_name).strip()
    artist_name = re.sub(r'\s+', ' ', artist_name).strip()

    # 引号内的歌词被剥掉后，歌手名常留下 "周杰伦 -" 这种尾巴，统一清掉。
    # 只剥首尾的分隔符，不切中间的连字符，避免误伤 A-Lin 这类名字。
    song_name = song_name.strip(' ｜|·,，、')
    artist_name = artist_name.strip(' -–—~｜|·,，、\'"‘’“”')
    # 兜底：回退到书名号前的文本时也可能带噪声词
    if artist_name and any(w in artist_name for w in _NOISE_WORDS):
        artist_name = ''

    return {
        'song_name': song_name,
        'artist_name': artist_name,
        'original_title': original_title
    }


def _qq_search(track_name: str, artist_name: str = ''):
    """QQ 音乐搜索，返回候选列表 [{id,title,artist,album}]"""
    keyword = f'{track_name} {artist_name}'.strip()
    params = {'w': keyword, 'format': 'json', 'p': 1, 'n': 10}
    resp = requests.get(QQ_SEARCH_URL, params=params, headers=QQ_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get('code') not in (0, None):
        raise ValueError(f"QQ音乐搜索返回错误码 {data.get('code')}")

    songs = ((data.get('data') or {}).get('song') or {}).get('list') or []
    candidates = []
    for song in songs:
        singers = song.get('singer') or []
        artist = '/'.join(s.get('name', '') for s in singers if s.get('name'))
        candidates.append({
            'id': song.get('songmid'),
            'title': song.get('songname', ''),
            'artist': artist,
            'album': song.get('albumname', ''),
            'synced': True,  # QQ 返回的都是逐行 LRC
        })
    return candidates


def _qq_lyric(songmid: str) -> str:
    """取 QQ 音乐歌词原文（LRC 文本），取不到返回空串"""
    if not songmid:
        return ''
    params = {'songmid': songmid, 'format': 'json', 'nobase64': 1, 'g_tk': 5381}
    resp = requests.get(QQ_LYRIC_URL, params=params, headers=QQ_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get('retcode') not in (0, None):
        return ''

    lyric = (data.get('lyric') or '').strip()
    # 少数情况下接口忽略 nobase64，仍返回 base64
    if lyric and not lyric.startswith('['):
        try:
            decoded = base64.b64decode(lyric).decode('utf-8')
            if decoded.strip().startswith('['):
                lyric = decoded.strip()
        except Exception:
            pass
    return lyric


def fetch_lyrics_from_qq(track_name: str, artist_name: str = ''):
    """从 QQ 音乐取歌词：搜索 → 打分选优 → 拉歌词"""
    candidates = _qq_search(track_name, artist_name)
    if not candidates:
        return {'success': False, 'lyrics': '', 'message': 'QQ音乐未找到匹配结果', 'source': 'qq'}

    best, score = _pick_best(candidates, track_name, artist_name)
    if not best or score < MIN_MATCH_SCORE:
        print(f"[歌词查询] QQ音乐匹配度过低({score:.2f})，放弃: '{track_name}'")
        return {'success': False, 'lyrics': '', 'message': 'QQ音乐匹配度过低', 'source': 'qq', 'score': score}

    lyric = _qq_lyric(best['id'])
    if not lyric:
        print(f"[歌词查询] QQ音乐命中 '{best['title']}' 但无歌词内容")
        return {'success': False, 'lyrics': '', 'message': 'QQ音乐无歌词内容', 'source': 'qq', 'score': score}
    if len(lyric.strip()) < MIN_LYRIC_LENGTH:
        print(f"[歌词查询] QQ音乐命中 '{best['title']}' 但歌词过短({len(lyric)} 字符)，判定为无效")
        return {'success': False, 'lyrics': '', 'message': 'QQ音乐歌词内容无效', 'source': 'qq', 'score': score}

    lyrics = _cc.convert(lyric)
    print(f"[歌词查询] QQ音乐命中: {best['title']} - {best['artist']} (score={score:.2f}, {len(lyrics)} 字符)")
    return {
        'success': True,
        'lyrics': lyrics,
        'message': '成功获取歌词',
        'source': 'qq',
        'score': score,
        'matched_track': best['title'],
        'matched_artist': best['artist'],
        'album': best['album'],
    }


def fetch_lyrics_from_lrclib(track_name: str, artist_name: str = ''):
    """
    通过 LRCLIB 接口获取歌词（兜底源）。
    会带上歌手名参与打分，并在多条结果里选匹配度最高的一条，
    而不是盲取第一条——同名不同歌在社区库里非常常见。
    """
    if not track_name:
        return {'success': False, 'lyrics': '', 'message': '歌曲名称不能为空', 'source': 'lrclib'}

    params = {'track_name': track_name}
    if artist_name:
        params['artist_name'] = artist_name

    print(f"[歌词查询] LRCLIB 搜索: '{track_name}' - '{artist_name}'")

    try:
        response = requests.get(LRCLIB_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            print("[歌词查询] LRCLIB 未找到匹配结果")
            return {'success': False, 'lyrics': '', 'message': '未找到匹配的歌词', 'source': 'lrclib'}

        candidates = []
        for item in data:
            raw = item.get('syncedLyrics') or item.get('plainLyrics')
            if not raw:
                continue
            candidates.append({
                'title': item.get('trackName', ''),
                'artist': item.get('artistName', ''),
                'album': item.get('albumName', ''),
                'lyrics': raw,
                'synced': bool(item.get('syncedLyrics')),
            })

        if not candidates:
            print("[歌词查询] LRCLIB 命中歌曲但均无歌词内容")
            return {'success': False, 'lyrics': '', 'message': '该歌曲暂无歌词内容', 'source': 'lrclib'}

        best, score = _pick_best(candidates, track_name, artist_name)
        if not best or score < MIN_MATCH_SCORE:
            print(f"[歌词查询] LRCLIB 匹配度过低({score:.2f})，放弃: '{track_name}'")
            return {'success': False, 'lyrics': '', 'message': '未找到匹配的歌词', 'source': 'lrclib', 'score': score}
        if len(best['lyrics'].strip()) < MIN_LYRIC_LENGTH:
            print(f"[歌词查询] LRCLIB 命中 '{best['title']}' 但歌词过短，判定为无效")
            return {'success': False, 'lyrics': '', 'message': '歌词内容无效', 'source': 'lrclib', 'score': score}

        lyrics = _cc.convert(best['lyrics'])
        print(f"[歌词查询] LRCLIB 命中: {best['title']} - {best['artist']} (score={score:.2f}, {len(lyrics)} 字符)")

        return {
            'success': True,
            'lyrics': lyrics,
            'message': '成功获取歌词',
            'source': 'lrclib',
            'score': score,
            'matched_track': best['title'],
            'matched_artist': best['artist'],
            'album': best['album'],
        }

    except requests.RequestException as e:
        print(f"[歌词查询] ⚠️ LRCLIB 接口请求失败: {e}")
        return {'success': False, 'lyrics': '', 'message': f'请求歌词接口失败: {str(e)}', 'source': 'lrclib'}
    except Exception as e:
        print(f"[歌词查询] ⚠️ LRCLIB 发生异常: {e}")
        return {'success': False, 'lyrics': '', 'message': f'发生内部错误: {str(e)}', 'source': 'lrclib'}


def fetch_lyrics(track_name: str, artist_name: str = ''):
    """
    统一歌词入口：QQ 音乐优先，失败回退 LRCLIB。
    返回: dict with keys: success / lyrics / message / source / matched_track / matched_artist / album
    """
    if not track_name:
        return {'success': False, 'lyrics': '', 'message': '歌曲名称不能为空', 'source': None}

    try:
        result = fetch_lyrics_from_qq(track_name, artist_name)
        if result.get('success'):
            return result
        print(f"[歌词查询] QQ音乐未命中（{result.get('message')}），回退 LRCLIB")
    except Exception as e:
        # QQ 接口是非官方的，网络抖动/风控都可能失败，静默降级即可
        print(f"[歌词查询] ⚠️ QQ音乐请求异常，回退 LRCLIB: {e}")

    return fetch_lyrics_from_lrclib(track_name, artist_name)


class LyricsSearchView(APIView):
    """
    通过歌名和歌手名查询歌词
    """
    
    def get(self, request):
        track_name = request.query_params.get('track_name', '').strip()
        artist_name = request.query_params.get('artist_name', '').strip()
        
        if not track_name:
            return Response(
                {'message': '缺少必需参数: track_name'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = fetch_lyrics(track_name, artist_name)

        return Response({
            'track_name': track_name,
            'artist_name': artist_name,
            'success': result['success'],
            'message': result['message'],
            'lyrics': result.get('lyrics', ''),
            'source': result.get('source'),
            'matched_track': result.get('matched_track'),
            'matched_artist': result.get('matched_artist'),
            'album': result.get('album')
        }, status=status.HTTP_200_OK)


class BilibiliTitleParserView(APIView):
    """
    解析B站歌曲标题，提取歌名和歌手名
    """
    
    def post(self, request):
        title = request.data.get('title', '')
        
        if not title:
            return Response(
                {'message': '缺少必需参数: title'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parsed = clean_bilibili_title(title)
        
        return Response({
            'original_title': parsed['original_title'],
            'song_name': parsed['song_name'],
            'artist_name': parsed['artist_name'],
            'message': '解析成功'
        }, status=status.HTTP_200_OK)


class BilibiliLyricsView(APIView):
    """
    为B站歌曲获取歌词：先解析标题，再查询歌词
    播放时自动调用，属于只读查询（不写库不改文件），豁免令牌校验
    """

    # 播放B站歌曲无需令牌：无令牌用户也能正常播放并看到歌词
    permission_classes = [AllowAny]

    def post(self, request):
        title = request.data.get('title', '')
        
        if not title:
            return Response(
                {'message': '缺少必需参数: title'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parsed = clean_bilibili_title(title)
        
        if not parsed['song_name']:
            return Response({
                'success': False,
                'message': '无法从标题中提取歌名',
                'original_title': parsed['original_title'],
                'song_name': '',
                'artist_name': '',
                'lyrics': ''
            }, status=status.HTTP_200_OK)
        
        # 带上解析出的歌手名参与打分，能显著减少同名歌曲错配
        result = fetch_lyrics(parsed['song_name'], parsed['artist_name'])

        return Response({
            'success': result['success'],
            'message': result['message'],
            'original_title': parsed['original_title'],
            'parsed_song_name': parsed['song_name'],
            'parsed_artist_name': parsed['artist_name'],
            'lyrics': result.get('lyrics', ''),
            'source': result.get('source'),
            'matched_track': result.get('matched_track'),
            'matched_artist': result.get('matched_artist'),
            'album': result.get('album')
        }, status=status.HTTP_200_OK)
