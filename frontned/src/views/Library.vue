<template>
  <div class="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 pb-4 custom-scrollbar">
    <div class="sticky top-0 z-10 bg-white border-b border-gray-200">
      <div class="flex items-center py-3 px-2 text-xs text-gray-500 font-medium uppercase tracking-wider">
        <div class="w-10 h-5 sm:w-12 sm:h-5 mr-3 sm:mr-4 shrink-0 text-center">#</div>
        <div class="flex-1 min-w-0 flex items-center cursor-pointer hover:text-gray-700 transition" @click="toggleSort('title')">
          <span class="truncate">标题</span>
          <span v-if="sortBy === 'title'" class="ml-1 text-blue-500">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
        </div>
        <div class="hidden sm:flex sm:w-24 md:w-1/4 items-center cursor-pointer hover:text-gray-700 transition truncate mx-2" @click="toggleSort('album_title')">
          <span class="truncate">专辑</span>
          <span v-if="sortBy === 'album_title'" class="ml-1 text-blue-500 shrink-0">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
        </div>
        <div class="hidden md:flex md:w-1/6 items-center cursor-pointer hover:text-gray-700 transition" @click="toggleSort('added_at')">
          <span>添加日期</span>
          <span v-if="sortBy === 'added_at'" class="ml-1 text-blue-500">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
        </div>
        <div class="hidden lg:block w-20 text-center text-xs cursor-pointer hover:text-gray-700 transition" @click="toggleSort('format')">
          <span>格式</span>
          <span v-if="sortBy === 'format'" class="ml-1 text-blue-500">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
        </div>
        <div class="w-16 sm:w-24 flex items-center justify-end cursor-pointer hover:text-gray-700 transition pr-2 sm:pr-4" @click="toggleSort('duration')">
          <span class="text-right">时长</span>
          <span v-if="sortBy === 'duration'" class="ml-1 text-blue-500">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
        </div>
        <div class="w-8 shrink-0"></div>
      </div>
    </div>
    <div 
      v-for="(track, index) in tracks" 
      :key="track.id" 
      :data-track-id="track.id"
      class="group flex items-center justify-between py-3 px-2 hover:bg-gray-50 rounded-lg transition cursor-pointer border-b border-gray-50"
      :class="{ '!bg-blue-50': highlightedTrackId === track.id }"
      @click="playTrack(track, index)"
    >
      <div class="flex items-center flex-1 min-w-0">
        <div class="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-md mr-3 sm:mr-4 shrink-0 overflow-hidden">
          <img v-if="track.track_cover" :src="track.track_cover" alt="cover" class="w-full h-full object-cover">
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
      <div class="relative">
        <button 
          class="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-black transition"
          @click.stop="showMoreMenu(track, $event)"
        >
          <span class="text-xl">•••</span>
        </button>
        <div v-if="showingMoreMenu === track.id" class="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-100 z-10">
          <button 
            class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition"
            @click.stop="handleEdit(track)"
          >
            编辑
          </button>
          <button 
            class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 transition"
            @click.stop="openDeleteConfirm(track)"
          >
            删除
          </button>
        </div>
      </div>
    </div>
    
    <div v-if="tracks.length === 0 && !loading" class="text-center py-20 text-gray-400">
      {{ searchKeyword ? '未找到匹配的歌曲' : '暂无歌曲，请先在设置中扫描音乐库' }}
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>

    <div ref="sentinel" class="h-10"></div>

    <EditTrackModal 
      v-model="showEditModal" 
      :track="currentTrack" 
      @success="handleEditSuccess"
    />
    
    <AppleConfirmModal 
      v-model="showConfirmModal"
      title="删除确认"
      message="可在设置页面的回收站找回删除的歌曲!"
      confirm-text="删除"
      cancel-text="取消"
      @confirm="handleDeleteConfirm"
    />
    
    <AppleToast 
      v-model="toastVisible"
      :message="toastMessage"
      :type="toastType"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue' // 新增 onUnmounted
import request from '../api'
import EditTrackModal from '../components/EditTrackModal.vue'
import AppleConfirmModal from '../components/AppleConfirmModal.vue'
import AppleToast from '../components/AppleToast.vue'
import { usePlayerStore } from '../stores/player'

const emit = defineEmits(['play'])
const player = usePlayerStore()

const tracks = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(50)
const highlightedTrackId = ref(null)
const sortBy = ref('added_at')
const sortOrder = ref('desc')

watch(() => player.currentTrack?.id, (newId) => {
  highlightedTrackId.value = newId
}, { immediate: true })

const totalCount = ref(0)
const searchKeyword = ref('')
const allLoaded = ref(false)
const sentinel = ref(null)
const showingMoreMenu = ref(null)
const showEditModal = ref(false)
const currentTrack = ref(null)
const showConfirmModal = ref(false)
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')
let observer = null

