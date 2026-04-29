<template>
  <Teleport to="body">
    <div v-if="modelValue" class="apple-confirm-overlay" @click.self="handleCancel">
      <div class="apple-confirm-container">
        <div class="apple-confirm-icon">
          <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
        </div>
        
        <h3 class="apple-confirm-title">{{ title }}</h3>
        <p class="apple-confirm-message">{{ message }}</p>
        
        <div class="apple-confirm-actions">
          <button class="apple-btn apple-btn-cancel" @click="handleCancel">
            {{ cancelText }}
          </button>
          <button class="apple-btn apple-btn-confirm" @click="handleConfirm">
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: '确认操作'
  },
  message: {
    type: String,
    default: ''
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  cancelText: {
    type: String,
    default: '取消'
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const handleConfirm = () => {
  emit('update:modelValue', false)
  emit('confirm')
}

const handleCancel = () => {
  emit('update:modelValue', false)
  emit('cancel')
}

watch(() => props.modelValue, (val) => {
  if (!val) {
    emit('cancel')
  }
})
</script>

<style scoped>
.apple-confirm-overlay {
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
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.apple-confirm-container {
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(40px);
  border-radius: 20px;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(0, 0, 0, 0.1);
  width: 90%;
  max-width: 340px;
  padding: 24px;
  text-align: center;
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

.apple-confirm-icon {
  margin-bottom: 16px;
}

.apple-confirm-title {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px 0;
}

.apple-confirm-message {
  font-size: 13px;
  color: #6e6e73;
  line-height: 1.5;
  margin: 0 0 20px 0;
}

.apple-confirm-actions {
  display: flex;
  gap: 12px;
}

.apple-btn {
  flex: 1;
  padding: 10px 16px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.apple-btn-cancel {
  color: #007AFF;
  background-color: #f2f2f7;
}

.apple-btn-cancel:hover {
  background-color: #e5e5ea;
}

.apple-btn-cancel:active {
  transform: scale(0.98);
}

.apple-btn-confirm {
  color: #ffffff;
  background: linear-gradient(180deg, #ff3b30 0%, #f53024 100%);
  box-shadow: 0 1px 3px rgba(255, 59, 48, 0.3);
}

.apple-btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 59, 48, 0.4);
}

.apple-btn-confirm:active {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(255, 59, 48, 0.2);
}

@media (max-width: 480px) {
  .apple-confirm-container {
    width: 95%;
    border-radius: 16px;
    padding: 20px;
  }
  
  .apple-btn {
    padding: 12px 16px;
  }
}
</style>