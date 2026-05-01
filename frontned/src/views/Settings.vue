<template>
  <div class="max-w-3xl mx-auto px-6 py-10 pb-32 apple-font text-[#1d1d1f]">
    <div class="mb-8">
      <div class="flex items-center border-b border-gray-200/60">
        <button
          @click="activeTab = 'settings'"
          class="pb-3 px-1 text-[17px] font-semibold border-b-2 transition-colors mr-6"
          :class="activeTab === 'settings' ? 'border-[#0071e3] text-[#0071e3]' : 'border-transparent text-[#86868b] hover:text-[#1d1d1f]'"
        >
          设置
        </button>
        <button
          @click="activeTab = 'interfaces'"
          class="pb-3 px-1 text-[17px] font-semibold border-b-2 transition-colors mr-6"
          :class="activeTab === 'interfaces' ? 'border-[#0071e3] text-[#0071e3]' : 'border-transparent text-[#86868b] hover:text-[#1d1d1f]'"
        >
          接口
        </button>
        <button
          @click="activeTab = 'trash'"
          class="pb-3 px-1 text-[17px] font-semibold border-b-2 transition-colors"
          :class="activeTab === 'trash' ? 'border-[#0071e3] text-[#0071e3]' : 'border-transparent text-[#86868b] hover:text-[#1d1d1f]'"
        >
          回收站
        </button>
      </div>
    </div>

    <AppleToast v-if="toastVisible" v-model="toastVisible" :message="toastMessage" :type="toastType" />
    <AppleConfirmModal
      v-if="activeTab === 'settings'"
      v-model="showConfirmModal"
      :title="confirmTitle"
      :message="confirmMessage"
      :confirm-text="confirmConfirmText"
      cancel-text="取消"
      @confirm="handleConfirm"
    />

    <template v-if="activeTab === 'settings'">
      <h1 class="text-[32px] md:text-[40px] font-bold mb-8 md:mb-12 tracking-tight">设置</h1>

      <section class="mb-8 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50 transition-all">
        <div class="flex items-center mb-3">
          <div class="w-10 h-10 bg-[#e8f2ff] text-[#0071e3] rounded-[10px] flex items-center justify-center mr-4">
            <FolderOpened class="w-5 h-5" />
          </div>
          <h2 class="text-xl font-semibold tracking-tight">媒体库路径</h2>
        </div>
        
        <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
          配置服务器扫描音乐文件的本地物理路径。支持多级目录递归扫描。
        </p>

        <div class="flex flex-col gap-4">
          <el-input
            v-model="musicPath"
            placeholder="例如: /home/music 或 C:\Music"
            class="flex-1 custom-apple-input"
          />
          <div class="flex flex-col sm:flex-row gap-4">
            <el-button
              type="primary"
              :loading="saving"
              @click="saveConfig"
              class="w-full sm:w-auto custom-apple-button"
            >
              保存路径
            </el-button>
            <el-button
              type="primary"
              :loading="scanning"
              @click="startScan"
              class="w-full sm:w-auto custom-apple-button"
            >
              立即扫描
            </el-button>
          </div>
        </div>
      </section>

      <section class="mb-10 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center">
            <Loading v-if="scanning" class="w-5 h-5 text-[#0071e3] animate-spin mr-3" />
            <CircleCheck v-else class="w-5 h-5 text-[#34c759] mr-3" />
            <span class="text-[17px] font-semibold">{{ statusText }}</span>
          </div>
          <span class="text-[13px] font-mono text-[#86868b] bg-[#f5f5f7] px-2 py-1 rounded-md">ID: #{{ scanTask.id }}</span>
        </div>

        <div class="space-y-6">
          <div>
            <div class="flex justify-between text-[13px] font-medium mb-2 text-[#86868b]">
              <span>总体进度</span>
              <span>{{ scanTask.progress }}%</span>
            </div>
            <el-progress 
              :percentage="scanTask.progress" 
              :status="scanTask.status === 'completed' ? 'success' : ''"
              :stroke-width="8"
              :show-text="false"
              color="#0071e3"
            />
          </div>

          <div class="grid grid-cols-5 gap-0 py-5 bg-[#f5f5f7] rounded-[14px]">
            <div class="text-center">
              <div class="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1">已处理</div>
              <div class="text-[22px] font-bold text-[#1d1d1f]">{{ scanTask.processed }}</div>
            </div>
            <div class="text-center border-x border-gray-200/60">
              <div class="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1">新增</div>
              <div class="text-[22px] font-bold text-[#34c759]">{{ scanTask.added }}</div>
            </div>
            <div class="text-center border-x border-gray-200/60">
              <div class="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1">更新</div>
              <div class="text-[22px] font-bold text-[#0071e3]">{{ scanTask.updated }}</div>
            </div>
            <div class="text-center border-x border-gray-200/60">
              <div class="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1">删除</div>
              <div class="text-[22px] font-bold text-[#ff3b30]">{{ scanTask.deleted }}</div>
            </div>
            <div class="text-center">
              <div class="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1">总计</div>
              <div class="text-[22px] font-bold text-[#1d1d1f]">{{ scanTask.total }}</div>
            </div>
          </div>

          <div v-if="scanTask.current_file" class="text-[13px] text-[#86868b] truncate pb-1">
            正在处理: {{ scanTask.current_file }}
          </div>
        </div>
      </section>

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
          <el-button
            type="warning"
            :loading="scanning"
            @click="openRescanCoversConfirm"
            class="w-full sm:w-auto custom-apple-button !bg-[#ff9500] !border-[#ff9500]"
          >
            <Icon icon="mdi:image-refresh" class="w-4 h-4 mr-2" />
            更新所有封面
          </el-button>
          <el-button
            type="primary"
            :loading="scraping"
            @click="openScrapeCoversConfirm"
            class="w-full sm:w-auto custom-apple-button"
          >
            <Icon icon="mdi:cloud-download" class="w-4 h-4 mr-2" />
            补全缺失封面
          </el-button>
          <el-button
            type="success"
            :loading="scrapingLyrics"
            @click="openScrapeLyricsConfirm"
            class="w-full sm:w-auto custom-apple-button !bg-[#34c759] !border-[#34c759]"
          >
            <Icon icon="mdi:music-note" class="w-4 h-4 mr-2" />
            补全缺失歌词
          </el-button>
        </div>
      </section>

      <section class="mt-12">
        <h2 class="text-[13px] font-semibold text-[#86868b] uppercase tracking-widest mb-4 ml-2">快捷键说明</h2>
        <div class="bg-white rounded-[20px] shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50 overflow-hidden">
          <div class="divide-y divide-gray-100">
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">播放 / 暂停</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">Space</kbd>
                <span class="text-gray-400">/</span>
                <kbd class="apple-kbd">P</kbd>
              </div>
            </div>
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">上一首</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">Q</kbd>
                <span class="text-gray-400">/</span>
                <kbd class="apple-kbd">←</kbd>
              </div>
            </div>
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">下一首</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">E</kbd>
                <span class="text-gray-400">/</span>
                <kbd class="apple-kbd">→</kbd>
              </div>
            </div>
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">切换播放模式</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">M</kbd>
              </div>
            </div>
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">音量增加 / 减少</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">↑</kbd>
                <span class="text-gray-400">/</span>
                <kbd class="apple-kbd">↓</kbd>
              </div>
            </div>
            <div class="flex justify-between items-center p-4 sm:px-6">
              <span class="text-[15px] font-medium">打开 / 关闭播放详情</span>
              <div class="flex gap-2">
                <kbd class="apple-kbd">Z</kbd>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <template v-else-if="activeTab === 'interfaces'">
      <InterfacesContent />
    </template>

    <template v-else-if="activeTab === 'trash'">
      <TrashContent />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, defineAsyncComponent } from 'vue'
