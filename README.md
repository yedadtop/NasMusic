# NasMusic

基于 Django + Vue 的本地音乐库管理系统。

---

## 功能特性

- **音乐扫描入库**：自动扫描本地音乐文件夹，读取音频文件标签（ID3、Vorbis）并提取封面
- **多歌手支持**：一首歌曲支持多个艺人演唱（通过 ManyToMany 关系实现）
- **智能歌手拆分**：自动拆分多艺人标签，支持 `/`, `,`, `&`, `-`, `feat.`, `ft.` 以及中文空格分隔
- **分页与搜索**：支持歌曲、艺人、专辑的模糊搜索和分页浏览
- **音频流媒体**：支持 HTTP 206 Partial Content，完美支持 HTML5 audio 标签拖拽
- **标签同步**：修改歌曲信息后自动同步写入物理音频文件的 ID3/Vorbis 标签
- **自动清理**：删除歌曲时自动清理孤立的艺人和专辑记录

---

## 项目结构

```
NasMusic/
├── library/           # 核心音乐库管理
│   ├── models.py      # Track, Artist, Album 模型
│   ├── views.py       # REST API ViewSet
│   ├── serializers.py # DRF 序列化器
│   ├── admin.py       # Django 后台管理
│   └── utils.py       # 封面同步工具
├── scanner/           # 音乐扫描入库
│   ├── views.py       # 扫描任务 API
│   ├── tasks.py       # 异步扫描任务
│   └── utils.py       # 音频标签解析
├── stream/            # 音频流媒体服务
│   └── views.py       # 分段流媒体支持
├── frontend/          # Vue 前端项目
└── cleanup_db.py      # 数据库清理脚本
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
| 中文空格 | `歌手1 歌手2` | `["歌手1", "歌手2"]` |

### 更新多歌手

```json
PUT /api/tracks/{id}/
{
    "artist_name": "主歌手",
    "all_artists_names": ["主歌手", "合作歌手1", "合作歌手2"]
}
```

---

## 数据库清理

当删除歌曲后，孤立的艺人和专辑会自动清理。如需手动清理：

```bash
python cleanup_db.py
```

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
