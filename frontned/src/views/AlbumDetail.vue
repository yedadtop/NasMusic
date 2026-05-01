<template>
  <div class="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 pb-4 custom-scrollbar">
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>

    <div v-else-if="album" class="pt-4">
      <div class="flex items-center gap-4 mb-6">
        <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-full transition">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <h2 class="text-xl font-bold">专辑详情</h2>
      </div>

      <div class="flex flex-col sm:flex-row gap-6 mb-8">
        <div class="w-48 h-48 rounded-xl overflow-hidden shadow-lg shrink-0 bg-gray-100">
          <img :src="getCoverUrl()" class="w-full h-full object-cover">
        </div>
        <div class="flex flex-col justify-center">
          <h1 class="text-2xl font-bold mb-2">{{ album.title }}</h1>
          <p class="text-gray-500 mb-2">{{ album.artist_name }}</p>
          <p class="text-sm text-gray-400">{{ album.track_count }} 首歌曲</p>
        </div>
      </div>

      <button 
        v-if="album.tracks && album.tracks.length > 0"
        @click="playAll"
        class="mb-4 px-6 py-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        播放全部
      </button>

      <TrackList
        v-if="album.tracks && album.tracks.length > 0"
        :tracks="album.tracks"
        :showAlbum="false"
        @play="handlePlay"
      />
    </div>

    <div v-else class="text-center py-20 text-gray-400">
      专辑不存在
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api'
import TrackList from '../components/TrackList.vue'

const emit = defineEmits(['play'])
const route = useRoute()
const router = useRouter()

const album = ref(null)
const loading = ref(true)

const fetchAlbumDetail = async () => {
  loading.value = true
  try {
    const res = await request.get(`/albums/${route.params.id}/`)
    album.value = res.data
  } catch (error) {
    console.error('获取专辑详情失败:', error)
    album.value = null
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.back()
}

const handlePlay = ({ track, index }) => {
  if (album.value.tracks) {
    emit('play', { track, index, tracks: album.value.tracks })
  }
}

const playAll = () => {
  if (album.value.tracks && album.value.tracks.length > 0) {
    emit('play', { track: album.value.tracks[0], index: 0, tracks: album.value.tracks })
  }
}

const getCoverUrl = () => {
  if (album.value.cover) {
    return album.value.cover
  }
  return `https://picsum.photos/seed/${album.value.id}/300/300`
}

onMounted(() => {
  fetchAlbumDetail()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 20px; }
.custom-scrollbar { scrollbar-width: thin; scrollbar-color: rgba(0, 0, 0, 0.1) transparent; }
</style>
