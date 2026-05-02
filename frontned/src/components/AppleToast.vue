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
  animation: slideDown 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.apple-toast-content {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
}

.apple-toast-icon {
  flex-shrink: 0;
}

.apple-toast-text {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

@media (max-width: 480px) {
  .apple-toast-container {
    top: 16px;
    left: 16px;
    right: 16px;
    transform: none;
  }
  
  .apple-toast-content {
    padding: 10px 16px;
  }
}
</style>