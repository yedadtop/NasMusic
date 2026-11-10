package com.nasmusic.tv;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.MediaMetadata;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 播放器单例：持有 MediaPlayer + MediaSession（让遥控器媒体键、系统"正在播放"都能用）。
 * 界面只订阅 onPlayerChanged，进度由内部 500ms 心跳驱动。
 */
public final class PlayerManager {

    private static final String TAG = "NasMusic";
    private static PlayerManager instance;

    /** 顺序播放（列表循环）/ 随机 / 单曲循环 */
    public static final int MODE_SEQUENTIAL = 0;
    public static final int MODE_SHUFFLE = 1;
    public static final int MODE_SINGLE = 2;
    private static final String KEY_MODE = "play_mode";

    public interface Listener {
        void onPlayerChanged();
    }

    private final Context ctx;
    private final android.content.SharedPreferences prefs;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final List<Track> queue = new ArrayList<>();
    private final List<Listener> listeners = new CopyOnWriteArrayList<>();

    private MediaPlayer mp;
    private MediaSession session;
    private int index = -1;
    private boolean playing;
    private boolean preparing;
    /** MediaPlayer 已进入错误状态，下一次 toggle 需要重建播放器 */
    private boolean errored;
    private int mode = MODE_SEQUENTIAL;

    private final Runnable ticker = new Runnable() {
        @Override
        public void run() {
            notifyChanged();
            if (mp != null) {
                handler.postDelayed(this, 500);
            }
        }
    };

    private PlayerManager(Context context) {
        this.ctx = context.getApplicationContext();
        this.prefs = ctx.getSharedPreferences("nasmusic_tv", Context.MODE_PRIVATE);
        this.mode = prefs.getInt(KEY_MODE, MODE_SEQUENTIAL);
        setupSession();
    }

    public static synchronized PlayerManager get(Context context) {
        if (instance == null) {
            instance = new PlayerManager(context);
        }
        return instance;
    }

    /* ---------------- 对外 API ---------------- */

    public void addListener(Listener l) {
        if (l != null && !listeners.contains(l)) {
            listeners.add(l);
        }
    }

    public void removeListener(Listener l) {
        listeners.remove(l);
    }

    public Track current() {
        if (index < 0 || index >= queue.size()) {
            return null;
        }
        return queue.get(index);
    }

    public boolean isPlaying() {
        return playing;
    }

    public boolean isPreparing() {
        return preparing;
    }

    public int position() {
        if (mp == null || preparing) {
            return 0;
        }
        try {
            return mp.getCurrentPosition();
        } catch (Exception e) {
            return 0;
        }
    }

    public int duration() {
        if (mp == null || preparing) {
            return 0;
        }
        try {
            return mp.getDuration();
        } catch (Exception e) {
            return 0;
        }
    }

    public void play(List<Track> tracks, int start) {
        if (tracks == null || tracks.isEmpty()) {
            return;
        }
        queue.clear();
        queue.addAll(tracks);
        index = Math.max(0, Math.min(start, queue.size() - 1));
        openCurrent();
    }

    public void toggle() {
        // 准备阶段既不能 start 也不能 pause：硬调会把 MediaPlayer 打进错误状态，
        // 之后就再也播不出来。直接忽略，等 onPrepared 自动开始。
        if (preparing) {
            return;
        }
        // 播放器已经出错/被释放：按播放键＝重新准备当前这首
        if (mp == null || errored) {
            openCurrent();
            return;
        }
        try {
            if (playing) {
                mp.pause();
                playing = false;
            } else {
                mp.start();
                playing = true;
            }
        } catch (Exception e) {
            Log.w(TAG, "toggle failed: " + e);
            // 状态机异常时重建，保证下一次按键一定能恢复播放
            openCurrent();
            return;
        }
        updateSession();
        notifyChanged();
    }

    public void next(boolean auto) {
        if (queue.isEmpty()) {
            return;
        }
        // 单曲循环只在"自然播完"时重放，手动按下一首仍然换歌
        if (mode == MODE_SINGLE && auto) {
            replayCurrent();
            return;
        }
        if (mode == MODE_SHUFFLE) {
            index = randomIndex();
        } else {
            index = (index + 1) % queue.size();
        }
        openCurrent();
    }

    public void prev() {
        if (queue.isEmpty()) {
            return;
        }
        if (position() > 3000) {
            seekTo(0);
            return;
        }
        if (mode == MODE_SHUFFLE) {
            index = randomIndex();
        } else {
            index = index <= 0 ? queue.size() - 1 : index - 1;
        }
        openCurrent();
    }

    private void replayCurrent() {
        if (mp == null) {
            openCurrent();
            return;
        }
        try {
            mp.seekTo(0);
            mp.start();
            playing = true;
        } catch (Exception e) {
            openCurrent();
            return;
        }
        updateSession();
        notifyChanged();
    }

    private int randomIndex() {
        if (queue.size() <= 1) {
            return 0;
        }
        int n;
        do {
            n = (int) (Math.random() * queue.size());
        } while (n == index);
        return n;
    }

    public void cycleMode() {
        mode = (mode + 1) % 3;
        prefs.edit().putInt(KEY_MODE, mode).apply();
        notifyChanged();
    }

