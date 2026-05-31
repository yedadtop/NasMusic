import io
import re
from PIL import Image
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils.html import mark_safe
from .models import Artist, Album, Track
from .utils import sync_cover_to_audio_file
import mutagen


def parse_artists(artist_string):
    """拆分多歌手字符串"""
    if not artist_string:
        return ["Unknown Artist"]
        
    has_asian = bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', artist_string))
    
    if has_asian:
        pattern = (
            r'[\s/,&\-　\xA0、·・;；|+_]+'
            r'|\s+(?:feat\.|ft\.)+\s*'                   
            r'|(?<=\S)\s*-\s+(?=\S)'
        )
    else:
        pattern = (
            r'[/,&\-、·・;；|+_]+'
            r'|\s+(?:feat\.|ft\.)+\s*'
            r'|(?<=\S)\s*-\s+(?=\S)'
        )
        
    parts = re.split(pattern, artist_string, flags=re.IGNORECASE)
    artists = [p.strip() for p in parts if p.strip()]
    return artists if artists else ["Unknown Artist"]


# 新增：Mp3tag 显示名称与 ID3 帧的映射关系
MP3TAG_TO_ID3 = {
    'ALBUM': 'TALB', 'ARTIST': 'TPE1', 'ALBUMARTIST': 'TPE2',
    'TITLE': 'TIT2', 'TRACK': 'TRCK', 'GENRE': 'TCON',
    'YEAR': 'TDRC', 'COMMENT': 'COMM', 'UNSYNCEDLYRICS': 'USLT',
    'COMPOSER': 'TCOM', 'DISC': 'TPOS'
}
ID3_TO_MP3TAG = {v: k for k, v in MP3TAG_TO_ID3.items()}
ID3_TO_MP3TAG['TYER'] = 'YEAR'  # 兼容旧版 ID3v2.3 年份标签

_INFO_KEYS = frozenset({'BITRATE', 'SAMPLE_RATE', 'LENGTH', 'CHANNELS', 'BITS_PER_SAMPLE'})

