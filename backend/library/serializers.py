# library/serializers.py
from rest_framework import serializers
from .models import Artist, Album, Track


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
    all_artists_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta(TrackListSerializer.Meta):
        fields = TrackListSerializer.Meta.fields + ['lyrics', 'all_artists_names']

    def update(self, instance, validated_data):
        artist_name = validated_data.pop('artist_name', None)
        album_title = validated_data.pop('album_title', None)
        all_artists_names = validated_data.pop('all_artists_names', None)

        if artist_name:
            artist, _ = Artist.objects.get_or_create(name=artist_name)
            instance.artist = artist
            if all_artists_names is None:
                current_artists = set(instance.artists.values_list('name', flat=True))
                if artist_name not in current_artists:
                    instance.artists.add(artist)

        if album_title and instance.artist:
            album, _ = Album.objects.get_or_create(title=album_title, artist=instance.artist)
            instance.album = album

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if all_artists_names is not None:
            artist_names_set = set(all_artists_names)
            existing_artists = Artist.objects.filter(name__in=artist_names_set)
            existing_names = set(existing_artists.values_list('name', flat=True))
            missing_names = artist_names_set - existing_names
            for name in missing_names:
                Artist.objects.get_or_create(name=name)
            new_arts = list(Artist.objects.filter(name__in=artist_names_set))
            instance.artists.set(new_arts)
            if instance.artist and instance.artist not in new_arts:
                instance.artists.add(instance.artist)

        return instance