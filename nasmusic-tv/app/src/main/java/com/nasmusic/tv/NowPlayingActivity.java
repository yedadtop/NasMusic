package com.nasmusic.tv;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.SeekBar;
import android.widget.TextView;

/**
 * 全屏播放页：复刻 NasMusic Vue 前端 PlayerDetail.vue 的布局。
 * 左半歌词（左对齐、垂直 mask 渐隐），右半封面+信息+进度+按钮垂直堆叠居中。
 */
public class NowPlayingActivity extends Activity implements PlayerManager.Listener {

    private ImageView bg;
    private ImageView cover;
    private TextView title;
    private TextView artist;
    private TextView timeNow;
    private TextView timeTotal;
    private SeekBar seek;
    private ImageButton play;
    private ImageButton prev;
    private ImageButton next;
    private ImageButton modeButton;
    private LyricsView lyrics;

    private PlayerManager player;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastUserSeek;
    private int lastTrackId = -1;
    private int lyricsTrackId = -1;
    /** 连续按键拖动时只记录目标，停手后再真正 seek，避免打断缓冲 */
    private int pendingSeek = -1;
    private boolean seekWasPlaying;

    private final Runnable applySeek = () -> {
        int ms = pendingSeek;
        pendingSeek = -1;
        if (ms < 0) {
            return;
        }
        player.seekTo(ms);
        if (seekWasPlaying && !player.isPlaying()) {
            player.toggle();
        }
    };

    /**
     * 歌词单独跑 120ms 心跳：PlayerManager 的 500ms 通知太粗，
     * 行切换会被量化成半秒一跳，看着发顿。这里只动歌词视图，代价可以忽略。
     */
    private final Runnable lyricTick = new Runnable() {
        @Override
        public void run() {
            if (player.current() != null) {
                lyrics.setPosition(player.position());
                handler.postDelayed(this, 120);
            }
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_now_playing);
        player = PlayerManager.get(this);

        bg = findViewById(R.id.bg);
        cover = findViewById(R.id.cover);
        title = findViewById(R.id.title);
        artist = findViewById(R.id.artist);
        timeNow = findViewById(R.id.time_now);
        timeTotal = findViewById(R.id.time_total);
        seek = findViewById(R.id.seek);
        play = findViewById(R.id.btn_play);
        prev = findViewById(R.id.btn_prev);
        next = findViewById(R.id.btn_next);
        modeButton = findViewById(R.id.btn_mode);
        lyrics = findViewById(R.id.lyrics);

        // 点击事件：全部直接调用 PlayerManager，不会串到 next
        play.setOnClickListener(v -> player.toggle());
        prev.setOnClickListener(v -> player.prev());
        next.setOnClickListener(v -> player.next(false));
        modeButton.setOnClickListener(v -> player.cycleMode());

        // 四颗按钮完全同构：默认半透明深底 + 白图标，只有拿到焦点才变纯白底 + 黑图标
        setupControl(prev);
        setupControl(play);
        setupControl(next);
        setupControl(modeButton);

        // 进度条：2% 一档微调，拖动防抖
        seek.setKeyProgressIncrement(20);
        seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar sb, int progress, boolean fromUser) {
                if (fromUser) {
                    lastUserSeek = System.currentTimeMillis();
                    int dur = player.duration();
                    if (dur > 0) {
                        seekWasPlaying = player.isPlaying();
                        pendingSeek = (int) (progress * (long) dur / 1000);
                        handler.removeCallbacks(applySeek);
                        handler.postDelayed(applySeek, 300);
                    }
                }
            }

