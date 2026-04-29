<template>
  <div class="h-screen w-full flex flex-col bg-gray-50 overflow-hidden font-sans">
    <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0 z-10 shadow-sm">
      <div class="flex items-center space-x-4">
        <el-button @click="goBack" circle :icon="Back" />
        <h1 class="text-lg font-bold text-gray-800 flex items-center">
          <el-icon class="mr-2 text-blue-500"><Microphone /></el-icon>
          歌词时间轴编辑器
        </h1>
        <span v-if="track" class="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          正在编辑: {{ track.title }} - {{ track.artist_name }}
        </span>
      </div>
      <div class="flex items-center space-x-4">
        <el-tooltip content="快捷键: [空格] 播放/暂停 | [回车] 标记当前行并跳至下一行" placement="bottom">
          <el-button type="info" plain circle :icon="InfoFilled" />
        </el-tooltip>
        <el-button type="primary" :icon="Check" :loading="saving" @click="saveLyrics" round>
          保存并同步至物理文件
        </el-button>
      </div>
    </header>

    <main class="flex-1 flex overflow-hidden">
      
      <aside class="w-1/3 min-w-[350px] max-w-[450px] bg-white border-r border-gray-200 flex flex-col z-0">
        <div class="p-6 border-b border-gray-100 flex flex-col items-center">
          <div class="w-40 h-40 rounded-xl bg-gray-100 shadow-md overflow-hidden mb-6 relative group">
            <img v-if="track?.track_cover" :src="track.track_cover" class="w-full h-full object-cover" />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-400">无封面</div>
            
            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <el-button @click="togglePlay" circle size="large" type="primary" class="scale-125">
                <el-icon class="text-2xl"><component :is="isPlaying ? VideoPause : VideoPlay" /></el-icon>
              </el-button>
            </div>
          </div>

          <div class="w-full px-4">
            <el-slider 
              v-model="currentTime" 
              :max="duration" 
              :format-tooltip="formatTime"
              @change="seekAudio"
              class="w-full"
            />
            <div class="flex justify-between text-xs text-gray-400 font-mono mt-1">
              <span>{{ formatTime(currentTime) }}</span>
              <span>{{ formatTime(duration) }}</span>
            </div>
          </div>
        </div>

        <div class="flex-1 p-6 flex flex-col min-h-0">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-bold text-gray-700">原始文本</h3>
            <el-button size="small" type="primary" link @click="parseRawText">
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

      <section class="flex-1 bg-gray-50 flex flex-col">
        <div class="px-8 py-4 border-b border-gray-200 bg-white/50 backdrop-blur flex justify-between items-center shadow-sm z-10">
          <span class="text-sm font-medium text-gray-600">时间轴对齐 (共 {{ lyrics.length }} 行)</span>
          <el-button size="small" :icon="RefreshLeft" @click="resetTimes">重置所有时间</el-button>
        </div>

        <div class="flex-1 overflow-y-auto p-8 custom-scrollbar" ref="lrcListRef">
          <div v-if="lyrics.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400">
            <el-icon class="text-6xl mb-4 text-gray-300"><Document /></el-icon>
            <p>请先在左侧输入纯文本歌词并解析</p>
          </div>

          <div 
            v-for="(item, index) in lyrics" 
            :key="index"
            :ref="el => { if (el) lineRefs[index] = el }"
            :class="[
              'group flex items-center p-3 mb-3 rounded-xl transition-all duration-300 border-2',
              activeLine === index 
                ? 'bg-blue-50 border-blue-400 shadow-md transform scale-[1.01]' 
                : 'bg-white border-transparent hover:border-gray-200 hover:shadow-sm'
            ]"
          >
            <div class="w-28 shrink-0 flex items-center">
              <el-input 
                v-model="item.timeStr" 
                size="small" 
                class="w-20 font-mono text-center"
                @change="syncTimeFromStr(index)"
                :class="{'text-blue-600 font-bold': activeLine === index}"
              />
            </div>

            <div class="flex-1 px-4 min-w-0">
              <el-input 
                v-model="item.text" 
                size="small"
                class="w-full lrc-input"
                :class="{'font-bold text-blue-900': activeLine === index}"
              />
            </div>

            <div class="w-32 shrink-0 flex justify-end items-center space-x-2 opacity-30 group-hover:opacity-100 transition-opacity" :class="{'opacity-100': activeLine === index}">
              <el-button 
                size="small" 
                type="primary" 
                @click="tagCurrentTime(index)"
              >
                打点
              </el-button>
              <el-button 
                size="small" 
                circle 
                plain
                @click="previewLine(item.time)"
                :icon="VideoPlay"
              />
            </div>
          </div>
          
          <div class="h-64 w-full"></div>
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Check, VideoPlay, VideoPause, RefreshLeft, Microphone, InfoFilled, Document } from '@element-plus/icons-vue'
import request from '../api' // 你的 axios 实例

const route = useRoute()
const router = useRouter()

// 状态
const track = ref(null)
const audioRef = ref(null)
const rawText = ref('')
const lyrics = ref([]) 
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const activeLine = ref(-1)
const saving = ref(false)

const lrcListRef = ref(null)
const lineRefs = ref([])

// 假设你的音频流接口是 /api/stream/{id}/
const audioStreamUrl = computed(() => {
  return track.value ? `http://127.0.0.1:8000/api/stream/${track.value.id}/` : ''
})

