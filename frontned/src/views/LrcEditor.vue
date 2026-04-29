<template>
  <div class="h-screen w-full flex flex-col bg-gray-50 overflow-hidden font-sans">
    <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
      <div class="flex items-center space-x-4">
        <span v-if="track" class="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full border border-gray-200">
          当前编辑: {{ track.title }} - {{ track.artist_name }}
        </span>
      </div>
      
      <div class="flex items-center space-x-6">
        <div class="hidden md:flex items-center space-x-3 text-sm text-gray-500 bg-gray-100/80 px-4 py-1.5 rounded-lg border border-gray-200 shadow-inner">
          <span class="flex items-center">
            <kbd class="bg-white border border-gray-300 shadow-sm px-2 py-0.5 rounded text-xs text-gray-700 mr-2 font-mono font-bold">Space</kbd> 
            播放 / 暂停
          </span>
          <span class="w-px h-4 bg-gray-300"></span>
          <span class="flex items-center">
            <kbd class="bg-white border border-gray-300 shadow-sm px-2 py-0.5 rounded text-xs text-blue-600 mr-2 font-mono font-bold">Enter</kbd>
            打点并跳至下行
          </span>
        </div>
        <div class="flex items-center space-x-2 text-sm text-gray-500">
          <span class="shrink-0">偏移量</span>
          <el-input-number
            v-model="timeOffsetMs"
            :min="0"
            :max="5000"
            :step="10"
            size="small"
            controls-position="right"
            class="w-28"
          />
          <span class="text-gray-400">ms</span>
        </div>
        <el-button type="primary" size="large" :icon="Check" :loading="saving" @click="saveLyrics" round class="px-6 font-bold shadow-md">
          保存并同步
        </el-button>
      </div>
    </header>

    <main class="flex-1 flex overflow-hidden">
      
      <aside class="shrink-0 bg-white border-r border-gray-200 flex flex-col z-0 shadow-[4px_0_15px_rgba(0,0,0,0.02)]">
        <div class="p-8 border-b border-gray-100 flex flex-col items-center bg-gray-50/50">
          <div class="w-full px-4 mb-4">
            <el-slider 
              v-model="currentTime" 
              :max="duration" 
              :format-tooltip="formatTime"
              @change="seekAudio"
              class="w-full"
            />
            <div class="flex justify-between items-center mt-2">
              <span class="text-sm text-gray-500 font-mono font-bold">{{ formatTime(currentTime) }}</span>
              <span class="text-sm text-gray-400 font-mono">{{ formatTime(duration) }}</span>
            </div>
          </div>

          <div class="flex items-center justify-center space-x-3">
            <el-button size="small" @click="seekRelative(-5)" title="快退5秒" class="rounded-lg hover:border-blue-300 hover:text-blue-500 font-bold px-3">-5s</el-button>
            <el-button size="small" @click="seekRelative(-1)" title="快退1秒" class="rounded-lg hover:border-blue-300 hover:text-blue-500 px-3">-1s</el-button>

            <button @click="togglePlay" class="w-12 h-12 flex items-center justify-center hover:opacity-80 transition">
              <svg v-if="!isPlaying" class="w-8 h-8 text-gray-700 ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
              <svg v-else class="w-8 h-8 text-gray-700" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
              </svg>
            </button>

            <el-button size="small" @click="seekRelative(1)" title="快进1秒" class="rounded-lg hover:border-blue-300 hover:text-blue-500 px-3">+1s</el-button>
            <el-button size="small" @click="seekRelative(5)" title="快进5秒" class="rounded-lg hover:border-blue-300 hover:text-blue-500 font-bold px-3">+5s</el-button>
          </div>

          <div class="flex items-center justify-center space-x-2 mt-4 pt-3 border-t border-gray-200">
            <span class="text-xs text-gray-400 font-bold shrink-0">倍速</span>
            <el-button size="small" @click="adjustPlaybackRate(-0.1)" :icon="Minus" class="rounded shadow-sm w-8 h-8" />
            <el-input
              v-model.number="playbackRate"
              type="number"
              :min="0.1"
              :max="2.0"
              :step="0.1"
              size="small"
              @change="setPlaybackRate(playbackRate)"
              class="w-16 text-center"
            >
              <template #suffix>
                <span class="text-xs text-gray-400 mr-1">x</span>
              </template>
            </el-input>
            <el-button size="small" @click="adjustPlaybackRate(0.1)" :icon="Plus" class="rounded shadow-sm w-8 h-8" />
            <div class="flex items-center space-x-1 ml-2 border-l border-gray-200 pl-2">
              <el-button size="small" type="info" plain @click="setPlaybackRate(0.5)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400': playbackRate === 0.5}">0.5x</el-button>
              <el-button size="small" type="info" plain @click="setPlaybackRate(1.0)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400': playbackRate === 1.0}">1x</el-button>
              <el-button size="small" type="info" plain @click="setPlaybackRate(1.5)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400': playbackRate === 1.5}">1.5x</el-button>
              <el-button size="small" type="info" plain @click="setPlaybackRate(2.0)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400': playbackRate === 2.0}">2x</el-button>
            </div>
          </div>
        </div>

        <div class="flex-1 p-6 flex flex-col min-h-0">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-bold text-gray-700 flex items-center">
              <el-icon class="mr-1"><Document /></el-icon>原始文本
            </h3>
            <el-button size="default" type="primary" plain @click="parseRawText" class="font-bold">
              解析到时间轴 &rarr;
            </el-button>
          </div>
          <el-input
            v-model="rawText"
            type="textarea"
            class="flex-1 custom-textarea h-full"
            placeholder="在此粘贴网上复制的纯文本歌词，然后点击右上角解析..."
            resize="none"
          />
        </div>
      </aside>

      <section class="flex-1 bg-gray-50 flex flex-col relative">
        <div class="px-8 py-4 border-b border-gray-200 bg-white/70 backdrop-blur flex justify-between items-center shadow-sm z-10 sticky top-0">
          <span class="text-sm font-bold text-gray-700">LRC 制作轨道 (共 {{ lyrics.filter(l => !l.deleted).length }} 行)</span>
          <div class="flex items-center space-x-3">
            <el-switch
              v-model="autoScroll"
              size="small"
              active-text="预览"
              class="shrink-0"
            />
            <el-button size="default" :icon="RefreshLeft" @click="resetTimes" type="danger" plain>重置时间</el-button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-8 custom-scrollbar" ref="lrcListRef">
          <div v-if="lyrics.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400">
            <el-icon class="text-6xl mb-4 text-gray-300"><Document /></el-icon>
            <p class="text-lg">请先在左侧粘贴纯文本歌词并点击解析</p>
          </div>

          <div 
            v-for="(item, index) in lyrics" 
            :key="index"
            :ref="el => { if (el) lineRefs[index] = el }"
            @click="setEditIndex(index)"
            :class="[
              'group flex items-center p-3 mb-3 rounded-xl transition-all duration-300 border-2 cursor-pointer',
              editIndex === index 
                ? 'bg-blue-50 border-blue-400 shadow-md transform scale-[1.01]' 
                : item.deleted
                ? 'bg-gray-100 border-transparent opacity-40'
                : 'bg-white border-transparent hover:border-blue-200 hover:shadow-sm'
            ]"
          >
            <div class="w-32 shrink-0 flex items-center">
              <el-input 
                v-model="item.timeStr" 
                size="default" 
                class="w-24 font-mono text-center"
                :disabled="item.deleted"
                @change="syncTimeFromStr(index)"
                @focus="setEditIndex(index)"
                :class="{'text-blue-600 font-bold': editIndex === index}"
              />
            </div>

            <div class="flex-1 px-4 min-w-0">
              <el-input 
                v-model="item.text" 
                size="default"
                class="w-full lrc-input text-lg"
                :disabled="item.deleted"
                :class="{'font-bold text-blue-600': playingIndex === index}"
                @focus="setEditIndex(index)"
              />
            </div>

            <div class="w-20 shrink-0 flex justify-end gap-3 opacity-30 group-hover:opacity-100 transition-opacity" :class="{'opacity-100': editIndex === index}">
              <svg v-if="!item.deleted" @click.stop="previewLine(item.time)" class="w-5 h-5 text-gray-400 hover:text-blue-500 cursor-pointer transition" fill="currentColor" viewBox="0 0 24 24" title="试听此行">
                <path d="M8 5v14l11-7z"/>
              </svg>
              <svg v-if="item.deleted" @click.stop="lineRefs[index] && (lyrics[index].deleted = false)" class="w-5 h-5 text-gray-400 hover:text-orange-500 cursor-pointer transition" fill="currentColor" viewBox="0 0 24 24" title="撤销删除">
                <path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/>
              </svg>
              <svg v-else @click.stop="deleteLine(index)" class="w-5 h-5 text-gray-400 hover:text-red-500 cursor-pointer transition" fill="currentColor" viewBox="0 0 24 24" title="删除此行">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            </div>
          </div>
          
          <div class="h-96 w-full flex items-center justify-center text-gray-300 font-bold text-sm">
            --- End of Track ---
          </div>
        </div>
      </section>
    </main>

    <audio 
      ref="audioRef" 
      :src="audioStreamUrl" 
      @timeupdate="onTimeUpdate" 
      @loadedmetadata="onMetadataLoaded"
      @ended="isPlaying = false"
    ></audio>

    <AppleToast
      v-model="toastVisible"
      :message="toastMessage"
      :type="toastType"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppleToast from '../components/AppleToast.vue'
