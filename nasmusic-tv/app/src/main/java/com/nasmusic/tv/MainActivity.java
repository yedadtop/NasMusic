package com.nasmusic.tv;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewParent;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity implements PlayerManager.Listener {

    private static final int SEC_LIBRARY = 0;
    private static final int SEC_ARTISTS = 1;
    private static final int SEC_ALBUMS = 2;
    private static final int SEC_SEARCH = 3;

    private static final String PREFS = "nasmusic_tv";
    private static final String KEY_BASE = "server_base";

    private RecyclerView list;
    private RecyclerView grid;
    private EditText searchInput;
    private TextView title;
    private TextView subtitle;
    private LinearLayout stateBox;
    private TextView stateText;
    private TextView stateHint;

    private View mini;
    private View miniInfo;
    private ImageView miniCover;
    private TextView miniTitle;
    private TextView miniArtist;
    private ImageButton miniPlay;
    private ImageButton miniNext;
    private ProgressBar miniProgress;

    private final LinearLayout[] navItems = new LinearLayout[4];
    private final ImageView[] navIcons = new ImageView[4];

    /** 设置按钮独立于分区数组：它不切换内容区，只开设置页 */
    private LinearLayout navSettings;
    private ImageView navSettingsIcon;

    private TrackAdapter trackAdapter;
    private CardAdapter cardAdapter;
    private PlayerManager player;

    private int section = SEC_LIBRARY;
    private final List<Track> libraryTracks = new ArrayList<>();
    private final List<Collection> artists = new ArrayList<>();
    private final List<Collection> albums = new ArrayList<>();

    private final Handler handler = new Handler(Looper.getMainLooper());
    private Runnable searchTask;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setContentView(R.layout.activity_main);

        SharedPreferences sp = getSharedPreferences(PREFS, MODE_PRIVATE);
        Api.setBase(sp.getString(KEY_BASE, "http://10.0.0.8"));
        // 手机扫码设置页：进桌面就起来，电视端地址随时可改，不依赖菜单键
        SettingsServer.start(this);
        player = PlayerManager.get(this);

        bind();
        setupLists();
        setupNav();
        setupMini();

        selectSection(SEC_LIBRARY, true);
    }

    /* ---------------- 初始化 ---------------- */

    private void bind() {
        list = findViewById(R.id.list);
        grid = findViewById(R.id.grid);
        searchInput = findViewById(R.id.search_input);
        title = findViewById(R.id.title);
        subtitle = findViewById(R.id.subtitle);
        stateBox = findViewById(R.id.state_box);
        stateText = findViewById(R.id.state_text);
        stateHint = findViewById(R.id.state_hint);

        mini = findViewById(R.id.mini);
        miniCover = findViewById(R.id.mini_cover);
        miniTitle = findViewById(R.id.mini_title);
        miniArtist = findViewById(R.id.mini_artist);
        miniPlay = findViewById(R.id.mini_play);
        miniNext = findViewById(R.id.mini_next);
        miniProgress = findViewById(R.id.mini_progress);

        navItems[0] = findViewById(R.id.nav_library);
        navItems[1] = findViewById(R.id.nav_artists);
        navItems[2] = findViewById(R.id.nav_albums);
        navItems[3] = findViewById(R.id.nav_search);
        navIcons[0] = findViewById(R.id.nav_library_icon);
        navIcons[1] = findViewById(R.id.nav_artists_icon);
        navIcons[2] = findViewById(R.id.nav_albums_icon);
        navIcons[3] = findViewById(R.id.nav_search_icon);

        navSettings = findViewById(R.id.nav_settings);
        navSettingsIcon = findViewById(R.id.nav_settings_icon);
    }

    private void setupLists() {
        trackAdapter = new TrackAdapter((data, position) -> {
            player.play(new ArrayList<>(data), position);
            openNowPlaying();
        });
        list.setLayoutManager(new LinearLayoutManager(this));
        list.setAdapter(trackAdapter);
        list.setItemAnimator(null);

        cardAdapter = new CardAdapter(140, item -> {
            Intent i = new Intent(this, DetailActivity.class);
            i.putExtra(DetailActivity.EXTRA_KIND, item.type);
            i.putExtra(DetailActivity.EXTRA_ID, item.id);
            i.putExtra(DetailActivity.EXTRA_NAME, item.name);
            startActivity(i);
        });
        grid.setAdapter(cardAdapter);
        grid.setItemAnimator(null);
    }

    private void setupNav() {
        navItems[0].setOnClickListener(v -> selectSection(SEC_LIBRARY, true));
        navItems[1].setOnClickListener(v -> selectSection(SEC_ARTISTS, true));
        navItems[2].setOnClickListener(v -> selectSection(SEC_ALBUMS, true));
        navItems[3].setOnClickListener(v -> selectSection(SEC_SEARCH, true));
        for (int i = 0; i < navItems.length; i++) {
            final int idx = i;
            navItems[i].setOnFocusChangeListener((v, has) -> {
                v.animate().scaleX(has ? 1.04f : 1f).scaleY(has ? 1.04f : 1f)
                        .setDuration(120).start();
                applyNavColors(idx);
            });
        }

        // 设置：不切分区，直接开设置页（二维码 + 手机设置地址）
        navSettings.setOnClickListener(v ->
                startActivity(new Intent(this, SettingsActivity.class)));
        navSettings.setOnFocusChangeListener((v, has) -> {
            v.animate().scaleX(has ? 1.04f : 1f).scaleY(has ? 1.04f : 1f)
                    .setDuration(120).start();
            applySettingsColors(has);
        });
        // 遥控器左右直接在「搜索」「设置」之间走，别让系统焦点搜索跳到别处
        navItems[3].setNextFocusRightId(R.id.nav_settings);
        navSettings.setNextFocusLeftId(R.id.nav_search);
    }

    private void applySettingsColors(boolean focused) {
        int color = focused ? 0xFF000000 : 0xFFA1A1A6;
        ((TextView) navSettings.getChildAt(1)).setTextColor(color);
        navSettingsIcon.setColorFilter(color);
    }

    private void setupMini() {
        miniInfo = findViewById(R.id.mini_info);
        miniInfo.setOnClickListener(v -> openNowPlaying());
        miniInfo.setOnFocusChangeListener((v, has) -> {
            v.animate().scaleX(has ? 1.012f : 1f).scaleY(has ? 1.012f : 1f)
                    .setDuration(140).start();
            miniTitle.setTextColor(has ? 0xFF000000 : 0xFFFFFFFF);
            miniArtist.setTextColor(has ? 0xFF6E6E73 : 0xFFA1A1A6);
        });
        miniPlay.setOnClickListener(v -> player.toggle());
        miniPlay.setOnFocusChangeListener((v, has) -> v.animate()
                .scaleX(has ? 1.1f : 1f).scaleY(has ? 1.1f : 1f)
                .setDuration(140).start());
        miniNext.setOnClickListener(v -> player.next(false));
        miniNext.setOnFocusChangeListener((v, has) -> {
            v.animate().scaleX(has ? 1.1f : 1f).scaleY(has ? 1.1f : 1f)
                    .setDuration(140).start();
            ((ImageButton) v).setColorFilter(has ? 0xFF000000 : 0xFFFFFFFF);
        });
        miniTitle.setSelected(true);
    }

    private void openNowPlaying() {
        if (player.current() == null) {
            return;
        }
        startActivity(new Intent(this, NowPlayingActivity.class));
    }

    /* ---------------- 分区切换 ---------------- */

    private void selectSection(int s, boolean moveFocus) {
        section = s;
        for (int i = 0; i < navItems.length; i++) {
            navItems[i].setSelected(i == s);
            applyNavColors(i);
        }

        searchInput.setVisibility(s == SEC_SEARCH ? View.VISIBLE : View.GONE);
        list.setVisibility(s == SEC_SEARCH || s == SEC_LIBRARY ? View.VISIBLE : View.GONE);
        grid.setVisibility(s == SEC_ARTISTS || s == SEC_ALBUMS ? View.VISIBLE : View.GONE);

        switch (s) {
            case SEC_LIBRARY:
                title.setText("音乐库");
                if (libraryTracks.isEmpty()) {
                    loadLibrary();
                } else {
                    subtitle.setText(libraryTracks.size() + " 首歌曲 · 按确定键播放");
                    if (moveFocus) {
                        focusList();
                    }
                }
                break;
            case SEC_ARTISTS:
                title.setText("歌手");
                grid.setLayoutManager(new GridLayoutManager(this, 5));
                grid.setAdapter(cardAdapter);
                if (artists.isEmpty()) {
                    loadArtists();
                } else {
                    subtitle.setText(artists.size() + " 位歌手");
                    cardAdapter.submit(artists);
                    if (moveFocus) {
                        focusGrid();
                    }
                }
                break;
            case SEC_ALBUMS:
                title.setText("专辑");
                grid.setLayoutManager(new GridLayoutManager(this, 4));
                grid.setAdapter(cardAdapter);
                if (albums.isEmpty()) {
                    loadAlbums();
                } else {
                    subtitle.setText(albums.size() + " 张专辑");
                    cardAdapter.submit(albums);
                    if (moveFocus) {
                        focusGrid();
                    }
                }
                break;
            case SEC_SEARCH:
                title.setText("搜索");
                subtitle.setText("输入歌名、歌手或专辑名");
                list.scrollToPosition(0);
                if (moveFocus) {
                    searchInput.requestFocus();
                    searchInput.postDelayed(() -> {
                        InputMethodManager imm =
                                (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            imm.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT);
                        }
                    }, 200);
                }
                break;
            default:
                break;
        }
    }

    private void applyNavColors(int index) {
        boolean active = navItems[index].isSelected();
        boolean focused = navItems[index].isFocused();
        TextView label = (TextView) navItems[index].getChildAt(1);
        if (focused) {
            // 聚焦：整颗胶囊变白，图标和文字都转黑
            label.setTextColor(0xFF000000);
            navIcons[index].setColorFilter(0xFF000000);
        } else if (active) {
            label.setTextColor(0xFFFFFFFF);
            navIcons[index].setColorFilter(0xFFFFFFFF);
        } else {
            label.setTextColor(0xFFA1A1A6);
            navIcons[index].setColorFilter(0xFFA1A1A6);
        }
    }

    /* ---------------- 数据 ---------------- */

    private void loadLibrary() {
        showState("正在读取音乐库…", null);
        Api.tracks(null, new Api.Cb<List<Track>>() {
            @Override
            public void onOk(List<Track> value) {
                libraryTracks.clear();
                libraryTracks.addAll(value);
                trackAdapter.submit(libraryTracks);
                syncPlaying();
                hideState();
                subtitle.setText(libraryTracks.size() + " 首歌曲 · 按确定键播放");
                focusList();
            }

            @Override
            public void onErr(Exception e) {
                showState("连不上 NasMusic", "地址 " + Api.base() + " · 点顶部「设置」扫码改地址");
            }
        });
    }

    private void loadArtists() {
        showState("正在读取歌手…", null);
        Api.artists(new Api.Cb<List<Collection>>() {
            @Override
            public void onOk(List<Collection> value) {
                artists.clear();
                artists.addAll(value);
                hideState();
                if (section == SEC_ARTISTS) {
                    cardAdapter.submit(artists);
                    subtitle.setText(artists.size() + " 位歌手");
                    focusGrid();
                }
            }

            @Override
            public void onErr(Exception e) {
                showState("连不上 NasMusic", "地址 " + Api.base());
            }
        });
    }

    private void loadAlbums() {
        showState("正在读取专辑…", null);
        Api.albums(new Api.Cb<List<Collection>>() {
            @Override
            public void onOk(List<Collection> value) {
                albums.clear();
                albums.addAll(value);
                hideState();
                if (section == SEC_ALBUMS) {
                    cardAdapter.submit(albums);
                    subtitle.setText(albums.size() + " 张专辑");
                    focusGrid();
                }
            }

            @Override
            public void onErr(Exception e) {
                showState("连不上 NasMusic", "地址 " + Api.base());
            }
        });
    }

    private void doSearch(String keyword) {
        Api.tracks(keyword, new Api.Cb<List<Track>>() {
            @Override
            public void onOk(List<Track> value) {
                if (section != SEC_SEARCH) {
                    return;
                }
                trackAdapter.submit(value);
                hideState();
                subtitle.setText(keyword.trim().isEmpty()
                        ? "输入歌名、歌手或专辑名"
                        : "找到 " + value.size() + " 首");
            }

            @Override
            public void onErr(Exception e) {
                showState("搜索失败", "地址 " + Api.base());
            }
        });
    }

    private void showState(String text, String hint) {
        stateBox.setVisibility(View.VISIBLE);
        stateText.setText(text);
        stateHint.setText(hint == null ? "" : hint);
        stateHint.setVisibility(hint == null ? View.GONE : View.VISIBLE);
    }

    private void hideState() {
        stateBox.setVisibility(View.GONE);
    }

    private void focusList() {
        list.postDelayed(() -> {
            View child = list.getChildAt(0);
            if (child != null) {
                child.requestFocus();
            }
        }, 80);
    }

    private void focusGrid() {
        grid.postDelayed(() -> {
            View child = grid.getChildAt(0);
            if (child != null) {
                child.requestFocus();
            }
        }, 80);
    }

    /* ---------------- 搜索输入 ---------------- */

    @Override
    protected void onResume() {
        super.onResume();
        player.addListener(this);
        syncPlaying();
        searchInput.addTextChangedListener(watcher);
        if (section == SEC_SEARCH) {
            searchInput.postDelayed(() -> {
                InputMethodManager imm =
                        (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
                if (imm != null) {
                    imm.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT);
                }
            }, 200);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        player.removeListener(this);
        searchInput.removeTextChangedListener(watcher);
    }

    private final TextWatcher watcher = new TextWatcher() {
        @Override
        public void beforeTextChanged(CharSequence s, int a, int b, int c) {
        }

        @Override
        public void onTextChanged(CharSequence s, int a, int b, int c) {
        }

        @Override
        public void afterTextChanged(Editable s) {
            if (searchTask != null) {
                handler.removeCallbacks(searchTask);
            }
            final String q = s.toString();
            searchTask = () -> doSearch(q);
            handler.postDelayed(searchTask, 320);
        }
    };

    /* ---------------- 播放器同步 ---------------- */

    @Override
    public void onPlayerChanged() {
        syncPlaying();
    }

    private void syncPlaying() {
        Track t = player.current();
        if (t == null) {
            mini.setVisibility(View.GONE);
            trackAdapter.setPlayingId(-1);
            setBottomInset(false);
            return;
        }
        mini.setVisibility(View.VISIBLE);
        setBottomInset(true);
        miniTitle.setText(t.title);
        miniArtist.setText(t.artistName.isEmpty() ? "未知歌手" : t.artistName);
        ImageLoader.load(miniCover, t.cover, 10);
        miniPlay.setImageResource(player.isPlaying() ? R.drawable.ic_pause : R.drawable.ic_play);
        // 白色圆底配黑色图标，和 tvOS 的播放按钮一致
        miniPlay.setColorFilter(0xFF000000);
        int dur = player.duration();
        int pos = player.position();
        miniProgress.setProgress(dur > 0 ? (int) (pos * 1000L / dur) : 0);
        trackAdapter.setPlayingId(t.id);
    }

    /** 迷你播放条占了底部约 96dp，没在放歌时把这部分还给列表。 */
    private void setBottomInset(boolean playing) {
        View root = findViewById(R.id.root_column);
        int bottom = Math.round((playing ? 98 : 12) * getResources().getDisplayMetrics().density);
        if (root.getPaddingBottom() != bottom) {
            root.setPadding(root.getPaddingLeft(), root.getPaddingTop(),
                    root.getPaddingRight(), bottom);
        }
    }

    /* ---------------- 按键 ---------------- */

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN && event.getKeyCode() == KeyEvent.KEYCODE_MENU) {
            showServerDialog();
            return true;
        }
        if (KeyRouter.handle(this, event)) {
            return true;
        }
        // 顶栏 <-> 内容区 的焦点切换显式兜底，避免系统焦点搜索在网格里乱跳
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            View focused = getCurrentFocus();
            if (event.getKeyCode() == KeyEvent.KEYCODE_DPAD_DOWN && isNavItem(focused)) {
                if (focusContent()) {
                    return true;
                }
            } else if (event.getKeyCode() == KeyEvent.KEYCODE_DPAD_DOWN && focused == searchInput) {
                // 从搜索框往下进入结果列表，不让光标留在输入框里
                if (list.getVisibility() == View.VISIBLE && list.getChildCount() > 0) {
                    hideKeyboard();
                    list.getChildAt(0).requestFocus();
                    return true;
                }
            } else if (event.getKeyCode() == KeyEvent.KEYCODE_DPAD_UP && focused == searchInput) {
                hideKeyboard();
                navItems[section].requestFocus();
                return true;
            } else if (event.getKeyCode() == KeyEvent.KEYCODE_DPAD_UP && isContentTopRow(focused)) {
                navItems[section].requestFocus();
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    /** 焦点离开搜索框时收起软键盘，避免挡住结果列表 */
    private void hideKeyboard() {
        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.hideSoftInputFromWindow(searchInput.getWindowToken(), 0);
        }
    }

    private boolean isNavItem(View v) {
        for (LinearLayout item : navItems) {
            if (item == v) {
                return true;
            }
        }
        return false;
    }

    private boolean focusContent() {
        if (section == SEC_SEARCH) {
            searchInput.requestFocus();
            return true;
        }
        RecyclerView rv = section == SEC_LIBRARY ? list : grid;
        if (rv.getVisibility() != View.VISIBLE) {
            return false;
        }
        View child = rv.getChildAt(0);
        if (child != null) {
            child.requestFocus();
            return true;
        }
        return false;
    }

    private boolean isContentTopRow(View v) {
        if (v == null) {
            return false;
        }
        // 只有 RecyclerView 的直接子项才能问位置；顶栏/迷你播放条在上层按 UP 时不能进来
        ViewParent parent = v.getParent();
        if (list.getVisibility() == View.VISIBLE && parent == list) {
            return list.getChildAdapterPosition(v) == 0;
        }
        if (grid.getVisibility() == View.VISIBLE && parent == grid) {
            int pos = grid.getChildAdapterPosition(v);
            if (pos < 0) {
                return false;
            }
            RecyclerView.LayoutManager lm = grid.getLayoutManager();
            int span = lm instanceof GridLayoutManager
                    ? ((GridLayoutManager) lm).getSpanCount() : 4;
            return pos < span;
        }
        return false;
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (section != SEC_LIBRARY) {
                selectSection(SEC_LIBRARY, true);
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    private void showServerDialog() {
        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        input.setText(Api.base());
        input.setSelection(input.getText().length());

        new AlertDialog.Builder(this)
                .setTitle("NasMusic 服务器地址")
                .setView(input)
                .setPositiveButton("保存并重载", (d, w) -> {
                    String v = input.getText().toString();
                    Api.setBase(v);
                    getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                            .putString(KEY_BASE, Api.base()).apply();
                    libraryTracks.clear();
                    artists.clear();
                    albums.clear();
                    Toast.makeText(this, "已切换到 " + Api.base(), Toast.LENGTH_SHORT).show();
                    selectSection(SEC_LIBRARY, true);
                })
                .setNegativeButton("取消", null)
                .show();
    }
}
