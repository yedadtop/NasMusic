package com.nasmusic.tv;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.os.Handler;
import android.os.Looper;
import android.util.LruCache;
import android.widget.ImageView;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 极简图片加载器：内存 LRU + 线程池 + 圆角/圆形裁剪 + 高斯近似模糊。
 * 不引 Glide/Coil，是因为封面都来自局域网，尺寸小、延迟低，够用且 APK 更小。
 */
public final class ImageLoader {

    private static final LruCache<String, Bitmap> CACHE =
            new LruCache<String, Bitmap>((int) (Runtime.getRuntime().maxMemory() / 1024 / 8)) {
                @Override
                protected int sizeOf(String key, Bitmap value) {
                    return value.getByteCount() / 1024;
                }
            };

    private static final ExecutorService POOL = Executors.newFixedThreadPool(4);
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private ImageLoader() {
    }

    /** 圆角/圆形封面。radiusDp 传 -1 表示圆形。 */
    public static void load(ImageView iv, String url, int radiusDp) {
        if (iv == null) {
            return;
        }
        if (url == null || url.isEmpty()) {
            iv.setImageDrawable(null);
            iv.setTag(null);
            return;
        }
        boolean circle = radiusDp < 0;
        String key = url + (circle ? "#circle" : "#r" + radiusDp);
        iv.setTag(key);

        Bitmap cached = CACHE.get(key);
        if (cached != null) {
            iv.setImageBitmap(cached);
            return;
        }
        iv.setImageDrawable(null);

        final int target = Math.max(iv.getWidth(), dp(iv.getContext(), 160));
        final int radiusPx = circle ? 0 : Math.round(radiusDp * iv.getResources().getDisplayMetrics().density);

        POOL.execute(() -> {
            try {
                Bitmap bmp = decode(url, target);
                if (bmp == null) {
                    return;
                }
                Bitmap out = circle ? circular(bmp) : rounded(bmp, radiusPx);
                CACHE.put(key, out);
                MAIN.post(() -> {
                    if (key.equals(iv.getTag())) {
                        iv.setImageBitmap(out);
                    }
                });
            } catch (Exception ignored) {
                // 封面加载失败就留空，不影响主流程
            }
        });
    }

    /** 全屏播放页的背景：小图 + 模糊 + 放大，成本极低。 */
    public static void loadBackground(ImageView iv, String url) {
        if (iv == null || url == null || url.isEmpty()) {
            return;
        }
        String key = url + "#blur";
        Bitmap cached = CACHE.get(key);
        if (cached != null) {
            iv.setImageBitmap(cached);
            return;
        }
        iv.setTag(key);
        POOL.execute(() -> {
            try {
                Bitmap small = decode(url, 128);
                if (small == null) {
                    return;
                }
                Bitmap blurred = blur(small, 12, 3);
                Bitmap scaled = Bitmap.createScaledBitmap(blurred, 640,
                        Math.max(1, blurred.getHeight() * 640 / Math.max(1, blurred.getWidth())), true);
                CACHE.put(key, scaled);
                MAIN.post(() -> {
                    if (key.equals(iv.getTag())) {
                        iv.setImageBitmap(scaled);
                    }
                });
            } catch (Exception ignored) {
            }
        });
    }

    /* ---------------- 内部实现 ---------------- */

    private static int dp(android.content.Context c, int v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }

    private static Bitmap decode(String url, int targetPx) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(6000);
        c.setReadTimeout(20000);
        c.setRequestProperty("User-Agent", "NasMusicTV/2.0");
        try {
            InputStream in = c.getInputStream();
            ByteArrayOutputStream bos = new ByteArrayOutputStream(32 * 1024);
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            in.close();
            byte[] data = bos.toByteArray();

            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(data, 0, data.length, o);
            int sample = 1;
            int w = o.outWidth, h = o.outHeight;
            while (w / (sample * 2) >= targetPx && h / (sample * 2) >= targetPx) {
                sample *= 2;
            }
            o.inJustDecodeBounds = false;
            o.inSampleSize = sample;
            o.inPreferredConfig = Bitmap.Config.RGB_565;
            return BitmapFactory.decodeByteArray(data, 0, data.length, o);
        } finally {
            c.disconnect();
        }
    }

    private static Bitmap rounded(Bitmap src, int radiusPx) {
        int w = src.getWidth();
        int h = src.getHeight();
        Bitmap out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        Canvas cv = new Canvas(out);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        Path path = new Path();
        path.addRoundRect(new RectF(0, 0, w, h), radiusPx, radiusPx, Path.Direction.CW);
        cv.clipPath(path);
        cv.drawBitmap(src, 0, 0, p);
        src.recycle();
        return out;
    }

    private static Bitmap circular(Bitmap src) {
        int w = src.getWidth();
        int h = src.getHeight();
        int d = Math.min(w, h);
        Bitmap out = Bitmap.createBitmap(d, d, Bitmap.Config.ARGB_8888);
        Canvas cv = new Canvas(out);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        Path path = new Path();
        path.addCircle(d / 2f, d / 2f, d / 2f, Path.Direction.CW);
        cv.clipPath(path);
        cv.drawBitmap(src, (d - w) / 2f, (d - h) / 2f, p);
        src.recycle();
        return out;
    }

    /** 多次盒式模糊近似高斯，纯 Java 实现，避免依赖 RenderScript。 */
    private static Bitmap blur(Bitmap src, int radius, int passes) {
        int w = src.getWidth();
        int h = src.getHeight();
        int[] pix = new int[w * h];
        src.getPixels(pix, 0, w, 0, 0, w, h);
        int[] tmp = new int[w * h];

        for (int pass = 0; pass < passes; pass++) {
            blurPass(pix, tmp, w, h, radius, true);
            blurPass(tmp, pix, w, h, radius, false);
        }
        src.recycle();
        Bitmap out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        out.setPixels(pix, 0, w, 0, 0, w, h);
        return out;
    }

    private static void blurPass(int[] in, int[] out, int w, int h, int r, boolean horizontal) {
        int outer = horizontal ? h : w;
        int inner = horizontal ? w : h;
        for (int i = 0; i < outer; i++) {
            int sumR = 0, sumG = 0, sumB = 0, count = 0;
            for (int j = -r; j <= r; j++) {
                int k = clamp(j, 0, inner - 1);
                int c = horizontal ? in[i * w + k] : in[k * w + i];
                sumR += (c >> 16) & 0xFF;
                sumG += (c >> 8) & 0xFF;
                sumB += c & 0xFF;
                count++;
            }
            for (int j = 0; j < inner; j++) {
                int idx = horizontal ? i * w + j : j * w + i;
                out[idx] = 0xFF000000 | ((sumR / count) << 16) | ((sumG / count) << 8) | (sumB / count);
                int add = clamp(j + r + 1, 0, inner - 1);
                int sub = clamp(j - r, 0, inner - 1);
                int cAdd = horizontal ? in[i * w + add] : in[add * w + i];
                int cSub = horizontal ? in[i * w + sub] : in[sub * w + i];
                sumR += ((cAdd >> 16) & 0xFF) - ((cSub >> 16) & 0xFF);
                sumG += ((cAdd >> 8) & 0xFF) - ((cSub >> 8) & 0xFF);
                sumB += (cAdd & 0xFF) - (cSub & 0xFF);
            }
        }
    }

    private static int clamp(int v, int lo, int hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }
}