import { Back, Check, VideoPlay, VideoPause, RefreshLeft, Document, Plus, Minus, Delete, Refresh } from '@element-plus/icons-vue'
import request from '../api'
import { usePlayerStore } from '../stores/player'

const route = useRoute()
const router = useRouter()
const playerStore = usePlayerStore()

const track = ref(null)
const audioRef = ref(null)
const rawText = ref('')
const lyrics = ref([]) 
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const saving = ref(false)

// 🚨 核心分离：编辑光标与播放光标
const editIndex = ref(-1)    // 当前等待被打点的行（高亮带边框）
const playingIndex = ref(-1) // 当前正在播放的行（仅文字变蓝）
const playbackRate = ref(1.0) // 播放倍速
const deletedLines = ref([]) // 被删除的行（用于撤销）
const timeOffsetMs = ref(251) // 时间偏移量（毫秒），用于补偿延迟
const autoScroll = ref(true) // 预览开关，自动滚动到当前播放行
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastVisible.value = false
  toastMessage.value = message
  toastType.value = type
  setTimeout(() => {
    toastVisible.value = true
  }, 50)
}

const lrcListRef = ref(null)
const lineRefs = ref([])

const audioStreamUrl = computed(() => {
  return track.value ? `http://127.0.0.1:8000/stream/${track.value.id}/` : ''
})

