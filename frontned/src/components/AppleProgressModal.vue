<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="apple-modal-overlay" @click.self="handleClose">
        <div class="apple-modal-container">
          <div class="apple-modal-header">
            <div class="apple-modal-icon" :class="iconClass">
              <svg v-if="status === 'idle'" class="w-6 h-6 text-[#007AFF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              <svg v-else-if="status === 'loading'" class="w-6 h-6 text-[#007AFF] animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <svg v-else-if="status === 'success'" class="w-6 h-6 text-[#34c759]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <svg v-else class="w-6 h-6 text-[#ff3b30]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <h3 class="apple-modal-title">{{ title }}</h3>
            <p class="apple-modal-message">{{ message }}</p>
          </div>

          <div v-if="status === 'idle' && actionType !== 'rescanCovers'" class="apple-modal-mode">
            <label class="apple-radio-label">
              <input type="radio" v-model="selectedMode" value="incremental" class="apple-radio-input" />
              <span class="apple-radio-custom"></span>
              <span class="apple-radio-text">
                <span class="apple-radio-title">增量模式</span>
                <span class="apple-radio-desc">只处理缺失的项目</span>
              </span>
            </label>
            <label class="apple-radio-label">
              <input type="radio" v-model="selectedMode" value="full" class="apple-radio-input" />
              <span class="apple-radio-custom"></span>
              <span class="apple-radio-text">
                <span class="apple-radio-title">全量模式</span>
                <span class="apple-radio-desc">重新处理所有项目</span>
              </span>
            </label>
          </div>

          <div v-if="status === 'loading'" class="apple-modal-progress">
            <div class="apple-progress-bar">
              <div class="apple-progress-fill" :style="{ width: (progress > 0 ? progress : 0) + '%' }"></div>
            </div>
            <div class="apple-progress-info">
              <p class="apple-progress-text">{{ progressText }}</p>
              <span v-if="progress > 0" class="apple-progress-percent">{{ Math.round(progress) }}%</span>
            </div>
          </div>

          <div v-if="status === 'success' || status === 'error'" class="apple-modal-result">
            <div class="apple-result-summary">
              <div class="apple-result-item apple-result-success">
                <span class="apple-result-count">{{ resultSummary?.success_count || 0 }}</span>
                <span class="apple-result-label">成功</span>
              </div>
              <div class="apple-result-item apple-result-failed">
                <span class="apple-result-count">{{ resultSummary?.failed_count || 0 }}</span>
                <span class="apple-result-label">失败</span>
              </div>
              <div class="apple-result-item apple-result-skipped">
                <span class="apple-result-count">{{ (resultSummary?.skipped_cover || resultSummary?.skipped_lyrics) || 0 }}</span>
                <span class="apple-result-label">跳过</span>
              </div>
            </div>

            <div v-if="resultSummary?.success_list?.length > 0" class="apple-result-list">
              <p class="apple-result-list-title">成功列表：</p>
              <div class="apple-result-list-content">
                <div v-for="(item, idx) in resultSummary.success_list" :key="idx" class="apple-result-list-item success">
                  <svg class="w-4 h-4 text-[#34c759]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                  </svg>
                  <span>{{ item.title }}</span>
                </div>
              </div>
            </div>

            <div v-if="resultSummary?.failed_list?.length > 0" class="apple-result-list">
              <p class="apple-result-list-title">失败列表：</p>
              <div class="apple-result-list-content">
                <div v-for="(item, idx) in resultSummary.failed_list" :key="idx" class="apple-result-list-item failed">
                  <svg class="w-4 h-4 text-[#ff3b30]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                  <span>{{ item.title }} - {{ item.message }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="apple-modal-actions">
            <button v-if="status === 'idle'" class="apple-btn apple-btn-primary" @click="handleStart" :disabled="loading">
              <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span v-else>开始</span>
            </button>
            <button v-if="status === 'success' || status === 'error'" class="apple-btn apple-btn-secondary" @click="handleClose">
              关闭
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: '批量操作'
  },
  message: {
    type: String,
    default: ''
  },
  actionType: {
    type: String,
    default: 'scrapeCovers',
    validator: (val) => ['scrapeCovers', 'scrapeLyrics', 'rescanCovers'].includes(val)
  }
})

const emit = defineEmits(['update:modelValue', 'started'])

const selectedMode = ref('incremental')
const status = ref('idle')
const loading = ref(false)
const progress = ref(0)
const progressText = ref('正在启动任务...')
const resultSummary = ref(null)
const currentTaskId = ref(null)
let pollTimer = null

const iconClass = computed(() => ({
  'text-[#007AFF]': status.value === 'idle',
  'animate-pulse': status.value === 'loading'
}))

watch(() => props.modelValue, (val) => {
  if (!val) {
    resetState()
  }
})

