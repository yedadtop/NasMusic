<template>
  <div class="flex flex-col h-screen w-screen bg-white text-gray-800 overflow-hidden font-sans">
    <div class="flex flex-1 overflow-hidden" v-show="!isFullScreen">
      <aside class="hidden md:flex flex-col w-16 bg-gray-100 rounded-2xl m-2 ml-1 shrink-0 items-center py-4 gap-1">
        <router-link to="/" class="sidebar-icon group" active-class="sidebar-icon-active" exact-active-class="sidebar-icon-active">
          <Icon icon="mdi:music-box-multiple" class="w-6 h-6" />
          <span class="sidebar-tooltip">本地音乐</span>
        </router-link>
        <router-link to="/artists" class="sidebar-icon group" active-class="sidebar-icon-active">
          <Icon icon="mdi:account-music" class="w-6 h-6" />
          <span class="sidebar-tooltip">艺人</span>
        </router-link>
        <router-link to="/albums" class="sidebar-icon group" active-class="sidebar-icon-active">
          <Icon icon="mdi:album" class="w-6 h-6" />
          <span class="sidebar-tooltip">专辑</span>
        </router-link>
        <router-link to="/search" class="sidebar-icon group" active-class="sidebar-icon-active">
          <Icon icon="mdi:magnify" class="w-6 h-6" />
          <span class="sidebar-tooltip">搜索</span>
        </router-link>
        <router-link to="/settings" class="sidebar-icon group" active-class="sidebar-icon-active">
          <Icon icon="mdi:cog" class="w-6 h-6" />
          <span class="sidebar-tooltip">设置</span>
        </router-link>
      </aside>

      <main class="flex-1 flex flex-col min-w-0 bg-white relative">
        <header class="h-14 sm:h-16 flex items-center justify-between px-4 sm:px-6 md:px-8 shrink-0 md:hidden">
          <div class="flex items-center space-x-2 sm:space-x-4 md:space-x-6 shrink-0">
            <router-link to="/" class="mobile-nav-icon" active-class="mobile-nav-icon-active" exact-active-class="mobile-nav-icon-active">
              <Icon icon="mdi:music-box-multiple" class="w-6 h-6" />
            </router-link>
            <router-link to="/artists" class="mobile-nav-icon" active-class="mobile-nav-icon-active">
              <Icon icon="mdi:account-music" class="w-6 h-6" />
            </router-link>
            <router-link to="/albums" class="mobile-nav-icon" active-class="mobile-nav-icon-active">
              <Icon icon="mdi:album" class="w-6 h-6" />
            </router-link>
          </div>
          <div class="flex items-center space-x-2 sm:space-x-4">
            <router-link 
              v-if="!showSearch"
              to="/search"
              class="p-2 hover:bg-gray-100 rounded-lg transition shrink-0"
            >
              <Icon icon="mdi:magnify" class="w-5 h-5 text-gray-500" />
            </router-link>
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
                  <Icon icon="mdi:close" class="w-4 h-4" />
                </button>
              </div>
            </div>
            <router-link to="/settings" class="mobile-nav-icon shrink-0" active-class="mobile-nav-icon-active" @click.stop>
              <Icon icon="mdi:cog" class="w-5 h-5" />
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

    <router-view v-if="isFullScreen" v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <footer v-show="!isFullScreen" class="h-16 sm:h-20 bg-white/75 backdrop-blur-2xl saturate-[150%] border-t border-gray-200/40 flex items-center justify-between px-4 sm:px-6 shrink-0 z-10 relative">

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
          class="text-gray-500 hover:text-gray-900 active:scale-90 transition-all p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.hasPrev }"
          @click.stop="prevTrack"
        >
          <Icon icon="mdi:skip-previous" class="w-6 h-6" />
        </button>
        
        <button 
          class="text-gray-900 active:scale-90 transition-transform flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12"
          :class="{ 'opacity-30 cursor-not-allowed': !player.currentTrack }"
          @click.stop="togglePlay"
        >
          <Icon v-if="!player.isPlaying" icon="mdi:play" class="w-8 h-8 sm:w-9 sm:h-9 ml-1" />
          <Icon v-else icon="mdi:pause" class="w-8 h-8 sm:w-9 sm:h-9" />
        </button>
        
        <button 
          class="text-gray-500 hover:text-gray-900 active:scale-90 transition-all p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.hasNext }"
          @click.stop="nextTrack"
        >
          <Icon icon="mdi:skip-next" class="w-6 h-6 sm:w-7 sm:h-7" />
        </button>
      </div>

      <div class="hidden md:flex items-center justify-end space-x-5 w-1/3 text-gray-400">
        <button
          class="text-gray-500 hover:text-gray-900 active:scale-90 transition-all p-2"
          :class="{ 'text-blue-500': player.playMode === 'shuffle' || player.playMode === 'single' }"
          @click.stop="player.togglePlayMode()"
        >
          <Icon v-if="player.playMode === 'shuffle'" icon="mdi:shuffle-variant" class="w-5 h-5" />
          <Icon v-else-if="player.playMode === 'single'" icon="mdi:repeat-once" class="w-5 h-5" />
          <Icon v-else icon="mdi:repeat" class="w-5 h-5" />
        </button>
        <button 
          class="hover:text-gray-900 transition p-2"
          :class="{ 'opacity-30 cursor-not-allowed': !player.currentTrack }"
          @click="scrollToCurrentTrack"
        >
          <Icon icon="lucide:crosshair" class="w-5 h-5" />
        </button>
      </div>

      <div 
        class="absolute top-0 left-0 w-full h-[2px] bg-transparent cursor-pointer hover:h-1.5 transition-all duration-200 group/progress"
        @click="handleSeek"
        ref="progressBar"
        @mousedown="startDrag"
        @mousemove="onDrag"
        @mouseup="endDrag"
        @mouseleave="endDrag"
      >
        <div class="absolute top-0 left-0 h-full bg-gray-200/50 w-full rounded-full"></div>
        <div class="h-full bg-[#0071e3] relative transition-all rounded-full" :style="{ width: player.progress + '%' }">
          <div 
            class="absolute w-3 h-3 bg-[#0071e3] rounded-full shadow-md transition-all duration-150"
            :class="isDragging ? 'opacity-100 scale-125' : 'opacity-0 group-hover/progress:opacity-100 group-hover/progress:scale-110'"
            :style="{ right: '-6px', top: '50%', transform: 'translateY(-50%)' }"
          ></div>
        </div>
      </div>
    </footer>
    
    <Transition name="slide-up">
      <PlayerDetail v-if="showPlayerDetail" @close="showPlayerDetail = false" @track-updated="handleTrackUpdated" />
    </Transition>

    <VolumeTooltip :visible="showVolumeTooltip" />

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
import { Icon } from '@iconify/vue'
import PlayerDetail from './components/PlayerDetail.vue'
import VolumeTooltip from './components/VolumeTooltip.vue'
import { usePlayerStore } from './stores/player'
import { Headset, Position, Setting, Search, Star, DArrowLeft, CaretRight, DArrowRight, Document, Operation, Refresh, Switch, Collection, VideoPause } from '@element-plus/icons-vue'
import { STREAM_BASE_URL } from './api'

