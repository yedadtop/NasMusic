<template>
  <div class="fixed inset-0 z-50 flex text-white selection:bg-white/20 font-sans overflow-hidden bg-gray-900">
    
    <div class="absolute inset-0 z-0 pointer-events-none">
      <div 
        class="absolute inset-0 bg-cover bg-center transition-all duration-1000 scale-125 blur-[80px] opacity-80"
        :style="{ backgroundImage: `url(${player.currentTrack?.track_cover || 'https://picsum.photos/600'})` }"
      ></div>
      <div class="absolute inset-0 bg-black/50 md:bg-black/40"></div>
    </div>

    <div class="relative z-10 flex flex-col md:flex-row w-full h-full mx-auto">
      
      <div class="w-full md:w-1/2 flex-1 md:h-full relative overflow-hidden order-1 md:order-2">
        <div 
          class="w-full h-full overflow-y-auto px-6 md:pl-12 md:pr-32 flex flex-col text-center md:text-left pb-[25vh] md:pb-[50vh] pt-[25vh] md:pt-[45vh] lyrics-scroll" 
          style="mask-image: linear-gradient(180deg, transparent 0%, black 15%, black 85%, transparent 100%); -webkit-mask-image: linear-gradient(180deg, transparent 0%, black 15%, black 85%, transparent 100%);"
          ref="lyricsContainer"
        >
          <template v-if="parsedLyrics && parsedLyrics.length > 0">
            <p 
              v-for="(line, index) in parsedLyrics" 
              :key="index"
              class="transition-colors duration-300 ease-in-out cursor-pointer block py-3 md:py-4"
              :class="getCurrentLyricClass(index)"
              :ref="el => setLyricRef(el, index)"
              @click="seekToLine(line.time)"
            >
              {{ line.text }}
            </p>
          </template>
          <p v-else class="text-white/40 text-2xl md:text-3xl font-bold mt-[10vh]">暂无歌词</p>
        </div>
      </div>

      <div class="w-full md:w-1/2 h-auto md:h-full flex flex-col items-center justify-end md:justify-center px-6 md:px-12 pb-10 md:pb-10 pt-8 md:py-10 shrink-0 order-2 md:order-1 z-20 bg-gradient-to-t from-black/80 via-black/40 to-transparent md:bg-none">
        
        <div class="w-full max-w-[360px] flex flex-col">
          
          <div class="hidden md:block w-full rounded-xl overflow-hidden bg-black/20 shrink-0 relative shadow-2xl transition-transform duration-500 hover:scale-[1.02]" style="aspect-ratio: 1 / 1;">
            <img v-if="player.currentTrack?.track_cover" :src="player.currentTrack.track_cover" alt="cover" class="w-full h-full object-cover" />
            <img v-else src="https://picsum.photos/600" alt="cover" class="w-full h-full object-cover" />
          </div>

          <div class="mt-0 md:mt-8 flex justify-between items-center w-full">
            <div class="flex flex-col truncate pr-4 text-left">
              <h2 class="text-xl md:text-2xl font-bold truncate tracking-wide text-white drop-shadow-sm">
                {{ player.currentTrack?.title || '未知歌曲' }}
              </h2>
              <div class="text-xs md:text-sm text-white/70 truncate mt-1 md:mt-1.5 font-medium">
                {{ player.currentTrack?.artist_name || '未知歌手' }}
              </div>
            </div>
            <div class="flex items-center space-x-3 md:space-x-4 text-white/70 shrink-0">
              <button class="hover:text-white transition"><svg class="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg></button>
              <button class="hover:text-white transition"><svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6"></path></svg></button>
              <button class="hover:text-white transition" @click="showEditModal = true"><svg class="w-4 h-4 md:w-5 md:h-5" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg></button>
            </div>
          </div>

          <div class="mt-5 md:mt-7 flex items-center justify-between w-full text-[10px] md:text-xs font-medium text-white/60 space-x-3 md:space-x-4">
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

          <div class="mt-5 md:mt-6 flex items-center justify-between w-full px-1">
            <button @click="$emit('close')" class="text-white/60 hover:text-white transition p-2 hover:scale-110">
              <svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            
            <button 
              class="text-white hover:text-white/80 active:scale-90 transition-all p-2"
              :class="{ 'opacity-30 cursor-not-allowed': !player.hasPrev }"
              @click="prevTrack"
            >
              <svg class="w-6 h-6 md:w-7 md:h-7" fill="currentColor" viewBox="0 0 24 24"><path d="M18 18l-8.5-6 8.5-6v12zM8 6v12H6V6h2z"/></svg>
            </button>
            
            <button 
              class="text-white hover:scale-105 active:scale-95 transition-all flex items-center justify-center w-12 h-12 md:w-14 md:h-14 drop-shadow-md"
              @click="togglePlay"
            >
              <svg v-if="!player.isPlaying" class="w-10 h-10 md:w-12 md:h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              <svg v-else class="w-10 h-10 md:w-12 md:h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            </button>
            
            <button 
              class="text-white hover:text-white/80 active:scale-90 transition-all p-2"
              :class="{ 'opacity-30 cursor-not-allowed': !player.hasNext }"
              @click="nextTrack"
            >
              <svg class="w-6 h-6 md:w-7 md:h-7" fill="currentColor" viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
            </button>

            <button class="text-white/60 hover:text-white transition p-2 hover:scale-110"><svg class="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          </div>



        </div>
      </div>
      
    </div>

    <EditTrackModal 
      v-model="showEditModal" 
      :track="player.currentTrack"
      @success="handleTrackUpdated"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onBeforeUpdate, onMounted, onUnmounted } from 'vue'