const resetState = () => {
  selectedMode.value = 'incremental'
  status.value = 'idle'
  loading.value = false
  progress.value = 0
  progressText.value = '正在启动任务...'
  resultSummary.value = null
  currentTaskId.value = null
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const handleClose = () => {
  emit('update:modelValue', false)
}

const handleStart = async () => {
  loading.value = true
  status.value = 'loading'
  progressText.value = '正在启动任务...'

  try {
    if (props.actionType === 'rescanCovers') {
      const scannerRes = await axios.post('/api/scanner/run/', {
        force_reextract_cover: true
      })
      currentTaskId.value = scannerRes.data.task_id
    } else {
      const scannerRes = await axios.post('/api/scanner/run/')
      const scannerTaskId = scannerRes.data.task_id
      emit('started', scannerTaskId)

      const endpoint = props.actionType === 'scrapeCovers'
        ? '/api/scraper/batch/scrape/'
        : '/api/scraper/batch/scrape_lyrics/'

      const scrapeRes = await axios.post(endpoint, {
        task_id: scannerTaskId,
        mode: selectedMode.value
      })
      currentTaskId.value = scrapeRes.data.task_id
    }

    progressText.value = '任务运行中...'
    startPolling()
  } catch (error) {
    const msg = error.response?.data?.message || '启动失败，请检查后端服务'
    status.value = 'error'
    resultSummary.value = {
      success_count: 0,
      failed_count: 1,
      failed_list: [{ title: '错误', message: msg }]
    }
    loading.value = false
  }
}

const startPolling = () => {
  pollTimer = setInterval(async () => {
    try {
      const res = await axios.get(`/api/scanner/status/?task_id=${currentTaskId.value}`)
      const data = res.data

      if (data.progress !== undefined) {
        progress.value = data.progress
      }

      if (data.result_summary) {
        clearInterval(pollTimer)
        pollTimer = null
        resultSummary.value = data.result_summary
        status.value = 'success'
        loading.value = false
      } else if (data.status === 'completed') {
        clearInterval(pollTimer)
        pollTimer = null
        resultSummary.value = {
          success_count: data.added_count + data.updated_count || 0,
          failed_count: 0,
          skipped_cover: 0
        }
        status.value = 'success'
        loading.value = false
      } else if (data.status === 'failed' || data.status === 'error') {
        clearInterval(pollTimer)
        pollTimer = null
        status.value = 'error'
        resultSummary.value = {
          success_count: 0,
          failed_count: 1,
          failed_list: [{ title: '任务失败', message: data.error_message || data.message || '未知错误' }]
        }
        loading.value = false
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 1000)
}
</script>

<style scoped>
.apple-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.apple-modal-container {
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(40px);
  border-radius: 20px;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 420px;
  padding: 24px;
  animation: scaleIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes scaleIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.apple-modal-header {
  text-align: center;
  margin-bottom: 20px;
}

.apple-modal-icon {
  margin-bottom: 12px;
}

.apple-modal-title {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.apple-modal-message {
  font-size: 13px;
  color: #6e6e73;
  line-height: 1.5;
  margin: 0;
}

.apple-modal-mode {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f5f5f7;
  border-radius: 12px;
}

.apple-radio-label {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background-color 0.15s ease;
}

.apple-radio-label:hover {
  background-color: rgba(0, 122, 255, 0.08);
}

.apple-radio-input {
  display: none;
}

.apple-radio-custom {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #d1d1d6;
  flex-shrink: 0;
  position: relative;
  transition: all 0.15s ease;
  margin-top: 2px;
}

.apple-radio-input:checked + .apple-radio-custom {
  border-color: #007AFF;
  background-color: #007AFF;
}

.apple-radio-input:checked + .apple-radio-custom::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: white;
}

.apple-radio-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.apple-radio-title {
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
}

.apple-radio-desc {
  font-size: 12px;
  color: #86868b;
}

.apple-modal-progress {
  margin-bottom: 20px;
}

.apple-progress-bar {
  height: 4px;
  background-color: #e5e5ea;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 12px;
}

.apple-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007AFF 0%, #5ac8fa 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.apple-progress-text {
  font-size: 13px;
  color: #6e6e73;
  text-align: center;
  margin: 0;
}

.apple-progress-info {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.apple-progress-percent {
  font-size: 13px;
  font-weight: 600;
  color: #007AFF;
}

.apple-modal-result {
  margin-bottom: 20px;
  max-height: 280px;
  overflow-y: auto;
}

.apple-result-summary {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 16px;
  background-color: #f5f5f7;
  border-radius: 12px;
  margin-bottom: 16px;
}

.apple-result-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.apple-result-count {
  font-size: 24px;
  font-weight: 600;
}

.apple-result-label {
  font-size: 12px;
  color: #86868b;
}

.apple-result-success .apple-result-count {
  color: #34c759;
}

.apple-result-failed .apple-result-count {
  color: #ff3b30;
}

.apple-result-skipped .apple-result-count {
  color: #ff9500;
}

.apple-result-list {
  margin-top: 12px;
}

.apple-result-list-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.apple-result-list-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.apple-result-list-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #1d1d1f;
  padding: 8px;
  background-color: #f9f9fb;
  border-radius: 8px;
}

.apple-result-list-item svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.apple-result-more {
  font-size: 12px;
  color: #86868b;
  margin: 4px 0 0 0;
  padding-left: 12px;
}

.apple-modal-actions {
  display: flex;
  gap: 12px;
}

.apple-btn {
  flex: 1;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.apple-btn-primary {
  color: #ffffff;
  background: linear-gradient(180deg, #007AFF 0%, #0066D6 100%);
  box-shadow: 0 1px 3px rgba(0, 122, 255, 0.3);
}

.apple-btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
}

.apple-btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.apple-btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.apple-btn-secondary {
  color: #007AFF;
  background-color: #f2f2f7;
}

.apple-btn-secondary:hover {
  background-color: #e5e5ea;
}

.apple-btn-secondary:active {
  transform: scale(0.98);
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .apple-modal-container,
.modal-leave-to .apple-modal-container {
  transform: scale(0.9);
}

@media (max-width: 480px) {
  .apple-modal-container {
    width: 95%;
    border-radius: 16px;
    padding: 20px;
  }

  .apple-result-summary {
    gap: 16px;
    padding: 12px;
  }

  .apple-result-count {
    font-size: 20px;
  }
}
</style>
