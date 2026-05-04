<template>
  <div class="relative w-full h-full flex flex-col overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-blue-50"></div>

    <div class="relative z-10 flex-shrink-0 flex items-start justify-center pt-2 sm:pt-8 px-4">
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
          本地 {{ localCount }} 首 · B站 {{ biliCount }} 首
        </div>
      </div>
    </div>

    <div class="relative z-10 flex-1 overflow-y-auto custom-scrollbar px-4 sm:px-6 md:px-8 pb-4 mt-4 min-h-0">
      <div v-if="localLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>

      <div v-else-if="localTracks.length === 0 && biliTracks.length === 0 && searchKeyword" class="text-center py-20 text-gray-400">
        未找到匹配的歌曲
      </div>

      <template v-else>
        <div v-if="localTracks.length > 0">
          <div class="text-sm font-medium text-gray-500 mb-2 px-2">本地音乐</div>
          <div
            v-for="(track, index) in localTracks"
            :key="track.id"
            :data-track-id="track.id"
            class="group flex items-center justify-between py-3 px-2 hover:bg-white/50 rounded-lg transition cursor-pointer border-b border-gray-100/50 backdrop-blur-sm"
            :class="{ '!bg-blue-50/80': highlightedTrackId === track.id }"
            @click="playTrack(track, index, 'local')"
          >
            <div class="flex items-center flex-1 min-w-0">
              <div class="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-md mr-3 sm:mr-4 shrink-0 overflow-hidden">
                <img v-if="track.track_cover" :src="track.track_cover" alt="cover" loading="lazy" @error="$event.target.src = `https://picsum.photos/seed/${track.id}/100/100`" class="w-full h-full object-cover">
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

        <div v-if="biliTracks.length > 0" :class="{ 'mt-6': localTracks.length > 0 }">
          <div class="text-sm font-medium text-gray-500 mb-2 px-2">Bilibili 在线</div>
          <div
            v-for="(track, index) in biliTracks"
            :key="track.id"
            :data-track-id="track.id"
            class="group flex items-center justify-between py-3 px-2 hover:bg-white/50 rounded-lg transition cursor-pointer border-b border-gray-100/50 backdrop-blur-sm"
            :class="{ '!bg-blue-50/80': highlightedTrackId === track.id }"
            @click="playTrack(track, index, 'bili')"
          >
            <div class="flex items-center flex-1 min-w-0">
              <div class="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-md mr-3 sm:mr-4 shrink-0 overflow-hidden">
                <img v-if="track.track_cover" :src="track.is_bilibili ? getBiliImageUrl(track.track_cover, 'small') : track.track_cover" alt="cover" loading="lazy" referrerpolicy="no-referrer" @error="$event.target.src = `https://picsum.photos/seed/${track.id}/100/100`" class="w-full h-full object-cover">
              </div>
              <div class="flex flex-col truncate min-w-0">
                <span class="font-medium text-sm sm:text-base truncate">{{ track.title }}</span>
                <span class="text-xs text-gray-500 truncate">{{ track.author }}</span>
              </div>
            </div>
            <div class="w-16 sm:w-24 text-sm text-gray-500 text-right pr-2 sm:pr-4">{{ track.duration }}</div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Icon } from '@iconify/vue'
import request from '../api'
import { getBiliImageUrl } from '../api'

const emit = defineEmits(['play'])

const localTracks = ref([])
const biliTracks = ref([])
const page = ref(1)
const size = ref(50)
const highlightedTrackId = ref(null)
const localCount = ref(0)
const biliCount = ref(0)
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

const localLoading = ref(false)
const biliLoading = ref(false)

const fetchLocalTracks = async (signal) => {
  if (localLoading.value) return
  localLoading.value = true
  try {
    const params = {
      page: page.value,
      size: size.value,
      ordering: '-added_at'
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }

    const localRes = await request.get('/tracks/', { params, signal }).catch(() => ({ data: { results: [], count: 0 } }))

    const localResults = localRes.data.results || []

    if (page.value > 1) {
      localTracks.value = [...localTracks.value, ...localResults]
    } else {
      localTracks.value = localResults
    }

    localCount.value = localRes.data.count || localTracks.value.length

    if (localResults.length < size.value || !localRes.data.next) {
      allLoaded.value = true
    }
  } catch (error) {
    if (error.name === 'CanceledError' || error.name === 'AbortError') return
    console.error('获取本地歌曲列表失败:', error)
  } finally {
    localLoading.value = false
  }
}

const fetchBiliTracks = async (signal) => {
  biliLoading.value = true
  try {
    const keyword = searchKeyword.value.trim()
    const biliRes = await request.get('/scraper/bili/search/', { params: { keyword }, signal }).catch(() => ({ data: { results: [], count: 0 } }))

    const biliResults = (biliRes.data.results || []).map(item => ({
      id: item.bvid,
      title: item.title,
      author: item.author,
      artist_name: item.author,
      track_cover: item.track_cover,
      duration: 0,
      is_bilibili: true,
      bvid: item.bvid,
      original_duration: item.duration
    }))

    biliTracks.value = biliResults
    biliCount.value = biliRes.data.count || biliTracks.value.length
  } catch (error) {
    if (error.name === 'CanceledError' || error.name === 'AbortError') return
    console.error('获取B站歌曲列表失败:', error)
  } finally {
    biliLoading.value = false
  }
}

const fetchTracks = async (signal) => {
  if (!searchKeyword.value.trim()) {
    localTracks.value = []
    biliTracks.value = []
    localCount.value = 0
    biliCount.value = 0
    return
  }

  if (page.value === 1) {
    localTracks.value = []
    biliTracks.value = []
  }

  fetchLocalTracks(signal)
  fetchBiliTracks(signal)
}

const loadMore = () => {
  if (!allLoaded.value && !localLoading.value && localTracks.value.length > 0) {
    page.value++
    const controller = new AbortController()
    fetchTracks(controller.signal)
  }
}

const playTrack = (track, index, source) => {
  emit('play', { track, index, tracks: source === 'bili' ? biliTracks.value : localTracks.value, source })
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
  localTracks.value = []
  biliTracks.value = []
  localCount.value = 0
  biliCount.value = 0
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
