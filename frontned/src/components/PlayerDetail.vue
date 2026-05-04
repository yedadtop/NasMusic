<template>
  <div class="fixed inset-0 z-50 flex text-white selection:bg-white/20 font-sans overflow-hidden bg-gray-900">
    
    <!-- 动态高斯模糊背景 -->
    <div class="absolute inset-0 z-0 pointer-events-none transform-gpu translate-z-0">
      <div 
        class="absolute inset-0 bg-cover bg-center transition-opacity duration-1000 scale-125 blur-[80px] opacity-80 will-change-transform"
        :style="{ backgroundImage: `url(${biliCoverBlobUrl || player.currentTrack?._coverUrlLarge || (player.currentTrack?.is_bilibili ? getBiliImageUrl(player.currentTrack?.track_cover, 'large') : player.currentTrack?.track_cover) || 'https://picsum.photos/600'})` }"
      ></div>
      <div class="absolute inset-0 bg-black/50 md:bg-black/40"></div>
    </div>

    <div class="relative z-10 flex flex-col landscape:flex-row md:flex-row w-full h-full mx-auto">
      
      <!-- 歌词/封面 区域 -->
      <div 
        class="w-full landscape:w-1/2 md:w-1/2 flex-1 landscape:h-full md:h-full relative overflow-hidden order-1 landscape:order-2 md:order-2"
        style="mask-image: linear-gradient(180deg, transparent 0%, black 10%, black 90%, transparent 100%); -webkit-mask-image: linear-gradient(180deg, transparent 0%, black 10%, black 90%, transparent 100%); transform: translateZ(0);"
      >
        <transition name="fade-slow">
          <!-- 状态A：详情数据加载中 -->
          <div v-if="isDetailLoading && !player.currentTrack?.is_bilibili" class="w-full h-full flex items-center justify-center"></div>

          <!-- 状态B：有歌词时 -> 显示滚动歌词面板 -->
          <div 
            v-else-if="parsedLyrics && parsedLyrics.length > 0"
            class="w-full h-full overflow-y-auto px-6 landscape:px-12 md:pl-12 md:pr-32 flex flex-col text-center landscape:text-left md:text-left pb-[35vh] landscape:pb-[50vh] md:pb-[50vh] pt-[35vh] landscape:pt-[45vh] md:pt-[45vh] lyrics-scroll" 
            ref="lyricsContainer"
            @wheel.passive="handleUserInteraction"
            @touchstart.passive="handleUserInteraction"
            @touchmove.passive="handleUserInteraction"
          >
            <p 
              v-for="(line, index) in parsedLyrics" 
              :key="index"
              style="word-break: keep-all; overflow-wrap: break-word;"
              class="transition-all duration-[800ms] ease-[cubic-bezier(0.2,0.8,0.2,1)] cursor-pointer block py-3 md:py-4 transform-gpu origin-center md:origin-left font-bold text-[clamp(19px,4vw,24px)] landscape:text-[clamp(24px,3vw,34px)] md:text-[clamp(24px,3vw,34px)] leading-[1.4]"
              :class="getCurrentLyricClass(index)"
              :ref="el => setLyricRef(el, index)"
              @click="seekToLine(line.time)"
            >
              {{ line.text }}
            </p>
          </div>

          <!-- 状态C：无歌词时 -->
          <div v-else class="w-full h-full flex flex-col items-center landscape:items-start md:items-start justify-center px-6 landscape:px-12 landscape:pr-32 md:pl-12 md:pr-32">
            <div class="md:hidden landscape:hidden w-[70vw] max-w-[320px] aspect-square rounded-2xl overflow-hidden shadow-2xl mb-8 bg-black/20 transition-transform duration-500">
              <img v-if="player.currentTrack?.track_cover" :src="biliCoverBlobUrl || player.currentTrack?._coverUrlLarge || (player.currentTrack?.is_bilibili ? getBiliImageUrl(player.currentTrack.track_cover, 'large') : player.currentTrack.track_cover)" alt="cover" class="w-full h-full object-cover" referrerpolicy="no-referrer" @error="$event.target.src = player.currentTrack?.track_cover || 'https://picsum.photos/600'" />
              <img v-else src="https://picsum.photos/600" alt="cover" class="w-full h-full object-cover" />
            </div>
            <p class="text-white/50 text-center landscape:text-left md:text-left text-lg landscape:text-3xl md:text-3xl font-bold tracking-wider">
              {{ player.currentTrack?.is_bilibili ? '在线音源暂无歌词' : '暂无歌词' }}
            </p>
          </div>
        </transition>
      </div>

      <!-- 播放控制区 -->
      <div class="w-full landscape:w-1/2 md:w-1/2 h-auto landscape:h-full md:h-full flex flex-col items-center justify-end landscape:justify-center md:justify-center px-6 landscape:px-8 md:px-12 pb-10 landscape:pb-4 md:pb-10 pt-8 landscape:pt-4 md:py-10 shrink-0 order-2 landscape:order-1 md:order-1 z-20 bg-gradient-to-t from-black/80 via-black/40 to-transparent landscape:bg-none md:bg-none">
        <div class="w-full max-w-[360px] flex flex-col">
          
          <div class="hidden landscape:block md:block landscape:w-[45vh] md:w-full mx-auto rounded-xl overflow-hidden bg-black/20 shrink-0 relative shadow-2xl transition-transform duration-500 hover:scale-[1.02]" style="aspect-ratio: 1 / 1;">
            <img v-if="player.currentTrack?.track_cover" :src="biliCoverBlobUrl || player.currentTrack?._coverUrlLarge || (player.currentTrack?.is_bilibili ? getBiliImageUrl(player.currentTrack.track_cover, 'large') : player.currentTrack.track_cover)" alt="cover" class="w-full h-full object-cover" referrerpolicy="no-referrer" @error="$event.target.src = player.currentTrack?.track_cover || 'https://picsum.photos/600'" />
            <img v-else src="https://picsum.photos/600" alt="cover" class="w-full h-full object-cover" />
          </div>

          <div class="mt-0 landscape:mt-3 md:mt-8 flex justify-between items-center w-full">
            <div class="flex flex-col truncate pr-4 text-left">
              <h2 class="text-xl landscape:text-xl md:text-2xl font-bold truncate tracking-wide text-white drop-shadow-sm">
                {{ player.currentTrack?.title || '未知歌曲' }}
              </h2>
              <div class="text-sm landscape:text-sm md:text-base text-white/70 truncate mt-1 landscape:mt-1 md:mt-1.5 font-medium">
                {{ player.currentTrack?.artist_name || '未知歌手' }}
              </div>
            </div>
            <div class="flex items-center space-x-3 md:space-x-4 text-white/70 shrink-0">
              <div class="relative">
                <button class="hover:text-white transition" @click="showOptionsMenu = !showOptionsMenu"><Icon icon="mdi:dots-vertical" class="w-4 h-4 md:w-5 md:h-5" /></button>
                <div 
                  v-if="showOptionsMenu"
                  class="absolute right-0 bottom-full mb-2 md:top-full md:mt-2 md:bottom-auto bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-xl py-2 min-w-[120px] z-50"
                >
                  <button 
                    class="flex items-center w-full px-4 py-2 text-sm text-white/80 hover:text-white hover:bg-white/10 transition"
                    @click="showEditModal = true; showOptionsMenu = false"
                  >
                    <Icon icon="mdi:pencil" class="w-4 h-4 mr-2" />
                    修改
                  </button>
                </div>
                <div v-if="showOptionsMenu" class="fixed inset-0 z-40" @click="showOptionsMenu = false"></div>
              </div>
            </div>
          </div>

          <div class="mt-5 landscape:mt-3 md:mt-7 flex items-center justify-between w-full text-xs landscape:text-xs md:text-sm font-medium text-white/60 space-x-3 landscape:space-x-3 md:space-x-4">
            <span class="w-8 text-left">{{ formatTime(player.currentTime) }}</span>
            <div 
              class="flex-1 h-1 md:h-1.5 bg-white/20 rounded-full cursor-pointer relative group flex items-center"
              @click="handleSeek"
            >
              <div class="absolute left-0 h-full bg-white rounded-full transition-all duration-150" :style="{ width: player.progress + '%' }"></div>
              <div 
                class="absolute w-3 h-3 md:w-3.5 md:h-3.5 bg-white rounded-full shadow transition-all duration-150"
                :style="{ left: `calc(${player.progress}% - 6px)` }"
              ></div>
            </div>
            <span class="w-8 text-right">{{ formatTime(player.duration) }}</span>
          </div>

          <div class="mt-5 landscape:mt-3 md:mt-6 flex items-center justify-between w-full px-1">
            <button @click="$emit('close')" class="text-white/60 hover:text-white transition p-2 hover:scale-110 focus-visible:outline-none">
              <Icon icon="mdi:chevron-down" class="w-5 h-5 md:w-6 md:h-6" />
            </button>
            <button class="text-white hover:text-white/80 active:scale-90 transition-all p-2 focus-visible:outline-none" :class="{ 'opacity-30 cursor-not-allowed': !player.hasPrev }" @click="prevTrack">
              <Icon icon="mdi:skip-previous" class="w-6 h-6 md:w-7 md:h-7" />
            </button>
            <button class="text-white hover:scale-105 active:scale-95 transition-all flex items-center justify-center w-12 h-12 md:w-14 md:h-14 drop-shadow-md focus-visible:outline-none" @click="togglePlay">
              <Icon v-if="!player.isPlaying" icon="mdi:play" class="w-10 h-10 md:w-12 md:h-12" />
              <Icon v-else icon="mdi:pause" class="w-10 h-10 md:w-12 md:h-12" />
            </button>
            <button class="text-white hover:text-white/80 active:scale-90 transition-all p-2 focus-visible:outline-none" :class="{ 'opacity-30 cursor-not-allowed': !player.hasNext }" @click="nextTrack">
              <Icon icon="mdi:skip-next" class="w-6 h-6 md:w-7 md:h-7" />
            </button>
            <button class="text-white/60 hover:text-white transition p-2 hover:scale-110 focus-visible:outline-none" :class="{ 'text-blue-400': player.playMode === 'shuffle' || player.playMode === 'single' }" @click="player.togglePlayMode()">
              <Icon v-if="player.playMode === 'shuffle'" icon="mdi:shuffle-variant" class="w-5 h-5" />
              <Icon v-else-if="player.playMode === 'single'" icon="mdi:repeat-once" class="w-5 h-5" />
              <Icon v-else icon="mdi:repeat" class="w-5 h-5" />
            </button>
          </div>

        </div>
      </div>
      
    </div>

    <EditTrackModal v-model="showEditModal" :track="player.currentTrack" @success="handleTrackUpdated" />
    <AppleToast v-model="toastVisible" :message="toastMessage" :type="toastType" />
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onBeforeUpdate, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import { usePlayerStore } from '../stores/player'
import EditTrackModal from './EditTrackModal.vue'
import AppleToast from './AppleToast.vue'
import { STREAM_BASE_URL, getBiliImageUrl } from '../api'
import request from '../api'

