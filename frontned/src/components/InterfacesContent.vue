<template>
  <div class="apple-font text-[#1d1d1f]">
    <AppleToast v-if="toastVisible" v-model="toastVisible" :message="toastMessage" :type="toastType" />

    <section class="mb-10 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50 transition-all">
      <div class="flex items-center mb-3">
        <div class="w-10 h-10 bg-[#e8f2ff] text-[#0071e3] rounded-[10px] flex items-center justify-center mr-4">
          <Icon icon="mdi:api" class="w-5 h-5" />
        </div>
        <h2 class="text-xl font-semibold tracking-tight">刮削接口</h2>
      </div>

      <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
        管理音乐元数据刮削接口，支持添加、编辑、删除和测试接口配置。
      </p>

      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <div class="w-full sm:w-auto">
          <el-button
            type="primary"
            :loading="loadingInterfaces"
            @click="fetchInterfaces"
            class="w-full custom-apple-button"
          >
            <Icon icon="mdi:refresh" class="w-4 h-4 mr-2" />
            刷新接口列表
          </el-button>
        </div>
        <div class="w-full sm:w-auto">
          <el-button
            type="success"
            @click="openAddDialog"
            class="w-full custom-apple-button !bg-[#34c759] !border-[#34c759]"
          >
            <Icon icon="mdi:add" class="w-4 h-4 mr-2" />
            添加接口
          </el-button>
        </div>
      </div>

      <div v-if="loadingInterfaces" class="text-center py-12">
        <Icon icon="mdi:loading" class="w-8 h-8 text-[#0071e3] animate-spin mx-auto" />
        <p class="text-[#86868b] mt-3">加载中...</p>
      </div>

      <div v-else-if="interfaces.length === 0" class="text-center py-12 text-[#86868b]">
        <Icon icon="mdi:api" class="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>暂无可用接口</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="iface in interfaces"
          :key="iface.id"
          class="p-4 bg-[#f5f5f7] rounded-[14px] hover:bg-[#efeff0] transition"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[15px] font-semibold">{{ iface.name }}</span>
                <span v-if="iface.is_active" class="text-[11px] font-medium px-2 py-0.5 bg-[#34c759] text-white rounded-full">启用</span>
                <span v-else class="text-[11px] font-medium px-2 py-0.5 bg-[#86868b] text-white rounded-full">禁用</span>
                <span class="text-[11px] font-medium px-2 py-0.5 bg-[#0071e3] text-white rounded-full">优先级: {{ iface.priority }}</span>
              </div>
              <div class="text-[13px] text-[#86868b] truncate">{{ iface.url }}</div>
              <div class="text-[11px] text-[#86868b] mt-1">创建时间: {{ formatDate(iface.created_at) }}</div>
            </div>
            <div class="flex gap-2 shrink-0 ml-4">
              <el-button
                size="small"
                @click="openEditDialog(iface)"
                class="!rounded-[8px] !px-3 !py-1.5 !text-[13px] !border-[#ff9500] !text-[#ff9500] hover:!bg-[#ff9500] hover:!text-white"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="openDeleteConfirm(iface)"
                class="!rounded-[8px] !px-3 !py-1.5 !text-[13px] !bg-[#ff3b30] !border-[#ff3b30]"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="totalCount > pageSize" class="flex justify-center mt-6 gap-2">
        <el-button
          size="small"
          :disabled="!previous"
          @click="changePage(currentPage - 1)"
          class="!rounded-[8px]"
        >
          上一页
        </el-button>
        <span class="text-[13px] text-[#86868b] self-center">
          第 {{ currentPage }} / {{ totalPages }} 页，共 {{ totalCount }} 条
        </span>
        <el-button
          size="small"
          :disabled="!next"
          @click="changePage(currentPage + 1)"
          class="!rounded-[8px]"
        >
          下一页
        </el-button>
      </div>
    </section>

    <el-dialog
      v-model="showFormDialog"
      :title="isEditing ? '编辑接口' : '添加接口'"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#1d1d1f] mb-2">接口名称 <span class="text-[#ff3b30]">*</span></label>
          <el-input
            v-model="formData.name"
            placeholder="例如: iTunes API"
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-[13px] font-medium text-[#1d1d1f] mb-2">接口地址 URL <span class="text-[#ff3b30]">*</span></label>
          <el-input
            v-model="formData.url"
            placeholder="例如: https://itunes.apple.com/search"
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-[13px] font-medium text-[#1d1d1f] mb-2">优先级</label>
          <el-input-number
            v-model="formData.priority"
            :min="0"
            :max="100"
            class="w-full"
          />
          <p class="text-[11px] text-[#86868b] mt-1">数字越小优先级越高，默认为 0</p>
        </div>
        <div class="flex items-center">
          <el-switch
            v-model="formData.is_active"
            active-text="启用"
            inactive-text="禁用"
            class="custom-apple-switch"
          />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="showFormDialog = false" class="!rounded-[10px]">取消</el-button>
          <el-button
            type="primary"
            :loading="saving"
            @click="saveInterface"
            class="!rounded-[10px] !bg-[#0071e3] !border-[#0071e3]"
          >
            {{ isEditing ? '保存' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showDeleteDialog"
      title="确认删除"
      width="400px"
    >
      <p class="text-[15px]">
        确定要删除接口 <span class="font-semibold">"{{ interfaceToDelete?.name }}"</span> 吗？此操作不可恢复。
      </p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="showDeleteDialog = false" class="!rounded-[10px]">取消</el-button>
          <el-button
            type="danger"
            :loading="deleting"
            @click="deleteInterface"
            class="!rounded-[10px] !bg-[#ff3b30] !border-[#ff3b30]"
          >
            删除
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import AppleToast from './AppleToast.vue'
import request from '../api'

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const loadingInterfaces = ref(false)
const interfaces = ref([])
const currentPage = ref(1)
const pageSize = ref(50)
const totalCount = ref(0)
const next = ref(null)
const previous = ref(null)

const fetchInterfaces = async (page = 1) => {
  try {
    loadingInterfaces.value = true
    const res = await request.get('/scraper/apis/', {
      params: { page, size: pageSize.value }
    })

    const data = res.data
    interfaces.value = Array.isArray(data) ? data : (data.results || [])
    totalCount.value = Array.isArray(data) ? data.length : (data.count || 0)
    next.value = Array.isArray(data) ? null : data.next
    previous.value = Array.isArray(data) ? null : data.previous
    currentPage.value = page
  } catch (error) {
    console.error('获取接口列表失败:', error)
    showToast('获取接口列表失败', 'error')
  } finally {
    loadingInterfaces.value = false
  }
}

const changePage = (page) => {
  fetchInterfaces(page)
}

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const showFormDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const currentInterfaceId = ref(null)
const formData = ref({
  name: '',
  url: '',
  priority: 0,
  is_active: true
})

const resetForm = () => {
  formData.value = {
    name: '',
    url: '',
    priority: 0,
    is_active: true
  }
  currentInterfaceId.value = null
  isEditing.value = false
}

const openAddDialog = () => {
  resetForm()
  showFormDialog.value = true
}

const openEditDialog = (iface) => {
  isEditing.value = true
  currentInterfaceId.value = iface.id
  formData.value = {
    name: iface.name,
    url: iface.url,
    priority: iface.priority,
    is_active: iface.is_active
  }
  showFormDialog.value = true
}

const saveInterface = async () => {
  if (!formData.value.name || !formData.value.url) {
    showToast('请填写必填项', 'error')
    return
  }

  try {
    saving.value = true
    if (isEditing.value) {
      await axios.patch(`/api/scraper/apis/${currentInterfaceId.value}/`, {
        name: formData.value.name,
        url: formData.value.url,
        priority: formData.value.priority,
        is_active: formData.value.is_active
      })
      showToast('接口更新成功', 'success')
    } else {
      await request.post('/scraper/apis/', {
        name: formData.value.name,
        url: formData.value.url,
        priority: formData.value.priority,
        is_active: formData.value.is_active
      })
      showToast('接口创建成功', 'success')
    }
    showFormDialog.value = false
    fetchInterfaces(currentPage.value)
  } catch (error) {
    console.error('保存接口失败:', error)
    showToast(error.response?.data?.error || '保存接口失败', 'error')
  } finally {
    saving.value = false
  }
}

const showDeleteDialog = ref(false)
const interfaceToDelete = ref(null)
const deleting = ref(false)

const openDeleteConfirm = (iface) => {
  interfaceToDelete.value = iface
  showDeleteDialog.value = true
}

const deleteInterface = async () => {
  if (!interfaceToDelete.value) return

  try {
    deleting.value = true
    await request.delete(`/scraper/apis/${interfaceToDelete.value.id}/`)
    showToast('接口删除成功', 'success')
    showDeleteDialog.value = false
    fetchInterfaces(currentPage.value)
  } catch (error) {
    console.error('删除接口失败:', error)
    showToast('删除接口失败', 'error')
  } finally {
    deleting.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchInterfaces()
})
</script>

<style scoped>
@reference "tailwindcss";

.apple-font {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:deep(.custom-apple-button) {
  @apply rounded-[12px] px-6 h-[44px] font-semibold text-[15px] transition-all duration-300 bg-[#0071e3] border-none shadow-sm;
}
:deep(.custom-apple-button:hover) {
  @apply bg-[#0077ED] transform scale-[1.02];
}
:deep(.custom-apple-button:active) {
  @apply transform scale-[0.98];
}

:deep(.custom-apple-switch .el-switch__label) {
  @apply text-[13px] font-medium;
}

:deep(.el-dialog) {
  @apply rounded-[16px];
}
:deep(.el-dialog__header) {
  @apply border-b border-gray-100 px-6 py-4;
}
:deep(.el-dialog__title) {
  @apply text-[17px] font-semibold;
}
:deep(.el-dialog__body) {
  @apply px-6 py-4;
}
:deep(.el-dialog__footer) {
  @apply border-t border-gray-100 px-6 py-4;
}
</style>
