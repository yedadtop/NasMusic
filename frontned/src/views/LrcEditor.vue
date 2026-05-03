<template>
  <div class="h-screen w-full flex flex-col bg-gray-50 overflow-hidden font-sans">
    
    <!-- Header 响应式导航栏 -->
    <header class="h-14 md:h-16 bg-white border-b border-gray-200 flex items-center justify-between px-3 md:px-6 shrink-0 z-20 shadow-sm gap-2">
      <div class="flex items-center flex-1 min-w-0 mr-2">
        <!-- 移动端：显示呼出侧边栏的按钮 -->
        <el-button 
          class="md:hidden mr-2 md:mr-3 shadow-sm shrink-0" 
          :icon="Operation" 
          circle 
          @click="sidebarDrawer = true"
        />
        <!-- 恢复歌名歌手，全尺寸显示并防溢出截断 -->
        <span v-if="track" class="inline-flex items-center text-[11px] md:text-sm text-gray-500 bg-gray-100 px-2 md:px-3 py-1 md:py-1.5 rounded-full border border-gray-200 truncate max-w-full">
          <span class="hidden sm:inline font-bold mr-1 shrink-0">当前编辑:</span>
          <span class="truncate">{{ track.title }} - {{ (track.all_artists || []).join('/') || track.artist_name || '未知歌手' }}</span>
        </span>
      </div>
      
      <div class="flex items-center space-x-2 md:space-x-4 shrink-0">
        
        <!-- PC端：恢复快捷键提示说明 -->
        <div class="hidden lg:flex items-center space-x-3 text-sm text-gray-500 bg-gray-100/80 px-4 py-1.5 rounded-lg border border-gray-200 shadow-inner mr-2">
          <span class="flex items-center">
            <kbd class="bg-white border border-gray-300 shadow-sm px-2 py-0.5 rounded text-xs text-gray-700 mr-2 font-mono font-bold">Space</kbd>
            播放/暂停
          </span>
          <span class="w-px h-4 bg-gray-300"></span>
          <span class="flex items-center">
            <kbd class="bg-white border border-gray-300 shadow-sm px-2 py-0.5 rounded text-xs text-blue-600 mr-2 font-mono font-bold">Enter</kbd>
            打点跳下行
          </span>
          <el-popover placement="bottom" :width="280" trigger="click">
            <template #reference>
              <el-icon class="ml-2 cursor-pointer text-gray-400 hover:text-gray-600 transition-colors"><QuestionFilled /></el-icon>
            </template>
            <div class="text-sm">
              <div class="font-bold text-gray-700 mb-3 border-b pb-2">键盘快捷键</div>
              <div class="space-y-2.5">
                <div class="flex items-center justify-between"><span class="flex items-center"><kbd class="bg-gray-100 border border-gray-300 shadow-sm px-1.5 py-0.5 rounded text-xs text-gray-600 mr-2 font-mono">Space</kbd>播放 / 暂停</span></div>
                <div class="flex items-center justify-between"><span class="flex items-center"><kbd class="bg-blue-50 border border-blue-300 shadow-sm px-1.5 py-0.5 rounded text-xs text-blue-600 mr-2 font-mono">Enter</kbd>打点并跳转下一行</span></div>
                <div class="flex items-center justify-between"><span class="flex items-center"><kbd class="bg-gray-100 border border-gray-300 shadow-sm px-1.5 py-0.5 rounded text-xs text-gray-600 mr-2 font-mono">1/2/3/4</kbd>快退/快进</span></div>
                <div class="flex items-center justify-between"><span class="flex items-center"><kbd class="bg-gray-100 border border-gray-300 shadow-sm px-1.5 py-0.5 rounded text-xs text-gray-600 mr-2 font-mono">Q/W/E/R</kbd>0.5x ~ 2.0x 倍速</span></div>
              </div>
            </div>
          </el-popover>
        </div>

        <!-- PC端保留头部偏移量 -->
        <div class="hidden md:flex items-center space-x-2 text-sm text-gray-500 mr-2">
          <span class="shrink-0 text-xs font-bold">偏移</span>
          <el-input-number v-model="timeOffsetMs" :min="0" :max="5000" :step="10" size="small" controls-position="right" class="w-24" />
          <span class="text-xs text-gray-400">ms</span>
        </div>

        <el-button type="primary" :size="isMobile ? 'small' : 'default'" :icon="Check" :loading="saving" @click="saveLyrics" round class="font-bold shadow-md px-4 md:px-6">
          {{ isMobile ? '保存' : '保存并同步' }}
        </el-button>
      </div>
    </header>

    <main class="flex-1 flex overflow-hidden relative">
      
      <!-- 移动端抽屉遮罩层 -->
      <div 
        v-if="isMobile && sidebarDrawer" 
        @click="sidebarDrawer = false" 
        class="fixed inset-0 bg-black/40 z-20 backdrop-blur-sm transition-opacity"
      ></div>

      <!-- 侧边栏：PC端为固定Aside，移动端通过CSS转化为滑动抽屉 -->
      <aside 
        :class="[
          'bg-white flex flex-col shrink-0 transition-transform duration-300 z-30',
          isMobile 
            ? 'fixed inset-y-0 left-0 w-[85%] max-w-[340px] shadow-2xl transform ' + (sidebarDrawer ? 'translate-x-0' : '-translate-x-full')
            : 'w-80 lg:w-96 border-r border-gray-200 relative translate-x-0 shadow-[4px_0_15px_rgba(0,0,0,0.02)]'
        ]"
      >
        <!-- 移动端抽屉专属 Header -->
        <div v-if="isMobile" class="flex justify-between items-center p-4 border-b border-gray-100 bg-gray-50/50 shrink-0">
          <span class="font-bold text-gray-700 flex items-center">
            <el-icon class="mr-2 text-blue-500"><Operation /></el-icon>工具与设置
          </span>
          <el-button :icon="Close" circle size="small" @click="sidebarDrawer = false" />
        </div>

        <!-- 移动端专属：抽屉里的时间偏移量设置 -->
        <div v-if="isMobile" class="p-4 border-b border-gray-100 bg-white flex items-center justify-between shrink-0">
          <span class="text-sm font-bold text-gray-700">时间偏移量</span>
          <div class="flex items-center">
            <el-input-number v-model="timeOffsetMs" :min="0" :max="5000" :step="10" size="small" controls-position="right" class="w-24" />
            <span class="text-xs text-gray-400 ml-2">ms</span>
          </div>
        </div>

        <!-- 播放控制区：移动端隐藏（移到底部打点栏），PC端保留 -->
        <div v-if="!isMobile" class="p-4 md:p-6 lg:p-8 border-b border-gray-100 flex flex-col items-center bg-gray-50/30 shrink-0">
          <div class="w-full mb-3 md:mb-4">
            <el-slider v-model="currentTime" :max="duration" :format-tooltip="formatTime" @change="seekAudio" size="small" class="w-full" />
            <div class="flex justify-between items-center mt-1 md:mt-2">
              <span class="text-xs md:text-sm text-gray-500 font-mono font-bold">{{ formatTime(currentTime) }}</span>
              <span class="text-xs md:text-sm text-gray-400 font-mono">{{ formatTime(duration) }}</span>
            </div>
          </div>

          <div class="flex items-center justify-center space-x-2 md:space-x-3 w-full">
            <el-button size="small" @click="seekRelative(-5)" title="快退5秒" class="rounded-lg hover:text-blue-500 font-bold px-2 md:px-3">-5s</el-button>
            <el-button size="small" @click="seekRelative(-1)" title="快退1秒" class="rounded-lg hover:text-blue-500 px-2 md:px-3">-1s</el-button>

            <button @click="togglePlay" class="w-12 h-12 flex items-center justify-center hover:opacity-80 transition active:scale-95 shrink-0 bg-blue-50 rounded-full text-blue-600">
              <svg v-if="!isPlaying" class="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
            </button>

            <el-button size="small" @click="seekRelative(1)" title="快进1秒" class="rounded-lg hover:text-blue-500 px-2 md:px-3">+1s</el-button>
            <el-button size="small" @click="seekRelative(5)" title="快进5秒" class="rounded-lg hover:text-blue-500 font-bold px-2 md:px-3">+5s</el-button>
          </div>

          <div class="flex flex-wrap items-center justify-center gap-y-2 mt-4 pt-4 border-t border-gray-200 w-full">
            <div class="flex items-center space-x-1">
              <el-button size="small" @click="adjustPlaybackRate(-0.1)" :icon="Minus" class="rounded shadow-sm w-7 h-7 md:w-8 md:h-8" />
              <el-input v-model.number="playbackRate" type="number" :min="0.1" :max="2.0" :step="0.1" size="small" @change="setPlaybackRate(playbackRate)" class="w-16 text-center font-mono" />
              <el-button size="small" @click="adjustPlaybackRate(0.1)" :icon="Plus" class="rounded shadow-sm w-7 h-7 md:w-8 md:h-8" />
            </div>
            
            <div class="flex items-center space-x-1 sm:ml-2 border-l-0 sm:border-l border-gray-200 sm:pl-2">
              <el-button size="small" type="info" plain @click="setPlaybackRate(0.5)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400 text-blue-600': playbackRate === 0.5}">0.5x</el-button>
              <el-button size="small" type="info" plain @click="setPlaybackRate(1.0)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400 text-blue-600': playbackRate === 1.0}">1x</el-button>
              <el-button size="small" type="info" plain @click="setPlaybackRate(1.5)" class="text-xs px-2 py-1" :class="{'bg-blue-100 border-blue-400 text-blue-600': playbackRate === 1.5}">1.5x</el-button>
            </div>
          </div>
        </div>

        <!-- 原始文本输入区 (移动端和PC端共用) -->
        <div class="flex-1 p-4 md:p-6 flex flex-col min-h-0 bg-white">
          <div class="flex justify-between items-center mb-2 md:mb-3">
            <h3 class="font-bold text-gray-700 flex items-center text-sm md:text-base">
              <el-icon class="mr-1"><Document /></el-icon>原始文本
            </h3>
            <el-button size="small" type="primary" plain @click="handleParse" class="font-bold text-xs md:text-sm">
              <span class="hidden sm:inline">解析到时间轴 &rarr;</span>
              <span class="sm:hidden">解析 &rarr;</span>
            </el-button>
          </div>
          <el-input 
            v-model="rawText" 
            type="textarea" 
            class="flex-1 custom-textarea h-full" 
            placeholder="粘贴纯文本歌词..." 
            resize="none" 
            @paste="handlePaste" 
          />
        </div>
      </aside>

      <!-- 歌词打点主轨道区 -->
      <section class="flex-1 flex flex-col relative min-w-0 bg-gray-50/50">
        
        <!-- 轨道工具栏 -->
        <div class="px-3 md:px-8 py-2 md:py-3 border-b border-gray-200 bg-white/80 backdrop-blur flex justify-between items-center sticky top-0 z-10 shadow-sm">
          <div class="flex items-center space-x-2">
            <el-button size="small" :icon="Plus" @click="addLine" type="primary" plain class="font-bold px-3">
              <span class="hidden sm:inline">新增行</span>
            </el-button>
            <el-button size="small" :icon="RefreshLeft" @click="resetTimes" type="danger" plain class="hidden sm:inline-flex px-3">重置</el-button>
          </div>
          
          <div class="flex items-center space-x-3">
            <span v-if="isMobile" class="text-xs text-blue-600 font-mono font-bold bg-blue-50 px-2 py-1 rounded">
              {{ formatTime(currentTime) }}
            </span>
            <span class="text-xs md:text-sm font-bold text-gray-500 hidden md:inline">共 {{ lyrics.filter(l => !l.deleted).length }} 行</span>
            <el-switch v-model="autoScroll" size="small" active-text="跟随预览" />
          </div>
        </div>

        <!-- 歌词列表区 -->
        <div class="flex-1 overflow-y-auto p-2 md:p-8 custom-scrollbar" ref="lrcListRef">
          <div v-if="lyrics.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400 p-4 text-center">
            <el-icon class="text-5xl md:text-6xl mb-4 text-gray-300"><Document /></el-icon>
            <p class="text-sm md:text-lg">请先粘贴纯文本歌词并点击解析</p>
          </div>

          <div 
            v-for="(item, index) in lyrics" 
            :key="index"
            :ref="el => { if (el) lineRefs[index] = el }"
            @click="setEditIndex(index, false)"
            :class="[
              'group flex items-center p-2 md:p-3 mb-2 md:mb-3 rounded-xl transition-all duration-200 border-2 cursor-pointer',
              editIndex === index 
                ? 'bg-blue-50 border-blue-400 shadow-sm md:shadow-md transform md:scale-[1.01]' 
                : item.deleted
                ? 'bg-gray-100 border-transparent opacity-40'
                : 'bg-white border-transparent hover:border-blue-200'
            ]"
          >
            <!-- 时间显示：纯文本块 -->
            <div class="w-16 md:w-24 shrink-0 flex items-center justify-center md:justify-start">
              <div 
                class="font-mono text-xs md:text-sm px-1.5 py-1 rounded transition-colors cursor-pointer select-none"
                :class="[
                  item.deleted ? 'text-gray-400 cursor-not-allowed' : (editIndex === index ? 'text-blue-600 font-bold bg-blue-100/50' : 'text-gray-500 hover:bg-gray-100')
                ]"
                @click.stop="!item.deleted && setEditIndex(index, true)"
              >
                {{ item.timeStr }}
              </div>
            </div>

            <!-- 歌词文本 -->
            <div class="flex-1 px-2 md:px-4 min-w-0 flex items-center">
              <input 
                v-model="item.text" 
                :disabled="item.deleted"
                class="w-full bg-transparent border-none outline-none text-[15px] md:text-lg transition-colors placeholder-gray-300"
                :class="{'font-bold text-gray-600': playingIndex === index, 'text-gray-700': playingIndex !== index}"
                @focus="setEditIndex(index, false)"
                @click.stop
                placeholder="在此输入歌词..."
              />
            </div>

            <!-- 操作按钮 -->
            <div class="flex justify-end gap-2 md:gap-3 shrink-0 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity" :class="{'md:opacity-100': editIndex === index}">
              <div v-if="!item.deleted" @click.stop="previewLine(item.time)" class="p-1.5 md:p-1 rounded-md hover:bg-gray-100 cursor-pointer">
                <el-icon class="text-lg md:text-xl text-gray-400 hover:text-blue-500"><VideoPlay /></el-icon>
              </div>
              <div v-if="item.deleted" @click.stop="lineRefs[index] && (lyrics[index].deleted = false)" class="p-1.5 md:p-1 rounded-md hover:bg-gray-100 cursor-pointer">
                <el-icon class="text-lg md:text-xl text-gray-400 hover:text-orange-500"><RefreshLeft /></el-icon>
              </div>
              <div v-else @click.stop="deleteLine(index)" class="p-1.5 md:p-1 rounded-md hover:bg-gray-100 cursor-pointer">
                <el-icon class="text-lg md:text-xl text-gray-400 hover:text-red-500"><Delete /></el-icon>
              </div>
            </div>
          </div>
          
          <div class="h-40 md:h-96 w-full flex items-center justify-center text-gray-300 font-bold text-xs md:text-sm">
            --- End of Track ---
          </div>
        </div>

        <!-- 移动端底部固定打点与播放控制栏 -->
        <div v-if="isMobile" class="shrink-0 bg-white border-t border-gray-200 flex flex-col shadow-[0_-4px_15px_rgba(0,0,0,0.05)] z-20 pb-safe">
          <!-- 上排：播放进度条 -->
          <div class="px-4 pt-2">
            <el-slider v-model="currentTime" :max="duration" size="small" @change="seekAudio" :show-tooltip="false" class="mobile-slider" />
            <div class="flex justify-between text-[10px] text-gray-400 mt-0.5 font-mono">
              <span>{{ formatTime(currentTime) }}</span>
              <span>{{ formatTime(duration) }}</span>
            </div>
          </div>
          <!-- 下排：控制与打点按钮 -->
          <div class="flex items-center px-4 pb-3 pt-2 gap-2 sm:gap-3">
            <button 
              @click="togglePlay" 
              class="w-12 h-12 shrink-0 bg-gray-100 text-blue-600 rounded-full flex items-center justify-center active:scale-95 transition-transform"
            >
              <el-icon size="24"><component :is="isPlaying ? VideoPause : VideoPlay" /></el-icon>
            </button>
            <button 
              @click="seekRelative(-5)" 
              class="w-12 h-12 shrink-0 bg-gray-100 text-gray-700 rounded-full flex items-center justify-center active:scale-95 transition-transform font-bold text-sm"
            >
              -5s
            </button>
            <button 
              @click="seekRelative(5)" 
              class="w-12 h-12 shrink-0 bg-gray-100 text-gray-700 rounded-full flex items-center justify-center active:scale-95 transition-transform font-bold text-sm"
            >
              +5s
            </button>
            <button 
              @click.stop="stampTime"
              class="flex-1 h-12 bg-blue-600 text-white rounded-xl flex items-center justify-center shadow-md active:scale-95 transition-transform font-bold text-[15px]"
            >
              <el-icon class="mr-1 text-lg"><Location /></el-icon>
              打点 (跳至下行)
            </button>
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

    <AppleToast v-model="toastVisible" :message="toastMessage" :type="toastType" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppleToast from '../components/AppleToast.vue'
