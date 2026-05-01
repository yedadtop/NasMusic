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
        <div class="w-10 h-10 bg-[#fff3e0] text-[#ff9500] rounded-[10px] flex items-center justify-center mr-4">
          <Icon icon="mdi:trash-can" class="w-5 h-5" />
        </div>
        <h2 class="text-xl font-semibold tracking-tight">垃圾箱</h2>
      </div>

      <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
        管理已删除的音乐文件。可以恢复误删的文件，或彻底删除以释放磁盘空间。
      </p>

      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <div class="w-full sm:w-auto">
          <el-button
            type="primary"
            :loading="loadingTrash"
            @click="fetchTrashFiles"
            class="w-full custom-apple-button"
          >
            <Icon icon="mdi:refresh" class="w-4 h-4 mr-2" />
            查看垃圾箱
          </el-button>
        </div>
        <div v-if="trashFiles.length > 0" class="w-full sm:w-auto">
          <el-button
            type="warning"
            :loading="restoringAll"
            @click="openRestoreAllConfirm"
            class="w-full custom-apple-button"
          >
            恢复全部
          </el-button>
        </div>
        <div v-if="trashFiles.length > 0" class="w-full sm:w-auto">
          <el-button
            type="danger"
            :loading="deletingAll"
            @click="openDeleteAllConfirm"
            class="w-full custom-apple-button !bg-[#ff3b30]"
          >
            <Icon icon="mdi:delete" class="w-4 h-4 mr-2" />
            清空回收站
          </el-button>
        </div>
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { Icon } from '@iconify/vue'
import AppleToast from './AppleToast.vue'
import AppleConfirmModal from './AppleConfirmModal.vue'

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
