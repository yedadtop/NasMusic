<template>
  <div class="flex flex-col h-screen w-screen bg-white text-gray-800 overflow-hidden font-sans">
    <div class="flex flex-1 overflow-hidden">
      <main class="flex-1 flex flex-col min-w-0 bg-white relative">
        <header class="h-14 sm:h-16 flex items-center justify-between px-4 sm:px-6 md:px-8 shrink-0">
          <div class="flex items-center space-x-3 sm:space-x-4 md:space-x-6 text-base md:text-lg font-medium text-gray-500 shrink-0">
            <router-link to="/" class="tab-link whitespace-nowrap" active-class="tab-active">本地歌曲</router-link>
            <router-link to="/albums" class="hidden sm:block tab-link whitespace-nowrap" active-class="tab-active">专辑</router-link>
            <router-link to="/artists" class="hidden sm:block tab-link whitespace-nowrap" active-class="tab-active">艺人</router-link>
          </div>
          <div class="flex items-center space-x-2 sm:space-x-4">
            <button 
              v-if="!showSearch"
              @click.stop="showSearch = true"
              class="p-2 hover:bg-gray-100 rounded-lg transition shrink-0"
            >
              <Search class="w-5 h-5 text-gray-500" />
            </button>
            <div v-else class="absolute right-16 sm:right-24 md:right-32 top-2 sm:top-3 z-50" ref="searchContainer">
              <div class="bg-gray-100 rounded-full px-4 py-2 flex items-center shadow-lg">
                <Search class="w-4 h-4 text-gray-400 mr-2" />
                <input 
                  type="text" 
                  placeholder="搜索歌曲..." 
                  v-model="searchKeyword"
                  @input="handleSearch"
                  @keydown.escape="closeSearch"
                  ref="searchInput"
                  class="bg-transparent outline-none w-40 sm:w-64 text-sm text-gray-800"
                >
                <button @click.stop="closeSearch" class="ml-2 text-gray-400 hover:text-gray-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>
            <router-link to="/settings" class="p-2 hover:bg-gray-100 rounded-lg transition shrink-0" @click.stop>
              <Setting class="w-5 h-5 text-gray-500" />
            </router-link>
          </div>
        </header>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" ref="libraryRef" @play="handlePlayTrack" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>

    <footer class="h-16 sm:h-20 bg-white/75 backdrop-blur-2xl saturate-[150%] border-t border-gray-200/40 flex items-center justify-between px-4 sm:px-6 shrink-0 z-10 relative">

      <div class="flex items-center cursor-pointer group flex-1 md:flex-none md:w-1/3 min-w-0 pr-3 h-full" @click="showPlayerDetail = true">
        <div class="relative w-11 h-11 sm:w-14 sm:h-14 bg-gray-100 rounded-[10px] shadow-sm mr-3 sm:mr-4 shrink-0 overflow-hidden group-hover:shadow-md transition-shadow">
           <img v-if="player.currentTrack?.track_cover" :src="player.currentTrack.track_cover" alt="cover" class="w-full h-full object-cover">
           <img v-else src="https://picsum.photos/150" alt="cover" class="w-full h-full object-cover">
           <div class="absolute inset-0 border border-black/5 rounded-[10px]"></div>
        </div>
        <div class="flex flex-col truncate min-w-0 justify-center">
          <span class="font-semibold text-[15px] sm:text-base text-gray-900 truncate tracking-tight leading-tight">{{ player.currentTrack?.title || '未选择歌曲' }}</span>
          <span class="text-[12px] sm:text-sm text-gray-500 truncate mt-0.5 font-medium">{{ player.currentTrack?.artist_name || '未知歌手' }}</span>
        </div>
      </div>

      <div class="flex items-center justify-end md:absolute md:left-1/2 md:top-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2 space-x-4 sm:space-x-6 shrink-0 pr-2">
        
        <button 
          class="hidden md:block text-gray-500 hover:text-gray-900 active:scale-90 transition-all p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.hasPrev }"
          @click.stop="prevTrack"
        >
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M18 18l-8.5-6 8.5-6v12zM8 6v12H6V6h2z"/></svg>
        </button>
        
        <button 
          class="text-gray-900 active:scale-90 transition-transform flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12"
          :class="{ 'opacity-30 cursor-not-allowed': !player.currentTrack }"
          @click.stop="togglePlay"
        >
          <svg v-if="!player.isPlaying" class="w-8 h-8 sm:w-9 sm:h-9 ml-1" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          <svg v-else class="w-8 h-8 sm:w-9 sm:h-9" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
        </button>
        
        <button 
          class="text-gray-500 hover:text-gray-900 active:scale-90 transition-all p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.hasNext }"
          @click.stop="nextTrack"
        >
          <svg class="w-6 h-6 sm:w-7 sm:h-7" fill="currentColor" viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
        </button>
      </div>

      <div class="hidden md:flex items-center justify-end space-x-5 w-1/3 text-gray-400">
        <button 
          class="hover:text-gray-900 transition p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.currentTrack }"
          @click="scrollToCurrentTrack"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        </button>
      </div>

      <div 
        class="absolute top-0 left-0 w-full h-[2px] bg-transparent cursor-pointer hover:h-1.5 transition-all duration-200 group/progress" 
        @click="handleSeek"
        ref="progressBar"
      >
        <div class="absolute top-0 left-0 h-full bg-gray-200/50 w-full"></div>
        <div class="h-full bg-[#0071e3] relative transition-all" :style="{ width: player.progress + '%' }">
          <div class="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-[#0071e3] rounded-full opacity-0 group-hover/progress:opacity-100 shadow-sm transition-opacity"></div>
        </div>
      </div>
    </footer>
    
    <Transition name="slide-up">
      <PlayerDetail v-if="showPlayerDetail" @close="showPlayerDetail = false" @track-updated="handleTrackUpdated" />
    </Transition>

    <audio 
      ref="audioRef" 
      @timeupdate="handleTimeUpdate"
      @loadedmetadata="handleLoadedMetadata"
      @ended="handleEnded"
    ></audio>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import PlayerDetail from './components/PlayerDetail.vue'