import { Check, VideoPlay, VideoPause, RefreshLeft, Document, Plus, Minus, Delete, Operation, Close, Location, QuestionFilled } from '@element-plus/icons-vue'
import request, { STREAM_BASE_URL } from '../api'
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

const isMobile = ref(window.innerWidth < 768)
const sidebarDrawer = ref(false)

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    sidebarDrawer.value = false 
  }
}

const editIndex = ref(-1)    
const playingIndex = ref(-1) 
const playbackRate = ref(1.0) 
const deletedLines = ref([]) 
const timeOffsetMs = ref(251) 
const autoScroll = ref(false) 
const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastVisible.value = false
  toastMessage.value = message
  toastType.value = type
  setTimeout(() => { toastVisible.value = true }, 50)
}

const handlePaste = (e) => {
  const pastedText = e.clipboardData?.getData('text') || ''
  const lines = pastedText.split('\n').filter(line => line.trim() !== '')
  const filteredText = lines.join('\n')
  rawText.value = rawText.value + filteredText
  e.preventDefault()
}

const lrcListRef = ref(null)
const lineRefs = ref([])

const audioStreamUrl = computed(() => {
  return track.value ? `${STREAM_BASE_URL}/stream/${track.value.id}/` : ''
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

const parseRawText = () => {
  if (!rawText.value.trim()) return
  const lines = rawText.value.split('\n')
  lyrics.value = lines.map(line => {
    const match = line.match(/^\[(\d{2}:\d{2}(?::\d{2}(?:\.\d{2,3})?|\.\d{2,3}))\](.*)/)
    if (match) {
      return { time: strToSeconds(match[1]), timeStr: match[1], text: match[2].trim(), deleted: false }
    }
    return { time: 0, timeStr: '00:00.00', text: line.trim(), deleted: false }
  })
  
  editIndex.value = 0
  showToast('解析完成，请开始播放并打点！', 'success')
}

const handleParse = () => {
  parseRawText()
  if (isMobile.value) {
    sidebarDrawer.value = false
  }
}

const formatTime = (seconds) => {
  if (isNaN(seconds)) return '00:00.00'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0')
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0')
  const ms = Math.floor((seconds % 1) * 100).toString().padStart(2, '0')
  return hours > 0 ? `${hours}:${mins}:${secs}.${ms}` : `${mins}:${secs}.${ms}`
}

const strToSeconds = (str) => {
  const parts = str.split(':')
  if (parts.length === 3) {
    if (parts[2].includes('.')) {
      return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2])
    }
    return parseFloat(parts[0]) * 60 + parseFloat(parts[1]) + parseFloat(parts[2]) / 100
  }
  if (parts.length === 2) {
    return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
  }
  return 0
}

