import re
import time
import requests
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


def make_bili_request(url, timeout=10, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=get_bili_headers(), timeout=timeout)
            response.raise_for_status()
            return response.json(), None
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None, str(e)
    return None, "最大重试次数已用尽"


def get_bili_headers():
    headers = BILI_HEADERS.copy()
    try:
        from scanner.models import SystemConfig
        sessdata_config = SystemConfig.objects.filter(key='bilibili_sessdata').first()
        if sessdata_config and sessdata_config.value:
            headers['Cookie'] = f'SESSDATA={sessdata_config.value}'
        else:
            print(f"[BiliAPI] 未配置 SESSDATA，可能触发限流")
    except Exception as e:
        print(f"[BiliAPI] 获取 SESSDATA 失败: {e}")
    return headers


class BiliSearchView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        if not keyword:
            return Response({'message': 'keyword 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        search_url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={requests.utils.quote(keyword)}&page=1&pagesize=20'

        data, error = make_bili_request(search_url)
        if error:
            return Response({'message': f'请求B站搜索接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        if data.get('code') != 0:
            return Response({'message': f'B站接口返回错误: {data.get("message", "未知错误")}'}, status=data.get('code', 400))

        results = []
        video_list = data.get('data', {}).get('result', [])
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

        return Response({
            'success': True,
            'keyword': keyword,
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)


class BiliPlayUrlView(APIView):
    def get(self, request):
        bvid = request.query_params.get('bvid', '').strip()
        if not bvid:
            return Response({'message': 'bvid 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        pagelist_url = f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}'

        pagelist_data, error = make_bili_request(pagelist_url)
        if error:
            return Response({'message': f'请求B站pagelist接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        if pagelist_data.get('code') != 0:
            return Response({'message': f'获取视频分页失败: {pagelist_data.get("message", "未知错误")}'}, status=502)

        pages = pagelist_data.get('data', [])
        if not pages:
            return Response({'message': '未找到视频分页信息'}, status=status.HTTP_404_NOT_FOUND)

        cid = pages[0].get('cid')

        playurl_url = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=16&fnver=0&fourk=1'

        playurl_data, error = make_bili_request(playurl_url)
        if error:
            return Response({'message': f'请求B站playurl接口失败: {error}'}, status=status.HTTP_502_BAD_GATEWAY)

        if playurl_data.get('code') != 0:
            return Response({'message': f'获取播放链接失败: {playurl_data.get("message", "未知错误")}'}, status=502)

        dash = playurl_data.get('data', {}).get('dash', {})
        audio_streams = dash.get('audio', [])
        video_streams = dash.get('video', [])

        print(f"[BiliAPI] 音频流数量: {len(audio_streams)}, 视频流数量: {len(video_streams)}")

        best_audio = None
        best_audio_size = 0
        for audio in audio_streams:
            audio_url = audio.get('baseUrl') or audio.get('src')
            audio_size = audio.get('size', 0)
            audio_codec = audio.get('codecid') or audio.get('id') or 0
            print(f"[BiliAPI] 检查音频流: codecid={audio_codec}, size={audio_size}, url={'有' if audio_url else '无'}")
            if audio_url and audio_size > best_audio_size:
                best_audio = audio
                best_audio_size = audio_size

        if not best_audio:
            for audio in audio_streams:
                audio_url = audio.get('baseUrl') or audio.get('src')
                if audio_url:
                    best_audio = audio
                    break

        if not best_audio:
            return Response({'message': '未找到可用的音频流'}, status=status.HTTP_404_NOT_FOUND)

        audio_url = best_audio.get('baseUrl') or best_audio.get('src')
        audio_codec = best_audio.get('codecid') or best_audio.get('id') or 0
        audio_size = best_audio.get('size', 0)

        quality_desc = BILI_QUALITY_MAP.get(audio_codec, '未知')
        print(f"[BiliAPI] 音频码率: codecid={audio_codec}, 音质={quality_desc}, 大小={audio_size / 1024 / 1024:.2f}MB")

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
            return Response({'message': f'请求上游媒体流失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        def stream_response():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        response = StreamingHttpResponse(stream_response(), content_type='audio/mp4')
        response['Content-Length'] = upstream.headers.get('Content-Length', 0)
        response['Content-Range'] = upstream.headers.get('Content-Range', f'bytes 0-{int(response["Content-Length"]) - 1}/{response["Content-Length"]}')
        response['Accept-Ranges'] = 'bytes'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Expose-Headers'] = 'Content-Range, Accept-Ranges'

        return response
