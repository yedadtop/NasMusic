# NasMusic TV —— 安卓电视端原生应用

在电视上听 NAS 音乐的独立 App，**纯原生实现**，直连 NasMusic 后端 API。
不是网页套壳：网页版是给手机/桌面设计的，焦点、字号、交互方式在 10 英尺外都不成立。

- 包名：`com.nasmusic.tv`
- 后端：`http://10.0.0.8`（按 MENU 键可改）
- 产物：`app/build/outputs/apk/release/app-release.apk`（约 1.2MB）

## 功能

| 页面 | 内容 |
|---|---|
| 音乐库 | 全部歌曲，按添加时间倒序，确定键播放 |
| 歌手 | 圆形头像网格，进详情看该歌手全部歌曲 |
| 专辑 | 封面网格，进详情看整张专辑，可"播放全部" |
| 搜索 | 输入关键词走 `/api/tracks/?search=`，自动弹输入法 |
| 播放页 | 模糊封面背景 + 大封面 + 进度条 + 上一首/播放/下一首 + 播放模式切换 |
| 迷你条 | 底部常驻，显示当前歌曲和进度，确定键进播放页 |

播放模式三种：**顺序播放**（列表循环）、**随机播放**、**单曲循环**。
播放页最右侧的圆钮点一下切一种，选择存 `SharedPreferences`，重启后保留。

支持遥控器媒体键（播放/暂停、上一首、下一首）。两条路都走：
`MediaSession` 注册（系统媒体键、正在播放卡片），以及前台 Activity 的
`dispatchKeyEvent` 直接吃掉这几个键（见 `KeyRouter.java`）。
后者是必需的 —— 这台电视预装的 AirScreen 也注册了 MediaSession，会抢走媒体键。

## 代码结构

```
app/src/main/java/com/nasmusic/tv/
  Api.java              HTTP + JSON（只读接口，写操作仍在网页版做）
  Track.java            歌曲模型
  Collection.java       歌手/专辑共用模型
  ImageLoader.java      内存 LRU + 圆角/圆形裁剪 + 盒式模糊（不引 Glide）
  PlayerManager.java    MediaPlayer 单例 + MediaSession + 播放模式 + 500ms 进度心跳
  KeyRouter.java        遥控器媒体键路由（前台 Activity 优先消费）
  MainActivity.java     导航栏 + 列表/网格 + 迷你播放条 + 搜索
  DetailActivity.java   歌手/专辑详情
  NowPlayingActivity.java 全屏播放页
  TrackAdapter.java     歌曲行（整行可聚焦）
  CardAdapter.java      网格卡片
```

## 关键实现选择

**为什么原生重写。** 第一版是把 `frontned` 的构建产物塞进 WebView。三个死结：
电视的 WebView 是 Chrome 81（Android 9 老 ROM 无法升级），Vite 8 默认产物用了
`||=`（Chrome 85+）直接白屏、Tailwind 4 的 `@layer` 整块被丢弃；
网页的布局按手机设计，1080p 电视上字小、要用方向键模拟鼠标；
打包进去的前端是静态的，NAS 上的网页更新了 App 不跟着变。

**为什么不用 RecyclerView 以外的库。** 只依赖 `androidx.recyclerview`。
播放用 framework 的 `MediaPlayer` + `MediaSession`，图片加载、模糊、圆角全部自己写，
APK 1.2MB，冷启动快，Android 9 上没有依赖冲突风险。

**焦点即交互。** 每个列表行/卡片都是 `focusable`，靠 selector 表达焦点态
（`bg_row.xml` / `bg_card.xml` / `bg_rail_item.xml`），配合 130ms 缩放动画。
方向键跨区移动完全交给系统焦点查找，没有自己写空间导航。

**媒体键要前台自己吃。** 光注册 `MediaSession` 不够。这台电视预装的 AirScreen
（`io.github.jssun.airplay`）也注册了 MediaSession，会周期性弹广告页抢焦点，
媒体键有时候派不到我们这。所以 Main/Detail/NowPlaying 三个 Activity 都在
`dispatchKeyEvent` 里用 `KeyRouter` 先消费 `KEYCODE_MEDIA_*`，前台时一定生效。

**详情页背景别用固定高度的遮罩。** 背景图铺满（`match_parent`），上面盖一层
**同样铺满**的渐变 scrim（`bg_detail_scrim`：`#4D` → `#E6` → `#FF`，angle 270）。
如果遮罩只盖 340dp 高，底边会出现一条明显的亮度台阶。

## 构建

```bash
./build.sh          # 构建 + 安装到 10.0.0.229
./build.sh build    # 只构建
```

需要 JDK 17（`../.tools/jdk-17.0.20.1+1`）和 SDK platform 34。
`targetSdk` 故意留在 28（就是这台电视的版本），lint 的 `ExpiredTargetSdkVersion` 已关掉。

## 调试

```bash
# 日志
TV_HOST=10.0.0.229 tools/venv/Scripts/python.exe -I tools/tv.py "logcat -s NasMusic"
```

改后端地址：应用内按 **MENU** 键。