const emit = defineEmits(['close', 'trackUpdated'])
const player = usePlayerStore()
const lyricsContainer = ref(null)
const showEditModal = ref(false)
const showOptionsMenu = ref(false)
const lyricRefs = ref({})
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')
const biliCoverBlobUrl = ref('')

let isUserScrolling = false
let scrollTimeout = null

let isSwitchingTrack = false

const isDetailLoading = ref(false)
let loadingTimeout = null

watch(() => player.currentTrack?.id, (newId, oldId) => {
  if (newId !== oldId) {
    isSwitchingTrack = true
    isUserScrolling = false
    
    if (lyricsContainer.value) {
      lyricsContainer.value.scrollTop = 0
    }
    lyricRefs.value = {}

    setTimeout(() => {
      isSwitchingTrack = false
    }, 800)
  }

  if (!newId || player.currentTrack?.is_bilibili) {
    isDetailLoading.value = false
    if (loadingTimeout) {
      clearTimeout(loadingTimeout)
      loadingTimeout = null
    }
    return
  }
  
  if (newId !== player.currentTrackDetail?.id) {
    isDetailLoading.value = true
    if (loadingTimeout) clearTimeout(loadingTimeout)
    loadingTimeout = setTimeout(() => {
      isDetailLoading.value = false
    }, 800)
  } else {
    isDetailLoading.value = false
  }
}, { immediate: true })

