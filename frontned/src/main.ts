import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { addCollection } from '@iconify/vue'
import icons from '@iconify-json/mdi/icons.json'

import './style.css'
import App from './App.vue'
import router from './router'

addCollection(icons)

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