            @Override public void onStartTrackingTouch(SeekBar sb) {}
            @Override public void onStopTrackingTouch(SeekBar sb) {}
        });
    }

    /** 控制按钮统一外观：未聚焦白图标 + 半透明底，聚焦填白、图标转黑 */
    private void setupControl(ImageButton b) {
        b.setColorFilter(b.isFocused() ? Color.BLACK : Color.WHITE);
        b.setOnFocusChangeListener((v, has) -> {
            v.animate().scaleX(has ? 1.08f : 1f).scaleY(has ? 1.08f : 1f)
                    .setDuration(140).start();
            ((ImageButton) v).setColorFilter(has ? Color.BLACK : Color.WHITE);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        player.addListener(this);
        lyricsTrackId = -1;
        render(true);
        // 保证 play 按钮最终拿到焦点：handler.post 等所有 UI 更新完成后再抢
        handler.post(play::requestFocus);
        handler.removeCallbacks(lyricTick);
        handler.post(lyricTick);
    }

    @Override
    protected void onPause() {
        super.onPause();
        handler.removeCallbacks(lyricTick);
        if (pendingSeek >= 0) {
            handler.removeCallbacks(applySeek);
            applySeek.run();
        }
        player.removeListener(this);
    }

    @Override
    public void onPlayerChanged() {
        render(false);
    }

    @Override
    public boolean dispatchKeyEvent(android.view.KeyEvent event) {
        if (KeyRouter.handle(this, event)) {
            return true;
        }
        // SeekBar 天生把 UP 当成"增加进度"：这里先接管方向键做纯焦点切换。
        // OK 键不再全局拦截：交给当前聚焦的按钮自己去 click，
        // 否则 ACTION_DOWN 一次 + ACTION_UP 的 click 一次会把 toggle 执行两遍。
        if (event.getAction() == android.view.KeyEvent.ACTION_DOWN) {
            View focused = getCurrentFocus();
            int key = event.getKeyCode();

            // 控制按钮 → seek（按 UP）
            if (key == android.view.KeyEvent.KEYCODE_DPAD_UP && isControlButton(focused)) {
                seek.requestFocus();
                return true;
            }
            // 进度条顶部：不再交给 SeekBar 改进度
            if (key == android.view.KeyEvent.KEYCODE_DPAD_UP && focused == seek) {
                return true;
            }
            // seek → 控制按钮（按 DOWN），优先回 play（用户最常点）
            if (key == android.view.KeyEvent.KEYCODE_DPAD_DOWN && focused == seek) {
                play.requestFocus();
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private boolean isControlButton(View v) {
        if (v == null) {
            return false;
        }
        return v == play || v == prev || v == next || v == modeButton;
    }

    private void render(boolean force) {
        Track t = player.current();
        if (t == null) {
            handler.postDelayed(this::finish, 300);
            return;
        }
        if (force || t.id != lastTrackId) {
            lastTrackId = t.id;
            title.setText(t.title);
            artist.setText(t.artistName.isEmpty() ? "未知歌手" : t.artistName);
            ImageLoader.load(cover, t.cover, 14);
            ImageLoader.loadBackground(bg, t.cover);
            loadLyrics(t);
        }

        // 换图标后必须重刷颜色，否则会被 ImageResource 重置成资源自带的白
        play.setImageResource(player.isPlaying() ? R.drawable.ic_pause : R.drawable.ic_play);
        play.setColorFilter(play.isFocused() ? Color.BLACK : Color.WHITE);

        int dur = player.duration();
        int pos = player.position();
        int total = dur > 0 ? dur : (int) (t.duration * 1000);
        timeTotal.setText(fmt(total));
        // 网络流起播要缓冲几秒，这段时间明确提示，避免看起来像"按了没反应"
        timeNow.setText(player.isPreparing() ? "缓冲" : fmt(pos));

        // 用户刚用方向键拖过进度条时别抢回来
        if (System.currentTimeMillis() - lastUserSeek > 1200) {
            seek.setProgress(dur > 0 ? (int) (pos * 1000L / dur) : 0);
        }

        int mode = player.mode();
        modeButton.setImageResource(mode == PlayerManager.MODE_SHUFFLE ? R.drawable.ic_shuffle
                : mode == PlayerManager.MODE_SINGLE ? R.drawable.ic_repeat_one
                : R.drawable.ic_repeat);
        modeButton.setColorFilter(modeButton.isFocused() ? Color.BLACK : Color.WHITE);

        lyrics.setPosition(pos);
    }

    /** 歌词只在切歌时拉一次，之后缓存在 Track 实例上 */
    private void loadLyrics(Track t) {
        if (lyricsTrackId == t.id) {
            return;
        }
        lyricsTrackId = t.id;
        if (t.lyrics != null && !t.lyrics.isEmpty()) {
            lyrics.setLyrics(t.lyrics);
            return;
        }
        lyrics.setLoading();
        Api.track(t.id, new Api.Cb<Track>() {
            @Override
            public void onOk(Track value) {
                if (lyricsTrackId != t.id) {
                    return;
                }
                if (value != null && value.lyrics != null) {
                    t.lyrics = value.lyrics;
                }
                lyrics.setLyrics(t.lyrics);
            }

            @Override
            public void onErr(Exception e) {
                if (lyricsTrackId == t.id) {
                    lyrics.setLyrics(null);
                }
            }
        });
    }

    private String fmt(int ms) {
        int total = Math.max(0, ms) / 1000;
        return total / 60 + ":" + String.format("%02d", total % 60);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        }
    }
}
