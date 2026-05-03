<template>
  <div class="relative w-full h-full overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-blue-50"></div>
    
    <div class="relative z-10 flex items-start justify-center pt-2 sm:pt-8 px-4">
      <div class="w-full max-w-2xl">
        <div 
          class="bg-white/80 backdrop-blur-2xl rounded-2xl shadow-2xl border border-white/50 p-1.5"
          ref="searchContainer"
        >
          <div class="flex items-center bg-gray-100/80 rounded-xl px-4 py-3 backdrop-blur-md">
            <Icon icon="mdi:magnify" class="w-6 h-6 text-gray-400 mr-3 shrink-0" />
            <input 
              type="text" 
              placeholder="搜索歌曲、歌手或专辑..." 
              v-model="searchKeyword"
              @input="handleSearch"
              ref="searchInput"
              class="bg-transparent outline-none flex-1 text-lg text-gray-800 placeholder-gray-400"
              autofocus
            >
            <button 
              v-if="searchKeyword" 
              @click="clearSearch" 
              class="ml-2 text-gray-400 hover:text-gray-600 transition p-1"
            >
              <Icon icon="mdi:close-circle" class="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div v-if="searchKeyword" class="mt-4 text-center text-sm text-gray-400">
          找到 {{ totalCount }} 首歌曲
        </div>
      </div>
    </div>

    <div class="relative z-10 flex-1 overflow-y-auto custom-scrollbar px-4 sm:px-6 md:px-8 pb-4 mt-4">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
      
      <div v-else-if="tracks.length === 0 && searchKeyword" class="text-center py-20 text-gray-400">
        未找到匹配的歌曲
      </div>

      <div 
        v-for="(track, index) in tracks" 
        :key="track.id" 
        :data-track-id="track.id"
        class="group flex items-center justify-between py-3 px-2 hover:bg-white/50 rounded-lg transition cursor-pointer border-b border-gray-100/50 backdrop-blur-sm"
        :class="{ '!bg-blue-50/80': highlightedTrackId === track.id }"
        @click="playTrack(track, index)"
      >
        <div class="flex items-center flex-1 min-w-0">
          <div class="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-md mr-3 sm:mr-4 shrink-0 overflow-hidden">
            <img v-if="track.track_cover" :src="track.track_cover" alt="cover" loading="lazy" class="w-full h-full object-cover">
          </div>
          <div class="flex flex-col truncate min-w-0">
            <span class="font-medium text-sm sm:text-base truncate">{{ track.title }}</span>
            <span class="text-xs text-gray-500 truncate">{{ track.artist_name }}</span>
          </div>
        </div>
        <div class="hidden sm:block w-24 md:w-1/4 text-sm text-gray-500 truncate mx-2">{{ track.album_title || '未知专辑' }}</div>
        <div class="hidden md:block w-1/6 text-sm text-gray-500 truncate">{{ formatDate(track.added_at) }}</div>
        <div class="hidden lg:block w-20 text-sm text-gray-500 text-center">{{ track.format || '-' }}</div>
        <div class="w-16 sm:w-24 text-sm text-gray-500 text-right pr-2 sm:pr-4">{{ formatDuration(track.duration) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Icon } from '@iconify/vue'
import request from '../api'

const emit = defineEmits(['play'])

const tracks = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(50)
const highlightedTrackId = ref(null)
const totalCount = ref(0)
const searchKeyword = ref('')
const allLoaded = ref(false)
const searchInput = ref(null)
const searchTimer = ref(null)
let currentController = null

const handleSearch = () => {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  searchTimer.value = setTimeout(() => {
    currentController?.abort()
    currentController = new AbortController()
    page.value = 1
    allLoaded.value = false
    fetchTracks(currentController.signal)
  }, 300)
}

const fetchTracks = async (signal) => {
  if (loading.value) return
  
  if (page.value === 1) {
    tracks.value = []
  }
  
  loading.value = true
  try {
    const params = {
      page: page.value,
      size: size.value,
      ordering: '-added_at'
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const res = await request.get('/tracks/', { params, signal })
    const results = res.data.results || []
    
    if (page.value > 1) {
      tracks.value = [...tracks.value, ...results]
    } else {
      tracks.value = results
    }
    
    totalCount.value = res.data.count || 0
    if (results.length < size.value || !res.data.next) {
      allLoaded.value = true
    }
  } catch (error) {
    if (error.name === 'CanceledError' || error.name === 'AbortError') return
    console.error('获取歌曲列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadMore = () => {
  if (!allLoaded.value && !loading.value && tracks.value.length > 0) {
    page.value++
    const controller = new AbortController()
    fetchTracks(controller.signal)
  }
}

const playTrack = (track, index) => {
  emit('play', { track, index, tracks: tracks.value })
}

const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return dateStr.split('T')[0]
}

const clearSearch = () => {
  searchKeyword.value = ''
  tracks.value = []
  totalCount.value = 0
  searchInput.value?.focus()
}

onMounted(async () => {
  await nextTick()
  searchInput.value?.focus()
})

onUnmounted(() => {
  if (searchTimer.value) {
    clearTimeout(searchTimer.value)
  }
  currentController?.abort()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.1);
  border-radius: 20px;
}
</style>
