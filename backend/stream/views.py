# stream/views.py
import os
import re
import mimetypes
from django.http import StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404
from library.models import Track

# --- 新增这三行，手动注册容易丢失的音频 MIME 类型 ---
mimetypes.add_type('audio/flac', '.flac')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('audio/ogg', '.ogg')

# 正则表达式，用于解析前端传来的 Range 头，例如 "bytes=32768-65535"
RANGE_RE = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)


def file_iterator(file_path, chunk_size=8192, offset=0, length=None):
    """
    文件生成器：将大文件切分成小块 (chunk) 返回，避免一次性吃满服务器内存。
    """
    with open(file_path, 'rb') as f:
        # 游标移动到前端请求的起始字节
        f.seek(offset, os.SEEK_SET)
        remaining = length
        while remaining > 0:
            # 每次最多只读 chunk_size 大小的数据
            bytes_to_read = min(chunk_size, remaining)
            data = f.read(bytes_to_read)
            if not data:
                break
            remaining -= len(data)
            yield data


def stream_audio(request, track_id):
    """
    处理 HTTP 206 范围请求的音频流视图
    """
    # 1. 从数据库获取歌曲路径
    track = get_object_or_404(Track, id=track_id)
    file_path = track.file_path

    if not os.path.exists(file_path):
        raise Http404("Audio file not found on disk")

    # 2. 获取文件总大小和 MIME 类型 (audio/mpeg, audio/flac 等)
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    # 3. 解析前端发来的 HTTP_RANGE 请求头
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = RANGE_RE.match(range_header)

    if range_match:
        # --- 前端拖拽了进度条，请求 HTTP 206 部分数据 ---
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else file_size - 1

        # 防止越界
        if last_byte >= file_size:
            last_byte = file_size - 1

        if first_byte > last_byte or first_byte >= file_size:
            response = StreamingHttpResponse("Requested Range Not Satisfiable", status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        length = last_byte - first_byte + 1

        # 使用 StreamingHttpResponse 和生成器返回数据
        response = StreamingHttpResponse(
            file_iterator(file_path, offset=first_byte, length=length),
            status=206,  # 核心：HTTP 206 状态码
            content_type=content_type
        )
        # 必须告诉浏览器我们实际返回了哪一段数据
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {first_byte}-{last_byte}/{file_size}'
    else:
        # --- 前端第一次请求（无 Range 头），默认返回 HTTP 200 全量数据 ---
        response = StreamingHttpResponse(
            file_iterator(file_path, length=file_size),
            status=200,
            content_type=content_type
        )
        response['Content-Length'] = str(file_size)

    # 核心：告诉浏览器，这个接口支持按字节 (bytes) 拖拽和切片
    response['Accept-Ranges'] = 'bytes'

    # 允许跨域请求（如果你前端 Vue 是运行在另外的端口上，这句很重要）
    response['Access-Control-Allow-Origin'] = '*'

    return response