# library/serializers.py
from rest_framework import serializers
from .models import Artist, Album, Track
from scanner.utils import parse_artists

class TrackMinimalSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    all_artists = serializers.SerializerMethodField(read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    track_cover = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Track
        fields = ['id', 'title', 'artist_name', 'all_artists', 'album_title', 'track_cover', 'duration', 'format', 'added_at']

    def get_all_artists(self, obj):
        return [a.name for a in obj.artists.all()]

    def get_track_cover(self, obj):
        if obj.cover_thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_thumbnail.url)
            return obj.cover_thumbnail.url
        return None


class ArtistSerializer(serializers.ModelSerializer):
    track_count = serializers.IntegerField(source='collaborated_tracks.count', read_only=True)
    album_count = serializers.IntegerField(source='albums.count', read_only=True)
    tracks = TrackMinimalSerializer(source='collaborated_tracks', many=True, read_only=True)

    class Meta:
        model = Artist
        fields = ['id', 'name', 'track_count', 'album_count', 'tracks']


class AlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    track_count = serializers.IntegerField(source='tracks.count', read_only=True)
    tracks = TrackMinimalSerializer(many=True, read_only=True)

    class Meta:
        model = Album
        fields = ['id', 'title', 'artist_name', 'track_count', 'tracks']

# --- 核心修复：定义 TrackListSerializer ---
class TrackListSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    all_artists = serializers.SerializerMethodField(read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    track_cover = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Track
        fields = ['id', 'title', 'artist_name', 'all_artists', 'album_title', 'track_cover', 'duration', 'format', 'added_at']

    def get_all_artists(self, obj):
        return [a.name for a in obj.artists.all()]

    def get_track_cover(self, obj):
        if obj.cover_thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_thumbnail.url)
            return obj.cover_thumbnail.url
        return None

# --- 定义 TrackDetailSerializer ---
class TrackDetailSerializer(TrackListSerializer):
    artist_name = serializers.CharField(write_only=True, required=False)
    album_title = serializers.CharField(write_only=True, required=False)
    # 前端传来的这个字段以后可以废弃了，为了不让前端报错先留着定义，但在逻辑里我们会忽略它
    all_artists_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta(TrackListSerializer.Meta):
        fields = TrackListSerializer.Meta.fields + ['lyrics', 'all_artists_names', 'artist_name', 'album_title']

    def update(self, instance, validated_data):
        # 1. 【核心】在修改前，记录下这首歌当前绑定的旧关联 ID [cite: 21]
        old_artist_id = instance.artist.id if instance.artist else None
        old_album_id = instance.album.id if instance.album else None
        # 记录旧的多对多歌手列表 [cite: 21]
        old_m2m_ids = list(instance.artists.values_list('id', flat=True))

        artist_name = validated_data.pop('artist_name', None)
        album_title = validated_data.pop('album_title', None)
        validated_data.pop('all_artists_names', None) # 忽略前端传来的旧数组 [cite: 21]

        # 2. 更新主歌手 [cite: 21]
        if artist_name:
            artist, _ = Artist.objects.get_or_create(name=artist_name)
            instance.artist = artist

        # 3. 更新专辑 [cite: 22]
        if album_title and instance.artist:
            album, _ = Album.objects.get_or_create(title=album_title, artist=instance.artist)
            instance.album = album

        # 4. 更新其他基础字段（歌名、歌词等）并保存 [cite: 22]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save() 

        # 5. 【核心】自动拆分并重新绑定“所有歌手” [cite: 23, 24]
        if instance.artist:
            parsed_names = parse_artists(instance.artist.name)
            if len(parsed_names) > 1:
                artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in parsed_names]
                instance.artists.set(artist_objs)
            else:
                instance.artists.set([instance.artist])

        # 6. 【核心】开始清理被废弃的“孤儿”数据 [cite: 25]
        # A. 先检查并清理旧专辑
        if old_album_id and old_album_id != instance.album_id:
            old_album = Album.objects.filter(id=old_album_id).first()
            # 如果这个旧专辑里已经一首歌都没有了，删掉它
            if old_album and not old_album.tracks.exists():
                old_album.delete()

        # B. 再检查并清理旧歌手（包括主歌手和所有合唱歌手）
        check_artist_ids = set(old_m2m_ids)
        if old_artist_id:
            check_artist_ids.add(old_artist_id)

        for aid in check_artist_ids:
            artist = Artist.objects.filter(id=aid).first()
            if artist:
                # 检查：既没当过主唱，也没当过合唱，名下也没专辑，说明是彻底的废弃名字 [cite: 25]
                if not artist.tracks.exists() and \
                not artist.collaborated_tracks.exists() and \
                not artist.albums.exists():
                    artist.delete()

        return instance