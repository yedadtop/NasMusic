<template>
  <Teleport to="body">
    <div class="edit-modal-overlay" v-if="dialogVisible" @click.self="handleClose">
      <div class="edit-modal-container">
        <div class="edit-modal-header">
          <button class="cancel-btn" @click="handleClose">取消</button>
          <h2 class="edit-modal-title">编辑歌曲信息</h2>
          <button class="save-btn" @click="handleSave" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>

        <div class="edit-modal-body">
          <div class="form-section">
            <div class="form-item">
              <label class="form-label">标题</label>
              <input 
                v-model="form.title" 
                class="form-input" 
                placeholder="歌曲标题"
              />
            </div>

            <div class="form-item">
              <label class="form-label">歌手</label>
              <input 
                v-model="form.artist_name" 
                class="form-input" 
                placeholder="歌手名称"
              />
            </div>

            <div class="form-item">
              <label class="form-label">专辑</label>
              <input 
                v-model="form.album_title" 
                class="form-input" 
                placeholder="专辑名称"
              />
            </div>
          </div>

          <div class="form-section">
            <div class="form-label-row">
              <label class="form-label">歌词</label>
              <button class="lrc-editor-btn" @click="goToLrcEditor">详细编辑</button>
            </div>
            <textarea
              v-model="form.lyrics"
              class="form-textarea"
              rows="6"
              placeholder="输入歌词（LRC格式）"
            />
          </div>

          <div class="form-section">
            <label class="form-label">封面</label>
            <div class="cover-section">
              <div class="cover-preview">
                <img v-if="coverPreview" :src="coverPreview" alt="封面" />
                <div v-else class="cover-placeholder">
                  <svg class="placeholder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                  </svg>
                </div>
              </div>
              <div class="cover-actions">
                <input 
                  type="file" 
                  ref="fileInput" 
                  accept="image/*" 
                  @change="handleCoverSelect" 
                  class="file-input"
                />
                <button class="change-cover-btn" @click="selectFile">更换封面</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <AppleToast 
      v-model="toastVisible"
      :message="toastMessage"
      :type="toastType"
    />
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePlayerStore } from '../stores/player'
import request from '../api'
import AppleToast from './AppleToast.vue'

const router = useRouter()

const props = defineProps({
  modelValue: Boolean,
  track: Object
})

const emit = defineEmits(['update:modelValue', 'success'])

const player = usePlayerStore()
const dialogVisible = ref(false)
const saving = ref(false)
const fileInput = ref(null)
const form = ref({
  title: '',
  artist_name: '',
  album_title: '',
  lyrics: ''
})
const coverFile = ref(null)
const coverPreview = ref('')

const toastVisible = ref(false)
const toastMessage = ref('')
const toastType = ref('success')

const showToast = (message, type = 'success') => {
  toastMessage.value = message
  toastType.value = type
  toastVisible.value = true
}

const goToLrcEditor = () => {
  if (props.track?.id) {
    window.open(`/lrc-editor?id=${props.track.id}`, '_blank')
  }
}

const scrapeCover = async (trackId) => {
  try {
    const res = await request.post(`/scraper/track/${trackId}/scrape/`)
    if (res.data.success && res.data.has_cover_after) {
      const trackRes = await request.get(`/tracks/${trackId}/`)
      if (trackRes.data.track_cover) {
        return trackRes.data.track_cover
      }
    }
  } catch (error) {
    console.error('自动爬取封面失败:', error)
  }
  return null
}

const scrapeLyrics = async (trackId) => {
  try {
    const res = await request.post(`/scraper/track/${trackId}/scrape_lyrics/`)
    if (res.data.success && res.data.has_lyrics_after) {
      if (res.data.lyrics_length > 0) {
        const trackRes = await request.get(`/tracks/${trackId}/`)
        if (trackRes.data.lyrics) {
          return { lyrics: trackRes.data.lyrics, source: res.data.source }
        }
      }
    } else if (!res.data.success && res.data.message) {
      return { error: res.data.message }
    }
  } catch (error) {
    console.error('自动爬取歌词失败:', error)
  }
  return null
}