METADATA_FIELD_DESCRIPTIONS = {
    'BITRATE': '比特率 - 音频文件的编码速率，单位为 kbps，数值越高音质越好但文件越大',
    'SAMPLE_RATE': '采样率 - 每秒采集音频信号的次数，单位为 Hz（如 44100Hz 为 CD 音质）',
    'LENGTH': '时长 - 音频文件的总播放时间，单位为秒',
    'CHANNELS': '声道数 - 音频的声道数量（1=单声道, 2=立体声）',
    'BITS_PER_SAMPLE': '位深度 - 每个采样点的位数（如 16bit、24bit），影响动态范围',
    'TITLE': '歌曲名称 - 这首曲目的正式标题',
    'ARTIST': '主要歌手 - 演唱这首歌曲的主要艺术家名称',
    'ALBUMARTIST': '专辑歌手 - 整张专辑的艺术家（通常与主要歌手相同，或为群星/ Various Artists）',
    'ALBUM': '专辑名称 - 这首歌曲所属的专辑标题',
    'TRACK': '曲目编号 - 在专辑中的排序号（如 "3/12" 表示第3首，共12首）',
    'DISC': '碟片编号 - 多碟专辑中的光盘编号（如 "1/2" 表示第1张盘，共2张）',
    'GENRE': '音乐风格 - 歌曲的音乐类型或流派（如 Pop、Rock、Jazz、Classical 等）',
    'YEAR': '发行年份 - 专辑或歌曲首次发布的年份',
    'COMMENT': '注释/备注 - 关于这首歌的附加说明或评论信息',
    'UNSYNCEDLYRICS': '完整歌词 - 未同步的完整歌词文本（非逐字卡拉OK式歌词）',
    'COMPOSER': '作曲者 - 创作这首歌曲旋律的作曲家姓名',
    'LYRICIST': '作词者 - 创作这首歌曲歌词的词作者姓名',
    'PERFORMER': '表演者 - 实际演奏或演唱此版本的具体艺人',
    'ARRANGER': '编曲者 - 对原曲进行编排和改编的音乐人',
    'PRODUCER': '制作人 - 负责录制和制作这张唱片的音乐制作人',
    'ENGINEER': '录音师 - 负责音频录制和混音的技术工程师',
    'COPYRIGHT': '版权信息 - 音乐作品的版权声明和所有者信息',
    'ENCODER': '编码器 - 用于编码音频文件的软件名称和版本',
    'COMPATIBLE_BRANDS': '兼容品牌 (M4A) - M4A 文件格式的兼容性标识',
    'ENCODERSETTINGS': '编码设置 (M4A) - M4A 编码时的具体参数配置',
    'MAJOR_BRAND': '主品牌 (M4A) - M4A 容器格式的主要标识符',
    'DATE': '日期 - 更精确的发布日期（通常包含年月日）',
    'BPM': '节拍速度 - 每分钟的节拍数，用于 DJ 混音和节奏匹配',
    'ISRC': '国际标准录音代码 - 全球唯一的录音制品识别码',
    'MOOD': '情绪标签 - 描述歌曲情感氛围的关键词（如 Happy、Sad、Energetic）',
    'RATING': '评分等级 - 用户对这首歌的质量评级（通常为 1-5 星）',
    'REPLAYGAIN_TRACK_GAIN': '音量增益 (Track) - 单曲级别的 ReplayGain 音量标准化增益值',
    'REPLAYGAIN_ALBUM_GAIN': '音量增益 (Album) - 专辑级别的 ReplayGain 音量标准化增益值',
    'MEDIA': '载体类型 - 原始发行介质（如 CD、Vinyl、Digital）',
    'LABEL': '唱片公司 - 发行这张专辑的唱片公司名称',
    'CATALOGNUMBER': '目录编号 - 唱片公司内部的产品编号',
    'BARCODE': '条形码 - 产品的 UPC/EAN 条形码用于零售识别',
    'ASIN': '亚马逊编号 - 亚马逊网站的标准识别号码',
    'MUSICBRAINZ_ARTISTID': 'MusicBrainz 艺术家ID - MusicBrainz 数据库中的唯一艺术家标识符',
    'MUSICBRAINZ_ALBUMID': 'MusicBrainz 专辑ID - MusicBrainz 数据库中的唯一专辑标识符',
    'MUSICBRAINZ_TRACKID': 'MusicBrainz 曲目ID - MusicBrainz 数据库中的唯一曲目标识符',
    'MUSICBRAINZ_RELEASEGROUPID': 'MusicBrainz 发行组ID - MusicBrainz 数据库中同一专辑不同发行的分组标识',
}

