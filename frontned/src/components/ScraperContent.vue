<template>
  <div class="apple-font text-[#1d1d1f]">

    <AppleToast v-if="toastVisible" v-model="toastVisible" :message="toastMessage" :type="toastType" />
    <AppleConfirmModal
      v-model="showConfirmModal"
      :title="confirmTitle"
      :message="confirmMessage"
      :confirm-text="confirmConfirmText"
      cancel-text="取消"
      @confirm="handleConfirm"
    />

    <section class="mb-10 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50">
      <div class="flex items-center mb-3">
        <div class="w-10 h-10 bg-[#f3e5f5] text-[#af52de] rounded-[10px] flex items-center justify-center mr-4">
          <Icon icon="mdi:image-multiple" class="w-5 h-5" />
        </div>
        <h2 class="text-xl font-semibold tracking-tight">批量操作</h2>
      </div>

      <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
        对音乐库中的封面、标签等信息进行批量管理和更新操作。
      </p>

      <div class="flex flex-col sm:flex-row gap-4">
        <div class="w-full sm:w-auto">
          <el-button
            type="warning"
            :loading="scanning"
            @click="openRescanCoversConfirm"
            class="w-full custom-apple-button !bg-[#ff9500] !border-[#ff9500]"
          >
            <Icon icon="mdi:image-refresh" class="w-4 h-4 mr-2" />
            更新所有封面
          </el-button>
        </div>
        <div class="w-full sm:w-auto">
          <el-button
            type="primary"
            :loading="scraping"
            @click="openScrapeCoversConfirm"
            class="w-full custom-apple-button"
          >
            <Icon icon="mdi:cloud-download" class="w-4 h-4 mr-2" />
            补全缺失封面
          </el-button>
        </div>
        <div class="w-full sm:w-auto">
          <el-button
            type="success"
            :loading="scrapingLyrics"
            @click="openScrapeLyricsConfirm"
            class="w-full custom-apple-button !bg-[#34c759] !border-[#34c759]"
          >
            <Icon icon="mdi:music-note" class="w-4 h-4 mr-2" />
            补全缺失歌词
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { Icon } from '@iconify/vue'
import AppleToast from './AppleToast.vue'
import AppleConfirmModal from './AppleConfirmModal.vue'

const emit = defineEmits(['task-started'])

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const scraping = ref(false)
const scrapingLyrics = ref(false)
const scanning = ref(false)

const showConfirmModal = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmConfirmText = ref('')
const confirmAction = ref(null)

const openRescanCoversConfirm = () => {
  confirmTitle.value = '更新所有封面'
  confirmMessage.value = '确定要更新所有歌曲的内嵌封面吗？这将删除并重新提取所有封面图片，可能需要较长时间。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'rescanCovers'
  showConfirmModal.value = true
}

const openScrapeCoversConfirm = () => {
  confirmTitle.value = '补全缺失封面'
  confirmMessage.value = '确定要通过网络爬取所有缺失封面的歌曲封面吗？系统会自动检测物理文件中没有封面的歌曲，然后通过API接口获取并嵌入高清封面。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'scrapeCovers'
  showConfirmModal.value = true
}

const openScrapeLyricsConfirm = () => {
  confirmTitle.value = '补全缺失歌词'
  confirmMessage.value = '确定要通过网络爬取所有缺失歌词的歌曲吗？系统会自动检测数据库中没有歌词的歌曲，然后通过LRCLIB接口获取并嵌入歌词。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'scrapeLyrics'
  showConfirmModal.value = true
}

const handleConfirm = async () => {
  showConfirmModal.value = false
  if (confirmAction.value === 'rescanCovers') {
    await rescanCovers()
  } else if (confirmAction.value === 'scrapeCovers') {
    await scrapeCovers()
  } else if (confirmAction.value === 'scrapeLyrics') {
    await scrapeLyrics()
  }
}

const rescanCovers = async () => {
  try {
    scanning.value = true
    const res = await axios.post('/api/scanner/run/', {
      force_reextract_cover: true
    })
    emit('task-started', res.data.task_id)
    showToast('封面重提取任务已在后台启动', 'success')
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scanning.value = false
  }
}

const scrapeCovers = async () => {
  try {
    scraping.value = true
    const res = await axios.post('/api/scanner/run/')
    emit('task-started', res.data.task_id)
    await axios.post('/api/scraper/batch/scrape/', {
      task_id: res.data.task_id
    })
    showToast('补全封面任务已在后台启动', 'success')
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scraping.value = false
  }
}

const scrapeLyrics = async () => {
  try {
    scrapingLyrics.value = true
    const res = await axios.post('/api/scanner/run/')
    emit('task-started', res.data.task_id)
    await axios.post('/api/scraper/batch/scrape_lyrics/', {
      task_id: res.data.task_id
    })
    showToast('补全歌词任务已在后台启动', 'success')
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scrapingLyrics.value = false
  }
}
</script>

<style scoped>
@reference "tailwindcss";

.apple-font {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:deep(.custom-apple-button) {
  @apply rounded-[12px] px-8 h-[44px] font-semibold text-[15px] transition-all duration-300 bg-[#0071e3] border-none shadow-sm;
}
:deep(.custom-apple-button:hover) {
  @apply bg-[#0077ED] transform scale-[1.02];
}
:deep(.custom-apple-button:active) {
  @apply transform scale-[0.98];
}
</style>
