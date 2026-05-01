import io
import json
import os
import uuid
import hashlib
import time
import shutil
from PIL import Image
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from django.db import models, transaction
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Artist, Album, Track
from .serializers import TrackListSerializer, TrackDetailSerializer, ArtistSerializer, AlbumSerializer
from .utils import sync_cover_to_audio_file
from scanner.models import SystemConfig
from scanner.utils import extract_and_save_thumbnail, parse_artists, _get_tag_value
import mutagen
from pathlib import Path
from scanner.utils import extract_and_save_thumbnail
from mutagen.id3 import USLT



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

        # 【新增】如果没有封面，自动提取音频内嵌封面
        if not track_instance.cover_thumbnail:
            try:
                extract_and_save_thumbnail(track_instance.file_path, track_instance)
            except Exception as e:
                print(f"自动提取封面失败: {e}")

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
            audio_easy = mutagen.File(track_instance.file_path, easy=True)
            if audio_easy is not None:
                audio_easy['title'] = track_instance.title or ''
                audio_easy['artist'] = track_instance.artist.name if track_instance.artist else 'Unknown Artist'
                audio_easy['album'] = track_instance.album.title if track_instance.album else ''
                audio_easy.save()

            audio_raw = mutagen.File(track_instance.file_path)
            if audio_raw is not None and track_instance.lyrics:
                ext = track_instance.format.lower()
                if ext == 'mp3':
                    if getattr(audio_raw, 'tags', None) is None:
                        audio_raw.add_tags()
                    audio_raw.tags.setall("USLT", [USLT(encoding=3, lang='eng', desc='', text=track_instance.lyrics)])
                elif ext in ['flac', 'ogg']:
                    audio_raw["lyrics"] = track_instance.lyrics
                elif ext == 'm4a':
                    audio_raw['\xa9lyr'] = track_instance.lyrics
                audio_raw.save()
        except Exception as e:
            print(f"物理文件标签写入失败: {e}")


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.annotate(
        track_count=models.Count('collaborated_tracks')
    ).filter(track_count__gt=0).prefetch_related('collaborated_tracks__artists', 'collaborated_tracks__album').order_by('-track_count', 'id')

    serializer_class = ArtistSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name']


class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.prefetch_related('tracks__artists', 'artist').all().annotate(
        track_count=models.Count('tracks')
    ).order_by('-track_count', 'id')
    serializer_class = AlbumSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['title', 'artist__name']


def get_upload_temp_dir():
    config = SystemConfig.objects.filter(key='music_path').first()
    if config and config.value:
        temp_dir = os.path.join(config.value, '.upload_temp')
    else:
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', '.upload_temp')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


