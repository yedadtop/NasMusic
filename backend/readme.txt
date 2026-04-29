---

### 2. 更新后的项目记忆文件 (`readme.txt`)

```text
# 🎵 项目记忆文件：内网音乐服务端 (NasMusic)
**最后更新状态：后端核心接口完全成型，已支持单曲独立封面、内嵌歌词读写、以及原生多线程异步扫描。**

## 1. 项目核心定位
* **目标场景**：个人/家庭全内网环境部署，自建服务器。
* **核心原则**：极致精简，完全砍掉用户系统（无注册/登录/鉴权），专注纯粹的媒体流播放体验和元数据管理 [cite: 3]。
* **架构模式**：前后端完全分离 (SPA + RESTful API) [cite: 3]。

## 2. 技术栈字典
* **后端引擎**：Python 3 + Django 4.2+ [cite: 3]
* **接口规范**：Django REST Framework (DRF) [cite: 3]带全局分页与搜索。
* **前端计划**：Vue 3 + Pinia + Element Plus [cite: 3]
* **存储方案**：SQLite (当前开发阶段) -> MySQL (未来容器化阶段) [cite: 3]
* **核心依赖库**：
  * `mutagen`: 提取 MP3(ID3/USLT/APIC) / FLAC(Vorbis/Picture) 内置元数据、内嵌歌词与封面 [cite: 3]。
  * `Pillow`: 图像处理，将高清封面压缩为 300x300 缩略图以优化加载 [cite: 3]。
  * Python `threading`: 原生实现轻量级后台异步任务，零外部依赖。

## 3. 后端模块划分 (Django Apps)
* `library` **[已完成]**
  * **职责**：曲库数据中枢与 API 提供者 [cite: 3]。
  * **核心进化**：封面图片字段已从 `Album` 转移到 `Track`，实现**1首歌=1张图**的精细化单曲封面控制。引入 DRF Pagination 和 SearchFilter 解决海量数据加载问题。
  * **文件同步**：通过 Django Signals 实现数据库记录删除时，同步抹除物理音频与图片；通过重写 `perform_update` 使得修改数据库时同步使用 Mutagen 刷写硬盘 ID3/Vorbis 标签。
  
* `stream` **[已完成]**
  * **职责**：媒体流分发 [cite: 3]。
  * **特性**：手写 Python 生成器，完美处理 `HTTP 206 Partial Content` (Range 请求)，支持前端 HTML5 `<audio>` 标签无损、无卡顿拖拽进度条 [cite: 3, 4]。
  
* `scanner` **[已完成]**
  * **职责**：本地硬盘目录增量同步与后台调度。
  * **特性**：已实现轻量级异步化。借助 SQLite 建立 `ScanTask` 任务表，使用 `threading` 将长耗时全盘扫描推入后台守护线程，并为前端提供实时 `status` 轮询接口以渲染进度条。
  
* `scraper` **[待开发]**
  * **职责**：异步网络爬虫，抓取缺失的元数据或高清图片 [cite: 4]。

## 4. 全局配置备忘
* 媒体文件存放与路由：
  `MEDIA_URL = '/media/'`
  `MEDIA_ROOT = os.path.join(BASE_DIR, 'media')` [cite: 4]
* 管理面板优化：已将外键下拉框全部替换为 `autocomplete_fields` 异步搜索框，并支持了单曲图片的后台预览。
* 本地音乐测试目录：`C:\1D\Mass\my_music`

## 5. 待办事项 (Next Steps)
1. **[前端] 搭建 Vue 3 工程**：配置 Vite、Pinia 和 Element Plus [cite: 4]。
2. **[前端] API 联调与状态管理**：使用 axios 请求 `/api/tracks/`（带分页），展示带有 `track_cover` 的播放列表。
3. **[前端] 异步扫描交互**：调用 `/api/scanner/run/` 并编写 `setInterval` 轮询 `/api/scanner/status/`，实现极客风的实时扫描进度条。
4. **[前端] 播放器核心**：封装 `<audio>` 标签，绑定 `/stream/{id}/`，并调用详情接口懒加载内嵌歌词。