// --- 1. 数据加载 ---
const loadTrackData = async () => {
  const trackId = route.query.id
  if (!trackId) {
    ElMessage.error('缺少歌曲 ID 参数')
    return
  }
  try {
    const res = await request.get(`/tracks/${trackId}/`)
    track.value = res.data
    rawText.value = track.value.lyrics || ''
    // 如果数据库里已经是LRC格式，直接解析
    if (rawText.value.includes('[')) {
      parseRawText()
    }
  } catch (error) {
    ElMessage.error('获取歌曲信息失败')
  }
}

// --- 2. 核心解析与转换 ---
const parseRawText = () => {
  if (!rawText.value.trim()) return
  const lines = rawText.value.split('\n')
  lyrics.value = lines.map(line => {
    // 匹配 [00:00.00] 格式
    const match = line.match(/^\[(\d{2}:?\d{2}\.\d{2,3})\](.*)/)
    if (match) {
      return { time: strToSeconds(match[1]), timeStr: match[1], text: match[2].trim() }
    }
    // 纯文本则默认 0 秒
    return { time: 0, timeStr: '00:00.00', text: line.trim() }
  })
  ElMessage.success('解析完成，请开始打点')
}

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
  // 重新排序，防止用户乱改导致时间错乱
  lyrics.value.sort((a, b) => a.time - b.time)
}

// --- 3. 播放与打点交互 ---
const togglePlay = () => {
  if (!audioRef.value) return
  if (isPlaying.value) {
    audioRef.value.pause()
  } else {
    audioRef.value.play()
  }
  isPlaying.value = !isPlaying.value
}

const seekAudio = (val) => {
  if (audioRef.value) {
    audioRef.value.currentTime = val
  }
}

const onMetadataLoaded = () => {
  duration.value = audioRef.value.duration
}

const onTimeUpdate = () => {
  if (!audioRef.value) return
  currentTime.value = audioRef.value.currentTime
  
  // 查找当前应该高亮哪一行
  const index = lyrics.value.findIndex((l, i) => {
    const next = lyrics.value[i + 1]
    return currentTime.value >= l.time && (!next || currentTime.value < next.time)
  })
  
  if (index !== -1 && activeLine.value !== index) {
    activeLine.value = index
    scrollToActiveLine()
  }
}

const scrollToActiveLine = async () => {
  await nextTick()
  const el = lineRefs.value[activeLine.value]
  if (el && lrcListRef.value) {
    // 平滑滚动到视口中间
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// ⭐ 核心动作：为当前行打上当前播放时间的标签
const tagCurrentTime = (index) => {
  if (!audioRef.value) return
  const time = audioRef.value.currentTime
  lyrics.value[index].time = time
  lyrics.value[index].timeStr = formatTime(time)
  
  // 打点后自动焦点移到下一行，方便连续操作
  if (index < lyrics.value.length - 1) {
    activeLine.value = index + 1
    scrollToActiveLine()
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

const resetTimes = () => {
  lyrics.value.forEach(l => {
    l.time = 0
    l.timeStr = '00:00.00'
  })
  ElMessage.success('所有时间已归零')
}

// --- 4. 保存与通信 ---
const saveLyrics = async () => {
  if (!track.value) return
  
  // 拼接成标准 LRC 格式字符串
  const lrcContent = lyrics.value
    .filter(l => l.text) // 忽略空行
    .map(l => `[${l.timeStr}]${l.text}`)
    .join('\n')
  
  saving.value = true
  try {
    // 调用你在后端写的 PUT/PATCH 接口更新歌词
    await request.patch(`/tracks/${track.value.id}/`, {
      lyrics: lrcContent
    })
    ElMessage.success('歌词已成功保存并同步至音频文件！')
    // 更新左侧的原始文本框
    rawText.value = lrcContent
  } catch (error) {
    ElMessage.error('保存失败，请检查网络')
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  router.back()
}

// --- 5. 快捷键劫持 ---
const handleKeyDown = (e) => {
  // 如果焦点在输入框（除了我们特殊的快捷操作），不拦截
  const activeTag = document.activeElement.tagName
  const isInput = activeTag === 'TEXTAREA' || activeTag === 'INPUT'

  if (e.code === 'Space') {
    if (!isInput) {
      e.preventDefault()
      togglePlay()
    }
  }
  
  // 回车键快速打点 (极其好用的功能)
  if (e.code === 'Enter' || e.code === 'NumpadEnter') {
    // 如果焦点在输入框内，阻止它默认的换行行为，改成打点
    e.preventDefault()
    let targetIndex = activeLine.value
    if (targetIndex === -1) targetIndex = 0
    if (lyrics.value.length > 0) {
      tagCurrentTime(targetIndex)
    }
  }
}

onMounted(() => {
  loadTrackData()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* 隐藏输入框边框使其与背景融为一体 */
.lrc-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent !important;
  padding: 0;
}
.lrc-input :deep(.el-input__inner) {
  font-size: 1rem;
}

/* 左侧多行文本框高度填满 */
.custom-textarea :deep(.el-textarea__inner) {
  height: 100% !important;
  border-radius: 12px;
  background-color: #f9fafb;
  border: 1px solid #f3f4f6;
}
.custom-textarea :deep(.el-textarea__inner:focus) {
  background-color: #fff;
  border-color: #bfdbfe;
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