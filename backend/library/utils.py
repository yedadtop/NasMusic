# library/utils.py
import mutagen


def has_embedded_cover(file_path, format_str):
    """
    检查物理音频文件是否已嵌入封面图片
    返回: True 表示已有封面, False 表示没有封面
    """
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return False

        # 按 mutagen 实际加载出来的对象类型判断，避开「后缀是 mp3 但内容是 m4a」的情况
        if isinstance(audio, mutagen.mp4.MP4):
            return 'covr' in audio and bool(audio['covr'])

        if hasattr(audio, 'pictures') and audio.pictures:
            return True

        tags = getattr(audio, 'tags', None)
        if tags is not None:
            for tag in tags:
                if tag.startswith('APIC'):
                    return True

        return False
    except Exception as e:
        print(f"检查封面失败 {file_path}: {e}")
        return False


def sync_cover_to_audio_file(file_path, format_str, image_bytes):
    """
    将图片二进制数据写入物理音频文件 (支持 MP3, FLAC, M4A)
    按 mutagen 实际加载的对象类型分支，避开后缀和内容不匹配的情况
    """
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return

        # 1) MP4 / M4A 容器：写到 covr
        if isinstance(audio, mutagen.mp4.MP4):
            from mutagen.mp4 import MP4Cover
            audio['covr'] = [MP4Cover(image_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
            return

        # 2) FLAC / OGG（带 pictures 的容器）
        if hasattr(audio, 'add_picture'):
            from mutagen.flac import Picture
            pic = Picture()
            pic.type = 3
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            pic.data = image_bytes
            if hasattr(audio, 'clear_pictures'):
                audio.clear_pictures()
            audio.add_picture(pic)
            audio.save()
            return

        # 3) MP3（ID3）
        tags = getattr(audio, 'tags', None)
        if tags is None:
            audio.add_tags()
            tags = audio.tags
        if tags is not None and hasattr(tags, 'setall'):
            from mutagen.id3 import APIC
            tags.setall("APIC", [APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=image_bytes)])
            audio.save()
            return

        print(f"写入封面失败 {file_path}: 未识别的音频类型 ({type(audio).__name__})")
    except Exception as e:
        print(f"写入封面失败 {file_path}: {e}")