// 新增：用于存放重试的定时器
let retryTimer = null

const totalPages = computed(() => Math.ceil(totalCount.value / size.value))

const fetchTracks = async () => {
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }

  if (loading.value) return
  
  if (page.value === 1) {
    tracks.value = []
  }
  
  loading.value = true
  try {
    const params = {
      page: page.value,
      size: size.value,
      ordering: `${sortOrder.value === 'desc' ? '-' : ''}${sortBy.value}`
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const res = await request.get('/tracks/', { params })
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
    console.error('获取歌曲列表失败:', error)
    if (page.value === 1) {
      tracks.value = []
      totalCount.value = 0
      
      // page为1时，后端不通则每1秒重试一次
      retryTimer = setTimeout(() => {
        fetchTracks()
      }, 2000)
    } else {
      // 核心修复：如果是加载更多时（page > 1）遇到 502，必须把页码退回去
      page.value--
      // 为了防止无限循环报错，临时设为 allLoaded，阻止继续触发滚动请求
      allLoaded.value = true 
      showToast('网络连接异常，请稍后再试', 'error')
    }
  } finally {
    loading.value = false
  }
}

const changePage = (newPage) => {
  page.value = newPage
  fetchTracks()
}

const loadMore = () => {
  // 核心修复：增加 tracks.value.length > 0 判断
  // 只有在已经成功拿到第一页数据的情况下，滚动到底部才允许加载下一页
  if (!allLoaded.value && !loading.value && tracks.value.length > 0) {
    page.value++
    fetchTracks()
  }
}

const playTrack = (track, index) => {
  if (player.currentTrack?.id === track.id) return
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

const toggleSort = (column) => {
  if (sortBy.value === column) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = column
    sortOrder.value = 'asc'
  }
  page.value = 1
  fetchTracks()
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

watch(loading, (isLoading) => {
  if (!isLoading) {
    nextTick(setupObserver)
  }
})

onMounted(() => {
  fetchTracks()
  document.addEventListener('click', () => {
    showingMoreMenu.value = null
  })
})

// 新增：组件卸载时清理定时器，防止内存泄漏和无效请求
onUnmounted(() => {
  if (retryTimer) {
    clearTimeout(retryTimer)
  }
  if (observer) {
    observer.disconnect()
    observer = null
  }
})

const showMoreMenu = (track, event) => {
  event.stopPropagation()
  showingMoreMenu.value = showingMoreMenu.value === track.id ? null : track.id
}

const handleEdit = (track) => {
  showingMoreMenu.value = null
  currentTrack.value = track
  showEditModal.value = true
}

const trackToDelete = ref(null)

const openDeleteConfirm = (track) => {
  showingMoreMenu.value = null
  trackToDelete.value = track
  showConfirmModal.value = true
}

const handleDeleteConfirm = async () => {
  showConfirmModal.value = false
  if (!trackToDelete.value) return

  const deletedTrack = trackToDelete.value
  const deletedIndex = tracks.value.findIndex(t => t.id === deletedTrack.id)
  
  if (deletedIndex !== -1) {
    tracks.value.splice(deletedIndex, 1)
    totalCount.value = Math.max(0, totalCount.value - 1)
  }
  
  if (player.currentTrack && player.currentTrack.id === deletedTrack.id) {
    player.stop()
  }
  
  try {
    await request.delete(`/tracks/${deletedTrack.id}/`)
    showToast('删除成功', 'success')
  } catch (error) {
    console.error('删除失败:', error)
    if (deletedIndex !== -1) {
      tracks.value.splice(deletedIndex, 0, deletedTrack)
      totalCount.value++
    }
    showToast('删除失败，请重试', 'error')
  }
}

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const handleEditSuccess = (updatedTrack) => {
  if (updatedTrack) {
    const index = tracks.value.findIndex(t => t.id === updatedTrack.id)
    if (index !== -1) {
      tracks.value[index] = { ...tracks.value[index], ...updatedTrack }
    }
    if (player.currentTrack && player.currentTrack.id === updatedTrack.id) {
      player.currentTrack = { ...player.currentTrack, ...updatedTrack }
      if (player.currentTrackDetail && player.currentTrackDetail.id === updatedTrack.id) {
        player.currentTrackDetail = { ...player.currentTrackDetail, ...updatedTrack }
      }
    }
  }
}

const scrollToCurrentTrack = async () => {
  if (!player.currentTrack) return
  await nextTick()
  const trackElement = document.querySelector(`[data-track-id="${player.currentTrack.id}"]`)
  if (trackElement) {
    trackElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
    trackElement.classList.add('bg-blue-50')
    setTimeout(() => {
      trackElement.classList.remove('bg-blue-50')
    }, 1500)
  }
}

defineExpose({ fetchTracks, searchKeyword, scrollToCurrentTrack, tracks, allLoaded, page })
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
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.1) transparent;
}
</style>