watch(() => player.currentTrackDetail?.id, (newDetailId) => {
  if (newDetailId === player.currentTrack?.id) {
    isDetailLoading.value = false
    if (loadingTimeout) {
      clearTimeout(loadingTimeout)
      loadingTimeout = null
    }
  }
})

watch(() => player.currentTrack, async (track) => {
  if (track?.is_bilibili && track.track_cover) {
    const cachedUrl = player.biliCoverCache.get(track.bvid)
    if (cachedUrl) {
      biliCoverBlobUrl.value = cachedUrl
    } else {
      const coverUrl = getBiliImageUrl(track.track_cover, 'large')
      const blobUrl = await player.preloadBiliCover(coverUrl, track.bvid)
      biliCoverBlobUrl.value = blobUrl
    }
  } else {
    biliCoverBlobUrl.value = ''
  }
}, { immediate: true })

const showToast = (message, type = 'error') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const getStreamUrl = async (track) => {
  if (track.is_bilibili) {
    const res = await request.get('/scraper/bili/playurl/', { params: { bvid: track.bvid } })
    if (res.data.audio_url) {
      return `${STREAM_BASE_URL}/api/scraper/bili/proxy/?url=${encodeURIComponent(res.data.audio_url)}`
    }
    throw new Error('获取B站播放链接失败')
  }
  return `${STREAM_BASE_URL}/stream/${track.id}/`
}