const syncTimeFromStr = (index) => {
  lyrics.value[index].time = strToSeconds(lyrics.value[index].timeStr)
  lyrics.value.sort((a, b) => a.time - b.time)
}

const togglePlay = () => {
  if (!audioRef.value) return
  isPlaying.value ? audioRef.value.pause() : audioRef.value.play()
  isPlaying.value = !isPlaying.value
  
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
  if (audioRef.value) audioRef.value.playbackRate = playbackRate.value
}

const setPlaybackRate = (rate) => {
  playbackRate.value = rate
  if (audioRef.value) audioRef.value.playbackRate = rate
}

const onMetadataLoaded = () => {
  duration.value = audioRef.value.duration
}

const setEditIndex = (index, blurInputs = true) => {
  if (blurInputs) {
    const active = document.activeElement
    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) active.blur()
  }
  editIndex.value = index
}

const onTimeUpdate = () => {
  if (!audioRef.value) return
  currentTime.value = audioRef.value.currentTime

  if (!autoScroll.value) return

  const index = lyrics.value.findIndex((l, i) => {
    const next = lyrics.value[i + 1]
    return currentTime.value >= l.time && (!next || currentTime.value < next.time)
  })

  if (index !== -1 && playingIndex.value !== index) {
    playingIndex.value = index
    scrollToLine(playingIndex.value)
  }
}

