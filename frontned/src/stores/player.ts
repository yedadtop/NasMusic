import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import request from '../api'
import { getBiliImageUrl } from '../api'
import { saveSnapshot, loadSnapshot, clearSnapshot, type PlaybackSnapshot } from '../utils/playbackSnapshot'

const biliCoverCache = new Map<string, string>()

// 本地快照：变更类字段 800ms 去抖合并；进度单独 5s 节流
// （timeupdate 约 4Hz，每次都写 localStorage 会明显卡顿）
const PERSIST_DEBOUNCE = 800
const PERSIST_POSITION_INTERVAL = 5000

// ===== 随机播放：本地洗牌队列 =====
// 旧实现是每次切歌请求后端 /tracks/random/（全曲库 order_by('?')，只能排除最近 20 首，
// 第 21 首起会重复）。现在改为：进入随机模式时把当前播放列表洗成一个固定顺序，
// 之后按队列依次播，播完一轮重新洗牌，全程不发请求。

/** Fisher-Yates 洗牌（原地） */
function shuffleInPlace(arr: number[]): void {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    const tmp = arr[i]!
    arr[i] = arr[j]!
    arr[j] = tmp
  }
}

/**
 * 生成乱序播放顺序（存 playlist 索引，不复制曲目对象）。
 * 当前正在播的曲目放在队首，保证它播完后才进入乱序队列。
 */
function buildShuffleOrder(total: number, currentIndex: number): number[] {
  if (total <= 0) return []
  const rest: number[] = []
  for (let i = 0; i < total; i++) {
    if (i !== currentIndex) rest.push(i)
  }
  shuffleInPlace(rest)
  return (currentIndex >= 0 && currentIndex < total) ? [currentIndex, ...rest] : rest
}

// ===== 多设备同步回执（由 useSyncPlayback 注入，避免 store 反向依赖 composable）=====
// 本地播放操作发生时回调 composable，由其提交到后端广播给其他设备
export interface SyncAdapter {
  onLocalChange(kind: 'state' | 'transport'): void
}

let syncAdapter: SyncAdapter | null = null
// 远端状态应用期间的守卫：防止把收到的广播再回环提交
let applyingRemote = false

async function preloadBiliCover(coverUrl: string, bvid: string): Promise<string> {
  if (biliCoverCache.has(bvid)) {
    return biliCoverCache.get(bvid)!
  }
  try {
    const response = await fetch(coverUrl, { referrerPolicy: 'no-referrer' })
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    biliCoverCache.set(bvid, blobUrl)
    return blobUrl
  } catch (error) {
    console.error('预加载B站封面失败:', error)
    return coverUrl
  }
}

function clearBiliCoverCache() {
  for (const blobUrl of biliCoverCache.values()) {
    URL.revokeObjectURL(blobUrl)
  }
  biliCoverCache.clear()
}