onBeforeUpdate(() => {
  lyricRefs.value = {}
})

onMounted(async () => {
  await nextTick()
  if (currentLyricIndex.value >= 0) {
    scrollToCenter(currentLyricIndex.value, 'auto')
  } else if (parsedLyrics.value.length > 0) {
    scrollToCenter(0, 'auto')
  }
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
    scrollTimeout = null
  }
  if (loadingTimeout) {
    clearTimeout(loadingTimeout)
    loadingTimeout = null
  }
  lyricRefs.value = {}
})

const handleKeydown = (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  switch (e.code) {
    case 'Space':
    case 'KeyP':
      e.preventDefault(); e.stopPropagation(); togglePlay(); break
    case 'KeyQ':
    case 'ArrowLeft':
      e.preventDefault(); e.stopPropagation(); prevTrack(); break
    case 'KeyE':
    case 'ArrowRight':
      e.preventDefault(); e.stopPropagation(); nextTrack(); break
    case 'KeyM':
      e.preventDefault(); e.stopPropagation(); player.togglePlayMode(); break
    case 'KeyZ':
      e.preventDefault(); e.stopPropagation(); emit('close'); break
  }
}

const setLyricRef = (el, index) => {
  if (el) {
    lyricRefs.value[index] = el
  }
}

const parsedLyrics = computed(() => {
  if (!player.currentTrack) return []
  if (player.currentTrack.is_bilibili) return []
  
  const lyrics = player.currentTrackDetail?.lyrics
  if (!lyrics) return []
  
  const lines = lyrics.split('\n')
  const result = []
  
  for (const line of lines) {
    const match = line.match(/\[(\d{2}):(\d{2})[:.](\d{2,3})\](.*)/)
    if (match) {
      const minutes = parseInt(match[1])
      const seconds = parseInt(match[2])
      const milliseconds = parseInt(match[3].padEnd(3, '0'))
      const time = minutes * 60 + seconds + milliseconds / 1000
      const text = match[4].trim()
      if (text) {
        result.push({ time, text })
      }
    }
  }
  
  return result.sort((a, b) => a.time - b.time)
})

const currentLyricIndex = computed(() => {
  const currentTime = player.currentTime
  if (!parsedLyrics.value.length) return -1
  for (let i = parsedLyrics.value.length - 1; i >= 0; i--) {
    if (currentTime >= parsedLyrics.value[i].time) {
      return i
    }
  }
  return -1
})

watch(currentLyricIndex, async (newIndex) => {
  if (!isUserScrolling && !isSwitchingTrack) {
    await nextTick()
    if (newIndex >= 0) {
      scrollToCenter(newIndex)
    } else if (newIndex === -1 && parsedLyrics.value.length > 0) {
      scrollToCenter(0, 'auto')
    }
  }
})

