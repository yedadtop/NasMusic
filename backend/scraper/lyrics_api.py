"""
歌词查询相关API，用于在线歌曲的歌词获取
"""
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from opencc import OpenCC


def clean_bilibili_title(title: str):
    """
    从B站歌曲标题中提取歌名和歌手名
    
    处理逻辑：
    1. 砍去尾部：移除换行符后面的内容（通常是UP主名字）
    2. 去标签：移除【】、[]等括号及其内部内容
    3. 去修饰：移除引号内部的情感抒发文案
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
    
    cleaned = re.sub(r'"\s*[^"]*\s*"', '', cleaned)
    
    cleaned = re.sub(r'"\s*[^"]*\s*"', '', cleaned)
    
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
    
    return {
        'song_name': song_name,
        'artist_name': artist_name,
        'original_title': original_title
    }


def fetch_lyrics_from_lrclib(track_name: str, artist_name: str = ''):
    """
    通过 LRCLIB 接口获取歌词（仅使用歌名搜索，不使用作者名以提高匹配成功率）
    
    返回: dict with keys: success (bool), lyrics (str), message (str)
    """
    if not track_name:
        return {'success': False, 'lyrics': '', 'message': '歌曲名称不能为空'}
    
    cc = OpenCC('t2s')
    api_url = "https://lrclib.net/api/search"
    
    params = {
        'track_name': track_name
    }
    
    print(f"[歌词查询] 搜索歌名: '{track_name}'")
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data or len(data) == 0:
            print(f"[歌词查询] LRCLIB 未找到匹配结果")
            return {'success': False, 'lyrics': '', 'message': '未找到匹配的歌词'}
        
        best_match = data[0]
        raw_lyrics = best_match.get('syncedLyrics') or best_match.get('plainLyrics')
        
        if not raw_lyrics:
            print(f"[歌词查询] 找到了歌曲信息，但暂无歌词内容")
            return {'success': False, 'lyrics': '', 'message': '该歌曲暂无歌词内容'}
        
        simplified_lyrics = cc.convert(raw_lyrics)
        print(f"[歌词查询] 成功获取歌词，长度: {len(simplified_lyrics)} 字符 (已转简体)")
        
        return {
            'success': True,
            'lyrics': simplified_lyrics,
            'message': '成功获取歌词',
            'matched_track': best_match.get('trackName'),
            'matched_artist': best_match.get('artistName'),
            'album': best_match.get('albumName')
        }
        
    except requests.RequestException as e:
        print(f"[歌词查询] ⚠️ LRCLIB 接口请求失败: {e}")
        return {'success': False, 'lyrics': '', 'message': f'请求歌词接口失败: {str(e)}'}
    except Exception as e:
        print(f"[歌词查询] ⚠️ 发生异常: {e}")
        return {'success': False, 'lyrics': '', 'message': f'发生内部错误: {str(e)}'}


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
        
        result = fetch_lyrics_from_lrclib(track_name, artist_name)
        
        return Response({
            'track_name': track_name,
            'artist_name': artist_name,
            'success': result['success'],
            'message': result['message'],
            'lyrics': result.get('lyrics', ''),
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
    """
    
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
        
        result = fetch_lyrics_from_lrclib(parsed['song_name'])
        
        return Response({
            'success': result['success'],
            'message': result['message'],
            'original_title': parsed['original_title'],
            'parsed_song_name': parsed['song_name'],
            'parsed_artist_name': parsed['artist_name'],
            'lyrics': result.get('lyrics', ''),
            'matched_track': result.get('matched_track'),
            'matched_artist': result.get('matched_artist'),
            'album': result.get('album')
        }, status=status.HTTP_200_OK)