CRITICAL_FIELD_WARNINGS = {
    'BITRATE': {
        'warning': '⚠️ 删除比特率信息',
        'consequence': '比特率是音频文件的编码属性，删除后可能导致播放器无法正确显示音质信息，但不影响音频播放本身。',
        'severity': 'low'
    },
    'SAMPLE_RATE': {
        'warning': '⚠️ 删除采样率信息',
        'consequence': '采样率是音频的基础技术参数（如 44100Hz），删除后可能影响某些专业音频软件的识别和兼容性。',
        'severity': 'low'
    },
    'LENGTH': {
        'warning': '⚠️ 删除时长信息',
        'consequence': '时长是从音频文件计算得出的，删除后播放器将无法显示歌曲总时长，但实际播放不受影响。',
        'severity': 'low'
    },
    'CHANNELS': {
        'warning': '⚠️ 删除声道数信息',
        'consequence': '声道数标识音频是单声道还是立体声，删除后可能影响环绕声系统的自动识别。',
        'severity': 'low'
    },
    'BITS_PER_SAMPLE': {
        'warning': '⚠️ 删除位深度信息',
        'consequence': '位深度影响音质表现（16bit/24bit），删除后高解析度音频可能被误认为是普通音质。',
        'severity': 'low'
    },
    'TITLE': {
        'warning': '🚨 删除歌曲名称',
        'consequence': '删除后歌曲将显示为"未知曲目"，在音乐库中难以识别和搜索，强烈建议保留此字段！',
        'severity': 'high'
    },
    'ARTIST': {
        'warning': '🚨 删除主要歌手',
        'consequence': '删除后将显示为"Unknown Artist"，会导致歌手页面混乱、艺术家归档丢失、按歌手筛选功能失效！',
        'severity': 'high'
    },
    'ALBUM': {
        'warning': '🚨 删除专辑名称',
        'consequence': '删除后歌曲将脱离专辑归属，导致专辑页面显示不完整、专辑封面关联失效！',
        'severity': 'high'
    },
    'TRACK': {
        'warning': '⚠️ 删除曲目编号',
        'consequence': '删除后歌曲在专辑中的排序将丢失，播放列表顺序可能被打乱，影响整张专辑的聆听体验。',
        'severity': 'medium'
    },
    'GENRE': {
        'warning': '⚠️ 删除音乐风格',
        'consequence': '删除后将无法按流派筛选歌曲，智能推荐和分类功能可能受影响。',
        'severity': 'medium'
    },
    'YEAR': {
        'warning': '⚠️ 删除发行年份',
        'consequence': '删除后无法按年代浏览歌曲，时间线视图和发行历史记录将缺失此信息。',
        'severity': 'medium'
    },
    'ALBUMARTIST': {
        'warning': '⚠️ 删除专辑歌手',
        'consequence': '对于合辑或群星专辑，删除后可能导致艺术家归类错误，影响多碟专辑的正确识别。',
        'severity': 'medium'
    },
    'DISC': {
        'warning': '⚠️ 删除碟片编号',
        'consequence': '对于多碟专辑/现场录音，删除后所有曲目将被视为同一张盘，导致排序混乱。',
        'severity': 'medium'
    },
}


