<template>
  <div class="max-w-3xl mx-auto px-6 py-10 pb-32 apple-font text-[#1d1d1f]">
    <AppleToast v-model="toastVisible" :message="toastMessage" :type="toastType" />
    <AppleConfirmModal
      v-model="showConfirmModal"
      :title="confirmTitle"
      :message="confirmMessage"
      :confirm-text="confirmConfirmText"
      cancel-text="取消"
      @confirm="handleConfirm"
    />
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

      <div class="flex flex-col sm:flex-row gap-4">
        <el-input
          v-model="musicPath"
          placeholder="例如: /home/music 或 C:\Music"
          class="flex-1 custom-apple-input"
        />
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
        <div class="w-10 h-10 bg-[#fff3e0] text-[#ff9500] rounded-[10px] flex items-center justify-center mr-4">
          <Icon icon="mdi:trash-can" class="w-5 h-5" />
        </div>
        <h2 class="text-xl font-semibold tracking-tight">回收站</h2>
      </div>

      <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
        管理已删除的音乐文件。可以恢复误删的文件，或彻底删除以释放磁盘空间。
      </p>

      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <el-button
          type="primary"
          :loading="loadingTrash"
          @click="fetchTrashFiles"
          class="w-full sm:w-auto custom-apple-button"
        >
          <Icon icon="mdi:refresh" class="w-4 h-4 mr-2" />
          查看垃圾箱
        </el-button>
        <el-button
          v-if="trashFiles.length > 0"
          type="warning"
          :loading="restoringAll"
          @click="openRestoreAllConfirm"
          class="w-full sm:w-auto custom-apple-button"
        >
          恢复全部
        </el-button>
        <el-button
          v-if="trashFiles.length > 0"
          type="danger"
          :loading="deletingAll"
          @click="openDeleteAllConfirm"
          class="w-full sm:w-auto custom-apple-button !bg-[#ff3b30]"
        >
          <Icon icon="mdi:delete" class="w-4 h-4 mr-2" />
          清空回收站
        </el-button>
      </div>

      <div v-if="trashFiles.length === 0 && showTrashList" class="text-center py-8 text-[#86868b]">
        <Icon icon="mdi:trash-can" class="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>回收站为空</p>
      </div>

      <div v-if="trashFiles.length > 0" class="space-y-2">
        <div
          v-for="(file, index) in trashFiles"
          :key="index"
          class="flex items-center justify-between p-3 bg-[#f5f5f7] rounded-[12px] hover:bg-[#efeff0] transition"
        >
          <div class="flex-1 min-w-0 mr-4">
            <div class="text-[14px] font-medium truncate">{{ file.filename }}</div>
            <div class="text-[12px] text-[#86868b] truncate">{{ file.original_dir }}</div>
          </div>
          <div class="flex gap-2 shrink-0">
            <el-button
              size="small"
              @click="openRestoreConfirm(file)"
              class="!rounded-[8px] !px-3 !py-1.5 !text-[13px] !border-[#34c759] !text-[#34c759] hover:!bg-[#34c759] hover:!text-white"
            >
              恢复
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="openDeleteConfirm(file)"
              class="!rounded-[8px] !px-3 !py-1.5 !text-[13px] !bg-[#ff3b30] !border-[#ff3b30]"
            >
              删除
            </el-button>
          </div>
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
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import { FolderOpened, Loading, CircleCheck } from '@element-plus/icons-vue'
import { Icon } from '@iconify/vue'
import AppleToast from '../components/AppleToast.vue'
import AppleConfirmModal from '../components/AppleConfirmModal.vue'

const musicPath = ref('')
const scanning = ref(false)
const saving = ref(false)
let timer = null
let delayedScanTimer = null

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const showTrashList = ref(false)
const trashFiles = ref([])
const loadingTrash = ref(false)
const restoringAll = ref(false)
const deletingAll = ref(false)

const showConfirmModal = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmConfirmText = ref('')
const confirmAction = ref(null)
const confirmFile = ref(null)

