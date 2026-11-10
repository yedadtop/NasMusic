package com.nasmusic.tv;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.EncodeHintType;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;

import java.util.HashMap;
import java.util.Map;

/**
 * 电视端设置页：只做一件事——把手机该打开的网址和二维码亮出来。
 *
 * <p>真正的表单在 {@link SettingsServer} 提供的网页里，手机扫码填完电视立即生效。
 * 这样遥控器不用再输 IP。</p>
 */
public class SettingsActivity extends Activity {

    private ImageView qrView;
    private TextView urlView;
    private TextView baseView;
    private TextView hintView;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_settings);

        qrView = findViewById(R.id.settings_qr);
        urlView = findViewById(R.id.settings_url);
        baseView = findViewById(R.id.settings_base);
        hintView = findViewById(R.id.settings_hint);

        refresh();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
    }

    private void refresh() {
        SettingsServer.start(this);
        String url = SettingsServer.url();

        baseView.setText(Api.base());

        if (url == null) {
            urlView.setText("未连接到网络");
            hintView.setText("请先让电视连上 WiFi 或网线，再回到这里。");
            qrView.setImageDrawable(null);
            return;
        }

        urlView.setText(url);
        hintView.setText("手机扫右侧二维码，或直接在浏览器输入上面的地址。"
                + "\n保存后电视端立刻切换后端，无需重启。");
        qrView.setImageBitmap(qr(url, 480));
    }

    /** 白底黑点：手机相机识别率最高，外面再套一层白色圆角卡片 */
    private static Bitmap qr(String text, int size) {
        try {
            Map<EncodeHintType, Object> hints = new HashMap<>();
            hints.put(EncodeHintType.MARGIN, 1);
            hints.put(EncodeHintType.CHARACTER_SET, "UTF-8");
            BitMatrix m = new QRCodeWriter().encode(text, BarcodeFormat.QR_CODE, size, size, hints);
            int w = m.getWidth();
            int h = m.getHeight();
            int[] pixels = new int[w * h];
            for (int y = 0; y < h; y++) {
                int off = y * w;
                for (int x = 0; x < w; x++) {
                    pixels[off + x] = m.get(x, y) ? Color.BLACK : Color.WHITE;
                }
            }
            Bitmap bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
            bmp.setPixels(pixels, 0, w, 0, 0, w, h);
            return bmp;
        } catch (Exception e) {
            return null;
        }
    }
}
