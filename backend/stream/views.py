# stream/views.py
import os
import re
import mimetypes
from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404
from library.models import Track
from scanner.models import SystemConfig

# 补充音频 MIME 类型
mimetypes.add_type('audio/flac', '.flac')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('audio/ogg', '.ogg')

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
    track = get_object_or_404(Track, id=track_id)
    file_path = track.file_path

    if not os.path.exists(file_path):
        raise Http404("Audio file not found on disk")

    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    is_nginx_proxy = x_real_ip is not None

    # 打印醒目的分割线和证明信息到后台日志
    print("\n" + "="*50)
    print(f"[NasMusic 代理追踪] 🎵 正在请求歌曲 ID: {track_id}")
    print(f"[NasMusic 代理追踪] 🌐 访客 X-Real-IP: {x_real_ip if x_real_ip else '无 (非 Nginx 转发)'}")
    print(f"[NasMusic 代理追踪] 🛠️ Nginx 代理状态: {'✅ 已接管' if is_nginx_proxy else '❌ 未接管 (直连/开发模式)'}")

    if is_nginx_proxy or not settings.DEBUG:
        response = HttpResponse()
        
        config = SystemConfig.objects.filter(key='music_path').first()
        music_root = config.value if config and config.value else ''
        
        if music_root and file_path.startswith(music_root):
            rel_path = os.path.relpath(file_path, music_root).replace('\\', '/')
            internal_path = f"/protected_music/{rel_path}"
        else:
            raise Http404("Audio file is outside of the managed music library")

        # 修复中文路径 Bug
        internal_path_safe = quote(internal_path, safe='/')

        response['X-Accel-Redirect'] = internal_path_safe
        response['Content-Type'] = '' 
        response['Access-Control-Allow-Origin'] = '*'

        # 打印最终下发给 Nginx 的指令
        print(f"[NasMusic 代理追踪] 🚀 下发 X-Accel-Redirect 指令: {internal_path_safe}")
        print("="*50 + "\n")
        
        return response


    print("[NasMusic 代理追踪] ⚠️ 降级为 Django 原生处理文件流 (耗费性能)")
    print("="*50 + "\n")
    
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = RANGE_RE.match(range_header)

    if range_match:
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
        response = StreamingHttpResponse(
            file_iterator(file_path, length=file_size),
            status=200,
            content_type=content_type
        )
        response['Content-Length'] = str(file_size)

    response['Accept-Ranges'] = 'bytes'
    response['Access-Control-Allow-Origin'] = '*'
    return response