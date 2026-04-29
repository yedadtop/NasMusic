# library/models.py
import os
from django.db import models, transaction
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver

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
    # 支持多人演唱的多对多关系
    artists = models.ManyToManyField(Artist, related_name='collaborated_tracks', blank=True, verbose_name="所有歌手")
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks', verbose_name="专辑")
    file_path = models.CharField(max_length=1024, unique=True, verbose_name="文件绝对路径")
    lyrics = models.TextField(blank=True, null=True, verbose_name="内嵌歌词")
    cover_thumbnail = models.ImageField(upload_to='covers/tracks/', null=True, blank=True, verbose_name="单曲封面")
    duration = models.FloatField(default=0.0, verbose_name="时长(秒)")
    format = models.CharField(max_length=10, verbose_name="格式")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")

    def save(self, *args, **kwargs):
        # 确保外键对象已持久化，防止 M2M 写入失败
        if self.artist and not self.artist.pk: self.artist.save()
        if self.album and not self.album.pk: self.album.save()
        super().save(*args, **kwargs)

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
    # 1. 物理清理
    for p in [getattr(instance, '_file_to_del', None), getattr(instance, '_thumb_to_del', None)]:
        if p and os.path.isfile(p):
            try: os.remove(p)
            except: pass

    # 2. 数据库清理 (在事务提交后执行，使用 filter 防止报错)
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