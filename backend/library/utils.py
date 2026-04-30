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

        ext = format_str.lower()

        if ext == 'mp3':
            if getattr(audio, 'tags', None):
                for tag in audio.tags:
                    if tag.startswith('APIC'):
                        return True
            return False

        elif ext in ['flac', 'ogg']:
            if hasattr(audio, 'pictures') and audio.pictures:
                return True
            return False

        elif ext == 'm4a':
            if 'covr' in audio:
                return True
            return False

        return False
    except Exception as e:
        print(f"检查封面失败 {file_path}: {e}")
        return False


def sync_cover_to_audio_file(file_path, format_str, image_bytes):
    """
    将图片二进制数据写入物理音频文件 (支持 MP3, FLAC, M4A)
    """
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return

        ext = format_str.lower()

        if ext == 'mp3':
            from mutagen.id3 import APIC
            if not getattr(audio, 'tags', None):
                audio.add_tags()
            # 使用 setall 替换原有的 APIC 封面
            audio.tags.setall("APIC", [APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=image_bytes)])
            audio.save()

        elif ext in ['flac', 'ogg']:
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

        elif ext == 'm4a':
            from mutagen.mp4 import MP4Cover
            audio['covr'] = [MP4Cover(image_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

    except Exception as e:
        print(f"写入封面失败 {file_path}: {e}")