const loadTrackData = async () => {
  const trackId = route.query.id
  if (!trackId) {
    showToast('缺少歌曲 ID 参数', 'error')
    return
  }
  try {
    const res = await request.get(`/tracks/${trackId}/`)
    track.value = res.data
    rawText.value = track.value.lyrics || ''
    if (rawText.value.includes('[')) {
      parseRawText()
    }
  } catch (error) {
    showToast('获取歌曲信息失败', 'error')
  }
}

// 解析文本
const parseRawText = () => {
  if (!rawText.value.trim()) return
  const lines = rawText.value.split('\n')
  lyrics.value = lines.map(line => {
    const match = line.match(/^\[(\d{2}:?\d{2}\.\d{2,3})\](.*)/)
    if (match) {
      return { time: strToSeconds(match[1]), timeStr: match[1], text: match[2].trim(), deleted: false }
    }
    return { time: 0, timeStr: '00:00.00', text: line.trim(), deleted: false }
  })
  
  // 解析完成后，光标默认停留在第一行
  editIndex.value = 0
  showToast('解析完成，已为您定位到第一行，请开始播放并打点！', 'success')
}

// 时间转换工具
const formatTime = (seconds) => {
  if (isNaN(seconds)) return '00:00.00'
  const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0')
  const ms = Math.floor((seconds % 1) * 100).toString().padStart(2, '0')
  return `${mins}:${secs}.${ms}`
}

