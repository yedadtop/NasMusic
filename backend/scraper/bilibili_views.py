import re
import time
import requests
import socket
import logging
import requests.packages.urllib3.util.connection as urllib3_cn

# --- 配置标准日志 ---
logger = logging.getLogger(__name__)


# 【新增补丁】强制 requests 放弃 IPv6，只使用 IPv4
def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

BILI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://search.bilibili.com/',
}

BILI_QUALITY_MAP = {
    30251: "Hi-Res 无损",
    30250: "杜比全景声",
    30280: "192K 高码率",
    30232: "132K 标准",
    30216: "64K 流畅",
}

MAX_RETRIES = 3
RETRY_DELAY = 1

AUDIO_QUALITY_PRIORITY = {
    30251: 5,  # Hi-Res 无损
    30250: 4,  # 杜比全景声
    30280: 3,  # 192K 高码率
    30232: 2,  # 132K 标准
    30216: 1,  # 64K 流畅
}
# - 默认模式 ( MANUAL_QUALITY_SELECTION = None )：按优先级自动选择最高音质
# - 手动指定模式 ：将 MANUAL_QUALITY_SELECTION = 30216 设置为你要测试的 codec ID
MANUAL_QUALITY_SELECTION = None


def make_bili_request(url, timeout=10, retries=MAX_RETRIES):
    headers = get_bili_headers()
    logger.info(f"[BiliAPI-Request] 发起请求: {url}")

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            # 打印 B 站的业务状态码，方便排查风控
            bili_code = data.get('code')
            bili_msg = data.get('message', '')
            logger.info(
                f"[BiliAPI-Response] 请求成功 (Attempt {attempt + 1}) - B站返回 Code: {bili_code}, Message: '{bili_msg}'")

            return data, None
        except requests.RequestException as e:
            logger.warning(f"[BiliAPI-Error] 请求异常 (Attempt {attempt + 1}/{retries}): {str(e)}")
            # 如果 B 站返回了错误页面（如 403/412），尝试打印前 200 个字符
            if 'response' in locals() and response is not None:
                logger.warning(f"[BiliAPI-Error] 异常响应内容: {response.text[:200]}")

            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None, str(e)
    return None, "最大重试次数已用尽"


def get_bili_headers():
    headers = BILI_HEADERS.copy()
    try:
        from scanner.models import SystemConfig
        # 为了兼容性，配置的 key 依然叫 bilibili_sessdata，但里面可以存整串 Cookie
        sessdata_config = SystemConfig.objects.filter(key='bilibili_sessdata').first()
        if sessdata_config and sessdata_config.value:
            # 清理首尾换行符
            clean_cookie = sessdata_config.value.strip()

            # 【核心修改】智能判断：如果用户填了完整的包含 SESSDATA= 的格式，直接使用
            if 'SESSDATA=' in clean_cookie:
                headers['Cookie'] = clean_cookie
            else:
                # 如果用户只填了纯净的值，帮他补上 SESSDATA=
                headers['Cookie'] = f'SESSDATA={clean_cookie}'

            logger.debug("[BiliAPI-Auth] 已携带 Cookie 发起请求")
        else:
            logger.warning("[BiliAPI-Auth] 警告: 未配置 Cookie，极易触发 B站风控限流！")
    except Exception as e:
        logger.error(f"[BiliAPI-Auth] 获取 Cookie 异常: {e}")
    return headers


