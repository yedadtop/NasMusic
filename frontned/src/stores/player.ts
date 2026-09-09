import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '../api'
import { getBiliImageUrl } from '../api'

const MAX_SHUFFLE_HISTORY = 100
const biliCoverCache = new Map<string, string>()

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
          currentTrack.value?.id,
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
  }

  function stop() {
    isPlaying.value = false
    currentTime.value = 0
    if (audioElement.value) {
      audioElement.value.pause()
      audioElement.value.currentTime = 0
    }
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
    setCurrentTime,
    setDuration,
    setVolume,
    setAudioElement,
    setLoadMoreCallback,
    checkAndLoadMore,
    resetPlayer,
    triggerLibraryRefresh,
    preloadBiliCover,
    biliCoverCache
  }
})
