package com.nasmusic.tv;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;

/** 歌手 / 专辑详情：上方大封面 + 信息，下方曲目列表。 */
public class DetailActivity extends Activity implements PlayerManager.Listener {

    public static final String EXTRA_KIND = "kind";
    public static final String EXTRA_ID = "id";
    public static final String EXTRA_NAME = "name";

    private TrackAdapter adapter;
    private Collection current;
    private PlayerManager player;
    private RecyclerView list;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_detail);
        player = PlayerManager.get(this);

        int kind = getIntent().getIntExtra(EXTRA_KIND, Collection.ALBUM);
        int id = getIntent().getIntExtra(EXTRA_ID, 0);
        String name = getIntent().getStringExtra(EXTRA_NAME);

        TextView kindView = findViewById(R.id.kind);
        TextView nameView = findViewById(R.id.name);
        TextView metaView = findViewById(R.id.meta);
        ImageView cover = findViewById(R.id.cover);
        ImageView bg = findViewById(R.id.bg);
        View playAll = findViewById(R.id.play_all);
        ImageView playIcon = findViewById(R.id.play_all_icon);
        TextView playLabel = findViewById(R.id.play_all_label);
        list = findViewById(R.id.list);

        kindView.setText(kind == Collection.ARTIST ? "歌手" : "专辑");
        nameView.setText(name == null ? "" : name);
        metaView.setText("读取中…");

        adapter = new TrackAdapter((data, position) -> {
            player.play(new ArrayList<>(data), position);
            startActivity(new android.content.Intent(this, NowPlayingActivity.class));
        });
        list.setLayoutManager(new LinearLayoutManager(this));
        list.setAdapter(adapter);
        list.setItemAnimator(null);

        playAll.setOnClickListener(v -> {
            if (current != null && !current.tracks.isEmpty()) {
                player.play(new ArrayList<>(current.tracks), 0);
                startActivity(new android.content.Intent(this, NowPlayingActivity.class));
            }
        });
        // 聚焦时胶囊填白，图标和文字转黑（和顶栏 tab 同一套语言）
        playAll.setOnFocusChangeListener((v, has) -> {
            v.animate().scaleX(has ? 1.05f : 1f).scaleY(has ? 1.05f : 1f)
                    .setDuration(150).start();
            playIcon.setColorFilter(has ? 0xFF000000 : 0xFFFFFFFF);
            playLabel.setTextColor(has ? 0xFF000000 : 0xFFFFFFFF);
        });

        Api.Cb<Collection> cb = new Api.Cb<Collection>() {
            @Override
            public void onOk(Collection value) {
                current = value;
                metaView.setText(kind == Collection.ARTIST
                        ? value.trackCount + " 首歌曲"
                        : value.subtitle + " · " + value.trackCount + " 首");
                ImageLoader.load(cover, value.cover, 16);
                ImageLoader.loadBackground(bg, value.cover);
                adapter.submit(value.tracks);
                syncPlaying();
                list.postDelayed(() -> {
                    View child = list.getChildAt(0);
                    if (child != null) {
                        child.requestFocus();
                    } else {
                        playAll.requestFocus();
                    }
                }, 120);
            }

            @Override
            public void onErr(Exception e) {
                metaView.setText("读取失败 · 检查网络后重试");
            }
        };

        if (kind == Collection.ARTIST) {
            Api.artist(id, cb);
        } else {
            Api.album(id, cb);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        player.addListener(this);
        syncPlaying();
    }

    @Override
    protected void onPause() {
        super.onPause();
        player.removeListener(this);
    }

    @Override
    public void onPlayerChanged() {
        syncPlaying();
    }

    @Override
    public boolean dispatchKeyEvent(android.view.KeyEvent event) {
        if (KeyRouter.handle(this, event)) {
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    private void syncPlaying() {
        Track t = player.current();
        adapter.setPlayingId(t == null ? -1 : t.id);
    }
}
