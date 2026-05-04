<template>
  <div class="relative w-full h-full overflow-hidden">
    <!-- 基础背景 -->
    <div class="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-blue-50"></div>

    <!-- 整个页面作为单一滚动容器，添加了触底滚动监听 -->
    <div class="relative z-10 w-full h-full overflow-y-auto custom-scrollbar" @scroll="handleScroll" ref="scrollContainer">
      
      <!-- 吸顶层：仅作为搜索框的悬浮容器 -->
      <div class="sticky top-0 z-30 w-full flex justify-center pt-4 sm:pt-6 px-4 pb-2">
        <div class="w-full max-w-2xl" ref="searchContainer">
          
          <!-- 搜索框本体：极简通透的毛玻璃效果 -->
          <div class="flex items-center bg-white/10 backdrop-blur-xl rounded-2xl shadow-lg border border-white/20 px-4 py-3 hover:bg-white/20 focus-within:bg-white/30 transition-colors">
            <Icon icon="mdi:magnify" class="w-6 h-6 text-gray-600 mr-3 shrink-0" />
            <input
              type="text"
              placeholder="搜索歌曲、歌手或专辑..."
              v-model="searchKeyword"
              @input="handleSearch"
              ref="searchInput"
              class="bg-transparent outline-none flex-1 text-lg text-gray-800 placeholder-gray-500"
              autofocus
            >
            <button
              v-if="searchKeyword"
              @click="clearSearch"
              class="ml-2 text-gray-500 hover:text-gray-700 transition p-1"
            >
              <Icon icon="mdi:close-circle" class="w-5 h-5" />
            </button>
          </div>

        </div>
      </div>

      <!-- 列表内容展示区 -->
      <div class="px-4 sm:px-6 md:px-8 pb-8 pt-4">
        
        <!-- 1. 首次搜索全局 Loading -->
        <div v-if="(localLoading || biliLoading) && localTracks.length === 0 && biliTracks.length === 0" class="flex flex-col items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3"></div>
          <span class="text-sm text-gray-500">
            <template v-if="localLoading && biliLoading">正在搜索本地和B站音乐...</template>
            <template v-else-if="localLoading">正在搜索本地音乐...</template>
            <template v-else-if="biliLoading">正在搜索B站音乐...</template>
          </span>
        </div>

        <!-- 2. 完全无结果 -->
        <div v-else-if="!localLoading && !biliLoading && localTracks.length === 0 && biliTracks.length === 0 && searchKeyword" class="text-center py-20 text-gray-500">
          未找到匹配的歌曲
        </div>

        <!-- 3. 结果展示区 -->
        <template v-else>
          <!-- 本地音乐列表 -->
          <div v-if="localTracks.length > 0">
            <div class="text-sm font-medium text-gray-600 mb-2 px-2 flex items-center">
              本地音乐
              <span v-if="localLoading" class="ml-2 text-xs text-blue-500">加载中...</span>
            </div>
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

          <!-- B站单独加载提示 -->
          <div v-if="biliLoading && biliTracks.length === 0" :class="{ 'mt-6': localTracks.length > 0 }" class="flex items-center justify-center py-6">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-pink-400"></div>
            <span class="ml-3 text-sm text-gray-500">正在检索 Bilibili...</span>
          </div>

          <!-- B站音乐列表 -->
          <div v-if="biliTracks.length > 0" :class="{ 'mt-6': localTracks.length > 0 }">
            <div class="text-sm font-medium text-gray-600 mb-2 px-2 flex items-center">
              Bilibili 在线
              <span v-if="biliLoading" class="ml-2 text-xs text-blue-500">加载中...</span>
            </div>
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
            </div>
          </div>

          <!-- 本地分页加载更多时的底部提示 -->
          <div v-if="localLoading && localTracks.length > 0" class="flex items-center justify-center py-4">
            <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
            <span class="ml-3 text-sm text-gray-500">正在加载更多...</span>
          </div>
        </template>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onActivated, onDeactivated, nextTick } from 'vue'
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
const scrollContainer = ref(null)
const searchTimer = ref(null)
const scrollPosition = ref(0)
let currentController = null
const MAX_CACHE_SIZE = 20
const CACHE_TTL = 5 * 60 * 1000
const searchCache = new Map()
const FALLBACK_IMAGE_BASE = 'https://picsum.photos/seed'

