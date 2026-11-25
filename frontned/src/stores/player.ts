import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import request from '../api'
import { getBiliImageUrl } from '../api'
import { saveSnapshot, loadSnapshot, clearSnapshot, type PlaybackSnapshot } from '../utils/playbackSnapshot'

const MAX_SHUFFLE_HISTORY = 100
// 本地快照：变更类字段 800ms 去抖合并；进度单独 5s 节流
// （timeupdate 约 4Hz，每次都写 localStorage 会明显卡顿）
const PERSIST_DEBOUNCE = 800
const PERSIST_POSITION_INTERVAL = 5000
const biliCoverCache = new Map<string, string>()

// ===== 多设备同步回执（由 useSyncPlayback 注入，避免 store 反向依赖 composable）=====
// 本地播放操作发生时回调 composable，由其提交到后端广播给其他设备
export interface SyncAdapter {
  onLocalChange(kind: 'state' | 'transport'): void
}

let syncAdapter: SyncAdapter | null = null
// 远端状态应用期间的守卫：防止把收到的广播再回环提交
let applyingRemote = false

async function preloadBiliCover(coverUrl: string, bvid: string): Promise<string> {
  if (biliCoverCache.has(bvid)) {
    return biliCoverCache.get(bvid)!
  }
  try {
    const response = await fetch(coverUrl, { referrerPolicy: 'no-referrer' })
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    biliCoverCache.set(bvid, blobUrl)
    return blobUrl
  } catch (error) {
    console.error('预加载B站封面失败:', error)
    return coverUrl
  }
}

function clearBiliCoverCache() {
  for (const blobUrl of biliCoverCache.values()) {
    URL.revokeObjectURL(blobUrl)
  }
  biliCoverCache.clear()
}