const strToSeconds = (str) => {
  const parts = str.split(':')
  if (parts.length !== 2) return 0
  return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
}

const syncTimeFromStr = (index) => {
  lyrics.value[index].time = strToSeconds(lyrics.value[index].timeStr)
  lyrics.value.sort((a, b) => a.time - b.time)
}

const togglePlay = () => {
  if (!audioRef.value) return
  isPlaying.value ? audioRef.value.pause() : audioRef.value.play()
  isPlaying.value = !isPlaying.value
  
  // 【新增】：强制移除按钮的焦点
  // 防止鼠标点击播放按钮后，按钮处于 focus 状态，导致按空格键时触发系统默认的按钮点击
  if (document.activeElement && document.activeElement.tagName === 'BUTTON') {
    document.activeElement.blur()
  }
}
const seekAudio = (val) => {
  if (audioRef.value) audioRef.value.currentTime = val
}

const seekRelative = (delta) => {
  if (!audioRef.value) return
  const newTime = Math.max(0, Math.min(duration.value, audioRef.value.currentTime + delta))
  audioRef.value.currentTime = newTime
  currentTime.value = newTime
}

const adjustPlaybackRate = (delta) => {
  const newRate = Math.max(0.1, Math.min(2.0, playbackRate.value + delta))
  playbackRate.value = parseFloat(newRate.toFixed(1))
  if (audioRef.value) {
    audioRef.value.playbackRate = playbackRate.value
  }
}

const setPlaybackRate = (rate) => {
  playbackRate.value = rate
  if (audioRef.value) {
    audioRef.value.playbackRate = rate
  }
}

const onMetadataLoaded = () => {
  duration.value = audioRef.value.duration
}

const setEditIndex = (index) => {
  editIndex.value = index
}

// 随着音乐播放更新文字变蓝的行
const onTimeUpdate = () => {
  if (!audioRef.value) return
  currentTime.value = audioRef.value.currentTime

  const index = lyrics.value.findIndex((l, i) => {
    const next = lyrics.value[i + 1]
    return currentTime.value >= l.time && (!next || currentTime.value < next.time)
  })

  if (index !== -1 && playingIndex.value !== index) {
    playingIndex.value = index
    if (autoScroll.value) {
      scrollToLine(playingIndex.value)
    }
  }
}

