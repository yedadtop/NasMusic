# scanner/utils.py
import os
import io
import re
import mutagen
from pathlib import Path
from PIL import Image
from django.core.files.base import ContentFile
from django.db.models.signals import pre_delete, post_delete
from library.models import Artist, Album, Track
from library.models import store_ids_before_delete, cleanup_after_track_delete
from scanner.models import SystemConfig

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
    # 统一格式化路径，避免斜杠差异
    norm_directory_path = os.path.normpath(directory_path)
    valid_files = []
    for root, dirs, files in os.walk(norm_directory_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if Path(file).suffix.lower() in SUPPORTED_FORMATS:
                valid_files.append(os.path.normpath(os.path.join(root, file)))

    # ================= 判断是增量扫描还是全量扫描 =================
    config_music_path = SystemConfig.objects.filter(key='music_path').first()
    config_path = config_music_path.value if config_music_path else None

    # 使用 normpath 统一路径格式，避免 / 与 \ 的差异
    norm_config_path = os.path.normpath(config_path) if config_path else None

    # 检查数据库中是否有歌曲，以及现有歌曲是否在当前扫描目录下
    # 【修复2】首个文件路径格式化：必须先对 db_track.file_path 做 normpath
    db_track = Track.objects.first()
    db_track_in_current_dir = False
    if db_track and db_track.file_path:
        norm_db_file_path = os.path.normpath(db_track.file_path)
        db_track_dir = os.path.dirname(norm_db_file_path)
        db_track_in_current_dir = db_track_dir.startswith(norm_directory_path)

    # 路径变化：当配置路径与当前扫描路径不同，或数据库中的歌曲不在当前目录下时
    is_path_changed = (norm_config_path != norm_directory_path) or \
                      (Track.objects.exists() and not db_track_in_current_dir)

    if is_path_changed:
        # 路径变化：全量清空数据库，重新提取
        print(f"  🔄 扫描路径已变化 ({config_path} → {directory_path})，执行全量扫描")

        # 清理封面缩略图物理文件
        for t in Track.objects.exclude(cover_thumbnail='').iterator():
            try:
                if t.cover_thumbnail and os.path.isfile(t.cover_thumbnail.path):
                    os.remove(t.cover_thumbnail.path)
            except Exception:
                pass

        pre_delete.disconnect(store_ids_before_delete, sender=Track)
        post_delete.disconnect(cleanup_after_track_delete, sender=Track)

        deleted_count = Track.objects.count()
        Track.objects.all().delete()
        Album.objects.all().delete()
        Artist.objects.all().delete()

        pre_delete.connect(store_ids_before_delete, sender=Track)
        post_delete.connect(cleanup_after_track_delete, sender=Track)

        # 更新配置路径为当前扫描路径
        SystemConfig.objects.update_or_create(
            key='music_path',
            defaults={'value': directory_path, 'description': '音乐文件路径'}
        )
    else:
        # 路径未变化：增量扫描
        print(f"  ➕ 增量扫描模式")

        # 【修复3】幽灵文件内存级比对：弃用存在斜杠陷阱的 Django ORM 查询
        # 改为获取所有 Track 记录，在 Python 内存中用 normpath 比对
        valid_files_set = set(valid_files)
        ghost_tracks = []
        for t in Track.objects.all():
            norm_file_path = os.path.normpath(t.file_path)
            if norm_file_path not in valid_files_set:
                ghost_tracks.append(t)
        deleted_count = len(ghost_tracks)

        if ghost_tracks:
            print(f"  👻 发现 {deleted_count} 首幽灵歌曲，开始清理...")
            for t in ghost_tracks:
                t._skip_physical_delete = True  # 跳过物理文件删除
                t.delete()
    # =================================================================

    if task:
        task.total_files = len(valid_files)
        task.deleted_count = deleted_count
        task.save()

    added_count = 0
    updated_count = 0

    # 【修复4】跳过机制集合格式化：将查出的每条历史路径都经过 normpath 处理后再放入 set
    existing_paths = set(os.path.normpath(p) for p in Track.objects.values_list('file_path', flat=True)) if not is_path_changed else set()

    # 2. 正式开始逐个扫描 (分子)
    for index, file_path in enumerate(valid_files):
        if task:
            task.processed_files = index + 1
            task.current_file = file_path
            if index % 5 == 0 or index == len(valid_files) - 1:
                task.save()

        # 增量扫描模式下，跳过已存在的歌曲
        if not is_path_changed and os.path.normpath(file_path) in existing_paths:
            continue

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