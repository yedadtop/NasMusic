"""
数据库清理脚本：合并重复的 Unknown Album
用法：python cleanup_db.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NasMusic.settings')
django.setup()

from library.models import Album, Artist, Track


def cleanup_unknown_albums():
    print("=" * 50)
    print("开始清理重复的 Unknown Album...")
    print("=" * 50)

    unknown_artist, created = Artist.objects.get_or_create(name="Unknown Artist")
    if created:
        print(f"✓ 创建默认艺人: Unknown Artist (ID: {unknown_artist.id})")
    else:
        print(f"✓ 找到默认艺人: Unknown Artist (ID: {unknown_artist.id})")

    unknown_albums = Album.objects.filter(title="Unknown Album").order_by('id')
    print(f"\n发现 {unknown_albums.count()} 个 Unknown Album:")

    for album in unknown_albums:
        print(f"  - Album ID:{album.id}, 艺人:{album.artist.name}, 歌曲数:{album.tracks.count()}")

    if unknown_albums.count() <= 1:
        print("\n✓ 没有重复的 Unknown Album，无需清理")
        return

    albums_list = list(unknown_albums)
    primary_album = albums_list[0]
    print(f"\n✓ 保留主 Album: ID:{primary_album.id} (艺人: {primary_album.artist.name})")

    total_tracks_moved = 0
    albums_to_delete = []

    for album in albums_list[1:]:
        tracks_to_move = album.tracks.all()
        track_count = tracks_to_move.count()

        if track_count > 0:
            for track in tracks_to_move:
                track.album = primary_album
                track.save()
            total_tracks_moved += track_count
            print(f"  → 合并 Album ID:{album.id}: 移动 {track_count} 首歌曲到 Album ID:{primary_album.id}")

        albums_to_delete.append(album)

    for album in albums_to_delete:
        album.delete()
        print(f"  ✓ 删除重复 Album ID:{album.id}")

    print(f"\n✓ 清理完成！共移动 {total_tracks_moved} 首歌曲")

    remaining = Album.objects.filter(title="Unknown Album").count()
    print(f"✓ 剩余 Unknown Album 数量: {remaining}")

    print("\n" + "=" * 50)
    print("检查孤立的艺人...")
    print("=" * 50)

    orphaned_artists = Artist.objects.filter(tracks__isnull=True, collaborated_tracks__isnull=True)
    artist_count = orphaned_artists.count()
    print(f"发现 {artist_count} 个孤立艺人（无歌曲关联）")

    if artist_count > 0:
        for artist in orphaned_artists:
            print(f"  - {artist.name} (ID: {artist.id})")
        confirm = input(f"\n是否删除这 {artist_count} 个孤立艺人？(y/n): ")
        if confirm.lower() == 'y':
            orphaned_artists.delete()
            print(f"✓ 已删除 {artist_count} 个孤立艺人")
        else:
            print("✗ 取消删除孤立艺人")
    else:
        print("✓ 没有孤立的艺人")

    print("\n" + "=" * 50)
    print("数据库清理完成！")
    print("=" * 50)


if __name__ == "__main__":
    cleanup_unknown_albums()
