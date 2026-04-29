<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none"
      >
        <div class="bg-black/50 rounded-2xl p-6 shadow-2xl">
          <Icon icon="mdi:volume-high" class="w-12 h-12 text-white mb-3 mx-auto" style="opacity: 0.8" />
          <div class="w-48 h-2 bg-white/20 rounded-full overflow-hidden">
            <div
              class="h-full bg-white rounded-full transition-all duration-100"
              :style="{ width: (playerStore.volume * 100) + '%' }"
              style="opacity: 0.8"
            ></div>
          </div>
          <p class="text-white text-center text-lg font-medium mt-2" style="opacity: 0.8">{{ Math.round(playerStore.volume * 100) }}%</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { usePlayerStore } from '../stores/player'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const playerStore = usePlayerStore()
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
