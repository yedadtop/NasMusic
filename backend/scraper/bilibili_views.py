import re
import logging
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
import requests

# --- 引入 bilibili-api-python 核心组件 ---
from bilibili_api import search, video, Credential, sync

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


def parse_cookie_string(cookie_str):
    """将拼接的 Cookie 字符串解析为字典，供 Credential 使用"""
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


def get_bili_credential():
    """获取并构造 Bilibili 凭证对象"""
    try:
        from scanner.models import SystemConfig
        sessdata_config = SystemConfig.objects.filter(key='bilibili_sessdata').first()
        if sessdata_config and sessdata_config.value:
            cookie_dict = parse_cookie_string(sessdata_config.value)
            # Credential 需要明确的字段
            return Credential(
                sessdata=cookie_dict.get('SESSDATA', ''),
                bili_jct=cookie_dict.get('bili_jct', ''),
                buvid3=cookie_dict.get('buvid3', ''),
                dedeuserid=cookie_dict.get('DedeUserID', '')
            )
    except Exception as e:
        logger.error(f"[BiliAPI-Auth] 构建凭证异常: {e}")

    logger.warning("[BiliAPI-Auth] 未找到有效的 Cookie，正在使用无登录凭证发起请求！")
    return Credential()


class BiliSearchView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        logger.info(f"\n========== 开始 B站搜索 (bilibili-api): '{keyword}' ==========")

        if not keyword:
            return Response({'message': 'keyword 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        credential = get_bili_credential()

        try:
            # 【核心】使用 bilibili_api 搜索，内置 Wbi 签名和风控处理
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
            # 【核心】构建 Video 对象
            v = video.Video(bvid=bvid, credential=credential)

            # 【核心】获取播放流字典，会自动计算 Wbi 签名获取最新链接
            playurl_data = sync(v.get_download_url(page_index=0))

            dash = playurl_data.get('dash', {})
            audio_streams = dash.get('audio', [])
            video_streams = dash.get('video', [])

            logger.info(f"[BiliAPI-Play] 解析到音频流: {len(audio_streams)} 条")

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
                priority = quality_priority.get(audio_codec, 0)

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

            if audio_size == 0:
                audio_size = best_audio.get('bandwidth', 0)
                if audio_size == 0:
                    audio_size = best_audio.get('length', 0) * 128 / 8

            quality_desc = BILI_QUALITY_MAP.get(audio_codec, '未知')
            logger.info(
                f"[BiliAPI-Play] 🏆 选定最优音频流: Codec={audio_codec} ({quality_desc}), Size={audio_size / 1024 / 1024:.2f}MB")

            return Response({
                'success': True,
                'bvid': bvid,
                'cid': playurl_data.get('last_play_cid', ''),
                'audio_url': audio_url,
                'quality_desc': quality_desc,
                'audio_size': audio_size,
                'audio_codecid': audio_codec,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[BiliAPI-Play] 获取播放链接异常: {str(e)}")
            return Response({'message': f'获取播放链接失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)


class BiliProxyStreamView(APIView):
    def get(self, request):
        """
        这个类保持不动！
        因为 bilibili-api 提取出来的依然是原生的防盗链 URL，
        必须通过这个代理接口拉流才能给前端播放。
        """
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