export const usePlayerStore = defineStore('player', () => {
  const currentTrack = ref(null)
  const currentTrackDetail = ref<any | null>(null)
  const playlist = ref<any[]>([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)
  const audioElement = ref<HTMLAudioElement | null>(null)
  const playMode = ref('sequential')
  const shuffleHistory = ref<any[]>([])
  const loadMoreCallback = ref<(() => Promise<void>) | null>(null)
  const isLoadingMore = ref(false)
  const refreshLibraryTrigger = ref(0)
  const coverStyleMode = ref(0)

  // 本地快照的定时器与上次写进度的时间戳
  let persistTimer: number | null = null
  let lastPositionPersistAt = 0
  // 音频恢复定位期间置 true：此时 <audio> 的 currentTime 还停在 0，
  // 直接采信会把快照里的进度写没（下次进页面又从 0 开始）
  const restoringPosition = ref(false)

  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  const hasPrev = computed(() => {
    if (playMode.value === 'shuffle') {
      return shuffleHistory.value.length > 0
    }
    if (playMode.value === 'single') {
      return true
    }
    return currentIndex.value > 0
  })

  const hasNext = computed(() => {
    if (playMode.value === 'shuffle') {
      // 随机模式由后端全曲库随机，始终有下一首（曲库为空时请求会失败并停止）
      return true
    }
    if (playMode.value === 'single') {
      return true
    }
    if (currentIndex.value < playlist.value.length - 1) {
      return true
    }
    return loadMoreCallback.value !== null && !isLoadingMore.value
  })

  function setLoadMoreCallback(callback: (() => Promise<void>) | null) {
    loadMoreCallback.value = callback
  }

  async function checkAndLoadMore() {
    if (loadMoreCallback.value && !isLoadingMore.value) {
      const remainingTracks = playlist.value.length - currentIndex.value - 1
      if (remainingTracks <= 10) {
        isLoadingMore.value = true
        try {
          await loadMoreCallback.value()
        } finally {
          isLoadingMore.value = false
        }
      }
    }
  }

  function togglePlayMode() {
    if (playMode.value === 'sequential') {
      playMode.value = 'shuffle'
      shuffleHistory.value = []
    } else if (playMode.value === 'shuffle') {
      playMode.value = 'single'
    } else {
      playMode.value = 'sequential'
      shuffleHistory.value = []
    }
    notifySync('state')
  }

  function resetPlayer() {
    currentTrack.value = null
    currentTrackDetail.value = null
    playlist.value = []
    currentIndex.value = -1
    isPlaying.value = false
    currentTime.value = 0
    duration.value = 0
    playMode.value = 'sequential'
    shuffleHistory.value = []
    loadMoreCallback.value = null
    isLoadingMore.value = false
    clearBiliCoverCache()
    // 主动清空播放器时同步清掉快照，否则下次进页面又把旧歌恢复回来
    if (persistTimer !== null) {
      window.clearTimeout(persistTimer)
      persistTimer = null
    }
    clearSnapshot()
  }

  function triggerLibraryRefresh() {
    refreshLibraryTrigger.value++
  }

  function toggleCoverStyle() {
    coverStyleMode.value = (coverStyleMode.value + 1) % 3
  }

  async function fetchTrackDetail(id: string | number) {
    try {
      const res = await request.get(`/tracks/${id}/`)
      currentTrackDetail.value = res.data
    } catch (error) {
      console.error('获取歌曲详情失败:', error)
    }
  }

  async function fetchBilibiliLyrics(title: string) {
    currentTrackDetail.value = null
    
    if (!title) {
      return
    }

    try {
      const res = await request.post('/scraper/lyrics/bilibili/', { title })
      if (res.data.success && res.data.lyrics) {
        currentTrackDetail.value = {
          id: `bilibili_${Date.now()}`,
          title: res.data.parsed_song_name || title,
          artist_name: res.data.parsed_artist_name || '',
          lyrics: res.data.lyrics,
          is_bilibili: true
        }
        console.log(`[播放器] B站歌曲歌词获取成功: ${res.data.parsed_song_name} - ${res.data.parsed_artist_name}`)
      } else {
        currentTrackDetail.value = {
          id: `bilibili_${Date.now()}`,
          title: title,
          artist_name: '',
          lyrics: '',
          is_bilibili: true
        }
        if (res.data.message && res.data.message !== '成功获取歌词') {
          console.log(`[播放器] B站歌曲歌词获取失败: ${res.data.message}`)
        }
      }
    } catch (error) {
      console.error('获取B站歌曲歌词失败:', error)
      currentTrackDetail.value = {
        id: `bilibili_${Date.now()}`,
        title: title,
        artist_name: '',
        lyrics: '',
        is_bilibili: true
      }
    }
  }

  function playTrack(track: any, index = -1, tracks: any[] = [], preservePlayingState = false) {
    if (tracks.length > 0) {
      playlist.value = tracks
      currentIndex.value = index
      shuffleHistory.value = []
    } else if (index >= 0) {
      if (playMode.value === 'shuffle' && currentIndex.value !== -1) {
        if (shuffleHistory.value.length >= MAX_SHUFFLE_HISTORY) {
          shuffleHistory.value.shift()
        }
        shuffleHistory.value.push(currentTrack.value)
      }
      currentIndex.value = index
    }
    currentTrack.value = track
    if (track.is_bilibili && track.track_cover) {
      track._coverUrlSmall = getBiliImageUrl(track.track_cover, 'small')
      track._coverUrlLarge = getBiliImageUrl(track.track_cover, 'large')
      preloadBiliCover(track._coverUrlLarge, track.bvid)
    }
    if (!preservePlayingState) {
      isPlaying.value = true
    }
    currentTime.value = 0
    duration.value = track.duration || 0
    if (!track.is_bilibili) {
      fetchTrackDetail(track.id)
    } else {
      fetchBilibiliLyrics(track.title)
    }
    // nextTrack/prevTrack 的成功路径均以 playTrack 收尾，此处统一回执同步
    notifySync('state')
  }

  function syncPlaylist(tracks: any[]) {
    if (tracks.length > 0) {
      playlist.value = tracks
    }
  }

  function prevTrack() {
    const wasPlaying = isPlaying.value
    if (playMode.value === 'shuffle') {
      // 随机模式：上一首 = 回退到历史中上一首实际播放过的歌曲（对象）
      if (shuffleHistory.value.length > 0) {
        const prevTrackObj = shuffleHistory.value.pop()
        if (!prevTrackObj) return false
        playTrack(prevTrackObj, -1, [], !wasPlaying)
        return true
      }
      return false
    }
    if (currentIndex.value > 0) {
      currentIndex.value--
      const track = playlist.value[currentIndex.value]
      playTrack(track, -1, [], !wasPlaying)
      return true
    }
    return false
  }

  async function nextTrack() {
    const wasPlaying = isPlaying.value
    if (playMode.value === 'shuffle') {
      // 随机模式：由后端从全曲库随机返回下一首（不限于前端已懒加载的分页列表）
      try {
        const excludeIds = [
          (currentTrack.value as any)?.id,
          ...shuffleHistory.value.slice(-19).map(t => t?.id)
        ].filter(id => id != null)
        const res = await request.get('/tracks/random/', {
          params: excludeIds.length ? { exclude: excludeIds.join(',') } : {}
        })
        const track = res.data?.track
        if (!track) return false
        if (currentTrack.value) {
          if (shuffleHistory.value.length >= MAX_SHUFFLE_HISTORY) {
            shuffleHistory.value.shift()
          }
          shuffleHistory.value.push(currentTrack.value)
        }
        playTrack(track, -1, [], !wasPlaying)
        return true
      } catch (error) {
        console.error('获取随机歌曲失败:', error)
        return false
      }
    }
    if (playMode.value === 'single') {
      return true
    }
    if (currentIndex.value < playlist.value.length - 1) {
      currentIndex.value++
      const track = playlist.value[currentIndex.value]
      playTrack(track, -1, [], !wasPlaying)
      return true
    }
    if (loadMoreCallback.value && !isLoadingMore.value) {
      await checkAndLoadMore()
      if (currentIndex.value < playlist.value.length - 1) {
        currentIndex.value++
        const track = playlist.value[currentIndex.value]
        playTrack(track, -1, [], !wasPlaying)
        return true
      }
    }
    return false
  }

  function togglePlay() {
    isPlaying.value = !isPlaying.value
    notifySync('transport')
  }

  function stop() {
    isPlaying.value = false
    currentTime.value = 0
    if (audioElement.value) {
      audioElement.value.pause()
      audioElement.value.currentTime = 0
    }
    notifySync('transport')
  }

  // ===== 同步基础设施：由 useSyncPlayback 调用 =====

  function setSyncAdapter(adapter: SyncAdapter | null) {
    syncAdapter = adapter
  }

  function setApplyingRemote(v: boolean) {
    applyingRemote = v
  }

  function notifySync(kind: 'state' | 'transport') {
    if (!applyingRemote && syncAdapter) syncAdapter.onLocalChange(kind)
  }

  // 用户主动 seek（进度条/歌词点击）：写 audio + store 并回执同步
  function seek(time: number) {
    currentTime.value = time
    if (audioElement.value) {
      audioElement.value.currentTime = time
    }
    notifySync('transport')
  }

  function setCurrentTime(time: number) {
    currentTime.value = time
  }

  function setDuration(dur: number) {
    duration.value = dur
  }

  function setVolume(vol: number) {
    volume.value = vol
  }

  function setAudioElement(el: HTMLAudioElement) {
    audioElement.value = el
  }

  // ===== 本地快照：持久化与恢复 =====

  /** 真实进度：优先取 <audio>（store 的 currentTime 受 timeupdate 节流影响略滞后） */
  function livePosition(): number {
    // 恢复定位中 / src 尚未就绪时，<audio>.currentTime 恒为 0，不能采信
    if (restoringPosition.value) return currentTime.value
    const audio = audioElement.value
    if (audio && audio.src && audio.readyState > 0) {
      const t = audio.currentTime
      if (typeof t === 'number' && isFinite(t)) return t
    }
    return currentTime.value
  }

  function writeSnapshot() {
    if (!currentTrack.value) {
      clearSnapshot()
      return
    }
    saveSnapshot({
      track: currentTrack.value,
      playlist: playlist.value,
      currentIndex: currentIndex.value,
      playMode: playMode.value as any,
      shuffleHistory: shuffleHistory.value,
      currentTime: livePosition(),
      volume: volume.value,
      coverStyleMode: coverStyleMode.value,
      wasPlaying: isPlaying.value
    })
  }

  function schedulePersist() {
    if (persistTimer !== null) window.clearTimeout(persistTimer)
    persistTimer = window.setTimeout(() => {
      persistTimer = null
      lastPositionPersistAt = Date.now()
      writeSnapshot()
    }, PERSIST_DEBOUNCE)
  }

  /** 立即落盘：页面隐藏/卸载前调用，避免去抖窗口内丢掉最后的状态 */
  function persistNow() {
    if (persistTimer !== null) {
      window.clearTimeout(persistTimer)
      persistTimer = null
    }
    lastPositionPersistAt = Date.now()
    writeSnapshot()
  }

  /** 从本地快照恢复曲目/列表/模式/进度，返回快照供调用方决定是否提示续播 */
  function restoreFromSnapshot(): PlaybackSnapshot | null {
    const snap = loadSnapshot()
    if (!snap || !snap.track) return null

    currentTrack.value = snap.track
    playlist.value = snap.playlist
    currentIndex.value = snap.currentIndex
    playMode.value = snap.playMode
    shuffleHistory.value = snap.shuffleHistory
    volume.value = snap.volume
    coverStyleMode.value = snap.coverStyleMode
    currentTime.value = snap.currentTime
    duration.value = Number(snap.track.duration) || 0
    // 恢复后一律从暂停态开始：无用户手势的 play() 会被浏览器拦截
    isPlaying.value = false

    const track = snap.track
    if (track.is_bilibili) {
      if (track.track_cover) {
        track._coverUrlSmall = getBiliImageUrl(track.track_cover, 'small')
        track._coverUrlLarge = getBiliImageUrl(track.track_cover, 'large')
        preloadBiliCover(track._coverUrlLarge, track.bvid)
      }
      fetchBilibiliLyrics(track.title)
    } else if (track.id != null) {
      fetchTrackDetail(track.id)
    }
    return snap
  }

  /** 恢复定位期间屏蔽进度持久化与 timeupdate 覆盖（由 App.vue 在音频定位前后调用） */
  function setRestoringPosition(v: boolean) {
    restoringPosition.value = v
  }

  // 变更类字段变化即写快照（去抖合并，避免一次切歌触发多次写盘）
  // isPlaying 必须在内：暂停后 currentTime 不再变化，只能靠它触发落盘
  watch(
    [currentTrack, playlist, currentIndex, playMode, shuffleHistory, volume, coverStyleMode, isPlaying],
    () => { schedulePersist() }
  )
  // 进度按固定间隔写：timeupdate 约 4Hz，逐次写 localStorage 会卡顿
  watch(currentTime, () => {
    if (!currentTrack.value) return
    const now = Date.now()
    if (now - lastPositionPersistAt < PERSIST_POSITION_INTERVAL) return
    lastPositionPersistAt = now
    writeSnapshot()
  })

  return {
    currentTrack,
    currentTrackDetail,
    playlist,
    currentIndex,
    isPlaying,
    currentTime,
    duration,
    volume,
    audioElement,
    playMode,
    shuffleHistory,
    progress,
    hasPrev,
    hasNext,
    isLoadingMore,
    refreshLibraryTrigger,
    coverStyleMode,
    toggleCoverStyle,
    fetchTrackDetail,
    fetchBilibiliLyrics,
    playTrack,
    syncPlaylist,
    prevTrack,
    nextTrack,
    togglePlay,
    togglePlayMode,
    stop,
    seek,
    setSyncAdapter,
    setApplyingRemote,
    setCurrentTime,
    setDuration,
    setVolume,
    setAudioElement,
    setLoadMoreCallback,
    checkAndLoadMore,
    resetPlayer,
    restoreFromSnapshot,
    persistNow,
    restoringPosition,
    setRestoringPosition,
    triggerLibraryRefresh,
    preloadBiliCover,
    biliCoverCache
  }
})