def _get_all_metadata(file_path, format_str):
    try:
        metadata_list = []
        ext = format_str.lower()
        idx = 0

        audio_raw = mutagen.File(file_path)
        if audio_raw is None:
            return metadata_list

        info = audio_raw.info
        if info:
            if hasattr(info, 'bitrate') and info.bitrate:
                metadata_list.append({'key': 'BITRATE', 'value': str(info.bitrate), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('BITRATE', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('BITRATE', None)}); idx += 1
            if hasattr(info, 'sample_rate') and info.sample_rate:
                metadata_list.append({'key': 'SAMPLE_RATE', 'value': str(info.sample_rate), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('SAMPLE_RATE', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('SAMPLE_RATE', None)}); idx += 1
            if hasattr(info, 'length') and info.length:
                metadata_list.append({'key': 'LENGTH', 'value': f"{info.length:.2f}", '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('LENGTH', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('LENGTH', None)}); idx += 1
            if hasattr(info, 'channels') and info.channels:
                metadata_list.append({'key': 'CHANNELS', 'value': str(info.channels), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('CHANNELS', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('CHANNELS', None)}); idx += 1
            if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                metadata_list.append({'key': 'BITS_PER_SAMPLE', 'value': str(info.bits_per_sample), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('BITS_PER_SAMPLE', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('BITS_PER_SAMPLE', None)}); idx += 1

        if ext == 'mp3':
            if getattr(audio_raw, 'tags', None):
                for frame in audio_raw.tags.values():
                    frame_id = frame.FrameID
                    if frame_id.startswith('APIC'):
                        continue

                    if frame_id == 'TXXX':
                        key_name = frame.desc.upper() if hasattr(frame, 'desc') else 'TXXX'
                        val = str(frame.text[0]) if hasattr(frame, 'text') and frame.text else str(frame)
                        metadata_list.append({'key': key_name, 'value': val, '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key_name, f'自定义文本标签 (TXXX) - 用户自定义的 {key_name} 字段'), 'warning': CRITICAL_FIELD_WARNINGS.get(key_name, None)}); idx += 1
                    elif frame_id == 'USLT':
                        val = str(frame.text) if hasattr(frame, 'text') else str(frame)
                        metadata_list.append({'key': 'UNSYNCEDLYRICS', 'value': val, '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('UNSYNCEDLYRICS', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('UNSYNCEDLYRICS', None)}); idx += 1
                    elif frame_id == 'COMM':
                        val = str(frame.text[0]) if hasattr(frame, 'text') and frame.text else str(frame)
                        metadata_list.append({'key': 'COMMENT', 'value': val, '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get('COMMENT', ''), 'warning': CRITICAL_FIELD_WARNINGS.get('COMMENT', None)}); idx += 1
                    else:
                        key_name = ID3_TO_MP3TAG.get(frame_id, frame_id)
                        if hasattr(frame, 'text') and isinstance(frame.text, list):
                            for text_val in frame.text:
                                metadata_list.append({'key': key_name, 'value': str(text_val), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key_name, f'ID3 标签 ({frame_id}) - {frame_id} 帧存储的数据'), 'warning': CRITICAL_FIELD_WARNINGS.get(key_name, None)}); idx += 1
                        else:
                            metadata_list.append({'key': key_name, 'value': str(frame), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key_name, f'ID3 标签 ({frame_id}) - {frame_id} 帧存储的数据'), 'warning': CRITICAL_FIELD_WARNINGS.get(key_name, None)}); idx += 1

        elif ext == 'm4a':
            audio_easy = mutagen.File(file_path, easy=True)
            if audio_easy and getattr(audio_easy, 'tags', None):
                for k, v in audio_easy.tags.items():
                    for val in v:
                        metadata_list.append({'key': k.upper(), 'value': str(val), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(k.upper(), f'M4A 标签 ({k}) - M4A/MP4 容器中的 {k} 字段'), 'warning': CRITICAL_FIELD_WARNINGS.get(k.upper(), None)}); idx += 1
            extra_keys = ['COMPATIBLE_BRANDS', 'ENCODERSETTINGS', 'HW', 'MAJOR_BRAND', 'MAXRATE', 'MINOR_VERSION', 'TE_IS_REENCODE']
            for key in extra_keys:
                if key in (audio_raw.tags or {}):
                    val = audio_raw.tags[key]
                    if isinstance(val, list):
                        for v in val:
                            metadata_list.append({'key': key, 'value': str(v), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key, f'M4A 技术属性 ({key}) - M4A 文件的 {key} 技术参数'), 'warning': CRITICAL_FIELD_WARNINGS.get(key, None)}); idx += 1
                    else:
                        metadata_list.append({'key': key, 'value': str(val), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key, f'M4A 技术属性 ({key}) - M4A 文件的 {key} 技术参数'), 'warning': CRITICAL_FIELD_WARNINGS.get(key, None)}); idx += 1

        elif ext in ['flac', 'ogg']:
            for key, val_list in (audio_raw.tags or {}).items():
                if key.lower().startswith('metadata_block_picture'):
                    continue
                if isinstance(val_list, list):
                    for v in val_list:
                        metadata_list.append({'key': key.upper(), 'value': str(v), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key.upper(), f'Vorbis 注释 ({key}) - FLAC/OGG Vorbis Comment 格式的 {key} 字段'), 'warning': CRITICAL_FIELD_WARNINGS.get(key.upper(), None)}); idx += 1
                else:
                    metadata_list.append({'key': key.upper(), 'value': str(val_list), '_idx': idx, 'description': METADATA_FIELD_DESCRIPTIONS.get(key.upper(), f'Vorbis 注释 ({key}) - FLAC/OGG Vorbis Comment 格式的 {key} 字段'), 'warning': CRITICAL_FIELD_WARNINGS.get(key.upper(), None)}); idx += 1

        return metadata_list
    except Exception as e:
        return [{'key': '_error', 'value': str(e)}]


def _find_mp3_frame_by_idx(audio_tags, target_idx):
    seen = 0
    for fk, f in audio_tags.items():
        if fk.startswith('APIC'):
            continue
        if seen == target_idx:
            return fk, f
        seen += 1
    return None, None


def _set_metadata_entry(file_path, format_str, key, value, idx=None):
    try:
        key_upper = key.upper()
        ext = format_str.lower()

        audio_easy = mutagen.File(file_path, easy=True)
        if audio_easy is not None and getattr(audio_easy, 'tags', None) and key.lower() in audio_easy.tags.valid_keys:
            if idx is not None:
                current_values = list(audio_easy.tags.get(key.lower(), []))
                if 0 <= idx < len(current_values):
                    current_values[idx] = value
                    audio_easy[key.lower()] = current_values
                else:
                    audio_easy[key.lower()] = value
            else:
                audio_easy[key.lower()] = value
            audio_easy.save()
            return True, '写入成功'

        audio_raw = mutagen.File(file_path)
        if audio_raw is None:
            return False, '无法读取音频文件'

        if ext == 'mp3':
            from mutagen import id3 as id3_module
            if not getattr(audio_raw, 'tags', None):
                audio_raw.add_tags()

            if idx is not None:
                fk, target_frame = _find_mp3_frame_by_idx(audio_raw.tags, idx)
                if target_frame is not None:
                    fid = target_frame.FrameID
                    if fid == 'TXXX':
                        old_desc = target_frame.desc if hasattr(target_frame, 'desc') else ''
                        audio_raw.tags.delall(fk)
                        audio_raw.tags.add(id3_module.TXXX(encoding=3, desc=old_desc, text=[value]))
                    elif fid == 'COMM':
                        lang = getattr(target_frame, 'lang', 'eng')
                        desc = getattr(target_frame, 'desc', '')
                        audio_raw.tags.delall(fk)
                        audio_raw.tags.add(id3_module.COMM(encoding=3, lang=lang, desc=desc, text=value))
                    elif fid == 'USLT':
                        lang = getattr(target_frame, 'lang', 'eng')
                        desc = getattr(target_frame, 'desc', '')
                        audio_raw.tags.delall(fk)
                        audio_raw.tags.add(id3_module.USLT(encoding=3, lang=lang, desc=desc, text=value))
                    else:
                        frame_cls = getattr(id3_module, fid, None)
                        if frame_cls:
                            try:
                                target_frame.text = [value]
                            except Exception:
                                try:
                                    target_frame.text = value
                                except Exception:
                                    audio_raw.tags.delall(fk)
                                    audio_raw.tags.add(frame_cls(encoding=3, text=[value]))
                    audio_raw.save()
                    return True, '写入成功'
                else:
                    return False, f'找不到索引为 {idx} 的帧'

            if key_upper in MP3TAG_TO_ID3:
                frame_id = MP3TAG_TO_ID3[key_upper]
                audio_raw.tags.delall(frame_id)
                frame_cls = getattr(id3_module, frame_id, None)
                if frame_cls:
                    if frame_id in ['COMM', 'USLT']:
                        audio_raw.tags.add(frame_cls(encoding=3, lang='eng', desc='', text=value))
                    else:
                        audio_raw.tags.add(frame_cls(encoding=3, text=[value]))
            else:
                to_delete = [fk for fk, f in audio_raw.tags.items() if fk.startswith('TXXX') and hasattr(f, 'desc') and f.desc.upper() == key_upper]
                for fk in to_delete:
                    audio_raw.tags.delall(fk)
                audio_raw.tags.add(id3_module.TXXX(encoding=3, desc=key_upper, text=[value]))
            audio_raw.save()

        elif ext in ['flac', 'ogg']:
            if key_upper in (audio_raw.tags or {}):
                current = audio_raw.tags[key_upper]
                if isinstance(current, list) and idx is not None and 0 <= idx < len(current):
                    current[idx] = value
                else:
                    audio_raw[key_upper] = value
            else:
                audio_raw[key_upper] = value
            audio_raw.save()
        elif ext == 'm4a':
            if key in (audio_raw.tags or {}):
                current = audio_raw.tags[key]
                if isinstance(current, list) and idx is not None and 0 <= idx < len(current):
                    current[idx] = value
                else:
                    audio_raw[key] = value
            else:
                audio_raw[key] = value
            audio_raw.save()
        return True, '写入成功'
    except Exception as e:
        return False, str(e)


def _count_info_offset(file_path):
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return 0
        info = audio.info
        count = 0
        if info:
            if hasattr(info, 'bitrate') and info.bitrate: count += 1
            if hasattr(info, 'sample_rate') and info.sample_rate: count += 1
            if hasattr(info, 'length') and info.length: count += 1
            if hasattr(info, 'channels') and info.channels: count += 1
            if hasattr(info, 'bits_per_sample') and info.bits_per_sample: count += 1
        return count
    except Exception:
        return 0


def _delete_metadata_entry(file_path, format_str, key, idx=None):
    try:
        key_upper = key.upper()

        ext = format_str.lower()
        info_offset = _count_info_offset(file_path)

        audio_easy = mutagen.File(file_path, easy=True)
        if audio_easy is not None and getattr(audio_easy, 'tags', None) and key.lower() in audio_easy.tags:
            easy_tag_idx = idx - info_offset if idx is not None else None
            if easy_tag_idx is not None and easy_tag_idx >= 0:
                current_values = list(audio_easy.tags.get(key.lower(), []))
                if 0 <= easy_tag_idx < len(current_values):
                    current_values.pop(easy_tag_idx)
                    if current_values:
                        audio_easy[key.lower()] = current_values
                    else:
                        del audio_easy[key.lower()]
                else:
                    del audio_easy[key.lower()]
            else:
                del audio_easy[key.lower()]
            audio_easy.save()
            return True, '删除成功'

        audio_raw = mutagen.File(file_path)
        if audio_raw is None:
            return False, '无法读取音频文件'

        if ext == 'mp3':
            if getattr(audio_raw, 'tags', None):
                tag_idx = idx - info_offset if idx is not None else None
                if tag_idx is not None and tag_idx >= 0:
                    fk, target_frame = _find_mp3_frame_by_idx(audio_raw.tags, tag_idx)
                    if target_frame is not None:
                        audio_raw.tags.delall(fk)
                        audio_raw.save()
                        return True, '删除成功'
                    else:
                        return False, f'找不到索引为 {idx} 的标签'

                if key_upper in MP3TAG_TO_ID3:
                    frame_id = MP3TAG_TO_ID3[key_upper]
                    audio_raw.tags.delall(frame_id)
                    if key_upper == 'YEAR':
                        audio_raw.tags.delall('TYER')
                else:
                    to_delete = [fk for fk, f in audio_raw.tags.items() if fk.startswith('TXXX') and hasattr(f, 'desc') and f.desc.upper() == key_upper]
                    for fk in to_delete:
                        audio_raw.tags.delall(fk)
                audio_raw.save()
        elif ext in ['flac', 'ogg']:
            if key_upper in (audio_raw.tags or {}):
                current = audio_raw.tags[key_upper]
                if isinstance(current, list) and idx is not None:
                    tag_idx = idx - info_offset
                    if 0 <= tag_idx < len(current):
                        current.pop(tag_idx)
                        if current:
                            audio_raw.tags[key_upper] = current
                        else:
                            del audio_raw.tags[key_upper]
                        audio_raw.save()
                        return True, '删除成功'
                del audio_raw.tags[key_upper]
                audio_raw.save()
        elif ext == 'm4a':
            extra_keys = ['COMPATIBLE_BRANDS', 'ENCODERSETTINGS', 'HW', 'MAJOR_BRAND', 'MAXRATE', 'MINOR_VERSION', 'TE_IS_REENCODE']
            if key in extra_keys:
                if key in (audio_raw.tags or {}):
                    current = audio_raw.tags[key]
                    if isinstance(current, list) and idx is not None:
                        if 0 <= idx < len(current):
                            current.pop(idx)
                            if current:
                                audio_raw.tags[key] = current
                            else:
                                del audio_raw.tags[key]
                        else:
                            del audio_raw.tags[key]
                    else:
                        del audio_raw.tags[key]
                    audio_raw.save()
                    return True, '删除成功'
            elif key in (audio_raw.tags or {}):
                del audio_raw.tags[key]
                audio_raw.save()
        return True, '删除成功'
    except Exception as e:
        return False, str(e)


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
    change_form_template = 'admin/library/track/change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/metadata/',
                 self.admin_site.admin_view(self.metadata_view),
                 name='library_track_metadata'),
        ]
        return custom_urls + urls

    def metadata_view(self, request, object_id):
        from django.shortcuts import get_object_or_404
        track = get_object_or_404(Track, pk=object_id)

        if request.method == 'GET':
            metadata = _get_all_metadata(track.file_path, track.format)
            return JsonResponse({'success': True, 'metadata': metadata})

        if request.method == 'POST':
            action = request.POST.get('action', '').strip()
            key = request.POST.get('key', '').strip()
            value = request.POST.get('value', '').strip()
            idx_str = request.POST.get('idx', '').strip()
            idx = int(idx_str) if idx_str.isdigit() else None

            if not key:
                return JsonResponse({'success': False, 'message': '键名不能为空'})

            if action == 'add':
                if not value:
                    return JsonResponse({'success': False, 'message': '值不能为空'})
                ok, msg = _set_metadata_entry(track.file_path, track.format, key, value)
            elif action == 'delete':
                ok, msg = _delete_metadata_entry(track.file_path, track.format, key, idx=idx)
            else:
                return JsonResponse({'success': False, 'message': f'未知操作: {action}'})

            if ok:
                metadata = _get_all_metadata(track.file_path, track.format)
                return JsonResponse({'success': True, 'message': msg, 'metadata': metadata})
            else:
                return JsonResponse({'success': False, 'message': msg})

        return JsonResponse({'success': False, 'message': '不支持的请求方法'})

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
        # 🚨 必须保留这一行！它是 Django 真正把修改后的数据存入数据库的核心指令
        super().save_model(request, obj, form, change)

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


    def save_related(self, request, form, formsets, change):
        # 1. 先让 Django 按默认表单保存关联数据 [cite: 39]
        super().save_related(request, form, formsets, change)

        obj = form.instance
        
        # 2. 【核心】无论后台表单怎么选，强制用主歌手的拆分结果覆盖“所有歌手” [cite: 40]
        raw_artist_name = obj.artist.name if obj.artist else "Unknown Artist"
        parsed = parse_artists(raw_artist_name)
        if len(parsed) > 1:
            artist_objs = [Artist.objects.get_or_create(name=n)[0] for n in parsed]
            obj.artists.set(artist_objs)
        else:
            obj.artists.set([obj.artist])

        # 3. 【核心】清理逻辑：通过对比修改前的初始数据 (form.initial)，删掉被改掉的旧名字 [cite: 41, 42, 43]
        if change and form.initial:
            old_artist_id = form.initial.get('artist')
            old_album_id = form.initial.get('album')
            old_m2m_ids = form.initial.get('artists', [])
            
            # A. 清理空专辑
            if old_album_id and old_album_id != obj.album_id:
                old_album = Album.objects.filter(id=old_album_id).first()
                if old_album and not old_album.tracks.exists():
                    old_album.delete()

            # B. 清理废弃歌手
            all_old_ids = set(old_m2m_ids)
            if old_artist_id:
                all_old_ids.add(old_artist_id)
                
            for aid in all_old_ids:
                if not aid: continue
                # 健壮性处理：aid 可能是 ID 也可能是对象 
                artist_item = aid if isinstance(aid, Artist) else Artist.objects.filter(pk=aid).first()
                
                if artist_item and artist_item.pk:
                    # 深度检查是否有任何关联记录 [cite: 43]
                    if not artist_item.tracks.exists() and \
                    not artist_item.collaborated_tracks.exists() and \
                    not artist_item.albums.exists():
                        artist_item.delete()