const scrollToLine = (index) => {
  nextTick(() => {
    const el = lineRefs.value[index]
    if (el && lrcListRef.value) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
}

const stampTime = () => {
  if (!audioRef.value || editIndex.value === -1 || editIndex.value >= lyrics.value.length) return

  const rawTime = audioRef.value.currentTime
  const offsetSeconds = timeOffsetMs.value / 1000
  const time = Math.max(0, rawTime - offsetSeconds)
  lyrics.value[editIndex.value].time = time
  lyrics.value[editIndex.value].timeStr = formatTime(time)

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
    showToast('已删除', 'success')
  }
}

const addLine = () => {
  const newLine = { time: 0, timeStr: '00:00.00', text: '', deleted: false }
  let insertIndex = editIndex.value >= 0 ? editIndex.value + 1 : lyrics.value.length
  if (insertIndex > lyrics.value.length) insertIndex = lyrics.value.length
  
  lyrics.value.splice(insertIndex, 0, newLine)
  editIndex.value = insertIndex
  scrollToLine(editIndex.value)
}

const resetTimes = () => {
  lyrics.value.forEach(l => {
    l.time = 0
    l.timeStr = '00:00.00'
  })
  editIndex.value = 0
  showToast('时间已归零', 'success')
}

const saveLyrics = async () => {
  if (!track.value) return
  const lrcContent = lyrics.value
    .filter(l => l.text && !l.deleted)
    .map(l => `[${l.timeStr}]${l.text}`)
    .join('\n')
  
  saving.value = true
  try {
    const formData = new FormData()
    formData.append('lyrics', lrcContent)

    await request.patch(`/tracks/${track.value.id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    showToast('歌词已同步至音频文件！', 'success')
    rawText.value = lrcContent
    deletedLines.value = []
  } catch (error) {
    showToast('保存失败，请检查网络', 'error')
  } finally {
    saving.value = false
  }
}

const handleKeyDown = (e) => {
  const activeTag = document.activeElement.tagName
  const isInput = activeTag === 'TEXTAREA' || activeTag === 'INPUT'

  if (e.code === 'Space') {
    if (!isInput) {
      e.preventDefault()
      e.stopImmediatePropagation()
      togglePlay()
    }
  }

  if (e.code === 'Enter' || e.code === 'NumpadEnter') {
    if (document.activeElement.type === 'textarea') return
    e.preventDefault()
    stampTime()
  }

  if (!isInput) {
    if (e.code === 'Digit1' || e.code === 'Numpad1') { e.preventDefault(); seekRelative(-5) }
    if (e.code === 'Digit2' || e.code === 'Numpad2') { e.preventDefault(); seekRelative(-1) }
    if (e.code === 'Digit3' || e.code === 'Numpad3') { e.preventDefault(); seekRelative(1) }
    if (e.code === 'Digit4' || e.code === 'Numpad4') { e.preventDefault(); seekRelative(5) }
    
    if (e.code === 'KeyQ') { e.preventDefault(); setPlaybackRate(0.5) }
    if (e.code === 'KeyW') { e.preventDefault(); setPlaybackRate(1.0) }
    if (e.code === 'KeyE') { e.preventDefault(); setPlaybackRate(1.5) }
    if (e.code === 'KeyR') { e.preventDefault(); setPlaybackRate(2.0) }
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  if (playerStore.audioElement) playerStore.audioElement.pause()
  playerStore.isPlaying = false
  loadTrackData()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeyDown)
  document.title = 'NasMusic'
})

watch(track, (newTrack) => {
  if (newTrack) {
    const artistName = (newTrack.all_artists || []).join('/') || newTrack.artist_name || '未知歌手'
    document.title = `编辑：${newTrack.title} - ${artistName}`
  }
})
</script>

<style scoped>
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

/* 滚动条美化 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 20px;
}

/* 移动端底部播放进度条修饰 */
.mobile-slider :deep(.el-slider__runway) {
  margin: 0;
}

/* iOS安全区适配 */
.pb-safe {
  padding-bottom: env(safe-area-inset-bottom);
}
</style>