import axios from 'axios'
import { FolderOpened, Loading, CircleCheck } from '@element-plus/icons-vue'
import { Icon } from '@iconify/vue'
import AppleToast from '../components/AppleToast.vue'
import AppleConfirmModal from '../components/AppleConfirmModal.vue'

const InterfacesContent = defineAsyncComponent(() => import('../components/InterfacesContent.vue'))
const TrashContent = defineAsyncComponent(() => import('../components/TrashContent.vue'))

const activeTab = ref('settings')

const musicPath = ref('')
const scanning = ref(false)
const scraping = ref(false)
const scrapingLyrics = ref(false)
const saving = ref(false)
let timer = null

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const showConfirmModal = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmConfirmText = ref('')
const confirmAction = ref(null)
const confirmFile = ref(null)

const openRescanCoversConfirm = () => {
  confirmTitle.value = '更新所有封面'
  confirmMessage.value = '确定要更新所有歌曲的内嵌封面吗？这将删除并重新提取所有封面图片，可能需要较长时间。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'rescanCovers'
  confirmFile.value = null
  showConfirmModal.value = true
}

const openScrapeCoversConfirm = () => {
  confirmTitle.value = '补全缺失封面'
  confirmMessage.value = '确定要通过网络爬取所有缺失封面的歌曲封面吗？系统会自动检测物理文件中没有封面的歌曲，然后通过API接口获取并嵌入高清封面。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'scrapeCovers'
  confirmFile.value = null
  showConfirmModal.value = true
}

