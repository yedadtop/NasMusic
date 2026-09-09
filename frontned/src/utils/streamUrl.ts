// 统一的播放流地址构造（从 App.vue / PlayerDetail.vue 的重复实现中提取）：
// 本地歌曲直连 /stream/，B站歌曲走 playurl 接口 + 代理播放
import request from '../api'
import { STREAM_BASE_URL } from '../api'

export async function getStreamUrl(track: any): Promise<string> {
  if (track.is_bilibili) {
    const res = await request.get('/scraper/bili/playurl/', { params: { bvid: track.bvid } })
    if (res.data.audio_url) {
      return `${STREAM_BASE_URL}/api/scraper/bili/proxy/?url=${encodeURIComponent(res.data.audio_url)}`
    }
    throw new Error('获取B站播放链接失败')
  }
  return `${STREAM_BASE_URL}/stream/${track.id}/`
}

// 曲目指纹：多设备同步时用于比对本地曲目与远端会话是否为同一首
export function trackFingerprint(track: any): string {
  if (!track) return ''
  return track.is_bilibili ? `b${track.bvid}` : `t${track.id}`
}
