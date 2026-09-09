# scanner/remux_utils.py
"""
使用 ffmpeg 把 MP4/M4A 文件的 moov atom 移到文件头部。
B 站等下载器给的文件经常是「后缀 mp3 但容器是 M4A + moov 在尾部」，
不重打包的话 HTML5 audio 播放到后半部分会卡住。
"""
import os
import shutil
import struct
import subprocess
import tempfile


def _resolve_ffmpeg_bin():
    """优先使用 PATH 中的 ffmpeg；找不到时回退到 imageio-ffmpeg 包内置的二进制（若已安装）"""
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    return 'ffmpeg'


def mp4_needs_remux(file_path, scan_bytes=4 * 1024 * 1024):
    """
    解析 MP4 顶层 atom 顺序，判断是否需要 remux。返回 True 表示需要 remux：
    - moov 在 mdat 之后（moov 在尾部，播放后半段会卡）
    - 存在 moof/styp 分片标记（fragmented MP4，B站 DASH 音频流即此格式，
      不重打包则 mutagen 读不出时长、无法写入标签）
    限流读前 4MB，对绝大多数歌曲文件足够判断。
    """
    try:
        with open(file_path, 'rb') as f:
            remaining = scan_bytes
            saw_moov = False
            while remaining > 0:
                header = f.read(8)
                if len(header) < 8:
                    break
                size = struct.unpack('>I', header[:4])[0]
                atom_type = header[4:8]

                if size == 0:
                    # 原子延续到文件结尾。还没看到 moov 就在这收尾 → moov 在尾部
                    return not saw_moov
                if size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    size = struct.unpack('>Q', ext)[0]

                if atom_type == b'moov':
                    # 不能立即返回 False：还要继续向后扫描，确认是否存在 moof 分片
                    saw_moov = True
                elif atom_type in (b'moof', b'styp'):
                    # 分片标记：fragmented MP4
                    return True
                elif atom_type == b'mdat' and not saw_moov:
                    # 碰到 mdat 时 moov 还没出现 → moov 在尾部
                    return True

                # 跳过当前原子（已读 8 字节头）
                if size < 8:
                    return not saw_moov
                skip = size - 8
                if skip > remaining - 8:
                    break
                f.seek(skip, 1)
                remaining -= (8 + skip)

        # 扫不到任何典型 atom：当作不需要 remux（让后续流程自己处理）
        return False
    except Exception:
        return False


def remux_audio_file(file_path, ffmpeg_bin=None, timeout=120):
    """
    使用 ffmpeg 原地重打包 MP4/M4A：
    - fragmented MP4 转普通 MP4；-movflags +faststart 把 moov 写到文件开头
    - -c copy：不重新编码，几乎不损音质，速度快
    原子替换原文件。返回 True/False。
    """
    if not os.path.isfile(file_path):
        return False
    if not ffmpeg_bin:
        ffmpeg_bin = _resolve_ffmpeg_bin()

    tmp_dir = os.path.dirname(file_path)
    # 必须保留原扩展名：ffmpeg 依赖输出扩展名推断封装格式，'.tmp' 会导致
    # "Unable to find a suitable output format" 而必然失败
    fd, tmp_path = tempfile.mkstemp(prefix='.remux_', suffix=os.path.splitext(file_path)[1] or '.tmp', dir=tmp_dir)
    os.close(fd)

    try:
        cmd = [
            ffmpeg_bin, '-y', '-loglevel', 'error',
            '-i', file_path,
            '-c', 'copy',
            '-movflags', '+faststart',
            tmp_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"[remux] ffmpeg 失败 {file_path}: {result.stderr.strip()[:300]}")
            return False

        # 原子替换（同目录下 rename 是原子的）
        os.replace(tmp_path, file_path)
        print(f"[remux] 已重打包: {file_path}")
        return True
    except FileNotFoundError:
        print(f"[remux] 未找到 ffmpeg（{ffmpeg_bin}），跳过: {file_path}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[remux] ffmpeg 超时: {file_path}")
        return False
    except Exception as e:
        print(f"[remux] 异常 {file_path}: {e}")
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
