import os
import re
import base64
import logging
import mutagen
import mutagen.flac
import mutagen.id3
import mutagen.mp3
import mutagen.mp4
import mutagen.oggopus
import mutagen.oggvorbis
from mutagen.flac import Picture
from mutagen.id3 import APIC
from mutagen.mp4 import MP4Cover
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
import requests

# --- 强制屏蔽系统代理，防止流量被错误地发往 frp 等内网穿透隧道 ---
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['all_proxy'] = ''

# --- 引入 bilibili-api-python 核心组件 ---
from bilibili_api import search, video, Credential, sync
from library.models import Track, Artist, Album, get_music_path
from scanner.remux_utils import remux_audio_file
from scanner.utils import parse_artists

logger = logging.getLogger(__name__)

BILI_QUALITY_MAP = {
    30251: "Hi-Res 无损",
    30250: "杜比全景声",
    30280: "192K 高码率",
    30232: "132K 标准",
    30216: "64K 流畅",
}

AUDIO_QUALITY_PRIORITY = {
    30251: 5, 30250: 4, 30280: 3, 30232: 2, 30216: 1,
}

MANUAL_QUALITY_SELECTION = None

BILI_DOWNLOAD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
}


def get_bili_credential():
    """获取 Bilibili 凭证对象"""
    return Credential()


