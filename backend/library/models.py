# library/models.py
import os
import time
import threading
import uuid
import shutil
from datetime import datetime
from django.db import models, transaction
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from scanner.models import SystemConfig

def _async_move(src, dst, max_retries=30, retry_delay=2.0):
    """后台守护线程：异步重试移动文件到回收站"""
    for attempt in range(max_retries):
        try:
            shutil.move(src, dst)
            print(f"✅ 文件已移动到回收站（后台重试成功）: {dst}")
            return
        except OSError:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
    print(f"⚠️ 文件移动到回收站失败，已放弃: {src}")

def get_music_path():
    config = SystemConfig.objects.filter(key='music_path').first()
    if config and config.value:
        return os.path.normpath(config.value)
    return None

def move_to_trash(file_path):
    """将文件移动到音乐库根目录下的 .trash 文件夹"""
    if not file_path or not os.path.isfile(file_path):
        return
    
    music_path = get_music_path()
    if not music_path:
        print(f"⚠️ 无法获取音乐库路径，文件 {file_path} 无法移动到回收站")
        return
    
    file_dir = os.path.dirname(os.path.normpath(file_path))
    if not file_dir.startswith(music_path):
        print(f"⚠️ 文件不在音乐库目录内: {file_path}")
        return
    
    trash_dir = os.path.join(music_path, '.trash')
    os.makedirs(trash_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    trash_path = os.path.join(trash_dir, filename)

    if os.path.exists(trash_path):
        base, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:6]
        trash_path = os.path.join(trash_dir, f"{base}_{timestamp}_{unique_id}{ext}")

    try:
        shutil.move(file_path, trash_path)
        print(f"✅ 文件已移动到回收站: {trash_path}")
    except OSError:
        print(f"⚠️ 文件正在被占用，已启动后台守护线程")
        threading.Thread(target=_async_move, args=(file_path, trash_path), daemon=True).start()

class Artist(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="歌手名")
    def __str__(self): return self.name

class Album(models.Model):
    title = models.CharField(max_length=255, verbose_name="专辑名")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums', verbose_name="所属歌手")
    def __str__(self): return self.title

class Track(models.Model):
    title = models.CharField(max_length=255, verbose_name="歌曲名")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='tracks', verbose_name="主歌手")
    artists = models.ManyToManyField(Artist, related_name='collaborated_tracks', blank=True, verbose_name="所有歌手")
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks', verbose_name="专辑")
    file_path = models.CharField(max_length=1024, unique=True, verbose_name="文件绝对路径")
    lyrics = models.TextField(blank=True, null=True, verbose_name="内嵌歌词")
    cover_thumbnail = models.ImageField(upload_to='covers/tracks/', null=True, blank=True, verbose_name="单曲封面")
    duration = models.FloatField(default=0.0, verbose_name="时长(秒)")
    format = models.CharField(max_length=10, verbose_name="格式")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")

    def save(self, *args, **kwargs):
        if self.artist and not self.artist.pk: self.artist.save()
        if self.album and not self.album.pk: self.album.save()

        if self.pk:
            try:
                old_track = Track.objects.get(pk=self.pk)
                old_cover = old_track.cover_thumbnail
                new_cover = self.cover_thumbnail

                old_cover_cleared = old_cover and not new_cover
                old_cover_replaced = old_cover and new_cover and new_cover != old_cover
                if old_cover_cleared or old_cover_replaced:
                    old_cover_path = old_cover.path
                    self._old_cover_path_to_delete = old_cover_path
            except Track.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if getattr(self, '_old_cover_path_to_delete', None):
            old_path = self._old_cover_path_to_delete
            if old_path and os.path.isfile(old_path):
                os.remove(old_path)
                print(f"✅ 已删除孤立的封面文件: {old_path}")
            del self._old_cover_path_to_delete

# --- 安全的清理信号逻辑 ---
@receiver(pre_delete, sender=Track)
def store_ids_before_delete(sender, instance, **kwargs):
    """保存 ID 而非对象引用，彻底规避级联删除导致的 RelatedObjectDoesNotExist 错误"""
    instance._saved_artist_id = instance.artist_id
    instance._saved_album_id = instance.album_id
    instance._saved_collab_ids = list(instance.artists.values_list('id', flat=True))
    instance._file_to_del = instance.file_path
    instance._thumb_to_del = instance.cover_thumbnail.path if instance.cover_thumbnail else None

@receiver(post_delete, sender=Track)
def cleanup_after_track_delete(sender, instance, **kwargs):
    skip_physical = getattr(instance, '_skip_physical_delete', False)

    if not skip_physical:
        file_path = getattr(instance, '_file_to_del', None)
        if file_path:
            move_to_trash(file_path)

        thumb_path = getattr(instance, '_thumb_to_del', None)
        if thumb_path and os.path.isfile(thumb_path):
            os.remove(thumb_path)

    # 数据库清理 (在事务提交后执行，使用 filter 防止报错)
    def do_cleanup():
        # 清理专辑
        a_id = getattr(instance, '_saved_album_id', None)
        if a_id:
            album = Album.objects.filter(id=a_id).first()
            if album and not album.tracks.exists(): album.delete()

        # 清理歌手组
        art_ids = {getattr(instance, '_saved_artist_id', None)} | set(getattr(instance, '_saved_collab_ids', []))
        for aid in art_ids:
            if not aid: continue
            artist = Artist.objects.filter(id=aid).first()
            if artist and not artist.tracks.exists() and not artist.collaborated_tracks.exists():
                artist.delete()

    transaction.on_commit(do_cleanup)