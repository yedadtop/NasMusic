# NasMusic 前端项目

NasMusic 音乐库管理系统的前端，基于 Vue 3 + Vite 构建。

## 环境要求

- **Node.js**: 18.x 或更高版本
- **npm**: 9.x 或更高版本（推荐使用最新版本）

## 安装

### 1. 安装 Node.js

如果还没有安装 Node.js，请前往 [Node.js 官网](https://nodejs.org/) 下载并安装 LTS 版本。

### 2. 安装项目依赖

在 `frontned` 目录下执行：

```bash
npm install
```

## 开发

### 启动开发服务器

```bash
npm run dev
```

执行后，会在 `http://localhost:5173` 启动开发服务器，支持热模块替换（HMR），修改代码后会自动刷新页面。

### 配置后端 API 地址

开发环境下，前端默认访问 `http://localhost:8000` 的后端 API。如果后端运行在不同的地址，请修改 `frontned\src\api\index.ts` 文件：

```
export const STREAM_BASE_URL = 'http://127.0.0.1:8000'
```

## 构建生产版本

### 打包项目

```bash
npm run build
```

构建产物会输出到 `frontned/dist` 目录，可直接部署到 Nginx 或其他静态文件服务器。

### 构建前检查类型

```bash
npm run type-check
```

执行 TypeScript 类型检查，确保代码没有类型错误。



## 常用命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 构建生产版本 |
| `npm run type-check` | 运行 TypeScript 类型检查 |
| `npm run preview` | 本地预览生产构建产物 |

## 开发建议

### 使用 VS Code 开发

推荐使用 [VS Code](https://code.visualstudio.com/) 作为开发工具，并安装以下扩展：

- **Vue - Official** (Volar)：Vue 3 的官方扩展，提供更好的 TypeScript 支持和组件提示
- **ESLint**：代码规范检查
- **Prettier**：代码格式化

### 使用 Vue DevTools

安装 [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 浏览器扩展，可以在开发者工具中查看组件状态、Vuex/Pinia 数据流等信息，方便调试。

## 更多信息

- [Vue 3 官方文档](https://vuejs.org/)
- [Vite 官方文档](https://vitejs.dev/)
- [Vue Router 官方文档](https://router.vuejs.org/)
- [Pinia 官方文档](https://pinia.vuejs.org/)
