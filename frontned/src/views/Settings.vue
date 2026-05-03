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
          @click="activeTab = 'scraper'"
          class="pb-3 px-1 text-[17px] font-semibold border-b-2 transition-colors mr-6"
          :class="activeTab === 'scraper' ? 'border-[#0071e3] text-[#0071e3]' : 'border-transparent text-[#86868b] hover:text-[#1d1d1f]'"
        >
          刮削
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

    <div v-show="activeTab === 'settings'" class="min-h-[600px]">

      <section class="mb-8 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50 transition-all">
        <div class="flex items-center mb-3">
          <div class="w-10 h-10 bg-[#fdf2e9] text-[#ff9500] rounded-[10px] flex items-center justify-center mr-4">
            <Upload class="w-5 h-5" />
          </div>
          <h2 class="text-xl font-semibold tracking-tight">上传歌曲</h2>
        </div>

        <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
          将本地音乐文件分片上传到服务器，支持大文件（>100MB）传输，上传后自动入库。
        </p>

        <div
          class="border-2 border-dashed border-[#d2d2d7] rounded-[16px] p-8 text-center transition-all cursor-pointer"
          :class="isDragging ? 'border-[#0071e3] bg-[#f5f5f7]' : 'hover:border-[#0071e3] hover:bg-[#fafafa]'"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input
            ref="fileInputRef"
            type="file"
            multiple
            accept=".mp3,.flac,.ogg,.m4a"
            class="hidden"
            @change="handleFileSelect"
          />
          <Upload class="w-12 h-12 text-[#86868b] mx-auto mb-4" />
          <p class="text-[15px] font-medium text-[#1d1d1f] mb-2">
            拖拽文件到此处，或<span class="text-[#0071e3]">点击选择</span>
          </p>
          <p class="text-[13px] text-[#86868b]">
            支持 MP3、FLAC、OGG、M4A 格式
          </p>
        </div>

        <div v-if="uploadQueue.length > 0" class="mt-6 space-y-3">
          <div
            v-for="item in uploadQueue"
            :key="item.id"
            class="bg-[#f5f5f7] rounded-[12px] p-4"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-3 min-w-0">
                <span class="text-[14px] font-medium truncate">{{ item.filename }}</span>
              </div>
              <button
                v-if="item.status === 'pending' || item.status === 'uploading'"
                @click.stop="cancelUpload(item)"
                class="text-[#86868b] hover:text-[#ff3b30] transition-colors ml-2 flex-shrink-0"
              >
                <Close class="w-4 h-4" />
              </button>
              <span v-else-if="item.status === 'completed'" class="text-[#34c759]">
                <CircleCheck class="w-5 h-5" />
              </span>
              <span v-else-if="item.status === 'error'" class="text-[#ff3b30]">
                <Close class="w-5 h-5" />
              </span>
            </div>
            <div class="flex items-center gap-3">
              <el-progress
                :percentage="item.progress"
                :status="item.status === 'completed' ? 'success' : item.status === 'error' ? 'exception' : ''"
                :stroke-width="6"
                :show-text="false"
                color="#0071e3"
              />
              <span class="text-[12px] text-[#86868b] w-12 text-right flex-shrink-0">
                {{ item.progress }}%
              </span>
            </div>
            <p v-if="item.error" class="text-[12px] text-[#ff3b30] mt-1">{{ item.error }}</p>
          </div>
        </div>
      </section>

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
            <div class="w-full sm:w-auto">
              <el-button
                type="primary"
                :loading="saving"
                @click="saveConfig"
                class="w-full custom-apple-button"
              >
                保存路径
              </el-button>
            </div>
            <div class="w-full sm:w-auto">
              <el-button
                type="primary"
                :loading="scanning"
                @click="startScan"
                class="w-full custom-apple-button"
              >
                立即扫描
              </el-button>
            </div>
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
    </div>

    <div v-show="activeTab === 'interfaces'" class="min-h-[600px]">
      <InterfacesContent />
    </div>

    <div v-show="activeTab === 'trash'" class="min-h-[600px]">
      <TrashContent />
    </div>

    <div v-show="activeTab === 'scraper'" class="min-h-[600px]">
      <ScraperContent @task-started="handleTaskStarted" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, defineAsyncComponent } from 'vue'
