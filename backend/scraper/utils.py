# scraper/utils.py
import requests
from django.core.files.base import ContentFile
from library.utils import sync_cover_to_audio_file
from .models import ScraperAPI


def fetch_and_embed_cover(track):
    """
    通过数据库配置的接口抓取高清封面，并直接嵌入到物理文件及数据库中 (原图保存，无压缩)
    返回: (布尔值是否成功, 提示信息)
    """
    apis = ScraperAPI.objects.filter(is_active=True).order_by('priority')
    if not apis.exists():
        print(f"[刮削] 歌曲 '{track.title}' 失败: 系统中没有已启用的刮削接口")
        return False, "系统中没有已启用的刮削接口，请先配置。"

    # 构造搜索词：歌名 + 主歌手
    artist_name = track.artist.name if track.artist and hasattr(track.artist, 'name') and track.artist.name else ''
    search_term = f"{track.title} {artist_name}".strip()
    print(f"[刮削] 歌曲 '{track.title}' 搜索词: '{search_term}'")

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