# scraper/utils.py
import requests
import mutagen
from django.core.files.base import ContentFile
from library.utils import sync_cover_to_audio_file
from .models import ScraperAPI
from opencc import OpenCC

def fetch_and_embed_cover(track):
    """
    通过数据库配置的接口抓取高清封面，并直接嵌入到物理文件及数据库中 (原图保存，无压缩)
    返回: (布尔值是否成功, 提示信息)
    """
    apis = ScraperAPI.objects.filter(is_active=True).order_by('priority')
    if not apis.exists():
        print(f"[刮削] 歌曲 '{track.title}' 失败: 系统中没有已启用的刮削接口")
        return False, "系统中没有已启用的刮削接口，请先配置。"

    artist_name = track.artist.name if track.artist and hasattr(track.artist, 'name') and track.artist.name else ''
    search_term = f"{track.title} {artist_name}".strip()
    print(f"[刮削] 歌曲 '{track.title}' 搜索词: '{search_term}'")

    if track.cover_thumbnail and str(track.cover_thumbnail).strip() != '':
        print(f"[刮削] 歌曲 '{track.title}' 已有封面，跳过刮削: {track.cover_thumbnail.url}")
        return False, "歌曲已有封面，已跳过刮削。"

    for api in apis:
        try:
            params = {
                'term': search_term,
                'media': 'music',
                'entity': 'song',
                'limit': 1
            }
            print(f"[刮削] 调用接口 [{api.name}]: {api.url}")
            # 设置较短的超时时间，防止阻塞
            response = requests.get(api.url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            result_count = data.get('resultCount', 0)
            print(f"[刮削] 接口 [{api.name}] 返回结果数: {result_count}")

            if result_count > 0:
                item = data['results'][0]
                artwork_url = item.get('artworkUrl100', '')
                print(f"[刮削] 接口 [{api.name}] 原始封面URL: {artwork_url}")

                if not artwork_url:
                    print(f"[刮削] 接口 [{api.name}] 未获取到封面URL，继续下一个接口")
                    continue

                # 将 100x100 的缩略图 URL 替换为 1000x1000 的高清原图
                high_res_url = artwork_url.replace('100x100bb.jpg', '1000x1000bb.jpg')
                print(f"[刮削] 接口 [{api.name}] 高清封面URL: {high_res_url}")

                # 下载高清图片原始字节流
                img_resp = requests.get(high_res_url, timeout=10)
                img_resp.raise_for_status()
                image_bytes = img_resp.content
                print(f"[刮削] 接口 [{api.name}] 图片下载成功，大小: {len(image_bytes)} bytes")

                # 1. 物理文件删除旧图（如果存在）
                if track.cover_thumbnail:
                    print(f"[刮削] 删除旧封面: {track.cover_thumbnail.path}")
                    track.cover_thumbnail.delete(save=False)

                # 2. 将未经压缩的高清原图字节直接存入数据库的 cover_thumbnail 字段
                filename = f"track_{track.id}_cover.jpg"
                track.cover_thumbnail.save(filename, ContentFile(image_bytes), save=True)
                print(f"[刮削] 保存封面到数据库: {track.cover_thumbnail.path}")

                # 3. 将高清原图字节直接写入物理音频文件
                print(f"[刮削] 嵌入封面到物理文件: {track.file_path}")
                sync_cover_to_audio_file(track.file_path, track.format, image_bytes)

                return True, f"成功通过接口 [{api.name}] 获取并原图嵌入高清封面！"

        except requests.RequestException as e:
            print(f"⚠️ 刮削接口 [{api.name}] 请求失败: {e}")
            continue  # 失败则无缝切换到下一个优先级的接口
        except Exception as e:
            print(f"⚠️ 解析或写入封面时发生异常: {e}")
            continue

    print(f"[刮削] 歌曲 '{track.title}' 失败: 所有可用接口均未匹配到封面或请求失败")
    return False, "所有可用接口均未匹配到封面或请求失败。"


def fetch_and_embed_lyrics(track):
    """
    通过 LRCLIB 接口抓取歌词（优先取时间轴滚动歌词），自动简繁转换，并嵌入物理文件与数据库。
    返回: dict with keys: success (bool), message (str), source ('local'|'lrclib'|None)
    """
    cc = OpenCC('t2s')

    artist_name = track.artist.name if track.artist and hasattr(track.artist, 'name') else ''
    title = track.title or ''

    if not title:
        print(f"[歌词刮削] 失败: 歌曲 (ID:{track.id}) 缺少标题")
        return {"success": False, "message": "歌曲缺少标题，无法进行搜索。", "source": None}

    has_existing_lyrics = bool(track.lyrics and track.lyrics.strip())
    if has_existing_lyrics:
        print(f"[歌词刮削] 歌曲 '{track.title}' 已有歌词 (长度: {len(track.lyrics)} 字符)，跳过刮削")
        return {"success": False, "message": "歌曲已有歌词，已跳过刮削。", "source": None}

    audio = mutagen.File(track.file_path)
    if audio is not None:
        ext = track.format.lower()
        local_lyrics = None

        try:
            if ext == 'mp3':
                if getattr(audio, 'tags', None):
                    for key in audio.tags.keys():
                        if key.startswith('USLT'):
                            uslt = audio.tags[key]
                            local_lyrics = uslt.text if hasattr(uslt, 'text') else str(uslt)
                            break
            elif ext in ['flac', 'ogg']:
                possible_keys = ['lyrics', 'unsyncedlyrics', 'syncedlyrics', 'lyric']
                for key in possible_keys:
                    lyrics_list = audio.get(key)
                    if lyrics_list:
                        local_lyrics = lyrics_list[0]
                        break
            elif ext == 'm4a':
                lyrics_list = audio.get('\xa9lyr')
                if lyrics_list:
                    local_lyrics = lyrics_list[0]

            if local_lyrics and str(local_lyrics).strip():
                clean_lyrics = str(local_lyrics).strip()
                if '||' in clean_lyrics[:15]:
                    clean_lyrics = clean_lyrics.split('||', 1)[-1]

                print(f"[歌词刮削] 从本地物理文件提取到歌词，长度: {len(clean_lyrics)} 字符")
                simplified_lyrics = cc.convert(clean_lyrics)
                track.lyrics = simplified_lyrics
                track.save(update_fields=['lyrics'])
                return {"success": True, "message": "已从本地物理文件恢复歌词", "source": "local"}
        except Exception as e:
            print(f"[歌词刮削] 读取本地文件歌词时发生异常: {e}")

    api_url = "https://lrclib.net/api/search"
    params = {
        'track_name': title,
        'artist_name': artist_name
    }

    print(f"[歌词刮削] 开始搜索: '{title}' - '{artist_name}'")

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            print(f"[歌词刮削] LRCLIB 未找到匹配结果")
            return {"success": False, "message": "未找到匹配的歌词。", "source": None}

        best_match = data[0]
        raw_lyrics = best_match.get('syncedLyrics') or best_match.get('plainLyrics')

        if not raw_lyrics:
            print(f"[歌词刮削] 找到了歌曲信息，但暂无歌词内容")
            return {"success": False, "message": "该歌曲在曲库中暂无歌词内容。", "source": None}

        simplified_lyrics = cc.convert(raw_lyrics)
        print(f"[歌词刮削] 成功获取歌词，长度: {len(simplified_lyrics)} 字符 (已转简体)")

        track.lyrics = simplified_lyrics
        track.save(update_fields=['lyrics'])

        if audio is not None:
            ext = track.format.lower()

            if ext == 'mp3':
                from mutagen.id3 import USLT
                if getattr(audio, 'tags', None) is None:
                    audio.add_tags()
                audio.tags.setall("USLT", [USLT(encoding=3, lang='eng', desc='', text=simplified_lyrics)])
            elif ext in ['flac', 'ogg']:
                audio["lyrics"] = simplified_lyrics
            elif ext == 'm4a':
                audio['\xa9lyr'] = simplified_lyrics

            audio.save()
            print(f"[歌词刮削] 成功将歌词嵌入到物理文件: {track.file_path}")

        return {"success": True, "message": "成功刮削并嵌入歌词！", "source": "lrclib"}

    except requests.RequestException as e:
        print(f"⚠️ LRCLIB 接口请求失败: {e}")
        return {"success": False, "message": f"请求歌词接口失败: {str(e)}", "source": None}
    except Exception as e:
        print(f"⚠️ 解析或写入歌词时发生异常: {e}")
        return {"success": False, "message": f"写入歌词时发生内部错误: {str(e)}", "source": None}