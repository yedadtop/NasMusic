<template>
  <div class="apple-font text-[#1d1d1f]">

    <AppleToast v-if="toastVisible" v-model="toastVisible" :message="toastMessage" :type="toastType" />

    <section class="mb-10 bg-white rounded-[20px] p-6 sm:p-8 shadow-[0_2px_20px_rgba(0,0,0,0.04)] border border-gray-100/50">
      <div class="flex items-center mb-3">
        <div class="w-10 h-10 bg-[#f3e5f5] text-[#af52de] rounded-[10px] flex items-center justify-center mr-4">
          <Icon icon="mdi:cookie" class="w-5 h-5" />
        </div>
        <h2 class="text-xl font-semibold tracking-tight">Bilibili Cookie 管理</h2>
      </div>

      <p class="text-[15px] text-[#86868b] mb-6 leading-relaxed">
        管理 Bilibili 登录凭证（SESSDATA），用于访问需要登录才能获取的资源。
      </p>

      <div v-if="loading" class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0071e3]"></div>
      </div>

      <div v-else-if="!cookieData" class="p-6 bg-[#f5f5f7] rounded-[12px] text-center">
        <div class="w-16 h-16 bg-[#ff3b30]/10 text-[#ff3b30] rounded-full flex items-center justify-center mx-auto mb-4">
          <Icon icon="mdi:alert-circle" class="w-8 h-8" />
        </div>
        <p class="text-[15px] text-[#86868b] mb-4">暂未配置 Bilibili Cookie</p>
        <el-button type="primary" @click="showForm = true" class="custom-apple-button">
          <Icon icon="mdi:plus" class="w-4 h-4 mr-2" />
          添加 Cookie
        </el-button>
      </div>

      <div v-else>
        <div class="mb-6 p-4 bg-[#f5f5f7] rounded-[12px]">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[13px] font-medium text-[#86868b]">当前 Cookie 状态</span>
            <span class="px-3 py-1 bg-[#34c759]/10 text-[#34c759] text-[12px] font-medium rounded-full">
              已配置
            </span>
          </div>
          <div class="space-y-3">
            <div class="flex items-start">
              <span class="text-[13px] text-[#86868b] w-20 flex-shrink-0">描述：</span>
              <span class="text-[13px] text-[#1d1d1f]">{{ cookieData.description || '无' }}</span>
            </div>
            <div class="flex items-start">
              <span class="text-[13px] text-[#86868b] w-20 flex-shrink-0">SESSDATA：</span>
              <span class="text-[13px] text-[#1d1d1f] font-mono bg-white px-2 py-1 rounded break-all">
                {{ maskedValue }}
              </span>
            </div>
            <div class="flex items-start">
              <span class="text-[13px] text-[#86868b] w-20 flex-shrink-0">更新时间：</span>
              <span class="text-[13px] text-[#1d1d1f]">{{ formatDate(cookieData.updated_at) }}</span>
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <el-button type="primary" @click="openEditForm" class="custom-apple-button">
            <Icon icon="mdi:pencil" class="w-4 h-4 mr-2" />
            修改 Cookie
          </el-button>
        </div>
      </div>

      <div v-if="showForm" class="mt-6 p-6 bg-[#f5f5f7] rounded-[12px]">
        <h3 class="text-[15px] font-semibold mb-4">{{ isEditing ? '修改 Cookie' : '添加 Cookie' }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-[13px] text-[#86868b] mb-2">SESSDATA</label>
            <el-input
              v-model="formData.value"
              type="textarea"
              :rows="3"
              placeholder="请输入 SESSDATA 值"
              class="!rounded-[10px]"
            />
          </div>
          <div>
            <label class="block text-[13px] text-[#86868b] mb-2">描述（可选）</label>
            <el-input
              v-model="formData.description"
              placeholder="例如：Bilibili 登录 Cookie"
              class="!rounded-[10px]"
            />
          </div>
          <div class="flex gap-3 pt-2">
            <el-button type="primary" @click="submitForm" :loading="submitting" class="custom-apple-button">
              保存
            </el-button>
            <el-button @click="cancelForm" class="!rounded-[10px]">取消</el-button>
          </div>
        </div>
      </div>

      <div class="mt-6 p-4 bg-[#f5f5f7] rounded-[12px] text-[13px] text-[#86868b] leading-relaxed">
        <div class="mb-3">
          <span class="font-semibold text-[#1d1d1f]">SESSDATA 获取方法：</span>
          登录 Bilibili 网页版后，在开发者工具中复制 cookies['SESSDATA'] 的值。
        </div>
        <div>
          <span class="font-semibold text-[#1d1d1f]">用途说明：</span>
          用于访问需要登录才能获取的资源，如高清封面、VIP 内容等。
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import AppleToast from './AppleToast.vue'
import axios from 'axios'

const API_BASE = '/api/scraper'

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const loading = ref(false)
const submitting = ref(false)
const cookieData = ref(null)
const showForm = ref(false)
const isEditing = ref(false)

const formData = ref({
  value: '',
  description: ''
})

const maskedValue = computed(() => {
  if (!cookieData.value?.value) return ''
  const val = cookieData.value.value
  if (val.length <= 20) return '***'
  return val.substring(0, 10) + '...' + val.substring(val.length - 10)
})

const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const fetchCookie = async () => {
  loading.value = true
  try {
    const response = await axios.get(`${API_BASE}/bilibili_cookie/`)
    cookieData.value = response.data
  } catch (error) {
    if (error.response?.status === 404) {
      cookieData.value = null
    } else {
      showToast('获取 Cookie 失败', 'error')
    }
  } finally {
    loading.value = false
  }
}

const openEditForm = () => {
  isEditing.value = true
  formData.value = {
    value: '',
    description: cookieData.value.description || ''
  }
  showForm.value = true
}

const cancelForm = () => {
  showForm.value = false
  isEditing.value = false
  formData.value = { value: '', description: '' }
}

const submitForm = async () => {
  if (!formData.value.value.trim()) {
    showToast('SESSDATA 不能为空', 'error')
    return
  }

  submitting.value = true
  try {
    const method = isEditing.value ? 'put' : 'post'
    const response = await axios[method](`${API_BASE}/bilibili_cookie/`, {
      value: formData.value.value,
      description: formData.value.description
    })
    cookieData.value = response.data
    showForm.value = false
    isEditing.value = false
    formData.value = { value: '', description: '' }
    showToast(isEditing.value ? 'Cookie 已更新' : 'Cookie 已保存')
  } catch (error) {
    showToast(error.response?.data?.message || '保存失败', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchCookie()
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
  @apply rounded-[12px] px-8 h-[44px] font-semibold text-[15px] transition-all duration-300 bg-[#0071e3] border-none shadow-sm;
}
:deep(.custom-apple-button:hover) {
  @apply bg-[#0077ED] transform scale-[1.02];
}
:deep(.custom-apple-button:active) {
  @apply transform scale-[0.98];
}
:deep(.el-textarea__inner) {
  @apply !rounded-[10px];
}
</style>
