import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { addCollection } from '@iconify/vue'
import icons from './icons-subset'

import './style.css'
// Element Plus 按需引入（unplugin-vue-components）不会注入全局基座样式，
// 需手动补齐：base.css 提供 CSS 变量与重置，el-icon.css 提供 .el-icon 的
// 1em 相对尺寸与 inline-flex 垂直居中，缺失会导致 SVG 图标撑满父容器
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-icon.css'
import App from './App.vue'
import router from './router'

// 仅注册源码中实际用到的 MDI 图标子集（scripts/generate-icons.mjs 生成）
addCollection(icons)

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
