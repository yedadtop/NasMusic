<template>
  <div class="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 pb-4 custom-scrollbar">
    <div class="flex items-center justify-between py-4">
      <h2 class="text-xl font-bold text-gray-900 dark:text-white">艺人</h2>
    </div>

    <div v-if="loading && artists.length === 0" class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
    </div>

    <div v-else-if="artists.length === 0" class="text-center py-20 text-gray-400">
      暂无艺人
    </div>

    <div v-else class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-4 sm:gap-5">
      <div
        v-for="artist in artists"
        :key="artist.id"
        class="group cursor-pointer"
        @click="selectArtist(artist)"
      >
        <div class="relative aspect-square rounded-xl overflow-hidden shadow-md group-hover:shadow-xl transition-all duration-300">
          <img
            :src="getAvatarUrl(artist)"
            :alt="artist.name"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          >
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300 rounded-xl"></div>
          <div class="absolute inset-0 flex items-center justify-center rounded-full">
            <div class="w-14 h-14 rounded-full bg-blue-500/90 flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-300 shadow-lg">
              <svg class="w-7 h-7 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>
        </div>
        <div class="mt-2 text-center">
          <div class="font-semibold text-sm text-blue-500 truncate">{{ artist.name }}</div>
          <div class="text-xs text-gray-500 mt-0.5">{{ artist.track_count }} 首歌曲</div>
        </div>
      </div>
    </div>

    <div ref="sentinel" class="h-10" v-if="hasMore"></div>

    <div v-if="loading && artists.length > 0" class="flex items-center justify-center py-4">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900 dark:border-white"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api'

const router = useRouter()

const artists = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(50)
const totalCount = ref(0)
const hasMore = ref(false)
const sentinel = ref(null)
let observer = null

const fetchArtists = async () => {
  if (loading.value) return
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    const res = await request.get('/artists/', { params })
    const results = res.data.results || []
    if (page.value > 1) {
      artists.value = [...artists.value, ...results]
    } else {
      artists.value = results
    }
    totalCount.value = res.data.count || 0
    hasMore.value = !!res.data.next
  } catch (error) {
    console.error('获取艺人列表失败:', error)
  } finally {
    loading.value = false
  }
}

const selectArtist = (artist) => {
  router.push(`/artists/${artist.id}`)
}

const loadMore = () => {
  if (!hasMore.value || loading.value) return
  page.value++
  fetchArtists()
}

const setupObserver = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  if (!sentinel.value) return
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      loadMore()
    }
  }, { threshold: 0.1 })
  observer.observe(sentinel.value)
}

const getAvatarUrl = (artist) => {
  if (artist.cover) {
    return artist.cover
  }
  return `https://picsum.photos/seed/${artist.id}/200/200`
}

onMounted(() => {
  fetchArtists()
  nextTick(setupObserver)
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 20px; }
.custom-scrollbar { scrollbar-width: thin; scrollbar-color: rgba(0, 0, 0, 0.1) transparent; }
</style>
