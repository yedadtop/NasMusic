import io
from PIL import Image
from django.core.files.base import ContentFile
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from .models import Artist, Album, Track
from .serializers import TrackListSerializer, TrackDetailSerializer, ArtistSerializer, AlbumSerializer
from .utils import sync_cover_to_audio_file
import mutagen


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'size'
    max_page_size = 1000


class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.prefetch_related('artists').select_related('artist', 'album').order_by('-added_at')
    serializer_class = TrackListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['title', 'artists__name', 'album__title']

    def get_serializer_class(self):
        if self.action == 'list':
            return TrackListSerializer
        return TrackDetailSerializer

    def perform_update(self, serializer):
        cover_upload = serializer.validated_data.pop('cover_upload', None)
        track_instance = serializer.save()

        if cover_upload:
            try:
                image = Image.open(cover_upload)
                if image.mode != 'RGB': image = image.convert('RGB')
                image.thumbnail((300, 300))
                thumb_io = io.BytesIO()
                image.save(thumb_io, format='JPEG', quality=85)
                image_bytes = thumb_io.getvalue()
                filename = f"track_{track_instance.id}_thumb.jpg"
                track_instance.cover_thumbnail.save(filename, ContentFile(image_bytes), save=True)
                sync_cover_to_audio_file(track_instance.file_path, track_instance.format, image_bytes)
            except Exception as e:
                print(f"API图片上传处理失败: {e}")

        try:
            audio = mutagen.File(track_instance.file_path)
            if audio is not None:
                audio['title'] = track_instance.title
                artist_list = [a.name for a in track_instance.artists.all()]
                if not artist_list and track_instance.artist:
                    artist_list = [track_instance.artist.name]
                elif not artist_list:
                    artist_list = ["Unknown Artist"]
                audio['artist'] = " / ".join(artist_list)
                audio['album'] = track_instance.album.title

                if track_instance.lyrics is not None:
                    ext = track_instance.format.lower()
                    lyrics_text = track_instance.lyrics
                    if ext == 'mp3':
                        from mutagen.id3 import USLT
                        if not audio.tags: audio.add_tags()
                        audio.tags.setall("USLT", [USLT(encoding=3, lang='eng', desc='', text=lyrics_text)])
                    elif ext in ['flac', 'ogg']:
                        audio["lyrics"] = lyrics_text
                    elif ext == 'm4a':
                        audio['\xa9lyr'] = lyrics_text

                audio.save()
        except Exception as e:
            print(f"物理文件标签写入失败: {e}")


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.prefetch_related('tracks__artists', 'tracks__album').all().order_by('id')
    serializer_class = ArtistSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name']


class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.prefetch_related('tracks__artists', 'artist').all().order_by('id')
    serializer_class = AlbumSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['title', 'artist__name']
