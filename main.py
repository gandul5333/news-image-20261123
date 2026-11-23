#!/usr/bin/env python3
"""news-image-20261123 entry (Python 3.13, standard library only).

Draws a one-page newspaper front page summing up the world news of
Monday 23 November 2026 and writes it to /output/entry.png (1024x1024,
under 1 MiB). Everything is drawn in code: no photographs, no fonts on
disk, no network. The picture is fully deterministic: the same bytes
come out of every run.

Run it the way the grader does:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

With MAKEFUN_OUTPUT_DIR unset it writes to /output.
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (248, 243, 230)   # warm newsprint
PAPER2 = (241, 235, 216)  # slightly darker panel paper
INK = (24, 24, 24)        # near-black text
NAVY = (28, 52, 96)       # masthead + kicker blue
RED = (176, 38, 28)       # lead red
TEAL = (14, 110, 110)     # markets teal
ORANGE = (214, 96, 20)    # fire orange
GOLD = (196, 148, 28)     # sport gold
GREY = (110, 104, 92)     # small-print grey
SKY = (146, 190, 220)     # sky blue
SEA = (46, 110, 160)      # sea blue
GREEN = (34, 120, 60)     # up / calm green
WHITE = (255, 255, 255)
DARK = (40, 40, 44)

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)
for _i in range(W * H):
    buf[_i * 3] = PAPER[0]
    buf[_i * 3 + 1] = PAPER[1]
    buf[_i * 3 + 2] = PAPER[2]


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = c[0]
        buf[i + 1] = c[1]
        buf[i + 2] = c[2]


def rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i] = c[0]
            buf[i + 1] = c[1]
            buf[i + 2] = c[2]


def hline(x0, x1, y, c, th=1):
    for t in range(th):
        for x in range(x0, x1 + 1):
            px(x, y + t, c)


def vline(x, y0, y1, c, th=1):
    for t in range(th):
        for y in range(y0, y1 + 1):
            px(x + t, y, c)


def line(x0, y0, x1, y1, c, th=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for a in range(th):
            for b in range(th):
                px(x + a, y + b, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def disc(cx, cy, r, c):
    for yy in range(cy - r, cy + r + 1):
        dyy = yy - cy
        half = int((r * r - dyy * dyy) ** 0.5) if r * r - dyy * dyy >= 0 else 0
        for xx in range(cx - half, cx + half + 1):
            px(xx, yy, c)


def circle(cx, cy, r, c, th=2):
    for yy in range(cy - r - 1, cy + r + 2):
        for xx in range(cx - r - 1, cx + r + 2):
            d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
            if abs(d - r) <= th / 2.0:
                px(xx, yy, c)


def tri(x0, y0, x1, y1, x2, y2, c):
    ymin = min(y0, y1, y2)
    ymax = max(y0, y1, y2)

    def edge(ax, ay, bx, by, y):
        if ay == by:
            return None
        if (y < min(ay, by)) or (y > max(ay, by)):
            return None
        return ax + (bx - ax) * (y - ay) / (by - ay)

    for y in range(ymin, ymax + 1):
        xs = []
        for e in (edge(x0, y0, x1, y1, y), edge(x1, y1, x2, y2, y),
                  edge(x2, y2, x0, y0, y)):
            if e is not None:
                xs.append(e)
        if len(xs) >= 2:
            for x in range(int(min(xs)), int(max(xs)) + 1):
                px(x, y, c)


def poly(points, c):
    if len(points) < 3:
        return
    ymin = min(p[1] for p in points)
    ymax = max(p[1] for p in points)
    n = len(points)
    for y in range(ymin, ymax + 1):
        xs = []
        for i in range(n):
            ax, ay = points[i]
            bx, by = points[(i + 1) % n]
            if ay == by:
                continue
            if (y < min(ay, by)) or (y > max(ay, by)):
                continue
            xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
        if len(xs) >= 2:
            xs.sort()
            for x in range(int(xs[0]), int(xs[-1]) + 1):
                px(x, y, c)


# ---------------------------------------------------------------- PNG out
def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is clear. All text on
# the page is set in capitals with this one face.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("10001", "10010", "00100", "01000", "01001", "10001", "10001"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
}

BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def text_width(s, scale):
    return len(s) * 6 * scale


def draw_text(x, y, s, scale, c, align="left"):
    s = s.upper()
    w = text_width(s, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    for ci, ch in enumerate(s):
        glyph = FONT.get(ch, BLANK)
        gx = x + ci * 6 * scale
        for r in range(7):
            row = glyph[r]
            for col in range(5):
                if row[col] == "1":
                    rect(gx + col * scale, y + r * scale, scale, scale, c)
    return w


def wrap_text(s, max_w, scale):
    """Word-wrap s into lines that fit max_w pixels at the given scale."""
    words = s.upper().split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, s, max_w, scale, c, leading=None):
    if leading is None:
        leading = 7 * scale + 6
    lines = wrap_text(s, max_w, scale)
    for ln in lines:
        draw_text(x, y, ln, scale, c)
        y += leading
    return y

# ---------------------------------------------------------------- pictograms
def draw_globe(cx, cy, r):
    """Earth with a crack and rising smoke: the climate summit."""
    disc(cx, cy, r, SKY)
    # land masses (abstract blobs)
    poly([(cx - r + 8, cy - 6), (cx - r + 34, cy - 22), (cx - r + 52, cy - 8),
          (cx - r + 40, cy + 10), (cx - r + 16, cy + 8)], GREEN)
    poly([(cx + 6, cy + 4), (cx + 30, cy - 4), (cx + r - 10, cy + 8),
          (cx + 22, cy + 22), (cx + 2, cy + 18)], GREEN)
    poly([(cx - 14, cy + r - 22), (cx + 6, cy + r - 26), (cx + 12, cy + r - 10),
          (cx - 8, cy + r - 4)], GREEN)
    # meridians
    for dx in (-r // 2, 0, r // 2):
        for yy in range(cy - r, cy + r + 1):
            dyy = yy - cy
            half = int((r * r - dyy * dyy) ** 0.5)
            if half == 0:
                continue
            px(cx + dx * half // r, yy, (90, 150, 190))
    hline(cx - r, cx + r, cy, (90, 150, 190))
    circle(cx, cy, r, NAVY, 3)
    # crack across the globe
    line(cx - r + 14, cy - r + 26, cx - r + 40, cy - 4, INK, 3)
    line(cx - r + 40, cy - 4, cx - 8, cy + 10, INK, 3)
    line(cx - 8, cy + 10, cx + 18, cy + r - 14, INK, 3)
    # smoke columns rising from the top
    for sx, sh in ((cx - 30, 34), (cx + 6, 44), (cx + 34, 28)):
        for k in range(sh):
            wdt = 3 + k // 6
            for xx in range(sx - wdt, sx + wdt + 1):
                px(xx, cy - r - 8 - k, (120, 118, 110))
    # red "NO DEAL" banner across the globe
    rect(cx - r - 6, cy + r - 30, 2 * r + 12, 24, RED)
    draw_text(cx, cy + r - 26, "NO DEAL", 2, WHITE, align="center")


def draw_chart(x, y, w, h):
    """Falling market chart with candlesticks and a red down arrow."""
    rect(x, y, w, h, WHITE)
    unit = (h - 28) / 110.0
    base = y + h - 14
    for gy in range(y + 14, base, max(16, (h - 28) // 4)):
        hline(x + 4, x + w - 4, gy, (220, 220, 210))
    # candlesticks: values in 0..110 units; red body where close > low
    candles = [(8, 30, 52), (16, 44, 62), (14, 26, 40), (30, 52, 74),
               (44, 66, 84), (58, 76, 92), (70, 88, 102)]
    cw = (w - 16) // len(candles)
    for i, (lo, hi, close) in enumerate(candles):
        cx = x + 8 + i * cw + cw // 2
        top = int(base - hi * unit)
        bot = int(base - lo * unit)
        vline(cx, top, bot, INK, 2)
        col = RED if close > lo else GREEN
        cb = int(base - close * unit)
        rect(cx - cw // 3, cb, (2 * cw) // 3, max(3, bot - cb), col)
    # falling trend line
    pts = [(x + 8, y + 12), (x + w // 3, y + h // 3),
           (x + 2 * w // 3, y + 2 * h // 3), (x + w - 10, base - 4)]
    for a, b in zip(pts, pts[1:]):
        line(a[0], a[1], b[0], b[1], RED, 3)
    # big down arrow
    ax = x + w - 46
    ay = y + 8
    tri(ax, ay + 20, ax + 20, ay + 20, ax + 10, ay + 34, RED)
    rect(ax + 5, ay, 10, 22, RED)
    # tick labels
    draw_text(x + 4, y + h - 11, "NIKKEI -5.1%", 1, RED)
    draw_text(x + w - 4, y + h - 11, "S&P -3.7%", 1, RED, align="right")


def draw_rubble(x, y, w, h):
    """A shelled apartment block and rescue beams."""
    rect(x, y, w, h, (226, 216, 196))
    # standing wall, jagged top
    poly([(x + 10, y + h - 6), (x + 10, y + int(h * 0.42)),
          (x + int(w * 0.28), y + int(h * 0.30)),
          (x + int(w * 0.44), y + int(h * 0.42)),
          (x + int(w * 0.62), y + int(h * 0.24)),
          (x + int(w * 0.78), y + int(h * 0.38)),
          (x + int(w * 0.78), y + h - 6)], (150, 140, 126))
    # dark windows
    for wx, wy in ((0.16, 0.52), (0.38, 0.52), (0.60, 0.52), (0.38, 0.74)):
        rect(x + int(w * wx), y + int(h * wy), max(10, w // 12),
             max(8, h // 6), DARK)
    # rubble pile
    poly([(x + int(w * 0.80), y + h - 6), (x + int(w * 0.86), y + int(h * 0.45)),
          (x + int(w * 0.94), y + int(h * 0.62)),
          (x + w - 4, y + int(h * 0.40)), (x + w - 4, y + h - 6)],
         (120, 110, 96))
    # rescue light beam
    line(x + w - 6, y + 6, x + int(w * 0.82), y + int(h * 0.55), GOLD, 4)
    disc(x + w - 6, y + 8, 6, GOLD)


def draw_fire(x, y, w, h):
    """Factory with flames and smoke."""
    rect(x, y, w, h, (226, 216, 196))
    # factory block + chimney
    rect(x + 10, y + int(h * 0.55), w - 20, h - int(h * 0.55) - 6,
         (120, 116, 108))
    rect(x + w - 34, y + int(h * 0.18), 12, int(h * 0.82) - 6,
         (100, 96, 88))
    rect(x + w - 38, y + int(h * 0.14), 20, 6, (80, 76, 68))
    # sawtooth roof
    tri(x + 10, y + int(h * 0.55), x + 10 + (w - 20) // 3, y + int(h * 0.38),
        x + 10 + 2 * (w - 20) // 3, y + int(h * 0.55), (100, 96, 88))
    # windows
    for wx in range(x + 22, x + w - 46, 34):
        rect(wx, y + int(h * 0.68), 18, max(10, h // 6), DARK)
    # flames
    base = y + int(h * 0.55)
    for fx, fh in ((0.10, 0.34), (0.30, 0.44), (0.50, 0.32), (0.68, 0.40)):
        x0 = x + int(w * fx)
        tri(x0, base, x0 + 11, base - int(h * fh), x0 + 22, base, ORANGE)
        tri(x0 + 5, base, x0 + 11, base - int(h * fh) + 16, x0 + 17, base,
            (232, 190, 40))
    # smoke from the chimney
    for k in range(int(h * 0.30)):
        wdt = 3 + k // 7
        for xx in range(x + w - 28 - wdt, x + w - 28 + wdt + 1):
            px(xx, y + int(h * 0.14) - k, (130, 128, 120))


def draw_tanker(x, y, w, h):
    """Oil tanker on rough seas under a warning triangle."""
    rect(x, y, w, h, SKY)
    # sun
    disc(x + w - 40, y + 22, 13, (232, 190, 40))
    # sea
    sea_y = y + int(h * 0.62)
    rect(x, sea_y, w, h - int(h * 0.62), SEA)
    for wy in range(sea_y + 8, y + h - 4, 10):
        for wx in range(x + 6, x + w - 6, 26):
            line(wx, wy, wx + 12, wy, (120, 180, 215), 2)
    # hull
    poly([(x + 12, sea_y), (x + w - 16, sea_y),
          (x + w - 28, y + h - 8), (x + 26, y + h - 8)], (60, 56, 52))
    # deck + bridge
    rect(x + 26, sea_y - 26, w - 56, 26, (140, 60, 44))
    rect(x + w - 70, sea_y - 50, 32, 24, (200, 200, 190))
    rect(x + w - 64, sea_y - 44, 20, 10, DARK)
    # funnel with smoke
    rect(x + 46, sea_y - 42, 11, 16, DARK)
    for k in range(20):
        wdt = 3 + k // 8
        for xx in range(x + 51 - wdt, x + 51 + wdt + 1):
            px(xx, sea_y - 44 - k, (120, 118, 110))
    # warning triangle
    cx = x + w // 2
    tri(cx - 24, y + 10, cx + 24, y + 10, cx, y + 50, (232, 190, 40))
    tri(cx - 18, y + 14, cx + 18, y + 14, cx, y + 44, INK)
    draw_text(cx, y + 24, "!", 2, (232, 190, 40), align="center")


def draw_badge(x, y, w, h):
    """A sheriff star over prison bars: the cartel arrest."""
    rect(x, y, w, h, PAPER2)
    # bars
    for bx in range(x + 12, x + w - 8, 18):
        vline(bx, y + 8, y + h - 8, (70, 66, 60), 5)
    # star
    cx, cy = x + w // 2, y + h // 2 - 4
    r = min(w, h) // 2 - 6
    pts = []
    import math
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * math.cos(ang)), int(cy + rr * math.sin(ang))))
    poly(pts, GOLD)
    disc(cx, cy, 11, NAVY)


def draw_sport(x, y, w, h):
    """Checkered flag and a football."""
    rect(x, y, w, h, PAPER2)
    # checkered flag
    fx, fy = x + 14, y + 14
    for r in range(4):
        for c in range(6):
            col = INK if (r + c) % 2 == 0 else WHITE
            rect(fx + c * 12, fy + r * 12, 12, 12, col)
    line(fx, fy, fx, fy + 56, INK, 3)
    # football
    bx, by, br = x + w - 46, y + h // 2, 26
    disc(bx, by, br, WHITE)
    circle(bx, by, br, INK, 2)
    poly([(bx, by - 9), (bx + 9, by - 3), (bx + 5, by + 8),
          (bx - 5, by + 8), (bx - 9, by - 3)], INK)
    for dx, dy in ((0, -20), (19, -6), (12, 17), (-12, 17), (-19, -6)):
        line(bx, by, bx + dx, by + dy, INK, 2)

# ---------------------------------------------------------------- the page
def draw_page():
    # ---- masthead
    draw_text(W // 2, 34, "THE WORLD IN ONE DAY", 7, NAVY, align="center")
    draw_text(W // 2, 100, "MONDAY 23 NOVEMBER 2026", 2, INK, align="center")
    hline(28, 996, 126, INK, 3)
    hline(28, 996, 132, INK, 1)

    # ---- row 1: lead + right column
    # lead: COP31
    draw_text(36, 164, "CLIMATE", 2, RED)
    draw_text(132, 164, "COP31 - ANTALYA, TURKEY", 2, INK)
    draw_text(36, 192, "COP31 ENDS", 4, INK)
    draw_text(36, 224, "WITH NO DEAL", 4, INK)
    text_block(36, 268,
               "SUMMIT IN ANTALYA COLLAPSES AFTER TWO DAYS OF OVERTIME",
               536, 2, INK)
    draw_globe(312, 415, 58)
    text_block(36, 480,
               "THE EU AND ABOUT 130 NATIONS REJECTED A TEXT THAT "
               "DROPPED FOSSIL FUELS. PACIFIC ISLANDS CALL THE "
               "FAILURE DESPAIR.",
               536, 2, INK)
    vline(606, 150, 560, INK, 2)

    # markets
    draw_text(624, 162, "MARKETS", 2, TEAL)
    draw_text(624, 188, "AI SELL-OFF RATTLES", 3, INK)
    draw_text(624, 212, "WORLD MARKETS", 3, INK)
    draw_chart(624, 234, 364, 64)
    text_block(624, 306, "ASIAN REGULATORS STEP IN AS THE ROUT SPREADS.",
               364, 2, INK)
    hline(616, 996, 356, INK, 2)

    # Dymer
    draw_text(624, 384, "UKRAINE WAR", 2, RED)
    draw_text(624, 408, "STRIKE ON DYMER", 3, INK)
    draw_text(624, 432, "KILLS 11", 3, INK)
    draw_rubble(624, 452, 364, 64)
    text_block(624, 524, "BOY, 7, PULLED ALIVE AFTER 14 HOURS UNDER "
               "RUBBLE.", 364, 2, INK)

    hline(28, 996, 568, INK, 2)

    # ---- row 2: three stories
    # Indonesia factory fire
    draw_text(36, 592, "DISASTER - INDONESIA", 2, ORANGE)
    draw_text(36, 618, "24 DEAD IN", 3, INK)
    draw_text(36, 642, "FACTORY FIRE", 3, INK)
    draw_fire(36, 672, 296, 80)
    text_block(36, 760,
               "BLAZE RIPS THROUGH A SWEET FACTORY IN CIKANDE, "
               "BANTEN. DOZENS STILL MISSING.",
               296, 2, INK)
    vline(348, 580, 836, INK, 2)

    # Hormuz / Trump
    draw_text(364, 592, "US - IRAN", 2, RED)
    draw_text(364, 618, "TRUMP THREATENS", 3, INK)
    draw_text(364, 642, "TO SINK IRAN", 3, INK)
    draw_text(364, 666, "SHIPS", 3, INK)
    draw_tanker(364, 690, 296, 70)
    text_block(364, 768,
               "AFTER A US STRIKE ON AN OIL TANKER, HE WARNS TEHRAN.",
               296, 2, INK)
    vline(676, 580, 836, INK, 2)

    # El Chapo Isidro captured
    draw_text(692, 592, "MEXICO", 2, NAVY)
    draw_text(692, 618, "FBI MOST WANTED", 3, INK)
    draw_text(692, 642, "'CHAPO ISIDRO'", 3, INK)
    draw_text(692, 666, "CAUGHT", 3, INK)
    draw_badge(692, 690, 296, 70)
    text_block(692, 768,
               "FAUSTO ISIDRO MEZA-FLORES SEIZED IN SINALOA. $5M "
               "BOUNTY. US SEEKS EXTRADITION.",
               296, 2, INK)

    hline(28, 996, 844, INK, 2)

    # ---- sport strip
    draw_text(36, 862, "SPORT", 2, GOLD)
    draw_sport(36, 884, 120, 56)
    draw_text(170, 880, "MARQUEZ WINS 8TH", 3, INK)
    draw_text(170, 904, "MOTOGP TITLE", 3, INK)
    draw_text(170, 930, "IN PORTIMAO, EQUALS AGOSTINI.", 2, GREY)
    vline(580, 868, 940, INK, 2)
    draw_text(600, 880, "LIVERPOOL 4-0", 3, INK)
    draw_text(600, 904, "MAN UTD", 3, INK)
    draw_text(600, 930, "POCHETTINO'S NIGHTMARE START.", 2, GREY)

    # ---- footer ticker
    hline(28, 996, 956, INK, 2)
    draw_text(36, 966,
              "ALSO: MOLLY MELDRUM DIES, 83 - SOUTH KOREA EXPORTS "
              "TOP $1 TRILLION", 2, GREY)
    draw_text(36, 986,
              "BELGIAN AIRPORTS SHUT BY STRIKE - SEOUL NAMES FIRST "
              "WOMAN SPY CHIEF", 2, GREY)


def main():
    draw_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    print(f"wrote {path} ({size} bytes, sha256 {digest.hexdigest()})")
    if size > 1048576:
        print("error: entry.png is over the 1 MiB limit", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