const openScrapeLyricsConfirm = () => {
  confirmTitle.value = '补全缺失歌词'
  confirmMessage.value = '确定要通过网络爬取所有缺失歌词的歌曲吗？系统会自动检测数据库中没有歌词的歌曲，然后通过LRCLIB接口获取并嵌入歌词。'
  confirmConfirmText.value = '确定'
  confirmAction.value = 'scrapeLyrics'
  confirmFile.value = null
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

const scanTask = ref({
  id: null,
  status: '',
  progress: 0,
  processed: 0,
  total: 0,
  added: 0,
  updated: 0,
  deleted: 0,
  current_file: ''
})

const statusText = computed(() => {
  const map = {
    'pending': '排队中',
    'running': '正在解析元数据...',
    'completed': '扫描已完成',
    'error': '扫描出错'
  }
  return map[scanTask.value.status] || '未开始'
})

const saveConfig = async () => {
  if (!musicPath.value) {
    showToast('请输入媒体库路径', 'info')
    return
  }
  try {
    saving.value = true
    await axios.put('/api/scanner/config/', {
      key: 'music_path',
      value: musicPath.value,
      description: '音乐文件路径'
    })
    showToast('路径保存成功', 'success')
  } catch (error) {
    showToast('保存失败，请检查后端服务', 'error')
  } finally {
    saving.value = false
  }
}

const startScan = async () => {
  try {
    scanning.value = true
    const res = await axios.post('/api/scanner/run/')
    scanTask.value.id = res.data.task_id
    showToast('扫描任务已在后台启动', 'success')
    startPolling()
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scanning.value = false
  }
}

const rescanCovers = async () => {
  try {
    scanning.value = true
    const res = await axios.post('/api/scanner/run/', {
      force_reextract_cover: true
    })
    scanTask.value.id = res.data.task_id
    showToast('封面重提取任务已在后台启动', 'success')
    startPolling()
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
    scanTask.value.id = res.data.task_id
    await axios.post('/api/scraper/batch/scrape/', {
      task_id: res.data.task_id
    })
    showToast('补全封面任务已在后台启动', 'success')
    startPolling()
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
    scanTask.value.id = res.data.task_id
    await axios.post('/api/scraper/batch/scrape_lyrics/', {
      task_id: res.data.task_id
    })
    showToast('补全歌词任务已在后台启动', 'success')
    startPolling()
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scrapingLyrics.value = false
  }
}

const fetchStatus = async () => {
  if (!scanTask.value.id) return
  try {
    const res = await axios.get('/api/scanner/status/', {
      params: { task_id: scanTask.value.id }
    })
    
    const data = res.data
    scanTask.value.status = data.status
    scanTask.value.progress = data.progress
    scanTask.value.processed = data.processed_files
    scanTask.value.total = data.total_files
    scanTask.value.added = data.added_count
    scanTask.value.updated = data.updated_count || 0
    scanTask.value.deleted = data.deleted_count || 0
    scanTask.value.current_file = data.current_file

    if (data.status === 'completed') {
      stopPolling()
      scanning.value = false
      if (scraping.value) {
        scraping.value = false
      }
      if (scrapingLyrics.value) {
        scrapingLyrics.value = false
      }
    } else if (data.status === 'error') {
      stopPolling()
      scanning.value = false
      if (scraping.value) {
        scraping.value = false
      }
      if (scrapingLyrics.value) {
        scrapingLyrics.value = false
      }
      const errMsg = data.error_message || '扫描发生未知错误'
      showToast(errMsg, 'error')
    }
  } catch (error) {
    console.error('获取状态失败', error)
  }
}

const startPolling = () => {
  if (timer) clearInterval(timer)
  timer = setInterval(fetchStatus, 2000)
}

const stopPolling = () => {
  if (timer) clearInterval(timer)
}

onMounted(async () => {
  try {
    const res = await axios.get('/api/scanner/config/')
    if (res.data.music_path) {
      musicPath.value = res.data.music_path.value
    }
  } catch (error) {
    console.error('获取配置失败', error)
  }
  fetchStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* 必须加上这行来让 Tailwind v4 在 scoped 样式中识别 @apply 使用的工具类 */
@reference "tailwindcss";

/* 强制应用 Apple 系统原生字体，渲染更加细腻 */
.apple-font {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* KBD 标签拟物化样式 */
.apple-kbd {
  @apply px-2 py-1 bg-[#f5f5f7] border border-[#d2d2d7] rounded-md text-[13px] font-mono text-[#1d1d1f] shadow-[0_1px_1px_rgba(0,0,0,0.05)];
}

/* 覆写 Element Plus 输入框样式：修复下划线截断、添加圆角和背景 */
:deep(.custom-apple-input .el-input__wrapper) {
  @apply rounded-[12px] bg-[#f5f5f7] border border-transparent shadow-none px-4 py-[10px] transition-all duration-300;
}
:deep(.custom-apple-input .el-input__wrapper.is-focus) {
  @apply bg-white border-[#0071e3] shadow-[0_0_0_4px_rgba(0,113,227,0.1)];
}
:deep(.custom-apple-input .el-input__inner) {
  @apply text-[#1d1d1f] font-medium text-[15px];
  line-height: normal !important; /* 强制修改行高，防止下划线 '_' 被截断 */
  padding-bottom: 1px; /* 微调底部间距，给下划线留出空间 */
}

/* 覆写 Element Plus 按钮样式：Apple 风格 */
:deep(.custom-apple-button) {
  @apply rounded-[12px] px-8 h-[44px] font-semibold text-[15px] transition-all duration-300 bg-[#0071e3] border-none shadow-sm;
}
:deep(.custom-apple-button:hover) {
  @apply bg-[#0077ED] transform scale-[1.02];
}
:deep(.custom-apple-button:active) {
  @apply transform scale-[0.98];
}

/* 覆写进度条样式，使其更贴近 iOS 进度条 */
:deep(.el-progress-bar__outer) {
  @apply bg-[#e5e5ea] rounded-full;
}
:deep(.el-progress-bar__inner) {
  @apply rounded-full transition-all duration-500;
}
</style>