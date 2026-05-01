# NasMusic

基于 Django + Vue 的本地音乐库管理系统。

---

## 功能特性

- **音乐扫描入库**：自动扫描本地音乐文件夹，读取音频文件标签（ID3、Vorbis）并提取封面
- **多歌手支持**：一首歌曲支持多个艺人演唱（通过 ManyToMany 关系实现）
- **智能歌手拆分**：自动拆分多艺人标签，支持 `/`, `,`, `&`, `-`, `feat.`, `ft.`, `;`, `|`, `+`, `_` 以及中文分隔符（空格、顿号、间隔号）
- **分页与搜索**：支持歌曲、艺人、专辑的模糊搜索和分页浏览
- **音频流媒体**：支持 HTTP 206 Partial Content，完美支持 HTML5 audio 标签拖拽
- **标签同步**：修改歌曲信息后自动同步写入物理音频文件的 ID3/Vorbis 标签
- **歌词同步**：支持歌词写入 MP3（USLT）、FLAC、OGG、M4A 格式
- **自动清理**：删除歌曲时自动清理孤立的艺人和专辑记录
- **回收站功能**：删除的文件自动移入 `.trash` 目录，支持恢复和彻底删除
- **分片上传**：支持大文件分片上传，断点续传，适合内网传输大音频文件
- **系统配置**：提供 API 配置音乐库路径等系统参数

---

## 项目结构

```
NasMusic/
├── backend/
│   ├── NasMusic/         # Django 项目配置
│   ├── library/          # 核心音乐库管理
│   │   ├── models.py     # Track, Artist, Album 模型
│   │   ├── views.py      # REST API ViewSet
│   │   ├── serializers.py# DRF 序列化器
│   │   ├── admin.py      # Django 后台管理
│   │   └── utils.py      # 封面同步工具
│   ├── scanner/          # 音乐扫描入库
│   │   ├── views.py      # 扫描任务 API
│   │   ├── tasks.py      # 异步扫描任务
│   │   └── utils.py      # 音频标签解析
│   ├── stream/           # 音频流媒体服务
│   │   └── views.py      # 分段流媒体支持
│   ├── scraper/          # 音乐信息刮削器
│   └── frontend/         # Vue 前端项目
└── cleanup_db.py         # 数据库清理脚本（已废弃，由回收站功能替代）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. 创建超级用户

```bash
python manage.py createsuperuser
```

### 4. 启动服务

```bash
python manage.py runserver
```

### 5. 扫描音乐库

```bash
POST /api/scanner/run/
```

---

## API 接口

### 歌曲接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tracks/` | GET | 获取歌曲列表（支持分页、搜索） |
| `/api/tracks/{id}/` | GET | 获取歌曲详情（含歌词） |
| `/api/tracks/{id}/` | PUT/PATCH | 修改歌曲信息 |
| `/api/tracks/{id}/` | DELETE | 删除歌曲 |

### 艺人接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/artists/` | GET | 获取艺人列表 |
| `/api/artists/{id}/` | GET | 获取艺人详情（含歌曲列表） |

### 专辑接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/albums/` | GET | 获取专辑列表 |
| `/api/albums/{id}/` | GET | 获取专辑详情（含歌曲列表） |

### 扫描接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scanner/run/` | POST | 触发音乐扫描 |
| `/api/scanner/status/` | GET | 查询扫描进度 |

### 流媒体接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/stream/{track_id}/` | GET | 音频流播放（支持断点续传） |

### 分片上传接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload/init/` | POST | 初始化分片上传 |
| `/api/upload/upload_chunk/` | POST | 上传分片 |
| `/api/upload/complete/` | POST | 合并分片完成 |
| `/api/upload/cancel/` | DELETE | 取消上传 |
| `/api/upload/status/` | GET | 查询上传状态 |

### 回收站接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scanner/trash/` | GET | 获取回收站文件列表 |
| `/api/scanner/trash/restore/` | POST | 恢复文件（支持批量） |
| `/api/scanner/trash/empty/` | DELETE | 清空回收站（支持批量） |

### 系统配置接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scanner/config/` | GET | 获取所有配置 |
| `/api/scanner/config/` | PUT | 更新配置项 |

---

## 多歌手支持

### 数据模型

- `Track.artist`：主歌手（ForeignKey）
- `Track.artists`：所有歌手列表（ManyToMany）

### 歌手标签拆分规则