class BiliSearchView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        logger.info(f"\n========== 开始 B站搜索: '{keyword}' ==========")

        if not keyword:
            return Response({'message': 'keyword 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        search_url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={requests.utils.quote(keyword)}&page=1&pagesize=20'

        data, error = make_bili_request(search_url)
        if error:
            return Response({'message': f'请求B站搜索接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        # 修复 HTTP 状态码崩溃漏洞：无论 B 站返回什么奇怪的负数 code，统一抛 400 给前端
        if data.get('code') != 0:
            err_msg = data.get("message", "未知错误")
            logger.error(f"[BiliAPI-Search] B站接口拒绝了服务, Code: {data.get('code')}, Message: {err_msg}")
            return Response({'message': f'B站接口返回错误: {err_msg}'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        # 安全获取结果列表
        video_list = data.get('data', {}).get('result') or []

        if not video_list:
            logger.warning(
                f"[BiliAPI-Search] 搜索 '{keyword}' 成功，但 B站返回的结果列表为空。这通常是因为该词触发了风控，或者 Cookie 失效。")

        for item in video_list[:20]:
            bvid = item.get('bvid', '')
            title = re.sub(r'<[^>]+>', '', item.get('title', ''))
            author = item.get('author', '')
            pic = item.get('pic', '')
            duration = item.get('duration', '')

            results.append({
                'bvid': bvid,
                'title': title,
                'author': author,
                'track_cover': pic,
                'duration': duration,
            })

        logger.info(f"[BiliAPI-Search] 搜索结束，成功解析 {len(results)} 条结果。")
        return Response({
            'success': True,
            'keyword': keyword,
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)


class BiliPlayUrlView(APIView):
    def get(self, request):
        bvid = request.query_params.get('bvid', '').strip()
        logger.info(f"\n========== 开始获取播放链接: {bvid} ==========")

        if not bvid:
            return Response({'message': 'bvid 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        pagelist_url = f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}'

        pagelist_data, error = make_bili_request(pagelist_url)
        if error:
            return Response({'message': f'请求B站pagelist接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        if pagelist_data.get('code') != 0:
            err_msg = pagelist_data.get("message", "未知错误")
            logger.error(f"[BiliAPI-Play] 获取分页失败: {err_msg}")
            return Response({'message': f'获取视频分页失败: {err_msg}'}, status=status.HTTP_400_BAD_REQUEST)

        pages = pagelist_data.get('data', [])
        if not pages:
            return Response({'message': '未找到视频分页信息'}, status=status.HTTP_404_NOT_FOUND)

        cid = pages[0].get('cid')
        logger.info(f"[BiliAPI-Play] 成功获取 CID: {cid}")

        playurl_url = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=16&fnver=0&fourk=1'

        playurl_data, error = make_bili_request(playurl_url)
        if error:
            return Response({'message': f'请求B站playurl接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        if playurl_data.get('code') != 0:
            err_msg = playurl_data.get("message", "未知错误")
            logger.error(f"[BiliAPI-Play] 获取播放链接被拒绝: {err_msg}")
            return Response({'message': f'获取播放链接失败: {err_msg}'}, status=status.HTTP_400_BAD_REQUEST)

        dash = playurl_data.get('data', {}).get('dash', {})
        audio_streams = dash.get('audio', [])
        video_streams = dash.get('video', [])

        logger.info(f"[BiliAPI-Play] 解析到音频流: {len(audio_streams)} 条, 视频流: {len(video_streams)} 条")

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

            logger.debug(
                f"[BiliAPI-Play] 检测到音频流 -> codecid={audio_codec}, size={audio_size}, priority={priority}")

            if audio_url and priority > best_priority:
                best_audio = audio
                best_priority = priority
                best_audio_size = audio_size

        if not best_audio:
            for audio in audio_streams:
                audio_url = audio.get('baseUrl') or audio.get('src')
                if audio_url:
                    best_audio = audio
                    audio_size = best_audio.get('size', 0)
                    break

        if not best_audio:
            logger.error(f"[BiliAPI-Play] 致命错误：该视频没有任何可用的音频流 URL")
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

        for video in video_streams:
            video_codec = video.get('codecid') or video.get('id') or 0
            if video_codec == audio_codec:
                quality_desc = video.get('desc', quality_desc)
                break

        return Response({
            'success': True,
            'bvid': bvid,
            'cid': cid,
            'audio_url': audio_url,
            'quality_desc': quality_desc,
            'audio_size': audio_size,
            'audio_codecid': audio_codec,
        }, status=status.HTTP_200_OK)


class BiliProxyStreamView(APIView):
    def get(self, request):
        url = request.query_params.get('url', '').strip()
        if not url:
            return Response({'message': 'url 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if not url.startswith('https://'):
            return Response({'message': '无效的媒体URL'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"[BiliAPI-Proxy] 接收到代理请求, 准备透传。Range: {request.META.get('HTTP_RANGE', '未指定')}")

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
            logger.info(
                f"[BiliAPI-Proxy] 上游连接成功, 状态码: {upstream.status_code}, Content-Length: {upstream.headers.get('Content-Length')}")
        except requests.RequestException as e:
            logger.error(f"[BiliAPI-Proxy] 请求上游媒体流失败: {str(e)}")
            return Response({'message': f'请求上游媒体流失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        def stream_response():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"[BiliAPI-Proxy] 流传输过程中断: {e}")
            finally:
                upstream.close()

        # 1. 核心修复：必须把 B 站的 status_code (206) 透传给前端
        response = StreamingHttpResponse(
            stream_response(),
            status=upstream.status_code,
            content_type=upstream.headers.get('Content-Type', 'audio/mp4')
        )

        # 2. 安全透传 headers：只有当上游真的返回了这些头时，才塞给前端
        if 'Content-Length' in upstream.headers:
            response['Content-Length'] = upstream.headers['Content-Length']

        if 'Content-Range' in upstream.headers:
            response['Content-Range'] = upstream.headers['Content-Range']

        response['Accept-Ranges'] = 'bytes'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Expose-Headers'] = 'Content-Range, Accept-Ranges'

        return response