import { usePlayerStore } from '../stores/player'
import EditTrackModal from './EditTrackModal.vue'

const emit = defineEmits(['close', 'trackUpdated'])
const player = usePlayerStore()
const lyricsContainer = ref(null)
const showEditModal = ref(false)
const lyricRefs = ref({})

onBeforeUpdate(() => {
  lyricRefs.value = {}
})

onMounted(async () => {
  await nextTick()
  if (currentLyricIndex.value >= 0) {
    scrollToCenter(currentLyricIndex.value)
  }
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

const handleKeydown = (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  
  switch (e.code) {
    case 'Space':
      e.preventDefault()
      e.stopPropagation()
      togglePlay()
      break
    case 'KeyP':
      e.preventDefault()
      e.stopPropagation()
      togglePlay()
      break
    case 'KeyQ':
      e.preventDefault()
      e.stopPropagation()
      prevTrack()
      break
    case 'KeyE':
      e.preventDefault()
      e.stopPropagation()
      nextTrack()
      break
    case 'KeyZ':
      e.preventDefault()
      e.stopPropagation()
      emit('close')
      break
    case 'ArrowLeft':
      e.preventDefault()
      e.stopPropagation()
      prevTrack()
      break
    case 'ArrowRight':
      e.preventDefault()
      e.stopPropagation()
      nextTrack()
      break
    case 'ArrowUp':
    case 'ArrowDown':
      e.preventDefault()
      e.stopPropagation()
      emit('close')
      break
  }
}

const setLyricRef = (el, index) => {
  if (el) {
    lyricRefs.value[index] = el
  }
}

const parsedLyrics = computed(() => {
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
  if (newIndex >= 0) {
    await nextTick()
    scrollToCenter(newIndex)
  }
})

const scrollToCenter = (index) => {
  const el = lyricRefs.value[index]
  if (el && lyricsContainer.value) {
    const container = lyricsContainer.value
    const containerHeight = container.clientHeight
    const elementTop = el.offsetTop
    const elementHeight = el.clientHeight
    
    // 居中定位计算
    const scrollTarget = elementTop - (containerHeight / 2) + (elementHeight / 2)
    container.scrollTo({
      top: scrollTarget,
      behavior: 'smooth'
    })
  }
}

// 这里的样式同样也把 lg 换成了 md，确保平板电脑也能显示较大的桌面级歌词字号
const getCurrentLyricClass = (index) => {
  if (index === currentLyricIndex.value) {
    return 'text-white font-bold text-[24px] md:text-[34px] opacity-100 drop-shadow-md'
  }
  return 'text-white/40 font-bold text-[24px] md:text-[34px] hover:text-white/70'
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

const prevTrack = () => {
  if (player.prevTrack() && player.audioElement) {
    player.audioElement.src = `http://127.0.0.1:8000/stream/${player.currentTrack.id}/`
    player.audioElement.play().catch(() => {})
  }
}

const nextTrack = () => {
  if (player.nextTrack() && player.audioElement) {
    player.audioElement.src = `http://127.0.0.1:8000/stream/${player.currentTrack.id}/`
    player.audioElement.play().catch(() => {})
  }
}

const seekToLine = (time) => {
  if (player.audioElement) {
    player.audioElement.currentTime = time
    player.setCurrentTime(time)
  }
}

const handleTrackUpdated = () => {
  if (player.currentTrack && player.playlist.length > 0) {
    const index = player.playlist.findIndex(t => t.id === player.currentTrack.id)
    if (index !== -1) {
      player.playlist[index] = { ...player.currentTrack }
    }
  }
  emit('trackUpdated')
}
</script>

<style scoped>
.lyrics-scroll {
  -ms-overflow-style: none;
  scrollbar-width: none;
  scroll-behavior: smooth;
}
.lyrics-scroll::-webkit-scrollbar {
  display: none;
}
</style>