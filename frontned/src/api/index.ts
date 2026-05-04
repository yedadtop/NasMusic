import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export const STREAM_BASE_URL = 'http://127.0.0.1:8000'

// 部署环境下的流媒体服务地址
// export const STREAM_BASE_URL = 'http://10.0.0.8'

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