const scrollToLine = async (index) => {
  await nextTick()
  const el = lineRefs.value[index]
  if (el && lrcListRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// ⭐ 核心逻辑：记录当前行，永远跳转下一行（跳过已删除的行）
const stampTime = () => {
  if (!audioRef.value || editIndex.value === -1 || editIndex.value >= lyrics.value.length) return

  const rawTime = audioRef.value.currentTime
  const offsetSeconds = timeOffsetMs.value / 1000
  const time = Math.max(0, rawTime - offsetSeconds)
  lyrics.value[editIndex.value].time = time
  lyrics.value[editIndex.value].timeStr = formatTime(time)

  // 打点后自动焦点移到下一行（跳过已删除的行）
  if (editIndex.value < lyrics.value.length - 1) {
    let nextIndex = editIndex.value + 1
    while (nextIndex < lyrics.value.length && lyrics.value[nextIndex].deleted) {
      nextIndex++
    }
    if (nextIndex < lyrics.value.length) {
      editIndex.value = nextIndex
      scrollToLine(editIndex.value)
    }
  }
}

const previewLine = (time) => {
  if (audioRef.value) {
    audioRef.value.currentTime = time
    if (!isPlaying.value) {
      audioRef.value.play()
      isPlaying.value = true
    }
  }
}

const deleteLine = (index) => {
  const line = lyrics.value[index]
  if (line && !line.deleted) {
    line.deleted = true
    deletedLines.value.push(index)
    showToast('已删除，可撤销', 'success')
  }
}

const undoDelete = () => {
  if (deletedLines.value.length === 0) return
  const lastIndex = deletedLines.value.pop()
  if (lyrics.value[lastIndex]) {
    lyrics.value[lastIndex].deleted = false
    showToast('已撤销', 'success')
  }
}

const resetTimes = () => {
  lyrics.value.forEach(l => {
    l.time = 0
    l.timeStr = '00:00.00'
  })
  editIndex.value = 0
  showToast('所有时间已归零，请重新开始打点', 'success')
}

// 保存逻辑
const saveLyrics = async () => {
  if (!track.value) return
  
  const lrcContent = lyrics.value
    .filter(l => l.text && !l.deleted) // 忽略空行和已删除的行
    .map(l => `[${l.timeStr}]${l.text}`)
    .join('\n')
  
  saving.value = true
  try {
    // 兼容 multipart/form-data 
    const formData = new FormData()
    formData.append('lyrics', lrcContent)

    await request.patch(`/tracks/${track.value.id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    showToast('歌词已成功保存并同步至音频文件！', 'success')
    rawText.value = lrcContent
    deletedLines.value = []
  } catch (error) {
    showToast('保存失败，请检查网络', 'error')
  } finally {
    saving.value = false
  }
}

// 键盘事件劫持
const handleKeyDown = (e) => {
  const activeTag = document.activeElement.tagName
  const isInput = activeTag === 'TEXTAREA' || activeTag === 'INPUT'

  // 空格键：在输入框内打字时不允许暂停
  if (e.code === 'Space') {
    if (!isInput) {
      e.preventDefault() // 阻止页面向下滚动
      e.stopImmediatePropagation() // 【新增】：彻底阻止事件冒泡！防止外层的全局播放器捕捉到空格键而同时播放
      togglePlay()
    }
  }
  
  // 回车键：即使在输入框内（比如修改歌词错别字），敲回车也会直接打点并跳下一行
  if (e.code === 'Enter' || e.code === 'NumpadEnter') {
    if (document.activeElement.type === 'textarea') return 
    
    e.preventDefault() 
    stampTime()
  }
}

onMounted(() => {
  if (playerStore.audioElement) {
    playerStore.audioElement.pause()
  }
  playerStore.isPlaying = false
  loadTrackData()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* 隐藏歌词输入框自带边框，背景透明 */
.lrc-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent !important;
  padding: 0;
}
.lrc-input :deep(.el-input__inner) {
  font-size: 1.125rem; /* 更大更清晰的歌词字体 */
  transition: all 0.3s;
}

/* 左侧多行文本框 */
.custom-textarea :deep(.el-textarea__inner) {
  height: 100% !important;
  border-radius: 12px;
  background-color: #f9fafb;
  border: 1px solid #f3f4f6;
  font-size: 14px;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}
.custom-textarea :deep(.el-textarea__inner:focus) {
  background-color: #fff;
  border-color: #bfdbfe;
}
.custom-textarea :deep(.el-textarea__inner::-webkit-scrollbar) {
  width: 6px;
}
.custom-textarea :deep(.el-textarea__inner::-webkit-scrollbar-track) {
  background: transparent;
}
.custom-textarea :deep(.el-textarea__inner::-webkit-scrollbar-thumb) {
  background-color: #d1d5db;
  border-radius: 3px;
}

/* 滚动条美化 */
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #d1d5db;
}
</style>