import { usePlayerStore } from './stores/player'
import { Headset, Position, Setting, Search, Star, DArrowLeft, CaretRight, DArrowRight, Document, Operation, Refresh, Switch, Collection, VideoPause } from '@element-plus/icons-vue'

const showPlayerDetail = ref(false)
const searchKeyword = ref('')
const showSearch = ref(false)
const searchInput = ref(null)
const libraryRef = ref(null)
const route = useRoute()
const player = usePlayerStore()
const audioRef = ref(null)
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)
const searchContainer = ref(null)

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

const closeSearch = () => {
  const hadKeyword = searchKeyword.value
  showSearch.value = false
  searchKeyword.value = ''
  
  if (libraryRef.value && route.path === '/' && hadKeyword) {
    libraryRef.value.searchKeyword = ''
    libraryRef.value.page = 1
    libraryRef.value.allLoaded = false
    libraryRef.value.fetchTracks()
  }
}

watch(showSearch, async (isShowing) => {
  if (isShowing) {
    await nextTick()
    searchInput.value?.focus()
  }
})

const handleClickOutside = (e) => {
  if (showSearch.value && searchContainer.value && !searchContainer.value.contains(e.target)) {
    closeSearch()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('click', handleClickOutside)
  player.setAudioElement(audioRef.value)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('click', handleClickOutside)
})

