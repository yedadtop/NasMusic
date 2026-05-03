import re
import requests
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

BILI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://search.bilibili.com/',
}


def get_bili_headers():
    headers = BILI_HEADERS.copy()
    try:
        from scanner.models import SystemConfig
        sessdata_config = SystemConfig.objects.filter(key='bilibili_sessdata').first()
        if sessdata_config and sessdata_config.value:
            headers['Cookie'] = f'SESSDATA={sessdata_config.value}'
    except Exception:
        pass
    return headers


class BiliSearchView(APIView):
    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        if not keyword:
            return Response({'message': 'keyword 参数不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        search_url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={requests.utils.quote(keyword)}&page=1&pagesize=20'

        try:
            response = requests.get(search_url, headers=get_bili_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return Response({'message': f'请求B站搜索接口失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

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

        try:
            pagelist_resp = requests.get(pagelist_url, headers=get_bili_headers(), timeout=10)
            pagelist_resp.raise_for_status()
            pagelist_data = pagelist_resp.json()
        except requests.RequestException as e:
            return Response({'message': f'请求B站pagelist接口失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        if pagelist_data.get('code') != 0:
            return Response({'message': f'获取视频分页失败: {pagelist_data.get("message", "未知错误")}'}, status=502)

        pages = pagelist_data.get('data', [])
        if not pages:
            return Response({'message': '未找到视频分页信息'}, status=status.HTTP_404_NOT_FOUND)

        cid = pages[0].get('cid')

        playurl_url = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=16&fnver=0&fourk=1'

        try:
            playurl_resp = requests.get(playurl_url, headers=get_bili_headers(), timeout=10)
            playurl_resp.raise_for_status()
            playurl_data = playurl_resp.json()
        except requests.RequestException as e:
            return Response({'message': f'请求B站playurl接口失败: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        if playurl_data.get('code') != 0:
            return Response({'message': f'获取播放链接失败: {playurl_data.get("message", "未知错误")}'}, status=502)

        dash = playurl_data.get('data', {}).get('dash', {})
        audio_streams = dash.get('audio', [])
        video_streams = dash.get('video', [])

        best_audio = None
        best_audio_size = 0
        for audio in audio_streams:
            audio_url = audio.get('baseUrl') or audio.get('src')
            audio_size = audio.get('size', 0)
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
        audio_codec = best_audio.get('codecid', 0)
        audio_size = best_audio.get('size', 0)

        quality_desc = '未知'
        for video in video_streams:
            if video.get('codecid') == audio_codec:
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
