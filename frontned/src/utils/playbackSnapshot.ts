// src/utils/playbackSnapshot.ts
// 播放状态的本地快照：刷新 / 关闭标签页后重新进入，恢复到上次的曲目、进度、
// 播放列表与播放模式。
//
// 设计约束：
// - 只做「序列化 + 存取」，节流与触发时机由 player store 控制
// - 曲目对象保留全部业务字段，但剔除歌词等大字段与 `_` 前缀的运行时派生字段，
//   否则几千首的播放列表会撞 localStorage 5MB 配额
// - 所有读写都 try/catch：配额溢出 / 数据损坏时静默降级，绝不打断播放
// - 带版本号：结构变更后丢弃旧快照，而不是让旧结构引发运行时崩溃

const SNAPSHOT_KEY = 'nasmusic_playback_snapshot'
// v2：随机播放改为「本地洗牌队列」（shuffleOrder/shufflePos），移除 shuffleHistory
const SNAPSHOT_VERSION = 2

// 播放列表上限。超出时保留当前曲目前后各一半，保证「上一首/下一首」仍然可用
const MAX_PLAYLIST = 2000

// 不参与持久化的字段：歌词可能上万字，其余是运行时派生/非 JSON 值
const SKIP_FIELDS = new Set(['lyrics', 'currentTrackDetail'])

export type PlayMode = 'sequential' | 'shuffle' | 'single'

export interface PlaybackSnapshot {
  version: number
  savedAt: number
  track: any | null
  playlist: any[]
  currentIndex: number
  playMode: PlayMode
  /** 随机模式的播放顺序（playlist 的索引序列），空数组表示尚未洗牌 */
  shuffleOrder: number[]
  /** 当前播到 shuffleOrder 的第几位 */
  shufflePos: number
  currentTime: number
  volume: number
  coverStyleMode: number
  /** 上次退出时是否处于播放中（仅用于提示，恢复后一律从暂停态开始） */
  wasPlaying: boolean
}

/** 曲目指纹：本地曲目用 id，B站曲目用 bvid（id 是临时拼接的，不可靠） */
export function trackKey(track: any): string {
  if (!track) return ''
  return track.is_bilibili ? `b${track.bvid}` : `t${track.id}`
}

/** 剔除大字段与运行时派生字段，保留可直接回填 store 的业务字段 */
function sanitizeTrack(track: any): any | null {
  if (!track || typeof track !== 'object') return null
  const out: Record<string, any> = {}
  for (const key of Object.keys(track)) {
    if (key.startsWith('_') || SKIP_FIELDS.has(key)) continue
    const value = track[key]
    if (value === undefined || typeof value === 'function') continue
    out[key] = value
  }
  return out
}

function sanitizeList(list: any[], limit: number): any[] {
  if (!Array.isArray(list)) return []
  const source = Number.isFinite(limit) ? list.slice(-limit) : list
  const out: any[] = []
  for (const item of source) {
    const t = sanitizeTrack(item)
    if (t) out.push(t)
  }
  return out
}

/**
 * 裁剪超长播放列表：以当前索引为中心保留一段窗口，并把索引换算到新数组内。
 * 截断后仍能顺序播放，只是列表两端会缺失（重新进入后本来也无法续接分页）。
 */
function trimPlaylist(playlist: any[], index: number): { playlist: any[]; index: number } {
  if (playlist.length <= MAX_PLAYLIST) return { playlist, index }
  const half = Math.floor(MAX_PLAYLIST / 2)
  const start = Math.max(0, Math.min(index - half, playlist.length - MAX_PLAYLIST))
  return {
    playlist: playlist.slice(start, start + MAX_PLAYLIST),
    index: index >= 0 ? index - start : -1
  }
}

function writeToStorage(snapshot: PlaybackSnapshot): void {
  try {
    localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(snapshot))
  } catch (error) {
    // 配额溢出（播放列表过大）或隐私模式下不可写：降级成只存当前曲目
    try {
      localStorage.setItem(SNAPSHOT_KEY, JSON.stringify({
        ...snapshot,
        playlist: [],
        currentIndex: -1,
        shuffleOrder: [],
        shufflePos: 0
      }))
    } catch {
      console.warn('[播放快照] 写入失败，已放弃持久化:', error)
    }
  }
}

export interface SnapshotInput {
  track: any | null
  playlist: any[]
  currentIndex: number
  playMode: PlayMode
  shuffleOrder: number[]
  shufflePos: number
  currentTime: number
  volume: number
  coverStyleMode: number
  wasPlaying: boolean
}

