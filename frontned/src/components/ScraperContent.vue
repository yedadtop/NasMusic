<template>
  <div class="apple-font text-[#1d1d1f]">

    <AppleToast v-if="toastVisible" v-model="toastVisible" :message="toastMessage" :type="toastType" />
    <AppleProgressModal
      v-model="showProgressModal"
      :title="progressModalTitle"
      :message="progressModalMessage"
      :action-type="progressModalAction"
      @started="handleTaskStarted"
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
            更新封面数据库
          </el-button>
        </div>
        <div class="w-full sm:w-auto">
          <el-button
            type="primary"
            @click="openScrapeCoversModal"
            class="w-full custom-apple-button"
          >
            <Icon icon="mdi:cloud-download" class="w-4 h-4 mr-2" />
            补全缺失封面
          </el-button>
        </div>
        <div class="w-full sm:w-auto">
          <el-button
            type="success"
            @click="openScrapeLyricsModal"
            class="w-full custom-apple-button !bg-[#34c759] !border-[#34c759]"
          >
            <Icon icon="mdi:music-note" class="w-4 h-4 mr-2" />
            补全缺失歌词
          </el-button>
        </div>
      </div>

      <div class="mt-6 p-4 bg-[#f5f5f7] rounded-[12px] text-[13px] text-[#86868b] leading-relaxed">
        <div class="mb-3">
          <span class="font-semibold text-[#1d1d1f]">更新封面数据库：</span>
          扫描提取歌曲的封面并保存到后端和数据库。适合手动添加的歌曲。
        </div>
        <div class="mb-3">
          <span class="font-semibold text-[#1d1d1f]">补全缺失封面：</span>
          自动检测缺少封面的歌曲，通过API爬取封面并嵌入歌曲文件中，同时保存封面到后端和数据库。
        </div>
        <div>
          <span class="font-semibold text-[#1d1d1f]">补全缺失歌词：</span>
          自动检测缺少歌词的歌曲，通过LRCLIB歌词库接口获取对应歌词并嵌入歌曲文件中。
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
import AppleProgressModal from './AppleProgressModal.vue'

const emit = defineEmits(['task-started'])

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const scanning = ref(false)

const showProgressModal = ref(false)
const progressModalTitle = ref('')
const progressModalMessage = ref('')
const progressModalAction = ref('scrapeCovers')

const openScrapeCoversModal = () => {
  progressModalTitle.value = '补全缺失封面'
  progressModalMessage.value = '通过网络爬取缺失封面的歌曲封面，系统会自动检测并通过API接口获取高清封面。'
  progressModalAction.value = 'scrapeCovers'
  showProgressModal.value = true
}

const openScrapeLyricsModal = () => {
  progressModalTitle.value = '补全缺失歌词'
  progressModalMessage.value = '通过网络爬取缺失歌词的歌曲，系统会自动检测并通过LRCLIB接口获取歌词。'
  progressModalAction.value = 'scrapeLyrics'
  showProgressModal.value = true
}

const handleTaskStarted = (taskId) => {
  emit('task-started', taskId)
}

const openRescanCoversConfirm = async () => {
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
