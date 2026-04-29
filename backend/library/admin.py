import io
import re
from PIL import Image
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Artist, Album, Track
from .utils import sync_cover_to_audio_file
import mutagen


def parse_artists(artist_string):
    """拆分多歌手字符串"""
    if not artist_string:
        return ["Unknown Artist"]
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', artist_string))
    if has_chinese:
        pattern = r'[\s/,&\-　\xA0]+|\s+(?:feat\.|ft\.)+\s*|(?<=\S)\s*-\s+(?=\S)'
    else:
        pattern = r'[/,&\-]|\s+(?:feat\.|ft\.)+\s*|(?<=\S)\s*-\s+(?=\S)'
    parts = re.split(pattern, artist_string, flags=re.IGNORECASE)
    artists = [p.strip() for p in parts if p.strip()]
    return artists if artists else ["Unknown Artist"]


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist')
    search_fields = ('title', 'artist__name')
    autocomplete_fields = ('artist',)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'display_all_artists', 'artist', 'album', 'format')
    list_filter = ('format', 'artist')
    search_fields = ('title', 'artist__name', 'album__title', 'artists__name')

    fields = ('title', 'artist', 'artists', 'album', 'cover_preview', 'cover_thumbnail', 'lyrics', 'file_path', 'duration',
              'format')

    readonly_fields = ('cover_preview', 'file_path', 'duration', 'format')
    autocomplete_fields = ('artist', 'album', 'artists')

    def display_all_artists(self, obj):
        return ', '.join([a.name for a in obj.artists.all()])
    display_all_artists.short_description = "所有歌手"

    def cover_preview(self, obj):
        """
        自定义方法：在后台渲染图片预览
        """
        if obj.cover_thumbnail:
            # 使用 mark_safe 告诉 Django 信任这段 HTML 并在页面上渲染
            return mark_safe(
                f'<img src="{obj.cover_thumbnail.url}" '
                f'style="max-width: 200px; max-height: 200px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); object-fit: cover;" />'
            )
        return "暂无封面"

    # 设置这个字段在后台显示的名称
    cover_preview.short_description = "封面预览"

    def save_model(self, request, obj, form, change):
        raw_artist_name = obj.artist.name if obj.artist else "Unknown Artist"
        parsed = parse_artists(raw_artist_name)

        if len(parsed) > 1:
            primary_name = parsed[0]
            primary_artist, _ = Artist.objects.get_or_create(name=primary_name)
            obj.artist = primary_artist

        super().save_model(request, obj, form, change)

        if len(parsed) > 1:
            artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in parsed]
            obj.artists.clear()
            obj.artists.add(*artist_objs)

        # 1. 处理单曲封面图片的上传与同步
        if 'cover_thumbnail' in form.changed_data and obj.cover_thumbnail:
            try:
                # 压缩图片为 300x300
                image = Image.open(obj.cover_thumbnail.path)
                if image.mode != 'RGB': image = image.convert('RGB')
                image.thumbnail((300, 300))
                thumb_io = io.BytesIO()
                image.save(thumb_io, format='JPEG', quality=85)
                image_bytes = thumb_io.getvalue()

                # 覆盖保存缩略图回硬盘
                with open(obj.cover_thumbnail.path, 'wb') as f:
                    f.write(image_bytes)

                # 将图片写入物理音频文件
                sync_cover_to_audio_file(obj.file_path, obj.format, image_bytes)
                self.message_user(request, "✅ 单曲专属封面已成功写入音频文件！", level='SUCCESS')
            except Exception as e:
                self.message_user(request, f"❌ 封面写入物理文件失败: {e}", level='ERROR')

        # 2. 同步写入文本标签 (歌名、歌手、专辑、歌词)
        try:
            audio_easy = mutagen.File(obj.file_path, easy=True)
            if audio_easy is not None:
                audio_easy['title'] = obj.title
                audio_easy['artist'] = obj.artist.name
                audio_easy['album'] = obj.album.title
                audio_easy.save()

            audio_raw = mutagen.File(obj.file_path)
            if audio_raw is not None:
                lyrics_text = obj.lyrics or ""
                ext = obj.format.lower()

                if ext == 'mp3':
                    from mutagen.id3 import USLT
                    if not audio_raw.tags: audio_raw.add_tags()
                    audio_raw.tags.setall("USLT", [USLT(encoding=3, lang='eng', desc='', text=lyrics_text)])
                    audio_raw.save()
                elif ext in ['flac', 'ogg']:
                    audio_raw["lyrics"] = lyrics_text
                    audio_raw.save()
                elif ext == 'm4a':
                    audio_raw['\xa9lyr'] = lyrics_text
                    audio_raw.save()
        except Exception as e:
            self.message_user(request, f"物理文件标签写入失败: {e}", level='ERROR')