def _sanitize_filename(name):
    """清理文件名中 Windows 不允许的字符，并限制长度"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().strip(' .')
    return cleaned[:100] or 'bilibili_audio'


def _select_best_audio(audio_streams):
    """按音质优先级挑选最优音频流（与播放接口同一套规则）"""
    best_audio = None
    best_priority = 0
    quality_priority = AUDIO_QUALITY_PRIORITY.copy()

    if isinstance(MANUAL_QUALITY_SELECTION, int) and MANUAL_QUALITY_SELECTION in quality_priority:
        for codecid in quality_priority:
            quality_priority[codecid] = 1 if codecid != MANUAL_QUALITY_SELECTION else 10

    for audio in audio_streams:
        audio_url = audio.get('baseUrl') or audio.get('src')
        audio_codec = audio.get('codecid') or audio.get('id') or 0
        priority = quality_priority.get(audio_codec, 0)
        if audio_url and priority > best_priority:
            best_audio = audio
            best_priority = priority

    if not best_audio and audio_streams:
        best_audio = audio_streams[0]
    return best_audio


def _embed_metadata(file_path, title, artist, album, cover_jpeg_data=None):
    """
    将标题/歌手/专辑（及封面）写入音频文件标签。
    兼容 M4A/MP4、MP3(ID3)、FLAC、OGG(Vorbis/Opus) 等主流格式。
    返回 (text_ok, cover_ok)。

    注意：文本标签必须通过 mutagen 的 easy 接口写入（mutagen.File(path, easy=True)）。
    非 easy 的 MP4 接口只认 '©nam' 等四字节原始键名，直接写 'title' 会被截断成
    'titl' 这样的废键，导致播放器和扫描器都读不到。
    """
    text_ok = False
    cover_ok = False

    # 1. 文本标签：easy 接口对各格式统一暴露 title/artist/album
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio is not None:
            audio['title'] = [str(title)]
            audio['artist'] = [str(artist)]
            audio['album'] = [str(album)]
            audio.save()
            text_ok = True
    except Exception as e:
        logger.warning(f"[BiliAPI-Download] 写入文本标签失败 ({file_path}): {e}")

    if not cover_jpeg_data:
        return text_ok, cover_ok

    # 2. 封面（及专辑作者）：不同容器格式需要各自的写入方式
    try:
        audio = mutagen.File(file_path)
        if isinstance(audio, mutagen.mp4.MP4):
            audio['covr'] = [MP4Cover(cover_jpeg_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio['aART'] = [str(artist)]
            audio.save()
            cover_ok = True
        elif isinstance(audio, mutagen.flac.FLAC):
            pic = Picture()
            pic.type = 3  # 封面 (front cover)
            pic.mime = 'image/jpeg'
            pic.data = cover_jpeg_data
            audio.clear_pictures()
            audio.add_picture(pic)
            audio['albumartist'] = [str(artist)]
            audio.save()
            cover_ok = True
        elif isinstance(audio, mutagen.mp3.MP3) or isinstance(audio.tags, mutagen.id3.ID3):
            # MP3 及其他使用 ID3 标签的格式 (WAV 等)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall('APIC')
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_jpeg_data))
            audio.tags.delall('TPE2')
            audio.tags.add(mutagen.id3.TPE2(encoding=3, text=str(artist)))
            audio.save()
            cover_ok = True
        elif isinstance(audio, (mutagen.oggvorbis.OggVorbis, mutagen.oggopus.OggOpus)):
            pic = Picture()
            pic.type = 3
            pic.mime = 'image/jpeg'
            pic.data = cover_jpeg_data
            audio['metadata_block_picture'] = [base64.b64encode(pic.write()).decode('ascii')]
            audio['albumartist'] = [str(artist)]
            audio.save()
            cover_ok = True
        else:
            logger.warning(f"[BiliAPI-Download] 暂不支持该格式的封面嵌入: {type(audio).__name__}")
    except Exception as e:
        logger.warning(f"[BiliAPI-Download] 嵌入封面失败 ({file_path}): {e}")

    return text_ok, cover_ok


class BiliSearchView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        logger.info(f"\n========== 开始 B站搜索 (bilibili-api): '{keyword}' ==========")

        if not keyword:
            return Response({'message': 'keyword 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 【搜索接口】无需 credential，让库底层自行处理公共搜索的 Wbi 签名
            data = sync(search.search_by_type(
                keyword=keyword,
                search_type=search.SearchObjectType.VIDEO,
                page=1
            ))

            results = []
            video_list = data.get('result') or []

            for item in video_list[:20]:
                results.append({
                    'bvid': item.get('bvid', ''),
                    'title': re.sub(r'<[^>]+>', '', item.get('title', '')),
                    'author': item.get('author', ''),
                    'track_cover': item.get('pic', ''),
                    'duration': item.get('duration', ''),
                })

            logger.info(f"[BiliAPI-Search] 搜索结束，成功解析 {len(results)} 条结果。")
            return Response({
                'success': True,
                'keyword': keyword,
                'count': len(results),
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[BiliAPI-Search] 搜索接口抛出异常: {str(e)}")
            return Response({'message': f'B站搜索失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)


class BiliPlayUrlView(APIView):
    def get(self, request):
        bvid = request.query_params.get('bvid', '').strip()
        logger.info(f"\n========== 开始获取播放链接 (bilibili-api): {bvid} ==========")

        if not bvid:
            return Response({'message': 'bvid 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        credential = get_bili_credential()

        try:
            # 构建 Video 对象
            v = video.Video(bvid=bvid, credential=credential)

            # ---> 新增：获取歌曲(视频)详细信息，用于日志打印 <---
            try:
                video_info = sync(v.get_info())
                song_title = video_info.get('title', '未知标题')
                song_author = video_info.get('owner', {}).get('name', '未知UP主')
                logger.warning(f"[BiliAPI-Play] 正在提取歌曲信息: 《{song_title}》 - UP主: {song_author}")
            except Exception as e:
                song_title, song_author = "未知标题", "未知UP主"
                logger.warning(f"[BiliAPI-Play] 获取歌曲基础信息失败: {e}")

            # 获取播放流字典，会自动计算 Wbi 签名获取最新链接
            playurl_data = sync(v.get_download_url(page_index=0))

            dash = playurl_data.get('dash', {})
            audio_streams = dash.get('audio', [])

            logger.warning(f"[BiliAPI-Play] 成功解析到音频流: {len(audio_streams)} 条候选线路")

            best_audio = None
            best_priority = 0
            quality_priority = AUDIO_QUALITY_PRIORITY.copy()

            if isinstance(MANUAL_QUALITY_SELECTION, int) and MANUAL_QUALITY_SELECTION in quality_priority:
                for codecid in quality_priority:
                    quality_priority[codecid] = 1 if codecid != MANUAL_QUALITY_SELECTION else 10

            for audio in audio_streams:
                audio_url = audio.get('baseUrl') or audio.get('src')
                audio_codec = audio.get('codecid') or audio.get('id') or 0
                audio_size = audio.get('size', 0)
                bandwidth = audio.get('bandwidth', 0)
                bitrate_kbps = round(bandwidth / 1000) if bandwidth else 0
                priority = quality_priority.get(audio_codec, 0)

                temp_desc = BILI_QUALITY_MAP.get(audio_codec, '未知')
                logger.warning(f"   --> 探测到候选流: 音质级别={audio_codec} ({temp_desc}), 码率: {bitrate_kbps}Kbps, 优先级={priority}")

                if audio_url and priority > best_priority:
                    best_audio = audio
                    best_priority = priority

            if not best_audio and audio_streams:
                best_audio = audio_streams[0]

            if not best_audio:
                logger.error(f"[BiliAPI-Play] 致命错误：该视频没有任何可用的音频流")
                return Response({'message': '未找到可用的音频流'}, status=status.HTTP_404_NOT_FOUND)

            audio_url = best_audio.get('baseUrl') or best_audio.get('src')
            audio_codec = best_audio.get('codecid') or best_audio.get('id') or 0
            audio_size = best_audio.get('size', 0)
            bandwidth = best_audio.get('bandwidth', 0)

            if audio_size == 0:
                audio_size = best_audio.get('bandwidth', 0)
                if audio_size == 0:
                    audio_size = best_audio.get('length', 0) * 128 / 8

            quality_desc = BILI_QUALITY_MAP.get(audio_codec, '未知')
            bitrate_kbps = round(bandwidth / 1000) if bandwidth else 0

            logger.warning(
                f"[BiliAPI-Play] 🏆 最终选定最优音频流 -> 《{song_title}》 | 音质: {quality_desc} (Codec:{audio_codec}) | 码率: {bitrate_kbps}Kbps | 大小: {audio_size / 1024 / 1024:.2f}MB"
            )
            logger.warning(
                f"[BiliAPI-Play] 🔗 音频下载链接: {audio_url}"
            )

            return Response({
                'success': True,
                'bvid': bvid,
                'cid': playurl_data.get('last_play_cid', ''),
                'audio_url': audio_url,
                'quality_desc': quality_desc,
                'audio_size': audio_size,
                'audio_codecid': audio_codec,
                'bitrate': bitrate_kbps,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[BiliAPI-Play] 获取播放链接异常: {str(e)}")
            return Response({'message': f'获取播放链接失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)


class BiliDownloadView(APIView):
    """保存 Bilibili 搜索歌曲：下载音频文件和封面到本地音乐库并入库（不含歌词）"""

    def post(self, request):
        bvid = request.data.get('bvid', '').strip()
        title = request.data.get('title', '').strip()
        author = request.data.get('author', '').strip()
        cover_url = request.data.get('cover', '').strip()

        logger.info(f"\n========== 开始保存B站歌曲到音乐库: {bvid} ==========")

        if not bvid:
            return Response({'message': 'bvid 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        music_path = get_music_path()
        if not music_path or not os.path.isdir(music_path):
            return Response({'message': '音乐库路径未配置或不存在，无法保存'}, status=status.HTTP_400_BAD_REQUEST)

        # 去重：文件名中包含 bvid 即视为已保存过
        if Track.objects.filter(file_path__icontains=bvid).exists():
            return Response({'success': True, 'already': True, 'message': '该歌曲已在音乐库中'})

        tmp_path = None
        try:
            v = video.Video(bvid=bvid, credential=get_bili_credential())

            # 获取视频信息，补全标题/歌手/封面/时长
            video_info = sync(v.get_info())
            if not title:
                title = re.sub(r'<[^>]+>', '', video_info.get('title', '')) or bvid
            if not author:
                author = video_info.get('owner', {}).get('name', '') or 'Unknown Artist'
            if not cover_url:
                cover_url = video_info.get('pic', '')
            video_duration = float(video_info.get('duration', 0) or 0)

            # 挑选最优音频流
            playurl_data = sync(v.get_download_url(page_index=0))
            audio_streams = playurl_data.get('dash', {}).get('audio', [])
            best_audio = _select_best_audio(audio_streams)
            if not best_audio:
                return Response({'message': '未找到可用的音频流'}, status=status.HTTP_404_NOT_FOUND)

            audio_url = best_audio.get('baseUrl') or best_audio.get('src')
            audio_codec = best_audio.get('codecid') or best_audio.get('id') or 0
            quality_desc = BILI_QUALITY_MAP.get(audio_codec, '未知')

            # 下载音频文件到音乐库根目录（与其他本地歌曲同级）
            save_dir = music_path
            os.makedirs(save_dir, exist_ok=True)
            safe_title = _sanitize_filename(title)
            file_path = os.path.normpath(os.path.join(save_dir, f"{safe_title}_{bvid}.m4a"))
            tmp_path = file_path + '.part'

            with requests.get(audio_url, headers=BILI_DOWNLOAD_HEADERS, stream=True, timeout=60) as upstream:
                upstream.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    for chunk in upstream.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp_path, file_path)
            tmp_path = None

            # remux：fragmented MP4 转普通 MP4 并将 moov 前置，保证浏览器可正常播放且 mutagen 可解析标签
            remux_ok = False
            try:
                remux_ok = remux_audio_file(file_path)
            except Exception as e:
                logger.warning(f"[BiliAPI-Download] remux 异常（已忽略）: {e}")
            if not remux_ok:
                logger.warning(
                    f"[BiliAPI-Download] ⚠️ remux 未成功（可能未安装 ffmpeg），"
                    f"文件可能仍为 fragmented MP4：浏览器一般可播放，但无法嵌入标签、读取时长"
                )

            # 下载封面（失败不影响保存结果），居中裁剪为正方形
            cover_jpeg_data = None
            if cover_url:
                try:
                    if cover_url.startswith('//'):
                        cover_url = 'https:' + cover_url
                    img_res = requests.get(cover_url, headers=BILI_DOWNLOAD_HEADERS, timeout=20)
                    img_res.raise_for_status()
                    image = Image.open(BytesIO(img_res.content))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    # 居中裁剪为正方形（B站视频封面多为 16:9，直接嵌入两侧会有黑边）
                    width, height = image.size
                    side = min(width, height)
                    left = (width - side) // 2
                    top = (height - side) // 2
                    image = image.crop((left, top, left + side, top + side))
                    img_io = BytesIO()
                    image.save(img_io, format='JPEG', quality=95, subsampling=0)
                    cover_jpeg_data = img_io.getvalue()
                except Exception as e:
                    logger.warning(f"[BiliAPI-Download] 封面下载失败（已忽略）: {e}")

            # 【核心】将元数据和封面嵌入音频文件本身。B站原始流无任何标签，
            # 嵌入后即使经过「删除到回收站 → 恢复 → 自动重扫描」，歌曲信息/封面/时长也不会丢失
            tags_embedded, cover_embedded = _embed_metadata(file_path, title, author, 'Bilibili', cover_jpeg_data)

            # 读取真实时长（remux 成功后 mutagen 可正常解析），失败则使用视频时长
            duration = video_duration
            try:
                audio_meta = mutagen.File(file_path)
                if audio_meta is not None and getattr(audio_meta.info, 'length', 0) > 0:
                    duration = audio_meta.info.length
            except Exception:
                pass

            # 入库：歌手 / 专辑 / 歌曲（专辑统一归到 Bilibili，与扫描器的按标题去重逻辑一致）
            primary_artist, _ = Artist.objects.get_or_create(name=author)
            album_obj = Album.objects.filter(title='Bilibili').first()
            if not album_obj:
                album_obj = Album.objects.create(title='Bilibili', artist=primary_artist)

            track = Track.objects.create(
                title=title,
                artist=primary_artist,
                album=album_obj,
                file_path=file_path,
                duration=duration,
                format='m4a',
            )
            all_artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in parse_artists(author)]
            track.artists.set(all_artist_objs)

            # 封面另存到封面库（covers/tracks/），数据库记录封面地址
            if cover_jpeg_data:
                try:
                    track.cover_thumbnail.save(f'bili_{bvid}.jpg', ContentFile(cover_jpeg_data), save=True)
                except Exception as e:
                    logger.warning(f"[BiliAPI-Download] 封面保存到封面库失败（已忽略）: {e}")

            logger.warning(
                f"[BiliAPI-Download] ✅ 保存成功 -> 《{title}》 | 音质: {quality_desc} | 时长: {duration:.0f}s | "
                f"remux: {'成功' if remux_ok else '失败'} | 标签嵌入: {'成功' if tags_embedded else '失败'} | 文件: {file_path}"
            )
            all_ok = tags_embedded and remux_ok
            return Response({
                'success': True,
                'message': '已保存到音乐库' if all_ok else '已保存到音乐库（部分信息未能写入文件，回收站恢复后封面/时长可能丢失）',
                'track_id': track.id,
                'quality_desc': quality_desc,
                'tags_embedded': tags_embedded,
                'remuxed': remux_ok,
            })

        except requests.RequestException as e:
            logger.error(f"[BiliAPI-Download] 下载音频流失败: {str(e)}")
            return Response({'message': f'下载音频流失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.error(f"[BiliAPI-Download] 保存失败: {str(e)}")
            return Response({'message': f'保存失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


class BiliProxyStreamView(APIView):
    def get(self, request):
        url = request.query_params.get('url', '').strip()
        if not url:
            return Response({'message': 'url 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if not url.startswith('https://'):
            return Response({'message': '无效的媒体URL'}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Range': request.META.get('HTTP_RANGE', 'bytes=0-'),
        }

        try:
            upstream = requests.get(url, headers=headers, stream=True, timeout=30)
            upstream.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"[BiliAPI-Proxy] 请求上游媒体流失败: {str(e)}")
            return Response({'message': f'请求上游媒体流失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        def stream_response():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        response = StreamingHttpResponse(
            stream_response(),
            status=upstream.status_code,
            content_type=upstream.headers.get('Content-Type', 'audio/mp4')
        )

        if 'Content-Length' in upstream.headers:
            response['Content-Length'] = upstream.headers['Content-Length']
        if 'Content-Range' in upstream.headers:
            response['Content-Range'] = upstream.headers['Content-Range']

        response['Accept-Ranges'] = 'bytes'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Expose-Headers'] = 'Content-Range, Accept-Ranges'

        return response