# stream/views.py
import os
import re
import mimetypes
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404
from library.models import Track
from scanner.models import SystemConfig

# 补充音频 MIME 类型
mimetypes.add_type('audio/flac', '.flac')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('audio/ogg', '.ogg')

# 正则表达式，用于解析前端传来的 Range 头
RANGE_RE = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)

def file_iterator(file_path, chunk_size=8192, offset=0, length=None):
    """文件分块生成器"""
    with open(file_path, 'rb') as f:
        f.seek(offset, os.SEEK_SET)
        remaining = length
        while remaining > 0:
            bytes_to_read = min(chunk_size, remaining)
            data = f.read(bytes_to_read)
            if not data:
                break
            remaining -= len(data)
            yield data


def stream_audio(request, track_id):
    """
    智能音频流视图：
    - DEBUG=False (生产环境): X-Accel-Redirect 交给 Nginx，解决假死。
    - DEBUG=True  (本地开发): 恢复手动 Range 解析，完美支持前端拖拽测试。
    """
    track = get_object_or_404(Track, id=track_id)
    file_path = track.file_path

    if not os.path.exists(file_path):
        raise Http404("Audio file not found on disk")

    # ==========================================
    # 场景一：生产环境 -> 高性能 Nginx 代理
    # ==========================================
    if not settings.DEBUG:
        response = HttpResponse()
        
        config = SystemConfig.objects.filter(key='music_path').first()
        music_root = config.value if config and config.value else ''
        
        if music_root and file_path.startswith(music_root):
            rel_path = os.path.relpath(file_path, music_root).replace('\\', '/')
            internal_path = f"/protected_music/{rel_path}"
        else:
            internal_path = f"/protected_music/{os.path.basename(file_path)}"

        response['X-Accel-Redirect'] = internal_path.encode('utf-8')
        response['Content-Type'] = '' 
        response['Access-Control-Allow-Origin'] = '*'
        return response

    # ==========================================
    # 场景二：本地开发 -> 恢复原生的 HTTP 206 断点续传逻辑
    # ==========================================
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = RANGE_RE.match(range_header)

    if range_match:
        # 处理前端拖拽进度条 (返回 206 Partial Content)
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else file_size - 1

        if last_byte >= file_size:
            last_byte = file_size - 1

        if first_byte > last_byte or first_byte >= file_size:
            response = StreamingHttpResponse("Requested Range Not Satisfiable", status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        length = last_byte - first_byte + 1
        response = StreamingHttpResponse(
            file_iterator(file_path, offset=first_byte, length=length),
            status=206,
            content_type=content_type
        )
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {first_byte}-{last_byte}/{file_size}'
    else:
        # 处理首次加载 (返回 200 OK)
        response = StreamingHttpResponse(
            file_iterator(file_path, length=file_size),
            status=200,
            content_type=content_type
        )
        response['Content-Length'] = str(file_size)

    response['Accept-Ranges'] = 'bytes'
    response['Access-Control-Allow-Origin'] = '*'
    return response