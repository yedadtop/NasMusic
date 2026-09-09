import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export const STREAM_BASE_URL = 'http://127.0.0.1:8000'

// 部署环境下的流媒体服务地址
// export const STREAM_BASE_URL = 'http://10.0.0.8'

// ===== 访问令牌（写操作鉴权）=====

// 允许调用方标记「令牌无效时不弹全局提示」（如设置页的令牌验证请求）
declare module 'axios' {
  export interface AxiosRequestConfig {
    skipTokenInvalidToast?: boolean
  }
}

const TOKEN_KEY = 'nasmusic_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
  // 通知已挂载的组件刷新按钮可见性（useTokenExists 监听此事件）
  window.dispatchEvent(new CustomEvent('nasmusic:token-changed'))
}

// 请求拦截器：自动附带令牌（调用方显式设置了 Authorization 时不覆盖）
request.interceptors.request.use(config => {
  const token = getToken()
  if (token && !config.headers?.get('Authorization')) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// 响应拦截器：令牌无效时全局提示
request.interceptors.response.use(
  response => response,
  error => {
    const status = error.response?.status
    if ((status === 401 || status === 403) && !error.config?.skipTokenInvalidToast) {
      window.dispatchEvent(new CustomEvent('nasmusic:token-invalid'))
    }
    return Promise.reject(error)
  }
)

export const BILI_IMAGE_SIZES = {
  small: '@240w_240h_1c.webp',
  large: '@400w_400h_1c.webp'
}

export function getBiliImageUrl(url: string, size: 'small' | 'large' = 'small'): string {
  if (!url || typeof url !== 'string') return ''
  if (!url.includes('hdslb.com')) return url
  const suffix = BILI_IMAGE_SIZES[size] || BILI_IMAGE_SIZES.small
  return url.includes('@') ? url.replace(/@.*\.webp$/, suffix) : `${url}${suffix}`
}

export default request
