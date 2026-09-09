// src/composables/useSyncPlayback.ts
// 多设备同步播放核心（SSE + REST，派对模式：所有设备同步出声，任意设备可控）：
// - 订阅后端 SSE 广播，把远端会话状态应用到本地 player store 与 <audio>
// - 本地操作经 player store 的 syncAdapter 回调提交到后端，广播给其他设备
// - 进度对齐：期望进度 = position + (服务器当前时间 - position_at)，
//   周期性漂移检查，偏差超过阈值才 seek，避免频繁打断播放
// - leader（最早上线的设备）负责切歌推进，掉线由服务器即时重选并广播 roster
import { ref } from 'vue'
import request from '../api'
import { usePlayerStore } from '../stores/player'
import { getStreamUrl, trackFingerprint } from '../utils/streamUrl'

const SYNC_ENABLED_KEY = 'nasmusic_sync_enabled'
const CLIENT_ID_KEY = 'nasmusic_sync_client_id'
// 进度偏差超过该值（秒）才 seek 纠正；更小的偏差人耳不可辨
const DRIFT_THRESHOLD = 0.4
// 传输事件携带的是权威进度，对齐容忍更小
const TRANSPORT_ALIGN_THRESHOLD = 0.15
// 漂移检查周期（毫秒）
const DRIFT_CHECK_INTERVAL = 5000

// ===== 模块级单例状态（多组件共享同一实例）=====
const enabled = ref(false)
const status = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
const online = ref(0)
const isLeader = ref(false)
// 浏览器自动播放策略拦截时置 true，等待用户点击"加入同步播放"（一次性手势）
const needJoin = ref(false)

let source: EventSource | null = null
let clientId = ''
let lastSeq = -1
// 时钟偏移（服务器时间 - 本地时间），最近 5 次事件的滑动平均
let clockOffset = 0
let offsetSamples: number[] = []
// 远端应用代数：异步加载流地址期间若又有新事件，则丢弃过期应用
let generation = 0
let driftTimer: number | null = null
// 最近一次已知传输态（漂移外推的基准）
let lastTransport: { isPlaying: boolean; position: number; positionAt: number; trackFp: string } | null = null

function serverNow(): number {
  return Date.now() / 1000 + clockOffset
}

/** 期望进度：播放中按服务器时间戳外推，暂停时为静态值 */
function expectedPosition(isPlaying: boolean, position: number, positionAt: number): number {
  if (!isPlaying) return position
  return position + Math.max(0, serverNow() - positionAt)
}

function getOrCreateClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY)
  if (!id) {
    id = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `c-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem(CLIENT_ID_KEY, id)
  }
  return id
}

function updateClock(serverTime: number) {
  offsetSamples.push(serverTime - Date.now() / 1000)
  if (offsetSamples.length > 5) offsetSamples.shift()
  clockOffset = offsetSamples.reduce((a, b) => a + b, 0) / offsetSamples.length
}

// ---------- 远端状态应用 ----------

async function applyRemoteState(envelope: any) {
  const player = usePlayerStore()
  if (!envelope.track) return // 空会话（服务器刚启动/无人播放）：保持本地不动
  const target = expectedPosition(envelope.is_playing, envelope.position, envelope.position_at)
  // 曲目一致（自己操作的回声 / 其他设备仅切了模式或重播同一首）：
  // 只对齐播放态与列表上下文，不重新加载音频，避免无谓的播放中断
  if (trackFingerprint(player.currentTrack) === trackFingerprint(envelope.track)) {
    player.setApplyingRemote(true)
    try {
      if (Array.isArray(envelope.playlist) && envelope.playlist.length > 0) {
        player.playlist = envelope.playlist
        player.currentIndex = envelope.index
      }
      player.playMode = envelope.play_mode
      player.shuffleHistory = envelope.shuffle_history || []
      player.isPlaying = envelope.is_playing
      player.currentTime = target
      const audio = player.audioElement
      if (audio) {
        if (Math.abs(audio.currentTime - target) > TRANSPORT_ALIGN_THRESHOLD) {
          audio.currentTime = target
        }
        if (envelope.is_playing) {
          audio.play().then(() => { needJoin.value = false }).catch(() => { needJoin.value = true })
        } else {
          audio.pause()
        }
      }
    } finally {
      player.setApplyingRemote(false)
    }
    return
  }
  // 曲目不同：完整加载远端曲目
  const gen = ++generation
  player.setApplyingRemote(true)
  try {
    // preservePlayingState=true：播放态由 envelope 决定而非本地
    player.playTrack(envelope.track, -1, [], true)
    if (Array.isArray(envelope.playlist) && envelope.playlist.length > 0) {
      player.playlist = envelope.playlist
      player.currentIndex = envelope.index
    }
    player.playMode = envelope.play_mode
    player.shuffleHistory = envelope.shuffle_history || []
    player.isPlaying = envelope.is_playing
    player.currentTime = target
    const audio = player.audioElement
    if (audio) {
      const url = await getStreamUrl(envelope.track)
      if (gen !== generation) return // 加载期间又有新事件到达，放弃过期应用
      audio.src = url
      if (target > 0.5) audio.currentTime = target
      if (envelope.is_playing) {
        try {
          await audio.play()
          needJoin.value = false
        } catch {
          needJoin.value = true // 自动播放被拦截，等待用户手势
        }
      } else {
        audio.pause()
      }
    }
  } catch (error) {
    console.error('[同步] 应用远端播放状态失败:', error)
  } finally {
    if (gen === generation) player.setApplyingRemote(false)
  }
}

function applyRemoteTransport(envelope: any) {
  const player = usePlayerStore()
  if (!player.currentTrack) return
  // 本地曲目与会话不一致（漏事件）：拉全量状态自愈
  if (envelope.track_fp && envelope.track_fp !== trackFingerprint(player.currentTrack)) {
    fetchAndApplyState()
    return
  }
  generation++ // 使在途的曲目加载应用作废
  player.setApplyingRemote(true)
  try {
    const target = expectedPosition(envelope.is_playing, envelope.position, envelope.position_at)
    player.isPlaying = envelope.is_playing
    player.currentTime = target
    const audio = player.audioElement
    if (audio) {
      if (Math.abs(audio.currentTime - target) > TRANSPORT_ALIGN_THRESHOLD) {
        audio.currentTime = target
      }
      if (envelope.is_playing) {
        audio.play().catch(() => { needJoin.value = true })
      } else {
        audio.pause()
      }
    }
  } finally {
    player.setApplyingRemote(false)
  }
}

async function fetchAndApplyState() {
  try {
    const res = await request.get('/playback/state/')
    applyRemoteState(res.data)
  } catch (error) {
    console.error('[同步] 拉取会话状态失败:', error)
  }
}

// ---------- 事件分发 ----------

function handleEvent(ev: MessageEvent) {
  let envelope: any
  try {
    envelope = JSON.parse(ev.data)
  } catch {
    return
  }
  if (typeof envelope.seq === 'number') {
    if (envelope.seq <= lastSeq) return // 丢弃过期/重复事件
    lastSeq = envelope.seq
  }
  if (typeof envelope.server_time === 'number') updateClock(envelope.server_time)
  if (typeof envelope.online === 'number') online.value = envelope.online
  if ('leader_id' in envelope) {
    const wasLeader = isLeader.value
    isLeader.value = envelope.leader_id === clientId
    if (isLeader.value && !wasLeader) onBecomeLeader()
  }
  if (typeof envelope.position_at === 'number' && envelope.kind !== 'roster') {
    lastTransport = {
      isPlaying: !!envelope.is_playing,
      position: envelope.position || 0,
      positionAt: envelope.position_at,
      trackFp: envelope.kind === 'transport'
        ? envelope.track_fp || ''
        : trackFingerprint(envelope.track),
    }
  }
  switch (envelope.kind) {
    case 'state':
      applyRemoteState(envelope)
      break
    case 'transport':
      applyRemoteTransport(envelope)
      break
    // roster：上面已更新 leader/online
  }
}

/** 兜底：前任 leader 在切歌瞬间掉线会导致全员停在曲目末尾；
 *  新 leader 发现自己本地已到末尾时主动推进下一首 */
function onBecomeLeader() {
  const player = usePlayerStore()
  if (player.isPlaying && player.duration && player.currentTime >= player.duration - 0.5) {
    player.nextTrack()
  }
}

// ---------- 漂移纠正 ----------

function startDriftTimer() {
  if (driftTimer !== null) return
  driftTimer = window.setInterval(() => {
    const player = usePlayerStore()
    const audio = player.audioElement
    if (!player.isPlaying || !player.currentTrack || needJoin.value) return
    // 仅当本地播放的曲目就是会话曲目时才做外推纠正
    if (!lastTransport || lastTransport.trackFp !== trackFingerprint(player.currentTrack)) return
    const target = expectedPosition(lastTransport.isPlaying, lastTransport.position, lastTransport.positionAt)
    if (!lastTransport.isPlaying) return
    if (audio && Math.abs(audio.currentTime - target) > DRIFT_THRESHOLD) {
      audio.currentTime = target
    }
  }, DRIFT_CHECK_INTERVAL)
}

function stopDriftTimer() {
  if (driftTimer !== null) {
    window.clearInterval(driftTimer)
    driftTimer = null
  }
}

// ---------- 连接管理 ----------

function connect() {
  if (source) return
  status.value = 'connecting'
  clientId = getOrCreateClientId()
  source = new EventSource(`/api/playback/stream/?client_id=${encodeURIComponent(clientId)}`)
  source.onopen = () => {
    status.value = 'connected'
    // 重连后 seq 可能因服务器重启而回退，重置以接受新会话的全量状态
    lastSeq = -1
    offsetSamples = []
  }
  source.onmessage = handleEvent
  source.onerror = () => {
    // EventSource 自动重连中；重连成功后会再次触发 onopen
    status.value = 'connecting'
  }
  startDriftTimer()
}

function disconnect() {
  if (source) {
    source.close()
    source = null
  }
  status.value = 'disconnected'
  online.value = 0
  isLeader.value = false
  needJoin.value = false
  lastTransport = null
  stopDriftTimer()
}

// ---------- 本地指令提交（player store 的 syncAdapter 回调） ----------

function collectAndSubmit(kind: 'state' | 'transport') {
  if (!enabled.value || !source) return
  const player = usePlayerStore()
  const audio = player.audioElement
  const payload: any = {
    kind,
    is_playing: player.isPlaying,
    // transport 取 audio 实时进度（store 的 currentTime 受 timeupdate 节流影响略滞后）
    position: kind === 'transport' && audio ? audio.currentTime : player.currentTime,
  }
  if (kind === 'state') {
    payload.track = player.currentTrack
    payload.playlist = player.playlist
    payload.index = player.currentIndex
    payload.play_mode = player.playMode
    payload.shuffle_history = player.shuffleHistory
  }
  // 失败静默（403 等异常由 axios 拦截器统一提示）
  request.post('/playback/command/', payload).catch(error => {
    console.error('[同步] 提交播放指令失败:', error)
  })
}

// ---------- 对外接口 ----------

async function setEnabled(v: boolean) {
  enabled.value = v
  localStorage.setItem(SYNC_ENABLED_KEY, v ? '1' : '0')
  if (v) {
    connect()
    // 远端为空且本地正在播放：把本地播放作为会话源提交（首个开启同步的设备）
    const player = usePlayerStore()
    if (player.currentTrack) {
      try {
        const res = await request.get('/playback/state/')
        if (!res.data.track) collectAndSubmit('state')
      } catch {
        // 拉取失败时留给后续事件自愈
      }
    }
  } else {
    disconnect()
  }
}

/** 自动播放被浏览器拦截后，用户点击"加入同步播放"的一次性手势 */
function joinPlayback() {
  const player = usePlayerStore()
  const audio = player.audioElement
  if (!audio) return
  audio.play().then(() => {
    needJoin.value = false
  }).catch(() => {})
}

// ===== 初始化（首次调用 useSyncPlayback 时执行一次）=====
let initialized = false

export function useSyncPlayback() {
  if (!initialized) {
    initialized = true
    enabled.value = localStorage.getItem(SYNC_ENABLED_KEY) === '1'
    usePlayerStore().setSyncAdapter({ onLocalChange: collectAndSubmit })
    if (enabled.value) connect()
  }
  return { enabled, status, online, isLeader, needJoin, setEnabled, joinPlayback, collectAndSubmit }
}
