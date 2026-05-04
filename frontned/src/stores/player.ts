import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '../api'

const MAX_SHUFFLE_HISTORY = 100

export const usePlayerStore = defineStore('player', () => {
  const currentTrack = ref(null)
  const currentTrackDetail = ref(null)
  const playlist = ref<any[]>([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)
  const audioElement = ref<HTMLAudioElement | null>(null)
  const playMode = ref('sequential')
  const shuffleOrder = ref<number[]>([])
  const shuffleHistory = ref<number[]>([])
  const loadMoreCallback = ref<(() => Promise<void>) | null>(null)
  const isLoadingMore = ref(false)

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
      return shuffleOrder.value.length > 0
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

  function generateShuffleOrder(excludeIndex = -1) {
    const indices = playlist.value.map((_, i) => i).filter(i => i !== excludeIndex)
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const temp = indices[i]!
      indices[i] = indices[j]!
      indices[j] = temp
    }
    return indices.slice(0, 100)
  }

  function togglePlayMode() {
    if (playMode.value === 'sequential') {
      playMode.value = 'shuffle'
      shuffleOrder.value = generateShuffleOrder(currentIndex.value)
      shuffleHistory.value = []
    } else if (playMode.value === 'shuffle') {
      playMode.value = 'single'
    } else {
      playMode.value = 'sequential'
      shuffleOrder.value = []
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
    shuffleOrder.value = []
    shuffleHistory.value = []
    loadMoreCallback.value = null
    isLoadingMore.value = false
  }

  async function fetchTrackDetail(id: string | number) {
    try {
      const res = await request.get(`/tracks/${id}/`)
      currentTrackDetail.value = res.data
    } catch (error) {
      console.error('获取歌曲详情失败:', error)
    }
  }

  function playTrack(track: any, index = -1, tracks: any[] = [], preservePlayingState = false) {
    if (tracks.length > 0) {
      playlist.value = tracks
      currentIndex.value = index
      shuffleOrder.value = playMode.value === 'shuffle' ? generateShuffleOrder(index) : []
      shuffleHistory.value = []
    } else if (index >= 0) {
      if (playMode.value === 'shuffle' && currentIndex.value !== -1) {
        if (shuffleHistory.value.length >= MAX_SHUFFLE_HISTORY) {
          shuffleHistory.value.shift()
        }
        shuffleHistory.value.push(currentIndex.value)
      }
      currentIndex.value = index
      if (playMode.value === 'shuffle') {
        shuffleOrder.value = generateShuffleOrder(index)
      }
    }
    currentTrack.value = track
    if (!preservePlayingState) {
      isPlaying.value = true
    }
    currentTime.value = 0
    duration.value = track.duration || 0
    if (!track.is_bilibili) {
      fetchTrackDetail(track.id)
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
      if (shuffleHistory.value.length > 0) {
        const prevIndex = shuffleHistory.value.pop()
        if (prevIndex === undefined) return false
        const track = playlist.value[prevIndex]
        currentIndex.value = prevIndex
        playTrack(track, -1, [], !wasPlaying)
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
      if (shuffleOrder.value.length > 0) {
        if (shuffleHistory.value.length >= MAX_SHUFFLE_HISTORY) {
          shuffleHistory.value.shift()
        }
        shuffleHistory.value.push(currentIndex.value)
        const nextIndex = shuffleOrder.value.shift()
        if (nextIndex === undefined) return false
        const track = playlist.value[nextIndex]
        currentIndex.value = nextIndex
        playTrack(track, -1, [], !wasPlaying)
        return true
      }
      return false
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
    fetchTrackDetail,
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
    resetPlayer
  }
})
