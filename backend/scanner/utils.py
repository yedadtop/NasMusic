# scanner/utils.py
import os
import io
import re
import mutagen
from pathlib import Path
from PIL import Image
from django.core.files.base import ContentFile
from library.models import Artist, Album, Track

SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.m4a'}

def parse_artists(artist_string):
    """
    拆分多歌手字符串，增强版
    """
    if not artist_string:
        return ["Unknown Artist"]

    # 扩大亚洲字符检测范围：涵盖中文、日文平假/片假名、韩文
    has_asian = bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', artist_string))

    if has_asian:
        # 新增涵盖了：顿号(、)、间隔号(·)、全角/半角分号(; ；)、竖线(|)、加号(+)、下划线(_)
        pattern = (
            r'[\s/,&\-　\xA0、·・;；|+_]+'
            r'|\s+(?:feat\.|ft\.)+\s*'                   
            r'|(?<=\S)\s*-\s+(?=\S)'
        )
    else:
        pattern = (
            r'[/,&\-、·・;；|+_]+'
            r'|\s+(?:feat\.|ft\.)+\s*'
            r'|(?<=\S)\s*-\s+(?=\S)'
        )

    parts = re.split(pattern, artist_string, flags=re.IGNORECASE)
    
    artists = []
    for part in parts:
        cleaned = part.strip()
        if cleaned:
            artists.append(cleaned)

    return artists if artists else ["Unknown Artist"]

def _get_tag_value(tags, key, default="Unknown"):
    if not tags or key not in tags: return default
    value = tags[key]
    # 【核心修复】：如果 mutagen 解析出的是列表 (常见于 FLAC/APE)，
    # 先用 '/' 拼接成字符串，再交由 parse_artists 统一且彻底地进行拆分
    if isinstance(value, list):
        return " / ".join(str(v) for v in value)
    return value

def _get_lyrics(audio):
    try:
        if audio is None: return ""
        if hasattr(audio, 'tags') and audio.tags:
            for key in audio.tags.keys():
                if key.startswith('USLT'): return audio.tags[key].text
        if 'lyrics' in audio: return audio['lyrics'][0]
        if '\xa9lyr' in audio: return audio['\xa9lyr'][0]
    except Exception: pass
    return ""


def extract_and_save_thumbnail(file_path, track_obj):
    """从音频文件提取封面并保存到 Track 模型 (带防丢图机制)"""

    # 1. 防御性检查：不仅查数据库，还要查物理文件是否真的存在
    if track_obj.cover_thumbnail:
        try:
            if os.path.isfile(track_obj.cover_thumbnail.path):
                return  # 只有当物理图片真的在硬盘上时，才跳过提取
        except ValueError:
            pass  # 如果触发异常，说明路径无效，继续往下执行提取逻辑

    try:
        audio = mutagen.File(file_path)
        if audio is None: return
        picture_data = None

        # 寻找内嵌封面数据
        if hasattr(audio, 'tags') and audio.tags:
            for tag_key in audio.tags.keys():
                if tag_key.startswith('APIC'):
                    picture_data = audio.tags[tag_key].data
                    break
        elif hasattr(audio, 'pictures') and audio.pictures:
            picture_data = audio.pictures[0].data
        elif 'covr' in audio:
            picture_data = bytes(audio['covr'][0])

        # 如果找到了图片，压缩并保存
        if picture_data:
            image = Image.open(io.BytesIO(picture_data))
            if image.mode != 'RGB': image = image.convert('RGB')
            image.thumbnail((300, 300))
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)

            filename = f"track_{track_obj.id}_thumb.jpg"
            track_obj.cover_thumbnail.save(filename, ContentFile(thumb_io.getvalue()), save=True)
            print(f"  📸 成功提取并保存封面: {filename}")
        else:
            print(f"  ⚪ 文件本身无内嵌图片: {file_path}")

    except Exception as e:
        # 暴露出真实的错误信息，不要再用 pass 掩盖了！
        print(f"  ⚠️ 提取封面失败 {file_path}: {str(e)}")


