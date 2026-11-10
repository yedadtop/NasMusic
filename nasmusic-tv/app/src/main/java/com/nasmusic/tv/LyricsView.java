package com.nasmusic.tv;

import android.animation.TimeInterpolator;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.text.TextPaint;
import android.util.AttributeSet;
import android.view.View;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 原生歌词视图。
 *
 * 为什么不用"当前行放大"：Android 的硬件加速画文字是先把字形光栅化进字形图集，
 * 再用一个矩阵采样到屏幕上。给文字加 scale 动画 = 拿固定分辨率的字形纹理做插值采样，
 * 60fps 也会糊、会抖，看起来就是"不流畅"。这不是掉帧，是采样质量差，救不了。
 * 所以这里**不缩放**，强调全靠"纯白 + 粗体"，字形永远按最终尺寸光栅化，绝对清晰。
 *
 * 性能要点：绘制循环里**绝不改 Paint 的状态**。Paint 的 alpha/size/typeface 一变，
 * 字形缓存 key 就变，等于每帧把所有中文重新光栅化一遍 —— 这台 S912 撑不住。
 * 每帧只改 canvas 的 translate 矩阵（纯 GPU 变换，字形走缓存）。
 */
public class LyricsView extends View {

    private static final Pattern TAG =
            Pattern.compile("\\[(\\d{1,2}):(\\d{1,2})(?:[.:](\\d{1,3}))?\\]");

    /** 滚动动画时长，与 Vue scrollToCenter 的 800ms 一致 */
    private static final int ANIM_MS = 800;
    /** easeOutQuart：1-(1-p)^4，和 Vue 完全一致 */
    private static final TimeInterpolator EASE_OUT_QUART = p -> 1f - (float) Math.pow(1f - p, 4);

    private static class Line {
        final int time;
        final String text;

        Line(int time, String text) {
            this.time = time;
            this.text = text;
        }
    }

    private final List<Line> lines = new ArrayList<>();
    private final List<String> rows = new ArrayList<>();
    private final List<Integer> rowOwner = new ArrayList<>();
    private final List<Integer> lineStart = new ArrayList<>();
    private final List<Integer> lineRows = new ArrayList<>();

    /** 非当前行：白 55% */
    private final TextPaint normalPaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
    /** 当前行：纯白 + 粗体 */
    private final TextPaint activePaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
    /** 上下渐隐带专用，alpha 取离散档位 */
    private final TextPaint edgePaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
    private final TextPaint hintPaint = new TextPaint(Paint.ANTI_ALIAS_FLAG);

    private final float baseSize;
    private final float rowHeight;
    private final float leftPad;
    /** 粗体比常规宽一点，排版留 4% 余量，避免当前行变粗后顶到右边缘 */
    private static final float BOLD_SLACK = 0.96f;

    private int currentLine = -1;
    private float scrollRow = 0f;
    private ValueAnimator animator;
    private String emptyText = "暂无歌词";

    public LyricsView(Context context) {
        this(context, null);
    }

    public LyricsView(Context context, AttributeSet attrs) {
        super(context, attrs);
        float sp = context.getResources().getDisplayMetrics().scaledDensity;
        float dp = context.getResources().getDisplayMetrics().density;

        normalPaint.setTextAlign(Paint.Align.LEFT);
        normalPaint.setColor(0xFFFFFFFF);
        normalPaint.setAlpha(0x8C);

        activePaint.setTextAlign(Paint.Align.LEFT);
        activePaint.setColor(0xFFFFFFFF);
        activePaint.setTypeface(Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD));

        edgePaint.setTextAlign(Paint.Align.LEFT);
        edgePaint.setColor(0xFFFFFFFF);
        edgePaint.setAlpha(0x8C);

        hintPaint.setColor(0xFF6E6E73);
        hintPaint.setTextSize(18 * sp);
        hintPaint.setTextAlign(Paint.Align.LEFT);

        // Vue 版 clamp(24px,3vw,34px)，960 CSS px 视口下取到 34px；原生面板同样占半屏，28sp 折中
        baseSize = 28 * sp;
        rowHeight = 68 * dp;
        leftPad = 56 * dp;