export const usePlayerStore = defineStore('player', () => {
  const currentTrack = ref(null)
  const currentTrackDetail = ref<any | null>(null)
  const playlist = ref<any[]>([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)
  const audioElement = ref<HTMLAudioElement | null>(null)
  const playMode = ref('sequential')
  // 随机模式的播放顺序（存 playlist 索引）与当前队列位置
  const shuffleOrder = ref<number[]>([])
  const shufflePos = ref(0)
  const loadMoreCallback = ref<(() => Promise<void>) | null>(null)
  const isLoadingMore = ref(false)
  const refreshLibraryTrigger = ref(0)
  const coverStyleMode = ref(0)

  // 本地快照的定时器与上次写进度的时间戳
  let persistTimer: number | null = null
  let lastPositionPersistAt = 0
  // 音频恢复定位期间置 true：此时 <audio> 的 currentTime 还停在 0，
  // 直接采信会把快照里的进度写没（下次进页面又从 0 开始）
  const restoringPosition = ref(false)

  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  const hasPrev = computed(() => {
    if (playMode.value === 'shuffle') {
      // 队列里的上一位；队首时没有上一首（新一轮洗牌后从头开始）
      return shufflePos.value > 0
    }
    if (playMode.value === 'single') {
      return true
    }
    return currentIndex.value > 0
  })

  const hasNext = computed(() => {
    if (playMode.value === 'shuffle') {
      // 播完一轮会重新洗牌继续，只要列表非空就永远有下一首
      return playlist.value.length > 0
    }
    if (playMode.value === 'single') {
      return true
    }
    if (currentIndex.value < playlist.value.length - 1) {
      return true
    }
    return loadMoreCallback.value !== null && !isLoadingMore.value
  })

  function setLoadMoreCallback(callback: (() => Promise<void>) | null) {
    loadMoreCallback.value = callback
  }

  async function checkAndLoadMore() {
    if (loadMoreCallback.value && !isLoadingMore.value) {
      const remainingTracks = playlist.value.length - currentIndex.value - 1
      if (remainingTracks <= 10) {
        isLoadingMore.value = true
        try {
          await loadMoreCallback.value()
        } finally {
          isLoadingMore.value = false
        }
      }
    }
  }

  /** 随机模式：按当前播放列表重新洗一副牌，当前曲目排在队首 */
  function reshuffleFromCurrent() {
    shuffleOrder.value = buildShuffleOrder(playlist.value.length, currentIndex.value)
    shufflePos.value = 0
  }

  function clearShuffleQueue() {
    shuffleOrder.value = []
    shufflePos.value = 0
  }

  /**
   * 分页加载后把新增曲目洗进队列尾部（不打断当前这一轮）。
   * 只在队列恰好覆盖旧列表时追加，避免整体刷新/搜索导致索引错位。
   */
  function appendNewTracksToShuffleQueue(fromLength: number) {
    const total = playlist.value.length
    if (total <= fromLength) return
    const fresh: number[] = []
    for (let i = fromLength; i < total; i++) fresh.push(i)
    shuffleInPlace(fresh)
    shuffleOrder.value = [...shuffleOrder.value, ...fresh]
  }

  /** 随机模式预取：队列剩余不足 10 首时加载下一页，新曲目由 syncPlaylist 洗入队尾 */
  async function prefetchForShuffle() {
    const remaining = shuffleOrder.value.length - shufflePos.value - 1
    if (remaining > 10) return
    if (!loadMoreCallback.value || isLoadingMore.value) return
    isLoadingMore.value = true
    try {
      await loadMoreCallback.value()
    } finally {
      isLoadingMore.value = false
    }
  }

  function togglePlayMode() {
    if (playMode.value === 'sequential') {
      playMode.value = 'shuffle'
      reshuffleFromCurrent()
    } else if (playMode.value === 'shuffle') {
      playMode.value = 'single'
      clearShuffleQueue()
    } else {
      playMode.value = 'sequential'
      clearShuffleQueue()
    }
    notifySync('state')
  }

  function resetPlayer() {
    currentTrack.value = null
    currentTrackDetail.value = null
    playlist.value = []
    currentIndex.value = -1
    isPlaying.value = false
    currentTime.value = 0
    duration.value = 0
    playMode.value = 'sequential'
    clearShuffleQueue()
    loadMoreCallback.value = null
    isLoadingMore.value = false
    clearBiliCoverCache()
    // 主动清空播放器时同步清掉快照，否则下次进页面又把旧歌恢复回来
    if (persistTimer !== null) {
      window.clearTimeout(persistTimer)
      persistTimer = null
    }
    clearSnapshot()
  }

  function triggerLibraryRefresh() {
    refreshLibraryTrigger.value++
  }

  function toggleCoverStyle() {
    coverStyleMode.value = (coverStyleMode.value + 1) % 3
  }

  async function fetchTrackDetail(id: string | number) {
    try {
      const res = await request.get(`/tracks/${id}/`)
      currentTrackDetail.value = res.data
    } catch (error) {
      console.error('获取歌曲详情失败:', error)
    }
  }

  async function fetchBilibiliLyrics(title: string) {
    currentTrackDetail.value = null
    
    if (!title) {
      return
    }

    try {
      const res = await request.post('/scraper/lyrics/bilibili/', { title })
      if (res.data.success && res.data.lyrics) {
        currentTrackDetail.value = {
          id: `bilibili_${Date.now()}`,
          title: res.data.parsed_song_name || title,
          artist_name: res.data.parsed_artist_name || '',
          lyrics: res.data.lyrics,
          is_bilibili: true
        }
        console.log(`[播放器] B站歌曲歌词获取成功: ${res.data.parsed_song_name} - ${res.data.parsed_artist_name}`)
      } else {
        currentTrackDetail.value = {
          id: `bilibili_${Date.now()}`,
          title: title,
          artist_name: '',
          lyrics: '',
          is_bilibili: true
        }
        if (res.data.message && res.data.message !== '成功获取歌词') {
          console.log(`[播放器] B站歌曲歌词获取失败: ${res.data.message}`)
        }
      }
    } catch (error) {
      console.error('获取B站歌曲歌词失败:', error)
      currentTrackDetail.value = {
        id: `bilibili_${Date.now()}`,
        title: title,
        artist_name: '',
        lyrics: '',
        is_bilibili: true
      }
    }
  }

  function playTrack(track: any, index = -1, tracks: any[] = [], preservePlayingState = false) {
    if (tracks.length > 0) {
      playlist.value = tracks
      currentIndex.value = index
      // 播放列表整体替换：随机模式下重新洗牌，其他模式清空队列
      if (playMode.value === 'shuffle') reshuffleFromCurrent()
      else clearShuffleQueue()
    } else if (index >= 0) {
      currentIndex.value = index
      // 点列表里的某一首：随机模式下把队列位置同步过去，
      // 保证「上一首/下一首」沿用户选的这首继续走
      if (playMode.value === 'shuffle') {
        const pos = shuffleOrder.value.indexOf(index)
        if (pos >= 0) {
          shufflePos.value = pos
        } else {
          // 不在当前队列里（如刚分页加载的新歌）：以它为起点重洗
          reshuffleFromCurrent()
        }
      }
    }
    currentTrack.value = track
    if (track.is_bilibili && track.track_cover) {
      track._coverUrlSmall = getBiliImageUrl(track.track_cover, 'small')
      track._coverUrlLarge = getBiliImageUrl(track.track_cover, 'large')
      preloadBiliCover(track._coverUrlLarge, track.bvid)
    }
    if (!preservePlayingState) {
      isPlaying.value = true
    }
    currentTime.value = 0
    duration.value = track.duration || 0
    if (!track.is_bilibili) {
      fetchTrackDetail(track.id)
    } else {
      fetchBilibiliLyrics(track.title)
    }
    // nextTrack/prevTrack 的成功路径均以 playTrack 收尾，此处统一回执同步
    notifySync('state')
  }

  function syncPlaylist(tracks: any[]) {
    if (tracks.length === 0) return
    const prevLen = playlist.value.length
    playlist.value = tracks
    if (playMode.value !== 'shuffle') return
    if (tracks.length > prevLen && shuffleOrder.value.length === prevLen) {
      // 分页追加：新曲目洗进队尾，当前这一轮不受影响
      appendNewTracksToShuffleQueue(prevLen)
    } else if (tracks.length !== shuffleOrder.value.length) {
      // 列表被整体替换（刷新/搜索重置）：队列作废，以当前曲目重洗
      reshuffleFromCurrent()
    }
  }

  function prevTrack() {
    const wasPlaying = isPlaying.value
    if (playMode.value === 'shuffle') {
      // 随机模式：沿乱序队列回退一位
      if (shufflePos.value > 0) {
        shufflePos.value--
        const realIndex = shuffleOrder.value[shufflePos.value]
        const track = realIndex != null ? playlist.value[realIndex] : null
        if (track) {
          playTrack(track, realIndex, [], !wasPlaying)
          return true
        }
      }
      return false
    }
    if (currentIndex.value > 0) {
      currentIndex.value--
      const track = playlist.value[currentIndex.value]
      playTrack(track, -1, [], !wasPlaying)
      return true
    }
    return false
  }

  async function nextTrack() {
    const wasPlaying = isPlaying.value
    if (playMode.value === 'shuffle') {
      // 队列异常（快照丢失/索引错位）：以当前曲目重洗一副牌
      if (shuffleOrder.value.length === 0) reshuffleFromCurrent()
      // 队列快见底时先预取下一页，新曲目会自动洗入队尾
      await prefetchForShuffle()

      if (shufflePos.value + 1 < shuffleOrder.value.length) {
        shufflePos.value++
        const realIndex = shuffleOrder.value[shufflePos.value]
        const track = realIndex != null ? playlist.value[realIndex] : null
        if (track) {
          playTrack(track, realIndex, [], !wasPlaying)
          return true
        }
      }

      // 一轮播完：重新洗牌。新队列把「刚播完的这首」排在队首，跳过它从下一首开始
      if (playlist.value.length === 0) return false
      reshuffleFromCurrent()
      const startPos = shuffleOrder.value.length > 1 ? 1 : 0
      shufflePos.value = startPos
      const realIndex = shuffleOrder.value[startPos]
      const track = realIndex != null ? playlist.value[realIndex] : null
      if (!track) return false
      playTrack(track, realIndex, [], !wasPlaying)
      return true
    }
    if (playMode.value === 'single') {
      return true
    }
    if (currentIndex.value < playlist.value.length - 1) {
      currentIndex.value++
      const track = playlist.value[currentIndex.value]
      playTrack(track, -1, [], !wasPlaying)
      return true
    }
    if (loadMoreCallback.value && !isLoadingMore.value) {
      await checkAndLoadMore()
      if (currentIndex.value < playlist.value.length - 1) {
        currentIndex.value++
        const track = playlist.value[currentIndex.value]
        playTrack(track, -1, [], !wasPlaying)
        return true
      }
    }
    return false
  }

  function togglePlay() {
    isPlaying.value = !isPlaying.value
    notifySync('transport')
  }

  function stop() {
    isPlaying.value = false
    currentTime.value = 0
    if (audioElement.value) {
      audioElement.value.pause()
      audioElement.value.currentTime = 0
    }
    notifySync('transport')
  }

  // ===== 同步基础设施：由 useSyncPlayback 调用 =====

  function setSyncAdapter(adapter: SyncAdapter | null) {
    syncAdapter = adapter
  }

  function setApplyingRemote(v: boolean) {
    applyingRemote = v
  }

  function notifySync(kind: 'state' | 'transport') {
    if (!applyingRemote && syncAdapter) syncAdapter.onLocalChange(kind)
  }

  // 用户主动 seek（进度条/歌词点击）：写 audio + store 并回执同步
  function seek(time: number) {
    currentTime.value = time
    if (audioElement.value) {
      audioElement.value.currentTime = time
    }
    notifySync('transport')
  }

  function setCurrentTime(time: number) {
    currentTime.value = time
  }

  function setDuration(dur: number) {
    duration.value = dur
  }

  function setVolume(vol: number) {
    volume.value = vol
  }

  function setAudioElement(el: HTMLAudioElement) {
    audioElement.value = el
  }

  // ===== 本地快照：持久化与恢复 =====

  /** 真实进度：优先取 <audio>（store 的 currentTime 受 timeupdate 节流影响略滞后） */
  function livePosition(): number {
    // 恢复定位中 / src 尚未就绪时，<audio>.currentTime 恒为 0，不能采信
    if (restoringPosition.value) return currentTime.value
    const audio = audioElement.value
    if (audio && audio.src && audio.readyState > 0) {
      const t = audio.currentTime
      if (typeof t === 'number' && isFinite(t)) return t
    }
    return currentTime.value
  }

  function writeSnapshot() {
    if (!currentTrack.value) {
      clearSnapshot()
      return
    }
    saveSnapshot({
      track: currentTrack.value,
      playlist: playlist.value,
      currentIndex: currentIndex.value,
      playMode: playMode.value as any,
      shuffleOrder: shuffleOrder.value,
      shufflePos: shufflePos.value,
      currentTime: livePosition(),
      volume: volume.value,
      coverStyleMode: coverStyleMode.value,
      wasPlaying: isPlaying.value
    })
  }

  function schedulePersist() {
    if (persistTimer !== null) window.clearTimeout(persistTimer)
    persistTimer = window.setTimeout(() => {
      persistTimer = null
      lastPositionPersistAt = Date.now()
      writeSnapshot()
    }, PERSIST_DEBOUNCE)
  }

  /** 立即落盘：页面隐藏/卸载前调用，避免去抖窗口内丢掉最后的状态 */
  function persistNow() {
    if (persistTimer !== null) {
      window.clearTimeout(persistTimer)
      persistTimer = null
    }
    lastPositionPersistAt = Date.now()
    writeSnapshot()
  }

  /** 从本地快照恢复曲目/列表/模式/进度，返回快照供调用方决定是否提示续播 */
  function restoreFromSnapshot(): PlaybackSnapshot | null {
    const snap = loadSnapshot()
    if (!snap || !snap.track) return null

    currentTrack.value = snap.track
    playlist.value = snap.playlist
    currentIndex.value = snap.currentIndex
    playMode.value = snap.playMode
    shuffleOrder.value = snap.shuffleOrder
    shufflePos.value = snap.shufflePos
    volume.value = snap.volume
    coverStyleMode.value = snap.coverStyleMode
    currentTime.value = snap.currentTime
    duration.value = Number(snap.track.duration) || 0
    // 恢复后一律从暂停态开始：无用户手势的 play() 会被浏览器拦截
    isPlaying.value = false

    const track = snap.track
    if (track.is_bilibili) {
      if (track.track_cover) {
        track._coverUrlSmall = getBiliImageUrl(track.track_cover, 'small')
        track._coverUrlLarge = getBiliImageUrl(track.track_cover, 'large')
        preloadBiliCover(track._coverUrlLarge, track.bvid)
      }
      fetchBilibiliLyrics(track.title)
    } else if (track.id != null) {
      fetchTrackDetail(track.id)
    }
    return snap
  }

  /** 恢复定位期间屏蔽进度持久化与 timeupdate 覆盖（由 App.vue 在音频定位前后调用） */
  function setRestoringPosition(v: boolean) {
    restoringPosition.value = v
  }

  // 变更类字段变化即写快照（去抖合并，避免一次切歌触发多次写盘）
  // isPlaying 必须在内：暂停后 currentTime 不再变化，只能靠它触发落盘
  watch(
    [currentTrack, playlist, currentIndex, playMode, shuffleOrder, shufflePos, volume, coverStyleMode, isPlaying],
    () => { schedulePersist() }
  )
  // 进度按固定间隔写：timeupdate 约 4Hz，逐次写 localStorage 会卡顿
  watch(currentTime, () => {
    if (!currentTrack.value) return
    const now = Date.now()
    if (now - lastPositionPersistAt < PERSIST_POSITION_INTERVAL) return
    lastPositionPersistAt = now
    writeSnapshot()
  })

  return {
    currentTrack,
    currentTrackDetail,
    playlist,
    currentIndex,
    isPlaying,
    currentTime,
    duration,
    volume,
    audioElement,
    playMode,
    shuffleOrder,
    shufflePos,
    progress,
    hasPrev,
    hasNext,
    isLoadingMore,
    refreshLibraryTrigger,
    coverStyleMode,
    toggleCoverStyle,
    fetchTrackDetail,
    fetchBilibiliLyrics,
    playTrack,
    syncPlaylist,
    prevTrack,
    nextTrack,
    togglePlay,
    togglePlayMode,
    stop,
    seek,
    setSyncAdapter,
    setApplyingRemote,
    setCurrentTime,
    setDuration,
    setVolume,
    setAudioElement,
    setLoadMoreCallback,
    checkAndLoadMore,
    resetPlayer,
    restoreFromSnapshot,
    persistNow,
    restoringPosition,
    setRestoringPosition,
    triggerLibraryRefresh,
    preloadBiliCover,
    biliCoverCache
  }
})
