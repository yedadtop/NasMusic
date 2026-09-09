// 响应式的「本机是否已保存访问令牌」状态
// 供需要写操作（POST/PUT/PATCH/DELETE，即需要令牌认证）的按钮控制显隐：
// 存在令牌显示按钮，不存在则隐藏
import { ref } from 'vue'
import { getToken } from '../api'

const hasToken = ref(!!getToken())

// 同一标签页内：Settings 页保存/清除令牌时（setToken）实时刷新
window.addEventListener('nasmusic:token-changed', () => {
  hasToken.value = !!getToken()
})

// 跨标签页：其他标签页修改 localStorage 时刷新
window.addEventListener('storage', (e) => {
  if (e.key === 'nasmusic_token') {
    hasToken.value = !!getToken()
  }
})

export function useTokenExists() {
  return hasToken
}