    public int mode() {
        return mode;
    }

    public String modeName() {
        switch (mode) {
            case MODE_SHUFFLE:
                return "随机播放";
            case MODE_SINGLE:
                return "单曲循环";
            default:
                return "顺序播放";
        }
    }

    public void seekTo(int ms) {
        if (mp == null || preparing) {
            return;
        }
        try {
            mp.seekTo(Math.max(0, ms));
        } catch (Exception e) {
            Log.w(TAG, "seek failed: " + e);
        }
        notifyChanged();
    }

    /* ---------------- 内部 ---------------- */

    private void pauseOnly() {
        if (mp != null) {
            try {
                mp.pause();
            } catch (Exception ignored) {
            }
            playing = false;
        }
        updateSession();
        notifyChanged();
    }

    private void openCurrent() {
        Track t = current();
        if (t == null) {
            return;
        }
        releasePlayer();
        preparing = true;
        playing = false;
        errored = false;
        mp = new MediaPlayer();
        mp.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build());
        mp.setOnPreparedListener(p -> {
            preparing = false;
            errored = false;
            try {
                p.start();
                playing = true;
            } catch (Exception e) {
                Log.w(TAG, "start failed: " + e);
            }
            updateSession();
            notifyChanged();
        });
        mp.setOnCompletionListener(p -> next(true));
        mp.setOnErrorListener((p, what, extra) -> {
            Log.w(TAG, "media error " + what + "/" + extra + " on track " + t.id
                    + " preparing=" + preparing + " playing=" + playing);
            // 先记住出错时的状态，再清标志
            boolean wasPlaying = playing;
            boolean wasPreparing = preparing;
            preparing = false;
            playing = false;
            errored = true;
            // 只有准备阶段的错误自动跳下一首（说明这首歌根本打不开）；
            // 播放过程中 toggle/seek 触发的错误就停住，别制造"点播放→跳歌"的错觉。
            if (wasPreparing && !wasPlaying) {
                handler.postDelayed(() -> next(true), 400);
            }
            return true;
        });
        try {
            mp.setDataSource(t.streamUrl());
            mp.prepareAsync();
        } catch (Exception e) {
            Log.w(TAG, "setDataSource failed: " + e);
            preparing = false;
            handler.postDelayed(() -> next(true), 400);
        }
        updateSession();
        notifyChanged();
        startTicker();
    }

    private void startTicker() {
        handler.removeCallbacks(ticker);
        handler.post(ticker);
    }

    private void releasePlayer() {
        if (mp != null) {
            try {
                mp.reset();
                mp.release();
            } catch (Exception ignored) {
            }
            mp = null;
        }
    }

    private void notifyChanged() {
        for (Listener l : listeners) {
            l.onPlayerChanged();
        }
    }

    private void setupSession() {
        try {
            session = new MediaSession(ctx, "NasMusic");
            session.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS
                    | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
            session.setCallback(new MediaSession.Callback() {
                @Override
                public void onPlay() {
                    if (!playing) {
                        toggle();
                    }
                }

                @Override
                public void onPause() {
                    if (playing) {
                        toggle();
                    }
                }

                @Override
                public void onStop() {
                    pauseOnly();
                }

                @Override
                public void onSkipToNext() {
                    next(false);
                }

                @Override
                public void onSkipToPrevious() {
                    prev();
                }

                @Override
                public void onSeekTo(long pos) {
                    seekTo((int) pos);
                }
            });
            session.setActive(true);
        } catch (Exception e) {
            Log.w(TAG, "media session unavailable: " + e);
        }
    }

    private void updateSession() {
        if (session == null) {
            return;
        }
        try {
            Track t = current();
            if (t != null) {
                MediaMetadata.Builder md = new MediaMetadata.Builder()
                        .putString(MediaMetadata.METADATA_KEY_TITLE, t.title)
                        .putString(MediaMetadata.METADATA_KEY_ARTIST, t.artistName)
                        .putString(MediaMetadata.METADATA_KEY_ALBUM, t.albumTitle)
                        .putLong(MediaMetadata.METADATA_KEY_DURATION,
                                duration() > 0 ? duration() : (long) (t.duration * 1000));
                session.setMetadata(md.build());
            }
            int state = playing ? PlaybackState.STATE_PLAYING
                    : (preparing ? PlaybackState.STATE_BUFFERING : PlaybackState.STATE_PAUSED);
            session.setPlaybackState(new PlaybackState.Builder()
                    .setActions(PlaybackState.ACTION_PLAY
                            | PlaybackState.ACTION_PAUSE
                            | PlaybackState.ACTION_PLAY_PAUSE
                            | PlaybackState.ACTION_SKIP_TO_NEXT
                            | PlaybackState.ACTION_SKIP_TO_PREVIOUS
                            | PlaybackState.ACTION_SEEK_TO)
                    .setState(state, position(), 1f)
                    .build());
        } catch (Exception ignored) {
        }
    }

    /** 队列快照，给界面显示"第几首/共几首"用。 */
    public List<Track> queueSnapshot() {
        return Collections.unmodifiableList(new ArrayList<>(queue));
    }

    public int index() {
        return index;
    }

    public int queueSize() {
        return queue.size();
    }
}