watch(() => props.modelValue, async (val) => {
  dialogVisible.value = val
  if (val && props.track) {
    let trackCover = ''
    let trackLyrics = ''
    if (props.track.id === player.currentTrack?.id && player.currentTrackDetail) {
      form.value = {
        title: player.currentTrackDetail.title || props.track.title || '',
        artist_name: player.currentTrackDetail.artist_name || props.track.artist_name || '',
        album_title: player.currentTrackDetail.album_title || props.track.album_title || '',
        lyrics: player.currentTrackDetail.lyrics || ''
      }
      trackCover = player.currentTrackDetail.track_cover || props.track.track_cover || ''
      trackLyrics = player.currentTrackDetail.lyrics || ''
    } else {
      form.value = {
        title: props.track.title || '',
        artist_name: props.track.artist_name || '',
        album_title: props.track.album_title || '',
        lyrics: ''
      }
      trackCover = props.track.track_cover || ''
      trackLyrics = ''
      if (props.track.id) {
        try {
          const res = await request.get(`/tracks/${props.track.id}/`)
          if (res.data.lyrics) {
            trackLyrics = res.data.lyrics
            form.value.lyrics = res.data.lyrics
          }
          if (res.data.track_cover) {
            trackCover = res.data.track_cover
          }
        } catch (error) {
          console.error('获取歌曲详情失败:', error)
        }
      }
    }

    coverPreview.value = trackCover
    coverFile.value = null

    const scrapeResults = {
      coverSuccess: false,
      lyricsSuccess: false,
      coverScraped: false,
      lyricsScraped: false,
      lyricsSource: null
    }

    if (!trackCover && props.track.id) {
      scrapeResults.coverScraped = true
      const scrapedCover = await scrapeCover(props.track.id)
      if (scrapedCover) {
        coverPreview.value = scrapedCover
        scrapeResults.coverSuccess = true
        if (player.currentTrack && player.currentTrack.id === props.track.id) {
          player.currentTrack = { ...player.currentTrack, track_cover: scrapedCover }
        }
        const playlistIndex = player.playlist.findIndex(t => t.id === props.track.id)
        if (playlistIndex !== -1) {
          player.playlist[playlistIndex] = { ...player.playlist[playlistIndex], track_cover: scrapedCover }
        }
      } else {
        showToast('封面刮削失败', 'error')
      }
    }

    if (!trackLyrics && props.track.id) {
      scrapeResults.lyricsScraped = true
      const scrapeResult = await scrapeLyrics(props.track.id)
      if (scrapeResult?.error) {
        showToast(scrapeResult.error, 'error')
      } else if (scrapeResult) {
        form.value.lyrics = scrapeResult.lyrics
        scrapeResults.lyricsSuccess = true
        scrapeResults.lyricsSource = scrapeResult.source
        if (player.currentTrack && player.currentTrack.id === props.track.id) {
          player.currentTrack = { ...player.currentTrack, lyrics: scrapeResult.lyrics }
        }
      }
    }

    if (scrapeResults.coverScraped || scrapeResults.lyricsScraped) {
      await new Promise(resolve => setTimeout(resolve, 500))
      if (scrapeResults.coverSuccess && scrapeResults.lyricsSuccess) {
        if (scrapeResults.lyricsSource === 'local') {
          showToast('封面刮削成功，歌词已从本地文件恢复', 'success')
        } else {
          showToast('封面和歌词刮削成功', 'success')
        }
      } else if (scrapeResults.coverSuccess) {
        showToast('封面刮削成功', 'success')
      } else if (scrapeResults.lyricsSuccess) {
        if (scrapeResults.lyricsSource === 'local') {
          showToast('歌词已从本地文件恢复', 'success')
        } else {
          showToast('歌词刮削成功', 'success')
        }
      }
    }
  }
})

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

const selectFile = () => {
  fileInput.value?.click()
}

const handleCoverSelect = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    coverFile.value = file
    const localUrl = URL.createObjectURL(file)
    coverPreview.value = localUrl

    if (player.currentTrack && player.currentTrack.id === props.track.id) {
      player.currentTrack = { ...player.currentTrack, track_cover: localUrl }
    }
    const playlistIndex = player.playlist.findIndex(t => t.id === props.track.id)
    if (playlistIndex !== -1) {
      player.playlist[playlistIndex] = { ...player.playlist[playlistIndex], track_cover: localUrl }
    }
  }
}