watch(parsedLyrics, async (newLyrics) => {
  isUserScrolling = false
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
    scrollTimeout = null
  }

  if (newLyrics && newLyrics.length > 0) {
    await nextTick()
    if (lyricsContainer.value) {
      lyricsContainer.value.scrollTop = 0
    }
  }
})

const handleUserInteraction = () => {
  isUserScrolling = true
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
    scrollTimeout = null
  }
  scrollTimeout = setTimeout(() => {
    isUserScrolling = false
    if (!isSwitchingTrack && currentLyricIndex.value >= 0) {
      scrollToCenter(currentLyricIndex.value)
    }
  }, 3000)
}

const scrollToCenter = (index, behavior = 'smooth') => {
  const el = lyricRefs.value[index]
  if (el && lyricsContainer.value) {
    const container = lyricsContainer.value
    const containerHeight = container.clientHeight
    const elementTop = el.offsetTop
    const elementHeight = el.clientHeight
    
    const scrollTarget = elementTop - (containerHeight / 2) + (elementHeight / 2)
    container.scrollTo({
      top: scrollTarget,
      behavior 
    })
  }
}

const getCurrentLyricClass = (index) => {
  if (index === currentLyricIndex.value) {
    return 'text-white opacity-100 scale-105 md:scale-[1.1] drop-shadow-xl'
  }
  return 'text-white/70 opacity-60 scale-100 hover:text-white/90 hover:scale-[1.02]'
}

const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const togglePlay = () => {
  player.togglePlay()
  if (player.audioElement) {
    if (player.isPlaying) {
      player.audioElement.play().catch(() => {})
    } else {
      player.audioElement.pause()
    }
  }
}

const handleSeek = (e) => {
  if (!player.audioElement || !player.duration) return
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  player.audioElement.currentTime = percent * player.duration
}

// 修复点：切上一曲时，判断 player.isPlaying 状态，而不是强制 play()
const prevTrack = async () => {
  if (player.prevTrack() && player.audioElement) {
    try {
      player.audioElement.src = await getStreamUrl(player.currentTrack)
      if (player.isPlaying) {
        player.audioElement.play().catch(() => {})
      } else {
        player.audioElement.pause()
      }
    } catch (error) {
      showToast('B站链接解析失败，请检查Cookie配置')
      setTimeout(() => nextTrack(), 1500)
    }
  }
}

// 修复点：切下一曲时，判断 player.isPlaying 状态，而不是强制 play()
const nextTrack = async () => {
  if (player.nextTrack() && player.audioElement) {
    try {
      player.audioElement.src = await getStreamUrl(player.currentTrack)
      if (player.isPlaying) {
        player.audioElement.play().catch(() => {})
      } else {
        player.audioElement.pause()
      }
    } catch (error) {
      showToast('B站链接解析失败，请检查Cookie配置')
      setTimeout(() => nextTrack(), 1500)
    }
  }
}

const seekToLine = (time) => {
  if (player.audioElement) {
    player.audioElement.currentTime = time
    player.setCurrentTime(time)
    
    isUserScrolling = false
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
      scrollTimeout = null
    }
  }
}

const handleTrackUpdated = (updatedTrack) => {
  if (updatedTrack) {
    if (player.currentTrack && player.currentTrack.id === updatedTrack.id) {
      player.currentTrack = { ...player.currentTrack, ...updatedTrack }
      if (player.currentTrackDetail && player.currentTrackDetail.id === updatedTrack.id) {
        player.currentTrackDetail = { ...player.currentTrackDetail, ...updatedTrack }
      }
    }
    const index = player.playlist.findIndex(t => t.id === updatedTrack.id)
    if (index !== -1) {
      player.playlist[index] = { ...player.playlist[index], ...updatedTrack }
    }
  }
  emit('trackUpdated')
}

</script>

<style scoped>
.lyrics-scroll {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.lyrics-scroll::-webkit-scrollbar {
  display: none;
}

.fade-slow-enter-active,
.fade-slow-leave-active {
  transition: opacity 0.3s ease;
}
.fade-slow-enter-from,
.fade-slow-leave-to {
  opacity: 0;
}
</style>