| 分隔符 | 示例 | 结果 |
|--------|------|------|
| `/` | `A/B` | `["A", "B"]` |
| `,` | `A, B` | `["A", "B"]` |
| `&` | `A & B` | `["A", "B"]` |
| `-` | `A - B` | `["A", "B"]` |
| `feat./ft.` | `A feat. B` | `["A", "B"]` |
| `;` `\|` `+` `_` | `A;B\|C+D_E` | `["A", "B", "C", "D", "E"]` |
| 中文分隔符 | `歌手1、歌手2・歌手3` | `["歌手1", "歌手2", "歌手3"]` |
| 混合分隔 | `A feat. B / C & D` | `["A", "B", "C", "D"]` |

> 代码会自动检测日文（平假名、片假名）和韩文，优先使用对应语言的分隔符规则。

### 更新歌曲信息

```json
PUT /api/tracks/{id}/
{
    "title": "新歌曲名",
    "artist_name": "主歌手",
    "album_title": "专辑名",
    "lyrics": "歌词内容"
}
```

> 注意：更新时系统会自动从 `artist_name` 中拆分为多个歌手，并绑定到歌曲的合作歌手列表。

---

## 回收站与数据清理

删除歌曲时，文件会自动移动到音乐库下的 `.trash` 文件夹，而不是直接删除。可以通过回收站接口恢复或彻底删除文件：

```bash
# 获取回收站文件列表
GET /api/scanner/trash/

# 恢复所有文件
POST /api/scanner/trash/restore/
{"restore_all": true}

# 清空回收站
DELETE /api/scanner/trash/empty/
{"delete_all": true}
```

> 注意：`cleanup_db.py` 脚本已废弃，由回收站功能替代。

---

## Nginx 部署配置

生产环境推荐使用 Nginx 作为反向代理，配合 Django 的 X-Accel-Redirect 实现高效音频流媒体服务。

```nginx
server {
    listen 80;
    server_name your_intranet_ip; # 替换为你的内网 IP 或域名，例如 192.168.1.100

    # 优化点 1：开启高效文件传输（流媒体必备）
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;

    # 优化点 2：设置足够大的 body 大小，防止分片上传大文件时被 Nginx 拦截报 413 错误
    client_max_body_size 50M;

    # =========================================
    # 核心区块 A：普通的 Django API 流量代理
    # =========================================
    location / {
        # 假设你的 Gunicorn 运行在本地 8000 端口
        proxy_pass http://127.0.0.1:8000;
        
        # 传递真实的客户端信息给 Django
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # =========================================
    # 核心区块 B：专门处理 X-Accel-Redirect 的流媒体通道
    # =========================================
    location /protected_music/ {
        # 【极其重要】internal 指令确保这个路由对外是封闭的！
        # 外部用户直接访问 `http://ip/protected_music/a.mp3`  会收到 404 错误。
        # 它只接受来自 Nginx 内部或后端 Django 返回的 X-Accel-Redirect 重定向。
        internal;

        # 【极其重要】alias 映射物理路径
        # 将前端请求的 /protected_music/... 映射到服务器真实的物理文件夹。
        # 注意：alias 后面的路径**必须**以斜杠 (/) 结尾！
        # 假设你的 SystemConfig 里配置的音乐库根目录是 /mnt/nas/music/
        alias /mnt/nas/music/;

        # 优化点 3：让 Nginx 自动处理断点续传（HTTP 206）和 MIME 类型
        # 强制 Nginx 根据文件后缀名（如 .mp3, .flac）自动推断 Content-Type
        default_type application/octet-stream;
    }

    # =========================================
    # 可选区块 C：处理普通的公开静态文件 (JS, CSS, 封面图等)
    # =========================================
    location /media/ {
        alias /path/to/your/django/media/; # 指向你的 Django media 目录
        expires 30d; # 封面图等缓存 30 天
    }

    location /static/ {
        alias /path/to/your/django/static/; # 指向你的 Django static 目录
        expires 30d;
    }
}
```

### 关键配置说明

| 配置项 | 说明 |
|--------|------|
| `internal` | 确保 `/protected_music/` 只接受内部重定向，外部直接访问返回 404 |
| `alias /mnt/nas/music/;` | 路径必须以 `/` 结尾，将 URL 路径映射到实际音乐库目录 |
| `sendfile on` | 开启高效文件传输，减少用户态/内核态切换 |
| `default_type application/octet-stream` | 让 Nginx 自动根据文件扩展名设置 Content-Type |

---

## 技术栈

- **后端**：Django 6 + Django REST Framework
- **数据库**：SQLite（默认）/ PostgreSQL
- **音频处理**：mutagen
- **图片处理**：Pillow
- **前端**：Vue 3

---

## 许可证

MIT License
