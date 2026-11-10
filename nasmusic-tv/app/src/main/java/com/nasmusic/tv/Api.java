package com.nasmusic.tv;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * NasMusic 后端访问层。只有 GET 读接口——电视端定位是"播放器"，
 * 增删改（扫描、刮削、上传、编辑）仍然在网页版做。
 */
public final class Api {

    private static final String TAG = "NasMusic";
    private static final String DEFAULT_BASE = "http://10.0.0.8";

    private static volatile String base = DEFAULT_BASE;
    private static final ExecutorService POOL = Executors.newFixedThreadPool(4);
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private Api() {
    }

    public interface Cb<T> {
        void onOk(T value);

        void onErr(Exception e);
    }

    public static String base() {
        return base;
    }

    public static void setBase(String value) {
        String b = value == null ? "" : value.trim();
        if (b.isEmpty()) {
            b = DEFAULT_BASE;
        }
        if (!b.startsWith("http://") && !b.startsWith("https://")) {
            b = "http://" + b;
        }
        while (b.endsWith("/")) {
            b = b.substring(0, b.length() - 1);
        }
        base = b;
    }

    /* ---------------- 接口 ---------------- */

    public static void tracks(String search, Cb<List<Track>> cb) {
        StringBuilder path = new StringBuilder("/api/tracks/?size=500&ordering=-added_at");
        if (search != null && !search.trim().isEmpty()) {
            path.append("&search=").append(enc(search.trim()));
        }
        get(path.toString(), new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Track.list(o.optJSONArray("results")));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    /** 曲目详情：只有这个接口会返回 lyrics（LRC 文本）。 */
    public static void track(int id, Cb<Track> cb) {
        get("/api/tracks/" + id + "/", new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Track.from(o));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    public static void artists(Cb<List<Collection>> cb) {
        get("/api/artists/?size=500", new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Collection.list(o.optJSONArray("results"), Collection.ARTIST));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    public static void albums(Cb<List<Collection>> cb) {
        get("/api/albums/?size=500", new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Collection.list(o.optJSONArray("results"), Collection.ALBUM));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    public static void artist(int id, Cb<Collection> cb) {
        get("/api/artists/" + id + "/", new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Collection.artist(o));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    public static void album(int id, Cb<Collection> cb) {
        get("/api/albums/" + id + "/", new Cb<JSONObject>() {
            @Override
            public void onOk(JSONObject o) {
                cb.onOk(Collection.album(o));
            }

            @Override
            public void onErr(Exception e) {
                cb.onErr(e);
            }
        });
    }

    /* ---------------- HTTP ---------------- */

    private static void get(String path, Cb<JSONObject> cb) {
        POOL.execute(() -> {
            try {
                JSONObject json = new JSONObject(getString(base + path));
                MAIN.post(() -> cb.onOk(json));
            } catch (Exception e) {
                Log.w(TAG, "GET " + path + " failed: " + e);
                MAIN.post(() -> cb.onErr(e));
            }
        });
    }

    private static String getString(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(6000);
        c.setReadTimeout(15000);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("User-Agent", "NasMusicTV/2.0");
        try {
            int code = c.getResponseCode();
            InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
            if (in == null) {
                throw new IllegalStateException("HTTP " + code);
            }
            ByteArrayOutputStream bos = new ByteArrayOutputStream(64 * 1024);
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            in.close();
            if (code >= 400) {
                throw new IllegalStateException("HTTP " + code);
            }
            return bos.toString("UTF-8");
        } finally {
            c.disconnect();
        }
    }

    private static String enc(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8");
        } catch (Exception e) {
            return s;
        }
    }
}