/** 过滤乱序队列：只保留合法的 playlist 索引，去重 */
function sanitizeIndexList(list: any[], length: number): number[] {
  if (!Array.isArray(list)) return []
  const seen = new Set<number>()
  const out: number[] = []
  for (const value of list) {
    if (!Number.isInteger(value) || value < 0 || value >= length || seen.has(value)) continue
    seen.add(value)
    out.push(value)
  }
  return out
}

/** 保存快照（调用方负责节流）。播放器为空时等同于清除。 */
export function saveSnapshot(input: SnapshotInput): void {
  const track = sanitizeTrack(input.track)
  if (!track) {
    clearSnapshot()
    return
  }
  const index = Number.isInteger(input.currentIndex) ? input.currentIndex : -1
  const playlist = sanitizeList(input.playlist, Infinity)
  const trimmed = trimPlaylist(playlist, index)
  // 列表被裁剪时索引整体偏移，乱序队列无法直接复用，丢弃后由 store 重建
  const trimmedByLength = trimmed.playlist.length !== playlist.length
  const shuffleOrder = trimmedByLength
    ? []
    : sanitizeIndexList(input.shuffleOrder, trimmed.playlist.length)
  const shufflePos = trimmedByLength
    ? 0
    : Math.min(Math.max(Number(input.shufflePos) || 0, 0), Math.max(0, shuffleOrder.length - 1))

  writeToStorage({
    version: SNAPSHOT_VERSION,
    savedAt: Date.now(),
    track,
    playlist: trimmed.playlist,
    currentIndex: trimmed.index,
    playMode: input.playMode,
    shuffleOrder,
    shufflePos,
    currentTime: Number.isFinite(input.currentTime) ? Math.max(0, input.currentTime) : 0,
    volume: Number.isFinite(input.volume) ? Math.min(1, Math.max(0, input.volume)) : 1,
    coverStyleMode: Number.isInteger(input.coverStyleMode) ? input.coverStyleMode : 0,
    wasPlaying: !!input.wasPlaying
  })
}

/** 读取快照。数据损坏、版本不符、结构非法时返回 null 并清掉脏数据 */
export function loadSnapshot(): PlaybackSnapshot | null {
  let raw: string | null = null
  try {
    raw = localStorage.getItem(SNAPSHOT_KEY)
  } catch {
    return null
  }
  if (!raw) return null

  let parsed: any
  try {
    parsed = JSON.parse(raw)
  } catch {
    clearSnapshot()
    return null
  }

  if (!parsed || parsed.version !== SNAPSHOT_VERSION || !parsed.track) {
    clearSnapshot()
    return null
  }

  const playlist = Array.isArray(parsed.playlist) ? parsed.playlist : []
  const index = Number.isInteger(parsed.currentIndex) ? parsed.currentIndex : -1
  // 索引越界时按曲目指纹重新定位，定位不到就退化成单曲（index = -1）
  let safeIndex = index
  if (safeIndex >= 0 && safeIndex < playlist.length) {
    if (trackKey(playlist[safeIndex]) !== trackKey(parsed.track)) {
      safeIndex = playlist.findIndex((t: any) => trackKey(t) === trackKey(parsed.track))
    }
  } else {
    safeIndex = playlist.findIndex((t: any) => trackKey(t) === trackKey(parsed.track))
  }

  const shuffleOrder = sanitizeIndexList(parsed.shuffleOrder, playlist.length)
  const shufflePos = Math.min(
    Math.max(Number(parsed.shufflePos) || 0, 0),
    Math.max(0, shuffleOrder.length - 1)
  )

  return {
    version: SNAPSHOT_VERSION,
    savedAt: Number(parsed.savedAt) || 0,
    track: parsed.track,
    playlist,
    currentIndex: safeIndex,
    playMode: (parsed.playMode === 'shuffle' || parsed.playMode === 'single')
      ? parsed.playMode
      : 'sequential',
    shuffleOrder,
    shufflePos,
    currentTime: Number.isFinite(parsed.currentTime) ? Math.max(0, parsed.currentTime) : 0,
    volume: Number.isFinite(parsed.volume) ? Math.min(1, Math.max(0, parsed.volume)) : 1,
    coverStyleMode: Number.isInteger(parsed.coverStyleMode) ? parsed.coverStyleMode : 0,
    wasPlaying: !!parsed.wasPlaying
  }
}

export function clearSnapshot(): void {
  try {
    localStorage.removeItem(SNAPSHOT_KEY)
  } catch {
    // 忽略：隐私模式下 removeItem 也可能抛错
  }
}
