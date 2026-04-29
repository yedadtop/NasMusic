"""调试 parse_artists 函数的脚本"""
import os
import sys
import django
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NasMusic.settings')
django.setup()

from library.models import Track

def debug_artist(track_id):
    track = Track.objects.get(id=track_id)
    raw_artist = track.artist.name

    print(f"歌曲: {track.title}")
    print(f"原始艺人名: '{raw_artist}'")
    print(f"字符编码:")
    for i, char in enumerate(raw_artist):
        hex_code = hex(ord(char))
        print(f"  [{i}] '{char}' -> {hex_code}")

    print(f"\n检测中文: {bool(re.search(r'[\u4e00-\u9fff]', raw_artist))}")

def parse_artists(artist_string):
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', artist_string))
    if has_chinese:
        parts = re.split(
            r'[\s/,&\-　\xA0]+',
            r'|\s+(?:feat\.|ft\.)+\s*',
            r'|(?<=\S)\s*-\s+(?=\S)',
            artist_string,
            flags=re.IGNORECASE
        )
    else:
        parts = re.split(
            r'[/,&\-]',
            r'|\s+(?:feat\.|ft\.)+\s*',
            r'|(?<=\S)\s*-\s+(?=\S)',
            artist_string,
            flags=re.IGNORECASE
        )
    artists = [p.strip() for p in parts if p.strip()]
    return artists if artists else ["Unknown Artist"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        debug_artist(int(sys.argv[1]))
    else:
        print("用法: python debug_parse.py <track_id>")
        print("示例: python debug_parse.py 50")