const handleKeydown = (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  
  switch (e.code) {
    case 'Space':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        togglePlay()
      }
      break
    case 'KeyP':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        togglePlay()
      }
      break
    case 'KeyQ':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        prevTrack()
      }
      break
    case 'KeyE':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        nextTrack()
      }
      break
    case 'KeyZ':
      e.preventDefault()
      showPlayerDetail.value = !showPlayerDetail.value
      break
    case 'ArrowLeft':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        prevTrack()
      }
      break
    case 'ArrowRight':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        nextTrack()
      }
      break
    case 'ArrowUp':
    case 'ArrowDown':
      e.preventDefault()
      showPlayerDetail.value = !showPlayerDetail.value
      break
  }
}

let searchTimer = null
const handleSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (libraryRef.value && route.path === '/') {
      libraryRef.value.searchKeyword = searchKeyword.value
      libraryRef.value.page = 1
      libraryRef.value.allLoaded = false
      libraryRef.value.fetchTracks()
    }
  }, 300)
}

watch(() => route.path, (newPath) => {
  if (newPath === '/') {
    searchKeyword.value = ''
  }
})

const handlePlayTrack = ({ track, index, tracks }) => {
  const wasSearching = showSearch.value && searchKeyword.value
   
  if (wasSearching) {
    showSearch.value = false
    searchKeyword.value = ''
  }
  
  player.playTrack(track, index, tracks)
  if (audioRef.value) {
    audioRef.value.src = `http://127.0.0.1:8000/stream/${track.id}/`
    audioRef.value.play()
  }
  
  if (libraryRef.value) {
    if (wasSearching) {
      libraryRef.value.searchKeyword = ''
      libraryRef.value.page = 1
      libraryRef.value.allLoaded = false
      libraryRef.value.fetchTracks().then(() => {
        libraryRef.value.scrollToCurrentTrack()
      })
    } else {
      libraryRef.value.scrollToCurrentTrack()
    }
  }
}

const togglePlay = () => {
  if (!player.currentTrack) return
  player.togglePlay()
  if (audioRef.value) {
    if (player.isPlaying) {
      audioRef.value.play()
    } else {
      audioRef.value.pause()
    }
  }
}

const handleTimeUpdate = () => {
  if (audioRef.value) {
    player.setCurrentTime(audioRef.value.currentTime)
  }
}

const handleLoadedMetadata = () => {
  if (audioRef.value) {
    player.setDuration(audioRef.value.duration)
  }
}

const handleEnded = () => {
  if (!player.nextTrack()) {
    player.isPlaying = false
  } else if (audioRef.value) {
    audioRef.value.src = `http://127.0.0.1:8000/stream/${player.currentTrack.id}/`
    audioRef.value.play()
  }
}

const handleSeek = (e) => {
  if (!audioRef.value || !player.duration) return
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audioRef.value.currentTime = percent * player.duration
}

const prevTrack = () => {
  if (player.prevTrack() && audioRef.value) {
    audioRef.value.src = `http://127.0.0.1:8000/stream/${player.currentTrack.id}/`
    audioRef.value.play()
  }
}

const nextTrack = () => {
  if (player.nextTrack() && audioRef.value) {
    audioRef.value.src = `http://127.0.0.1:8000/stream/${player.currentTrack.id}/`
    audioRef.value.play()
  }
}

const scrollToCurrentTrack = () => {
  if (libraryRef.value && route.path === '/') {
    libraryRef.value.scrollToCurrentTrack()
  }
}

const handleTrackUpdated = () => {
  if (libraryRef.value && route.path === '/') {
    libraryRef.value.fetchTracks()
  }
}
</script>

<style>
@reference "tailwindcss";

/* 保持扁平化滚动条样式 */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 20px; }

/* 基础样式适配 */
.nav-btn { @apply p-3 rounded-xl hover:bg-gray-200 transition hover:text-black flex items-center justify-center; }
.nav-btn.active { @apply bg-blue-600 text-white shadow-md; }
.tab-link { @apply transition pb-1 border-b-2 border-transparent; }
.tab-active { @apply text-black font-bold border-black; }

/* 页面淡入淡出动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.4s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); opacity: 0; }
</style>
