<template>
  <div class="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 pb-4 custom-scrollbar">
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>

    <div v-else-if="artist" class="pt-4">
      <div class="flex items-center gap-4 mb-6">
        <button @click="goBack" class="p-2 hover:bg-gray-100 rounded-full transition">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <h2 class="text-xl font-bold">艺人详情</h2>
      </div>

      <div class="flex flex-col sm:flex-row items-center sm:items-start gap-6 mb-8">
        <div class="w-40 h-40 rounded-full overflow-hidden shadow-lg bg-gray-100 shrink-0">
          <img v-if="artist.avatar_url" :src="artist.avatar_url" class="w-full h-full object-cover">
          <img v-else src="https://picsum.photos/200" class="w-full h-full object-cover">
        </div>
        <div class="flex flex-col items-center sm:items-start justify-center text-center sm:text-left">
          <h1 class="text-2xl font-bold mb-2">{{ artist.name }}</h1>
          <p class="text-gray-500 mb-1">{{ artist.track_count }} 首歌曲</p>
          <p class="text-sm text-gray-400">{{ artist.album_count }} 张专辑</p>
        </div>
      </div>

      <button 
        v-if="artist.tracks && artist.tracks.length > 0"
        @click="playAll"
        class="mb-4 px-6 py-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        播放全部
      </button>

      <TrackList
        v-if="artist.tracks && artist.tracks.length > 0"
        :tracks="artist.tracks"
        :showAlbum="true"
        @play="handlePlay"
      />
    </div>

    <div v-else class="text-center py-20 text-gray-400">
      艺人不存在
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

const artist = ref(null)
const loading = ref(true)

const fetchArtistDetail = async () => {
  loading.value = true
  try {
    const res = await request.get(`/artists/${route.params.id}/`)
    artist.value = res.data
  } catch (error) {
    console.error('获取艺人详情失败:', error)
    artist.value = null
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.back()
}

const handlePlay = ({ track, index }) => {
  if (artist.value.tracks) {
    emit('play', { track, index, tracks: artist.value.tracks })
  }
}

const playAll = () => {
  if (artist.value.tracks && artist.value.tracks.length > 0) {
    emit('play', { track: artist.value.tracks[0], index: 0, tracks: artist.value.tracks })
  }
}

onMounted(() => {
  fetchArtistDetail()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.1); border-radius: 20px; }
.custom-scrollbar { scrollbar-width: thin; scrollbar-color: rgba(0, 0, 0, 0.1) transparent; }
</style>
