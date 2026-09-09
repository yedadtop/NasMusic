import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { addCollection } from '@iconify/vue'
import icons from './icons-subset'

import './style.css'
import App from './App.vue'
import router from './router'

// 仅注册源码中实际用到的 MDI 图标子集（scripts/generate-icons.mjs 生成）
addCollection(icons)

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