const getFallbackImageUrl = (id) => `${FALLBACK_IMAGE_BASE}/${id}/100/100`

const cleanExpiredCache = () => {
  const now = Date.now()
  for (const [key, value] of searchCache.entries()) {
    if (now - value.timestamp > CACHE_TTL) {
      searchCache.delete(key)
    }
  }
}

// 处理触底滚动，触发加载更多
const handleScroll = (e) => {
  const { scrollTop, clientHeight, scrollHeight } = e.target
  // 当距离底部小于 50px 时，尝试加载下一页数据
  if (scrollTop + clientHeight >= scrollHeight - 50) {
    loadMore()
  }
}

const handleSearch = () => {
  if (searchTimer.value) {
    clearTimeout(searchTimer.value)
    searchTimer.value = null
  }
  searchTimer.value = setTimeout(() => {
    if (currentController) {
      currentController.abort()
      currentController = null
    }
    currentController = new AbortController()
    page.value = 1
    allLoaded.value = false

    const keyword = searchKeyword.value.trim()
    if (keyword) {
      const cached = searchCache.get(keyword)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        localTracks.value = cached.localTracks
        biliTracks.value = cached.biliTracks
        localCount.value = cached.localCount
        biliCount.value = cached.biliCount
        return
      }
    }

    fetchTracks(currentController.signal)
  }, 500)
}

const getCacheKey = (keyword, source) => `${source}_${keyword}`

const setCache = (keyword, localData, biliData) => {
  cleanExpiredCache()
  if (searchCache.size >= MAX_CACHE_SIZE) {
    const firstKey = searchCache.keys().next().value
    if (firstKey !== undefined) searchCache.delete(firstKey)
  }
  searchCache.set(keyword, {
    localTracks: localData.tracks,
    localCount: localData.count,
    biliTracks: biliData.tracks,
    biliCount: biliData.count,
    timestamp: Date.now()
  })
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
      track_cover: item.pic || item.cover || item.track_cover || '',
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
    localTracks.value.length = 0
    biliTracks.value.length = 0
    localCount.value = 0
    biliCount.value = 0
    return
  }

  if (page.value === 1) {
    localTracks.value.length = 0
    biliTracks.value.length = 0
  }

  const keyword = searchKeyword.value.trim()

  const localPromise = fetchLocalTracks(signal).then(() => ({
    tracks: [...localTracks.value],
    count: localCount.value
  }))

  const biliPromise = fetchBiliTracks(signal).then(() => ({
    tracks: [...biliTracks.value],
    count: biliCount.value
  }))

  const [localData, biliData] = await Promise.allSettled([localPromise, biliPromise])

  if (localData.status === 'fulfilled' && biliData.status === 'fulfilled') {
    if (localData.value.count > 0 || biliData.value.count > 0) {
      setCache(keyword, localData.value, biliData.value)
    }
  }
}

const loadMore = () => {
  // 确保前一次加载完成，并且还有数据可加载时才触发
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
  localTracks.value.length = 0
  biliTracks.value.length = 0
  localCount.value = 0
  biliCount.value = 0
  page.value = 1
  allLoaded.value = false
  searchInput.value?.focus()
}

onActivated(() => {
  requestAnimationFrame(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollPosition.value
    }
    searchInput.value?.focus()
  })
})

onDeactivated(() => {
  if (searchTimer.value) {
    clearTimeout(searchTimer.value)
    searchTimer.value = null
  }
  if (scrollContainer.value) {
    scrollPosition.value = scrollContainer.value.scrollTop
  }
  if (currentController) {
    currentController.abort()
    currentController = null
  }
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