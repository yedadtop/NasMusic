"""生成应用图标与电视 banner（无第三方依赖，纯 zlib 写 PNG）。

设计：深色底 + 蓝色辉光 + 五根均衡器条（SDF 抗锯齿，无需超采样）。
用法: python tools/gen_assets.py
"""
import math
import os
import struct
import zlib

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "app", "src", "main", "res", "drawable")

BG_TOP = (9, 14, 26)
BG_BOTTOM = (22, 34, 56)
GLOW = (37, 99, 235)
BAR_A = (56, 189, 248)     # sky-400
BAR_B = (99, 102, 241)     # indigo-500

BARS = [
    # (中心 x, 高度占比)
    (0.295, 0.30),
    (0.395, 0.52),
    (0.500, 0.74),
    (0.605, 0.46),
    (0.705, 0.24),
]
BAR_HALF_W = 0.036
BAR_RADIUS = 0.036


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sdf_round_rect(px, py, cx, cy, hw, hh, r):
    dx = abs(px - cx) - (hw - r)
    dy = abs(py - cy) - (hh - r)
    ax = max(dx, 0.0)
    ay = max(dy, 0.0)
    return math.hypot(ax, ay) + min(max(dx, dy), 0.0) - r


def render(w, h):
    rows = []
    px_size = 1.0 / max(w, h)   # 抗锯齿过渡宽度
    for y in range(h):
        ny = (y + 0.5) / h
        row = bytearray()
        for x in range(w):
            nx = (x + 0.5) / w

            # 背景竖向渐变
            r, g, b = mix(BG_TOP, BG_BOTTOM, ny * 0.9)

            # 中间偏上的径向辉光
            gx = (nx - 0.5) * 1.15
            gy = (ny - 0.52) * 1.15
            dist = math.hypot(gx, gy)
            glow = max(0.0, 1.0 - dist / 0.62) ** 2 * 0.55
            r, g, b = mix((r, g, b), GLOW, glow)

            # 均衡器条
            for cx, hh_ratio in BARS:
                hh = hh_ratio / 2
                cy = 0.5 + (0.0 if w == h else 0.0)
                d = sdf_round_rect(nx, ny, cx, cy, BAR_HALF_W, hh, min(BAR_RADIUS, hh * 0.9))
                cov = clamp(0.5 - d / px_size)
                if cov <= 0:
                    continue
                # 条内竖向渐变：上浅下深
                t = clamp((ny - (cy - hh)) / max(hh * 2, 1e-6))
                bar = mix(BAR_A, BAR_B, t)
                r = int(round(r + (bar[0] - r) * cov))
                g = int(round(g + (bar[1] - g) * cov))
                b = int(round(b + (bar[2] - b) * cov))

            row += bytes((r, g, b, 255))
        rows.append(bytes(row))
    return rows


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    print(f"  {os.path.basename(path)}  {w}x{h}  {len(png) / 1024:.1f}KB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("生成图片资源:")
    write_png(os.path.join(OUT_DIR, "ic_launcher.png"), 512, 512, render(512, 512))
    write_png(os.path.join(OUT_DIR, "tv_banner.png"), 320, 180, render(320, 180))


if __name__ == "__main__":
    main()
