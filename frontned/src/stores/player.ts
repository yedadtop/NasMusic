import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '../api'

export const usePlayerStore = defineStore('player', () => {
  const currentTrack = ref(null)
  const currentTrackDetail = ref(null)
  const playlist = ref([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)
  const audioElement = ref(null)
  const playMode = ref('sequential')
  const shuffleOrder = ref([])
  const shuffleHistory = ref([])

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
    return currentIndex.value < playlist.value.length - 1
  })

  function generateShuffleOrder(excludeIndex = -1) {
    const indices = playlist.value.map((_, i) => i).filter(i => i !== excludeIndex)
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indices[i], indices[j]] = [indices[j], indices[i]]
    }
    return indices
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

  async function fetchTrackDetail(id) {
    try {
      const res = await request.get(`/tracks/${id}/`)
      currentTrackDetail.value = res.data
    } catch (error) {
      console.error('获取歌曲详情失败:', error)
    }
  }

  function playTrack(track, index = -1, tracks = []) {
    if (tracks.length > 0) {
      playlist.value = tracks
      currentIndex.value = index
      shuffleOrder.value = playMode.value === 'shuffle' ? generateShuffleOrder(index) : []
      shuffleHistory.value = []
    } else if (index >= 0) {
      if (playMode.value === 'shuffle' && currentIndex.value !== -1) {
        shuffleHistory.value.push(currentIndex.value)
      }
      currentIndex.value = index
      if (playMode.value === 'shuffle') {
        shuffleOrder.value = generateShuffleOrder(index)
      }
    }
    currentTrack.value = track
    isPlaying.value = true
    currentTime.value = 0
    duration.value = track.duration || 0
    fetchTrackDetail(track.id)
  }

  function prevTrack() {
    if (playMode.value === 'shuffle') {
      if (shuffleHistory.value.length > 0) {
        const prevIndex = shuffleHistory.value.pop()
        const track = playlist.value[prevIndex]
        currentIndex.value = prevIndex
        playTrack(track)
        return true
      }
      return false
    }
    if (currentIndex.value > 0) {
      currentIndex.value--
      const track = playlist.value[currentIndex.value]
      playTrack(track)
      return true
    }
    return false
  }

  function nextTrack() {
    if (playMode.value === 'shuffle') {
      if (shuffleOrder.value.length > 0) {
        shuffleHistory.value.push(currentIndex.value)
        const nextIndex = shuffleOrder.value.shift()
        const track = playlist.value[nextIndex]
        currentIndex.value = nextIndex
        playTrack(track)
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
      playTrack(track)
      return true
    }
    return false
  }

  function togglePlay() {
    isPlaying.value = !isPlaying.value
  }

  function setCurrentTime(time) {
    currentTime.value = time
  }

  function setDuration(dur) {
    duration.value = dur
  }

  function setVolume(vol) {
    volume.value = vol
  }

  function setAudioElement(el) {
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
    fetchTrackDetail,
    playTrack,
    prevTrack,
    nextTrack,
    togglePlay,
    togglePlayMode,
    setCurrentTime,
    setDuration,
    setVolume,
    setAudioElement
  }
})
