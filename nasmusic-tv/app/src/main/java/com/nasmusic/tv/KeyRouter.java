package com.nasmusic.tv;

import android.app.Activity;
import android.view.KeyEvent;

/**
 * 遥控器媒体键路由。
 *
 * <p>MediaSession 已经注册了，但 Android 9 上系统派发媒体键时可能被别的
 * 注册了 MediaSession 的应用（比如预装的 AirScreen）抢走，导致按播放/暂停
 * 没反应甚至把当前应用顶到后台。所以前台 Activity 自己先吃掉这些键，
 * 保证遥控器在应用内一定有效。</p>
 */
final class KeyRouter {

    private KeyRouter() {
    }

    static boolean handle(Activity activity, KeyEvent event) {
        if (event.getAction() != KeyEvent.ACTION_DOWN) {
            return false;
        }
        PlayerManager player = PlayerManager.get(activity);
        switch (event.getKeyCode()) {
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
            case KeyEvent.KEYCODE_HEADSETHOOK:
                player.toggle();
                return true;
            case KeyEvent.KEYCODE_MEDIA_PLAY:
                if (!player.isPlaying()) {
                    player.toggle();
                }
                return true;
            case KeyEvent.KEYCODE_MEDIA_PAUSE:
            case KeyEvent.KEYCODE_MEDIA_STOP:
                if (player.isPlaying()) {
                    player.toggle();
                }
                return true;
            case KeyEvent.KEYCODE_MEDIA_NEXT:
                player.next(false);
                return true;
            case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                player.prev();
                return true;
            default:
                return false;
        }
    }
}