        normalPaint.setTextSize(baseSize);
        activePaint.setTextSize(baseSize);
        edgePaint.setTextSize(baseSize);
    }

    /** 歌词正在拉取 */
    public void setLoading() {
        clear();
        emptyText = "正在获取歌词…";
        invalidate();
    }

    /** 设置 LRC 文本；null / 空 / 无时间标签都会落到空状态 */
    public void setLyrics(String lrc) {
        clear();
        emptyText = "暂无歌词";
        if (lrc != null && !lrc.trim().isEmpty()) {
            List<Line> parsed = parse(lrc);
            if (parsed.isEmpty()) {
                emptyText = "暂无同步歌词";
            } else {
                lines.addAll(parsed);
                Collections.sort(lines, (a, b) -> Integer.compare(a.time, b.time));
                buildRows();
            }
        }
        invalidate();
    }

    /** 每次播放进度心跳调用；只有跨行时才触发滚动 */
    public void setPosition(int ms) {
        if (lines.isEmpty()) {
            return;
        }
        int idx = -1;
        int t = ms + 60;
        for (int i = 0; i < lines.size(); i++) {
            if (t >= lines.get(i).time) {
                idx = i;
            } else {
                break;
            }
        }
        if (idx == currentLine) {
            return;
        }
        currentLine = idx;
        animateTo(idx >= 0 ? centerRow(idx) : 0f);
    }

    /* ---------------- 解析与排版 ---------------- */

    private static List<Line> parse(String raw) {
        List<Line> out = new ArrayList<>();
        for (String rawLine : raw.split("\\r?\\n")) {
            Matcher m = TAG.matcher(rawLine);
            List<Integer> times = new ArrayList<>();
            int textStart = 0;
            while (m.find()) {
                int min = Integer.parseInt(m.group(1));
                int sec = Integer.parseInt(m.group(2));
                int frac = 0;
                String f = m.group(3);
                if (f != null) {
                    if (f.length() == 1) {
                        frac = Integer.parseInt(f) * 100;
                    } else if (f.length() == 2) {
                        frac = Integer.parseInt(f) * 10;
                    } else {
                        frac = Integer.parseInt(f.substring(0, 3));
                    }
                }
                times.add((min * 60 + sec) * 1000 + frac);
                textStart = m.end();
            }
            if (times.isEmpty()) {
                continue;
            }
            String text = rawLine.substring(textStart).trim();
            if (text.isEmpty()) {
                continue;
            }
            for (int time : times) {
                out.add(new Line(time, text));
            }
        }
        return out;
    }

    private void buildRows() {
        int width = getWidth() - getPaddingLeft() - getPaddingRight();
        if (width <= 0) {
            return;
        }
        float maxW = (width - leftPad - 24 * getResources().getDisplayMetrics().density)
                * BOLD_SLACK;
        for (int i = 0; i < lines.size(); i++) {
            lineStart.add(rows.size());
            int before = rows.size();
            wrap(i, lines.get(i).text, maxW);
            lineRows.add(rows.size() - before);
        }
    }

    private void wrap(int lineIndex, String text, float maxW) {
        if (maxW <= 0 || text.isEmpty()) {
            return;
        }
        int from = 0;
        while (from < text.length()) {
            int n = normalPaint.breakText(text, from, text.length(), true, maxW, null);
            if (n <= 0) {
                n = 1;
            }
            String piece = text.substring(from, from + n).trim();
            if (!piece.isEmpty()) {
                rows.add(piece);
                rowOwner.add(lineIndex);
            }
            from += n;
            while (from < text.length() && text.charAt(from) == ' ') {
                from++;
            }
        }
    }

    private float centerRow(int lineIndex) {
        if (lineIndex < 0 || lineIndex >= lineStart.size()) {
            return 0f;
        }
        int n = Math.max(1, lineRows.get(lineIndex));
        return lineStart.get(lineIndex) + (n - 1) / 2f;
    }

    private void clear() {
        cancelAnim();
        lines.clear();
        rows.clear();
        rowOwner.clear();
        lineStart.clear();
        lineRows.clear();
        currentLine = -1;
        scrollRow = 0f;
    }

    /* ---------------- 滚动动画（只动 translate，不动 Paint） ---------------- */

    private void animateTo(float target) {
        cancelAnim();
        float start = scrollRow;
        if (Math.abs(target - start) < 0.001f) {
            invalidate();
            return;
        }
        animator = ValueAnimator.ofFloat(start, target);
        animator.setDuration(ANIM_MS);
        animator.setInterpolator(EASE_OUT_QUART);
        animator.addUpdateListener(a -> {
            scrollRow = (float) a.getAnimatedValue();
            invalidate();
        });
        animator.start();
    }

    private void cancelAnim() {
        if (animator != null) {
            animator.cancel();
            animator = null;
        }
    }

    @Override
    protected void onDetachedFromWindow() {
        cancelAnim();
        super.onDetachedFromWindow();
    }

    /* ---------------- 绘制 ---------------- */

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        cancelAnim();
        rows.clear();
        rowOwner.clear();
        lineStart.clear();
        lineRows.clear();
        buildRows();
        scrollRow = currentLine >= 0 ? centerRow(currentLine) : 0f;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        int w = getWidth();
        int h = getHeight();
        if (w <= 0 || h <= 0) {
            return;
        }
        if (rows.isEmpty()) {
            Paint.FontMetrics fm = hintPaint.getFontMetrics();
            canvas.drawText(emptyText, leftPad, h / 2f - (fm.ascent + fm.descent) / 2f, hintPaint);
            return;
        }

        float centerY = h / 2f;
        Paint.FontMetrics fm = normalPaint.getFontMetrics();
        float baseline = -(fm.ascent + fm.descent) / 2f;

        for (int r = 0; r < rows.size(); r++) {
            float y = centerY + (r - scrollRow) * rowHeight;
            if (y < -rowHeight || y > h + rowHeight) {
                continue;
            }

            // 上下 10% 渐隐，等价 Vue 的 mask-image linear-gradient
            float lineTop = y - rowHeight / 2f;
            float lineBottom = y + rowHeight / 2f;
            float rowCenterRel = (Math.max(0f, lineTop / h) + Math.min(1f, lineBottom / h)) / 2f;
            float maskAlpha = computeMaskAlpha(rowCenterRel);

            boolean isCurrent = currentLine >= 0 && rowOwner.get(r) == currentLine;

            TextPaint p;
            if (maskAlpha >= 0.999f) {
                p = isCurrent ? activePaint : normalPaint;
            } else {
                // 贴边的 1~2 行：alpha 量化成 32 的整数倍，一次滚动只变几档
                int a = Math.round(255 * 0.55f * maskAlpha / 32f) * 32;
                edgePaint.setAlpha(Math.min(255, Math.max(0, a)));
                p = edgePaint;
            }

            canvas.drawText(rows.get(r), leftPad, y + baseline, p);
        }
    }

    /** 单行垂直位置对应的 mask 透明度：
     *  顶部 10% 透明 → 255，中间 80% 满透明，底部 10% 255 → 透明。 */
    private static float computeMaskAlpha(float centerRel) {
        if (centerRel <= 0.1f) {
            return centerRel / 0.1f;
        }
        if (centerRel >= 0.9f) {
            return (1f - centerRel) / 0.1f;
        }
        return 1f;
    }
}