const showPlayerDetail = ref(false)
const searchKeyword = ref('')
const showSearch = ref(false)
const showVolumeTooltip = ref(false)
const searchInput = ref(null)
const libraryRef = ref(null)
const progressBar = ref(null)
const isDragging = ref(false)
const route = useRoute()
const player = usePlayerStore()
const audioRef = ref(null)
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)
const isFullScreen = computed(() => route.meta?.fullScreen === true)
const searchContainer = ref(null)
let volumeTimer = null

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
    case 'KeyM':
      e.preventDefault()
      if (!showPlayerDetail.value) {
        player.togglePlayMode()
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
      e.preventDefault()
      adjustVolume(0.1)
      break
    case 'ArrowDown':
      e.preventDefault()
      adjustVolume(-0.1)
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
    audioRef.value.src = `${STREAM_BASE_URL}/stream/${track.id}/`
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
    audioRef.value.src = `${STREAM_BASE_URL}/stream/${player.currentTrack.id}/`
    audioRef.value.play()
  }
}

const handleSeek = (e) => {
  if (!audioRef.value || !player.duration) return
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audioRef.value.currentTime = percent * player.duration
}

const startDrag = (e) => {
  if (!audioRef.value || !player.duration) return
  isDragging.value = true
  handleSeek(e)
}

const onDrag = (e) => {
  if (!isDragging.value || !audioRef.value || !player.duration) return
  const rect = progressBar.value.getBoundingClientRect()
  const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  audioRef.value.currentTime = percent * player.duration
}

const endDrag = () => {
  isDragging.value = false
}

const prevTrack = () => {
  if (player.prevTrack() && audioRef.value) {
    audioRef.value.src = `${STREAM_BASE_URL}/stream/${player.currentTrack.id}/`
    audioRef.value.play()
  }
}

const nextTrack = () => {
  if (player.nextTrack() && audioRef.value) {
    audioRef.value.src = `${STREAM_BASE_URL}/stream/${player.currentTrack.id}/`
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

const adjustVolume = (delta) => {
  const newVolume = Math.max(0, Math.min(1, player.volume + delta))
  player.setVolume(newVolume)
  if (audioRef.value) {
    audioRef.value.volume = newVolume
  }
  showVolumeTooltip.value = true
  if (volumeTimer) clearTimeout(volumeTimer)
  volumeTimer = setTimeout(() => {
    showVolumeTooltip.value = false
  }, 1500)
}

watch(() => player.currentTrack, (track) => {
  if (track) {
    document.title = `${track.title} - ${track.artist_name || '未知歌手'}`
  } else {
    document.title = 'NasMusic'
  }
}, { immediate: true })
</script>

<style>
@reference "tailwindcss";

.sidebar-icon {
  @apply w-11 h-11 flex items-center justify-center rounded-xl text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-all relative;
}
.sidebar-icon-active {
  @apply bg-blue-500 text-white hover:bg-blue-600 hover:text-white;
}
.sidebar-tooltip {
  @apply absolute left-full ml-3 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity whitespace-nowrap;
}

.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 20px; }

/* 基础样式适配 */
.nav-btn { @apply p-3 rounded-xl hover:bg-gray-200 transition hover:text-black flex items-center justify-center; }
.nav-btn.active { @apply bg-blue-600 text-white shadow-md; }
.tab-link { @apply transition pb-1 border-b-2 border-transparent; }
.tab-active { @apply text-black font-bold border-black; }

.mobile-nav-icon { @apply p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-all; }
.mobile-nav-icon-active { @apply text-gray-700; }

/* 页面淡入淡出动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.4s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); opacity: 0; }
</style>
