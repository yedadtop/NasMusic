import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Element Plus 按需导入：模板中直接写 <el-xxx>，编译时自动引入组件及其样式
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
      // 只处理 Vue 组件文件，避免干扰 Tailwind PostCSS 处理
      include: [/\.vue$/, /\.vue\?vue/],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    // 监听 0.0.0.0，允许局域网内其他设备通过本机 IP 访问开发服务器
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // 音频流直连后端（STREAM_BASE_URL 现为同源相对路径，开发环境经此代理转发）
      '/stream': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