const openRestoreConfirm = (file) => {
  confirmTitle.value = '恢复文件'
  confirmMessage.value = `确定要恢复 "${file.filename}" 吗？文件将回到原始目录。`
  confirmConfirmText.value = '恢复'
  confirmAction.value = 'restore'
  confirmFile.value = file
  showConfirmModal.value = true
}

const openRestoreAllConfirm = () => {
  confirmTitle.value = '恢复全部'
  confirmMessage.value = `确定要恢复回收站中的全部 ${trashFiles.value.length} 个文件吗？`
  confirmConfirmText.value = '恢复全部'
  confirmAction.value = 'restoreAll'
  confirmFile.value = null
  showConfirmModal.value = true
}

const openDeleteConfirm = (file) => {
  confirmTitle.value = '物理删除！！'
  confirmMessage.value = `确定要彻底删除 "${file.filename}" 吗？此操作不可恢复！！！`
  confirmConfirmText.value = '删除'
  confirmAction.value = 'delete'
  confirmFile.value = file
  showConfirmModal.value = true
}

const openDeleteAllConfirm = () => {
  confirmTitle.value = '清空回收站'
  confirmMessage.value = `确定要彻底删除回收站中的全部 ${trashFiles.value.length} 个文件吗？此操作不可恢复！`
  confirmConfirmText.value = '清空'
  confirmAction.value = 'deleteAll'
  confirmFile.value = null
  showConfirmModal.value = true
}

const handleConfirm = async () => {
  showConfirmModal.value = false
  if (confirmAction.value === 'restore') {
    await restoreFile(confirmFile.value.trash_path)
  } else if (confirmAction.value === 'restoreAll') {
    await restoreAllFiles()
  } else if (confirmAction.value === 'delete') {
    await deleteFile(confirmFile.value.trash_path)
  } else if (confirmAction.value === 'deleteAll') {
    await deleteAllFiles()
  }
}

const fetchTrashFiles = async () => {
  try {
    loadingTrash.value = true
    const res = await axios.get('/api/scanner/trash/')
    trashFiles.value = res.data.files || []
    showTrashList.value = true
  } catch (error) {
    console.error('获取回收站失败:', error)
    showToast('获取回收站失败', 'error')
  } finally {
    loadingTrash.value = false
  }
}

const restoreFile = async (path) => {
  try {
    await axios.post('/api/scanner/trash/', { paths: [path] })
    showToast('文件已恢复', 'success')
    await fetchTrashFiles()
    scheduleScanAfterRestore()
  } catch (error) {
    console.error('恢复失败:', error)
    showToast('恢复失败', 'error')
  }
}

const restoreAllFiles = async () => {
  try {
    restoringAll.value = true
    await axios.post('/api/scanner/trash/', { restore_all: true })
    showToast('已恢复全部文件', 'success')
    await fetchTrashFiles()
    scheduleScanAfterRestore()
  } catch (error) {
    console.error('恢复全部失败:', error)
    showToast('恢复失败', 'error')
  } finally {
    restoringAll.value = false
  }
}

const deleteFile = async (path) => {
  try {
    await axios.delete('/api/scanner/trash/', { data: { paths: [path] } })
    showToast('文件已彻底删除', 'success')
    await fetchTrashFiles()
  } catch (error) {
    console.error('删除失败:', error)
    showToast('删除失败', 'error')
  }
}

const deleteAllFiles = async () => {
  try {
    deletingAll.value = true
    await axios.delete('/api/scanner/trash/', { data: { delete_all: true } })
    showToast('已清空回收站', 'success')
    await fetchTrashFiles()
  } catch (error) {
    console.error('清空失败:', error)
    showToast('清空失败', 'error')
  } finally {
    deletingAll.value = false
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

// 保存配置
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

// 启动扫描
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

// 延迟扫描（恢复操作后使用，防止用户连续点击）
const scheduleScanAfterRestore = (delay = 5000) => {
  if (delayedScanTimer) {
    clearTimeout(delayedScanTimer)
  }
  delayedScanTimer = setTimeout(() => {
    startScan()
    delayedScanTimer = null
  }, delay)
}

// 轮询状态
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