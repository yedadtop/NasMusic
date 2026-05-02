<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="modelValue" class="apple-toast-container">
        <div class="apple-toast-content">
          <div class="apple-toast-icon" :class="type">
            <svg v-if="type === 'success'" class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
            </svg>
            <svg v-else-if="type === 'error'" class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <svg v-else class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <span class="apple-toast-text">{{ message }}</span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, ref, onMounted } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'success',
    validator: (val) => ['success', 'error', 'info'].includes(val)
  },
  duration: {
    type: Number,
    default: 2000
  }
})

const emit = defineEmits(['update:modelValue'])

let timer = null

const startTimer = () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    emit('update:modelValue', false)
  }, props.duration)
}

watch(() => props.modelValue, (val) => {
  if (val) {
    startTimer()
  } else {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }
}, { immediate: true })

onMounted(() => {
  if (props.modelValue) {
    startTimer()
  }
})
</script>

<style scoped>
.apple-toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 99999;
  /* 限制最大宽度，防止内容过长时贴边 */
  max-width: 90vw;
  width: max-content;
}

.apple-toast-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 20px;
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
  /* 核心：宽度自适应内容 */
  width: fit-content;
}

.apple-toast-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.apple-toast-text {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  text-align: left;
  white-space: nowrap;
}

.toast-enter-active {
  animation: toastIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.toast-leave-active {
  animation: toastOut 0.3s cubic-bezier(0.4, 0, 1, 1);
}

@keyframes toastIn {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-30px) scale(0.9);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

@keyframes toastOut {
  0% {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px) scale(0.9);
  }
}

/* 移动端优化 */
@media (max-width: 480px) {
  .apple-toast-container {
    top: 16px;
    /* 移除强制拉伸，保持左侧50%居中 */
  }
  
  .apple-toast-content {
    padding: 10px 16px;
    /* 移除 width: 100%，让它继承 fit-content */
  }
  
  .apple-toast-text {
    /* 如果文字太长，允许换行显示 */
    white-space: normal;
    word-break: break-word;
  }
  
  /* 移动端直接复用 PC 端的动画（因为都保留了 translateX(-50%) 居中逻辑） */
}
</style>