const handleClose = () => {
  dialogVisible.value = false
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleSave = async () => {
  if (!props.track) return

  saving.value = true
  try {
    const formData = new FormData()
    formData.append('title', form.value.title)
    formData.append('artist_name', form.value.artist_name)
    formData.append('album_title', form.value.album_title)
    formData.append('lyrics', form.value.lyrics)

    if (coverFile.value) {
      formData.append('cover_upload', coverFile.value)
    }

    const res = await request.patch(`/tracks/${props.track.id}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    const updatedTrack = {
      ...props.track,
      title: form.value.title,
      artist_name: form.value.artist_name,
      album_title: form.value.album_title,
      lyrics: form.value.lyrics,
      track_cover: coverPreview.value || props.track.track_cover
    }
    emit('success', updatedTrack)
    handleClose()
  } catch (error) {
    console.error('保存失败:', error)
    showToast('保存失败，请重试', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.edit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.edit-modal-container {
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(40px);
  border-radius: 16px;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(0, 0, 0, 0.1);
  width: 90%;
  max-width: 520px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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

.edit-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 0.5px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.95));
}

.cancel-btn {
  font-size: 15px;
  font-weight: 400;
  color: #007AFF;
  background: none;
  border: none;
  padding: 6px 0;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.cancel-btn:hover {
  opacity: 0.6;
}

.edit-modal-title {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.3px;
  margin: 0;
}

.save-btn {
  font-size: 15px;
  font-weight: 600;
  color: #007AFF;
  background: none;
  border: none;
  padding: 6px 0;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.6;
}

.save-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.edit-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scrollbar-width: thin;
  scrollbar-color: #d1d1d6 #f5f5f7;
}

.edit-modal-body::-webkit-scrollbar {
  width: 6px;
}

.edit-modal-body::-webkit-scrollbar-track {
  background: #f5f5f7;
  border-radius: 3px;
}

.edit-modal-body::-webkit-scrollbar-thumb {
  background-color: #d1d1d6;
  border-radius: 3px;
  border: 2px solid #f5f5f7;
}

.edit-modal-body::-webkit-scrollbar-thumb:hover {
  background-color: #98989d;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.form-label-row .form-label {
  margin-bottom: 0;
}

.lrc-editor-btn {
  font-size: 13px;
  font-weight: 500;
  color: #007AFF;
  background: rgba(0, 122, 255, 0.1);
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.lrc-editor-btn:hover {
  background: rgba(0, 122, 255, 0.2);
}

.form-item {
  margin-bottom: 16px;
}

.form-item:last-child {
  margin-bottom: 0;
}

.form-input {
  width: 100%;
  height: 44px;
  padding: 0 16px;
  font-size: 17px;
  color: #1d1d1f;
  background-color: #f5f5f7;
  border: 0.5px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  outline: none;
  transition: all 0.2s ease;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
}

.form-input::placeholder {
  color: #86868b;
}

.form-input:focus {
  background-color: #ffffff;
  border-color: #007AFF;
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
}

.form-textarea {
  width: 100%;
  padding: 12px 16px;
  font-size: 15px;
  color: #1d1d1f;
  background-color: #f5f5f7;
  border: 0.5px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  outline: none;
  resize: vertical;
  min-height: 120px;
  transition: all 0.2s ease;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
  line-height: 1.5;
}

.form-textarea::placeholder {
  color: #86868b;
}

.form-textarea:focus {
  background-color: #ffffff;
  border-color: #007AFF;
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
}

.form-textarea {
  scrollbar-width: thin;
  scrollbar-color: #d1d1d6 #f5f5f7;
}

.form-textarea::-webkit-scrollbar {
  width: 6px;
}

.form-textarea::-webkit-scrollbar-track {
  background: #f5f5f7;
  border-radius: 3px;
}

.form-textarea::-webkit-scrollbar-thumb {
  background-color: #d1d1d6;
  border-radius: 3px;
  border: 2px solid #f5f5f7;
}

.form-textarea::-webkit-scrollbar-thumb:hover {
  background-color: #98989d;
}

.cover-section {
  display: flex;
  gap: 20px;
  align-items: center;
}

.cover-preview {
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #f5f5f7;
  border: 0.5px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d1d1d6;
}

.placeholder-icon {
  width: 40px;
  height: 40px;
}

.cover-actions {
  flex: 1;
}

.file-input {
  display: none;
}

.change-cover-btn {
  padding: 10px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #ffffff;
  background: linear-gradient(180deg, #007AFF 0%, #0066CC 100%);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 122, 255, 0.3);
}

.change-cover-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
}

.change-cover-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 122, 255, 0.2);
}

@media (max-width: 480px) {
  .edit-modal-container {
    width: 95%;
    border-radius: 12px;
  }

  .edit-modal-header {
    padding: 14px 16px;
  }

  .edit-modal-body {
    padding: 16px;
  }

  .cover-section {
    flex-direction: column;
    align-items: flex-start;
  }

  .cover-preview {
    width: 80px;
    height: 80px;
  }
}
</style>