def scan_local_directory(directory_path, task_id=None):
    task = None
    if task_id:
        from .models import ScanTask 
        task = ScanTask.objects.filter(id=task_id).first()

    if not os.path.exists(directory_path):
        if task:
            task.status = 'error'
            task.error_message = f"目录 {directory_path} 不存在"
            task.save()
        return

    if task:
        task.status = 'running'
        task.save()

    # 1. 预扫描：统计总共有多少个支持的音频文件 (分母)
    valid_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if Path(file).suffix.lower() in SUPPORTED_FORMATS:
                valid_files.append(os.path.join(root, file))
                
    # ================= 同步删除逻辑 =================
    # 获取数据库中属于该扫描目录，但在物理硬盘上已不存在的歌曲
    valid_files_set = set(valid_files)
    obsolete_tracks = Track.objects.filter(file_path__startswith=directory_path).exclude(file_path__in=valid_files_set)
    deleted_count = obsolete_tracks.count()
    
    # 逐个调用 delete() 以确保触发 pre_delete/post_delete 信号，清理孤儿数据
    for t in obsolete_tracks:
        t.delete()
    # ========================================================

    if task:
        task.total_files = len(valid_files)
        task.deleted_count = deleted_count
        task.save()

    added_count = 0
    updated_count = 0

    # 2. 正式开始逐个扫描 (分子)
    for index, file_path in enumerate(valid_files):
        if task:
            task.processed_files = index + 1
            task.current_file = file_path
            if index % 5 == 0 or index == len(valid_files) - 1:
                task.save()

        try:
            audio_easy = mutagen.File(file_path, easy=True)
            if audio_easy is None: continue

            title = _get_tag_value(audio_easy, 'title', default=Path(file_path).stem)
            
            # 【核心】：先获取完整未拆分的原始字符串作为主歌手
            raw_artist_string = _get_tag_value(audio_easy, 'artist', default="Unknown Artist")
            # 提取拆分后的列表用于 M2M 字段
            artist_names = parse_artists(raw_artist_string)  

            album_title = _get_tag_value(audio_easy, 'album', default="Unknown Album")
            duration = getattr(audio_easy.info, 'length', 0.0)

            # 主歌手直接使用未拆分的原始字符串，保留原貌
            primary_artist_obj, _ = Artist.objects.get_or_create(name=raw_artist_string)

            # 【核心】：专辑去重逻辑。只认名字，不绑定具体的歌手！
            album_obj = Album.objects.filter(title=album_title).first()
            if not album_obj:
                # 只有当这是一个从未见过的新专辑时，才顺手把当前主歌手挂上去
                if album_title == "Unknown Album":
                    unknown_artist, _ = Artist.objects.get_or_create(name="Unknown Artist")
                    album_obj = Album.objects.create(title=album_title, artist=unknown_artist)
                else:
                    album_obj = Album.objects.create(title=album_title, artist=primary_artist_obj)

            audio_raw = mutagen.File(file_path)
            lyrics_text = _get_lyrics(audio_raw)

            # 更新或创建歌曲
            track_obj, created = Track.objects.update_or_create(
                file_path=file_path,
                defaults={
                    'title': title, 'artist': primary_artist_obj, 'album': album_obj,
                    'lyrics': lyrics_text, 'duration': duration, 'format': Path(file_path).suffix.lower().lstrip('.'),
                }
            )

            # 把拆分后的独立歌手写入“所有歌手”(多对多) 字段
            all_artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in artist_names]
            track_obj.artists.set(all_artist_objs)
            track_obj.save()

            extract_and_save_thumbnail(file_path, track_obj)

            if created: added_count += 1
            else: updated_count += 1

        except Exception as e:
            print(f"解析失败 {file_path}: {str(e)}")

    # 3. 扫描结束，标记任务完成
    if task:
        task.status = 'completed'
        task.added_count = added_count
        task.updated_count = updated_count
        task.current_file = '扫描完成'
        task.save()