import { FolderOpened, Loading, CircleCheck, Upload, Close } from '@element-plus/icons-vue'
import AppleToast from '../components/AppleToast.vue'
import AppleConfirmModal from '../components/AppleConfirmModal.vue'
import request from '../api'

const InterfacesContent = defineAsyncComponent(() => import('../components/InterfacesContent.vue'))
const TrashContent = defineAsyncComponent(() => import('../components/TrashContent.vue'))
const ScraperContent = defineAsyncComponent(() => import('../components/ScraperContent.vue'))

const activeTab = ref('settings')

const musicPath = ref('')
const scanning = ref(false)
const saving = ref(false)
let timer = null

const isDragging = ref(false)
const fileInputRef = ref(null)
const uploadQueue = ref([])
let uploadIdCounter = 0

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleDrop = (e) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files).filter(f =>
    /\.(mp3|flac|ogg|m4a)$/i.test(f.name)
  )
  if (files.length === 0) {
    showToast('请上传 MP3、FLAC、OGG 或 M4A 格式的文件', 'error')
    return
  }
  files.forEach(file => addToQueue(file))
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  files.forEach(file => addToQueue(file))
  e.target.value = ''
}

const addToQueue = (file) => {
  const item = {
    id: ++uploadIdCounter,
    filename: file.name,
    file: file,
    status: 'pending',
    progress: 0,
    error: null,
    uploadId: null
  }
  uploadQueue.value.push(item)
  processQueue()
}

const processQueue = async () => {
  const pending = uploadQueue.value.find(u => u.status === 'pending')
  if (!pending) return

  pending.status = 'uploading'
  await uploadFile(pending)
}

const uploadFile = async (item) => {
  const CHUNK_SIZE = 1024 * 1024
  const file = item.file
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  try {
    const initRes = await request.post('/upload/init/', {
      filename: file.name,
      total_chunks: totalChunks,
      file_size: file.size
    })

    item.uploadId = initRes.data.upload_id
    const chunkSize = initRes.data.chunk_size

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const chunk = file.slice(start, end)

      const formData = new FormData()
      formData.append('upload_id', item.uploadId)
      formData.append('chunk_index', i)
      formData.append('chunk', chunk)

      await request.post('/upload/upload_chunk/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      item.progress = Math.round(((i + 1) / totalChunks) * 100)
    }

    await request.post('/upload/complete/', {
      upload_id: item.uploadId
    })

    item.status = 'completed'
    item.progress = 100
    showToast(`${item.filename} 上传成功`, 'success')

  } catch (err) {
    item.status = 'error'
    item.error = err.response?.data?.error || err.message || '上传失败'
    showToast(`${item.filename} 上传失败: ${item.error}`, 'error')
  }

  processQueue()
}

const cancelUpload = async (item) => {
  if (item.uploadId) {
    try {
      await request.delete('/upload/cancel/', {
        params: { upload_id: item.uploadId }
      })
    } catch (e) {
      console.error('取消上传失败', e)
    }
  }
  uploadQueue.value = uploadQueue.value.filter(u => u.id !== item.id)
}

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

const handleConfirm = async () => {
  showConfirmModal.value = false
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
    await request.put('/scanner/config/', {
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
    const res = await request.post('/scanner/run/')
    scanTask.value.id = res.data.task_id
    showToast('扫描任务已在后台启动', 'success')
    startPolling()
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    showToast(msg, 'error')
    scanning.value = false
  }
}

const handleTaskStarted = (taskId) => {
  scanTask.value.id = taskId
  startPolling()
}

const fetchStatus = async () => {
  if (!scanTask.value.id) return
  try {
    const res = await request.get('/scanner/status/', {
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
    } else if (data.status === 'error') {
      stopPolling()
      scanning.value = false
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
    const res = await request.get('/scanner/config/')
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