class ChunkedUploadViewSet(viewsets.ViewSet):
    CHUNK_SIZE = 1024 * 1024

    @action(detail=False, methods=['post'])
    def init(self, request):
        temp_dir = get_upload_temp_dir()
        current_time = time.time()
        for dirname in os.listdir(temp_dir):
            dir_path = os.path.join(temp_dir, dirname)
            if os.path.isdir(dir_path):
                if current_time - os.path.getmtime(dir_path) > 86400:
                    try:
                        shutil.rmtree(dir_path)
                    except Exception:
                        pass

        filename = request.data.get('filename')
        total_chunks = int(request.data.get('total_chunks', 1))
        file_size = int(request.data.get('file_size', 0))
        file_hash = request.data.get('file_hash', '')

        if not filename:
            return Response({'error': 'filename is required'}, status=status.HTTP_400_BAD_REQUEST)

        upload_id = str(uuid.uuid4())
        temp_dir = get_upload_temp_dir()
        upload_dir = os.path.join(temp_dir, upload_id)
        os.makedirs(upload_dir, exist_ok=True)

        metadata = {
            'filename': filename,
            'total_chunks': total_chunks,
            'file_size': file_size,
            'file_hash': file_hash
        }

        metadata_file = os.path.join(upload_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)

        return Response({
            'upload_id': upload_id,
            'chunk_size': self.CHUNK_SIZE
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def upload_chunk(self, request):
        upload_id = request.data.get('upload_id')
        chunk_index = int(request.data.get('chunk_index', 0))
        chunk = request.data.get('chunk')

        if not upload_id or chunk_index < 0 or not chunk:
            return Response({'error': 'upload_id, chunk_index and chunk are required'}, status=status.HTTP_400_BAD_REQUEST)

        temp_dir = get_upload_temp_dir()
        upload_dir = os.path.join(temp_dir, upload_id)
        metadata_file = os.path.join(upload_dir, 'metadata.json')

        if not os.path.exists(metadata_file):
            return Response({'error': 'upload not found or expired'}, status=status.HTTP_404_NOT_FOUND)

        chunk_file = os.path.join(upload_dir, f'chunk_{chunk_index:06d}')
        with open(chunk_file, 'wb') as f:
            for block in chunk.chunks():
                f.write(block)

        uploaded_count = len([name for name in os.listdir(upload_dir) if name.startswith('chunk_')])

        return Response({
            'upload_id': upload_id,
            'chunk_index': chunk_index,
            'uploaded_chunks': uploaded_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def complete(self, request):
        upload_id = request.data.get('upload_id')

        if not upload_id:
            return Response({'error': 'upload_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        temp_dir = get_upload_temp_dir()
        upload_dir = os.path.join(temp_dir, upload_id)
        metadata_file = os.path.join(upload_dir, 'metadata.json')

        if not os.path.exists(metadata_file):
            return Response({'error': 'upload not found or expired'}, status=status.HTTP_404_NOT_FOUND)

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        filename = metadata.get('filename', 'unknown')
        total_chunks = metadata.get('total_chunks', 0)

        uploaded_chunks = [name for name in os.listdir(upload_dir) if name.startswith('chunk_')]
        if len(uploaded_chunks) != total_chunks:
            return Response({
                'error': f'missing chunks, expected {total_chunks}, got {len(uploaded_chunks)}',
                'uploaded_chunks': len(uploaded_chunks)
            }, status=status.HTTP_400_BAD_REQUEST)

        config = SystemConfig.objects.filter(key='music_path').first()
        music_path = config.value if config and config.value else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        safe_filename = get_valid_filename(os.path.basename(filename))
        dest_path = os.path.join(music_path, safe_filename)
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(safe_filename)
            safe_filename = f"{name}_{counter}{ext}"
            dest_path = os.path.join(music_path, safe_filename)
            counter += 1

        try:
            with open(dest_path, 'wb') as dest_file:
                for i in range(total_chunks):
                    chunk_file = os.path.join(upload_dir, f'chunk_{i:06d}')
                    with open(chunk_file, 'rb') as chunk_file_obj:
                        while True:
                            block = chunk_file_obj.read(self.CHUNK_SIZE)
                            if not block:
                                break
                            dest_file.write(block)
        except Exception as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return Response({'error': f'failed to merge chunks: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for i in range(total_chunks):
            chunk_file = os.path.join(upload_dir, f'chunk_{i:06d}')
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        os.remove(metadata_file)
        os.rmdir(upload_dir)

        try:
            audio_easy = mutagen.File(dest_path, easy=True)
            if audio_easy is None:
                audio_easy = mutagen.File(dest_path)

            title = _get_tag_value(audio_easy, 'title', default=Path(filename).stem)
            raw_artist_string = _get_tag_value(audio_easy, 'artist', default='Unknown Artist')
            album_title = _get_tag_value(audio_easy, 'album', default='Unknown Album')
            duration = getattr(audio_easy.info, 'length', 0.0) if hasattr(audio_easy, 'info') else 0.0
            format_str = Path(dest_path).suffix.lower().lstrip('.')

            audio_raw = mutagen.File(dest_path)
            lyrics_text = ''
            if audio_raw and hasattr(audio_raw, 'tags') and audio_raw.tags:
                for key in audio_raw.tags.keys():
                    if key.startswith('USLT'):
                        lyrics_text = audio_raw.tags[key].text
                        break
                if not lyrics_text:
                    if 'lyrics' in audio_raw:
                        lyrics_text = str(audio_raw['lyrics'][0])
                    elif '\xa9lyr' in audio_raw:
                        lyrics_text = str(audio_raw['\xa9lyr'][0])

            primary_artist_obj, _ = Artist.objects.get_or_create(name=raw_artist_string)

            album_obj = Album.objects.filter(title=album_title).first()
            if not album_obj:
                if album_title == 'Unknown Album':
                    unknown_artist, _ = Artist.objects.get_or_create(name='Unknown Artist')
                    album_obj = Album.objects.create(title=album_title, artist=unknown_artist)
                else:
                    album_obj = Album.objects.create(title=album_title, artist=primary_artist_obj)

            track_obj = Track.objects.create(
                title=title,
                artist=primary_artist_obj,
                album=album_obj,
                file_path=dest_path,
                lyrics=lyrics_text,
                duration=duration,
                format=format_str
            )

            artist_names = parse_artists(raw_artist_string)
            all_artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in artist_names]
            track_obj.artists.set(all_artist_objs)
            track_obj.save()

            extract_and_save_thumbnail(dest_path, track_obj)

            return Response({
                'success': True,
                'track_id': track_obj.id,
                'title': title,
                'file_path': dest_path
            }, status=status.HTTP_200_OK)

        except Exception as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return Response({'error': f'failed to process file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'])
    def cancel(self, request):
        upload_id = request.query_params.get('upload_id')

        if not upload_id:
            return Response({'error': 'upload_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        temp_dir = get_upload_temp_dir()
        upload_dir = os.path.join(temp_dir, upload_id)
        metadata_file = os.path.join(upload_dir, 'metadata.json')

        if not os.path.exists(metadata_file):
            return Response({'error': 'upload not found'}, status=status.HTTP_404_NOT_FOUND)

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        total_chunks = metadata.get('total_chunks', 0)
        for i in range(total_chunks):
            chunk_file = os.path.join(upload_dir, f'chunk_{i:06d}')
            if os.path.exists(chunk_file):
                os.remove(chunk_file)

        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        if os.path.exists(upload_dir):
            try:
                os.rmdir(upload_dir)
            except Exception:
                pass

        return Response({'success': True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def status(self, request):
        upload_id = request.query_params.get('upload_id')

        if not upload_id:
            return Response({'error': 'upload_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        temp_dir = get_upload_temp_dir()
        upload_dir = os.path.join(temp_dir, upload_id)
        metadata_file = os.path.join(upload_dir, 'metadata.json')

        if not os.path.exists(metadata_file):
            return Response({'error': 'upload not found'}, status=status.HTTP_404_NOT_FOUND)

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        uploaded_count = len([name for name in os.listdir(upload_dir) if name.startswith('chunk_')])

        return Response({
            'filename': metadata.get('filename'),
            'total_chunks': metadata.get('total_chunks', 0),
            'uploaded_chunks': uploaded_count,
            'file_size': metadata.get('file_size', 0)
        }, status=status.HTTP_200_OK)
