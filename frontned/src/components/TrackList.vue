<template>
  <div class="space-y-1">
    <div
      v-for="(track, index) in tracks"
      :key="track.id"
      :data-track-id="track.id"
      class="group flex items-center justify-between py-3 px-2 hover:bg-gray-50 rounded-lg transition cursor-pointer border-b border-gray-50"
      @click="$emit('play', { track, index })"
    >
      <div class="flex items-center flex-1 min-w-0">
        <div class="w-10 h-10 sm:w-12 sm:h-12 bg-gray-200 rounded-md mr-3 sm:mr-4 shrink-0 overflow-hidden">
          <img v-if="track.track_cover" :src="track.track_cover" alt="cover" class="w-full h-full object-cover">
        </div>
        <div class="flex flex-col truncate min-w-0">
          <span class="font-medium text-sm sm:text-base truncate">{{ track.title }}</span>
          <span class="text-xs text-gray-500 truncate hidden sm:block">{{ track.artist_name }}</span>
        </div>
      </div>
      <div class="hidden sm:block w-24 md:w-1/4 text-sm text-gray-500 truncate mx-2">{{ track.album_title || '未知专辑' }}</div>
      <div class="hidden md:block w-1/6 text-sm text-gray-500 truncate">{{ formatDate(track.added_at) }}</div>
      <div class="w-16 sm:w-24 text-sm text-gray-500 text-right pr-2 sm:pr-4">{{ formatDuration(track.duration) }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tracks: {
    type: Array,
    required: true
  }
})

defineEmits(['play'])

const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return dateStr.split('T')[0]
}
</script>
