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

  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  const hasPrev = computed(() => currentIndex.value > 0)
  const hasNext = computed(() => currentIndex.value < playlist.value.length - 1)

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
    } else if (index >= 0) {
      currentIndex.value = index
    }
    currentTrack.value = track
    isPlaying.value = true
    currentTime.value = 0
    duration.value = track.duration || 0
    fetchTrackDetail(track.id)
  }

  function prevTrack() {
    if (currentIndex.value > 0) {
      currentIndex.value--
      const track = playlist.value[currentIndex.value]
      playTrack(track)
      return true
    }
    return false
  }

  function nextTrack() {
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
    progress,
    hasPrev,
    hasNext,
    fetchTrackDetail,
    playTrack,
    prevTrack,
    nextTrack,
    togglePlay,
    setCurrentTime,
    setDuration,
    setVolume,
    setAudioElement
  }
})
