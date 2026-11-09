#!/usr/bin/env python3
"""Builds the profile README: pixel-art GIFs in assets/, then README.md.

Every picture is drawn on a small grid, then scaled up by a whole number with no
smoothing, so the pixels stay square. Roles and dividers are plain ASCII text.

Frame 0 of each GIF is its complete pose (name typed, letter out, line drawn).
GitHub can pause animated images for people who ask for reduced motion, and a
paused GIF shows frame 0, so that frame has to make sense by itself.

Needs: pip install pillow.  Run: python3 tools/build.py
"""

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

THEMES = {
    "dark": dict(bg="#0E1330", bg2="#1A2050", line="#2C3370", text="#F4F2FF", muted="#A9ADD8", faint="#3A4186",
                 gold="#F2C14E", lilac="#B9A6FF", pink="#FF8FB8", win_a="#2B3078", win_b="#6A4596", shade="#090C24",
                 paper="#F4F2FF", paper_line="#B9A6FF", city="#1A1E4E"),
    "light": dict(bg="#F7F5FF", bg2="#E9E5FF", line="#D3CDF4", text="#171A45", muted="#5A5D8A", faint="#C8C2EE",
                  gold="#B27C00", lilac="#6A4ED2", pink="#CE3C78", win_a="#CFC8FF", win_b="#FFD3E2", shade="#272A63",
                  paper="#FFFFFF", paper_line="#A796EC", city="#9C97CC"),
}
KEYS = list(THEMES["dark"])
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# Classic 5x7 bitmap font: five column bytes per glyph, bit 0 at the top, bit 7 for descenders.
FONT_HEX = (
    "0000000000 00005F0000 0007000700 147F147F14 242A7F2A12 2313086462 3649562050 0000030000 "
    "001C224100 0041221C00 2A1C7F1C2A 08083E0808 0080703000 0808080808 0000606000 2010080402 "
    "3E5149453E 00427F4000 7249494946 2141494D33 1814127F10 2745454539 3C4A494931 4121110907 "
    "3649494936 464949291E 0000140000 0040340000 0008142241 1414141414 0041221408 0201590906 "
    "3E415D594E 7C1211127C 7F49494936 3E41414122 7F4141413E 7F49494941 7F09090901 3E41415173 "
    "7F0808087F 00417F4100 2040413F01 7F08142241 7F40404040 7F021C027F 7F0408107F 3E4141413E "
    "7F09090906 3E4151215E 7F09192946 2649494932 03017F0103 3F4040403F 1F2040201F 3F4038403F "
    "6314081463 0304780403 6159494D43 007F414100 0204081020 0041417F00 0402010204 4040404040 "
    "0001020400 2054547840 7F28444438 3844444428 384444287F 3854545418 00087E0902 18A4A49C78 "
    "7F08040478 00447D4000 2040403D00 7F10284400 00417F4000 7C04780478 7C08040478 3844444438 "
    "FC18242418 18242418FC 7C08040408 4854545424 04043F4424 3C4040207C 1C2040201C 3C4030403C "
    "4428102844 4C9090907C 4464544C44"
).split()
FONT = {chr(32 + i): bytes.fromhex(h) for i, h in enumerate(FONT_HEX)}


def glyph(ch):
    if ch == " ":
        return [0, 0, 0]
    cols = list(FONT[ch])
    while cols and cols[0] == 0:
        cols.pop(0)
    while cols and cols[-1] == 0:
        cols.pop()
    return cols


def text_width(s, scale=1):
    return (sum(len(glyph(ch)) + 1 for ch in s) - 1) * scale if s else 0


class Canvas:
    def __init__(self, w, h, theme):
        self.w, self.h, self.t = w, h, theme
        self.img = Image.new("P", (w, h), KEYS.index("bg"))
        palette = []
        for key in KEYS:
            value = THEMES[theme][key]
            palette += [int(value[i:i + 2], 16) for i in (1, 3, 5)]
        self.img.putpalette(palette)
        self.d = ImageDraw.Draw(self.img)

    def copy(self):
        other = Canvas.__new__(Canvas)
        other.w, other.h, other.t = self.w, self.h, self.t
        other.img = self.img.copy()
        other.d = ImageDraw.Draw(other.img)
        return other

    def rect(self, x, y, w, h, c):
        self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=KEYS.index(c))

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.img.putpixel((x, y), KEYS.index(c))

    def line(self, pts, c, width=1):
        self.d.line(pts, fill=KEYS.index(c), width=width)

    def poly(self, pts, c):
        self.d.polygon(pts, fill=KEYS.index(c))

    def frame(self, c="line"):
        self.d.rectangle([0, 0, self.w - 1, self.h - 1], outline=KEYS.index(c))

    def text(self, s, x, y, c, scale=1):
        for ch in s:
            cols = glyph(ch)
            for i, col in enumerate(cols):
                for row in range(8):
                    if col >> row & 1:
                        self.rect(x + i * scale, y + row * scale, scale, scale, c)
            x += (len(cols) + 1) * scale

    def sprite(self, rows, x, y, cmap, flip=False, shift=None):
        width = max(len(r) for r in rows)
        for j, row in enumerate(rows):
            dx = shift(j) if shift else 0
            for i, ch in enumerate(row):
                if ch != ".":
                    self.px(x + dx + (width - 1 - i if flip else i), y + j, cmap[ch])

    def dither(self, c, amount):
        """Ordered dither of colour c, where amount(x, y) runs from 0 (none) to 1 (solid)."""
        for y in range(self.h):
            for x in range(self.w):
                if amount(x, y) > (BAYER[y % 4][x % 4] + 0.5) / 16:
                    self.px(x, y, c)


written = {}


def scene(name, w, h, scale, n, ms, bg, draw):
    """Writes name-dark.gif and name-light.gif. bg paints the still layer, draw(c, f) one frame."""
    for theme in THEMES:
        base = Canvas(w, h, theme)
        bg(base)
        frames = []
        for f in range(n):
            c = base.copy()
            draw(c, f)
            frames.append(c.img.resize((w * scale, h * scale), Image.NEAREST))
        frames[0].save(ASSETS / f"{name}-{theme}.gif", save_all=True, append_images=frames[1:],
                       duration=ms, loop=0, optimize=False)
    written[name] = (w * scale, h * scale)


SPARK_BIG = ["...g...", "...g...", "..ggg..", "ggggggg", "..ggg..", "...g...", "...g..."]
SPARK_SMALL = [".......", ".......", "...g...", "..ggg..", "...g...", ".......", "......."]
GOLD = {"g": "gold"}


# --- Hero --------------------------------------------------------------------
def hero():
    W, H = 200, 60
    name, tag = "Hi, I'm Sajal.", "Designer and builder."
    mediums = ["all just mediums.", "AI", "Hardware", "Software", "Canvas"]
    name_w = text_width(name, 2)
    x0 = (W - name_w) // 2 - 4

    # Frame 0 is the finished line. Mediums cycle, then the name retypes itself.
    seq = [(0, 0, len(name))] * 22 + [(0, -1, len(name)), (0, -3, len(name))]
    for m in range(1, 5):
        seq += [(m, 3, len(name)), (m, 1, len(name))] + [(m, 0, len(name))] * 14 + [(m, -1, len(name)), (m, -3, len(name))]
    seq += [(None, 0, i) for i in range(len(name), -1, -1)] + [(None, 0, i) for i in range(len(name) + 1)]
    seq += [(0, 3, len(name)), (0, 1, len(name))]
    n = len(seq)

    rnd = random.Random(7)
    stars = []
    while len(stars) < 34:
        x, y = rnd.randint(3, W - 4), rnd.randint(3, H - 4)
        if (y < 26 and 30 < x < 170) or (26 <= y < 36 and 12 < x < 188) or (y >= 36 and 6 < x < 193):
            continue
        stars.append((x, y, rnd.choice(["lilac", "gold", "pink"]), rnd.random(), rnd.choice([1, 1, 2])))

    def bg(c):
        c.dither("bg2", lambda x, y: (x / W + y / H) / 2 * 0.9)
        c.frame()
        c.text(tag, (W - text_width(tag)) // 2, 28, "muted")

    def draw(c, f):
        m, off, typed = seq[f]
        for x, y, col, phase, size in stars:
            on = math.sin(2 * math.pi * (f / n * 8 + phase)) > 0
            c.rect(x, y, size, size, col if on else "faint")
        c.text(name[:typed], x0, 8, "text", 2)
        typing = typed < len(name) or m is None
        if typing or f // 6 % 2 == 0:
            c.rect(x0 + text_width(name[:typed], 2) + 2, 8, 2, 15, "gold")
        if not typing:
            c.sprite(SPARK_BIG if f // 10 % 2 == 0 else SPARK_SMALL, x0 + name_w + 7, 7, GOLD)
        if m is not None:
            label = mediums[m]
            col = "faint" if off else ("pink" if m == 0 else "gold")
            c.text(label, (W - text_width(label, 2)) // 2, 39 + off, col, 2)

    scene("hero", W, H, 4, n, 110, bg, draw)


# --- Metro -------------------------------------------------------------------
def metro():
    W, H = 80, 55
    n, period = 80, 80
    blocks = []
    r = random.Random(11)
    x = 0
    while x < period - 6:
        w, h = r.randint(7, 12), r.randint(9, 21)
        lights = [(r.randint(1, w - 3), r.randint(2, h - 2)) for _ in range(2)]
        blocks.append((x, w, h, lights))
        x += w + r.randint(1, 2)

    def bg(c):
        c.rect(3, 3, W - 6, H - 6, "win_a")
        c.dither("win_b", lambda x, y: (x / W + y / H) / 2 * 1.3 - 0.1)
        c.rect(0, 0, W, 3, "bg")
        c.rect(0, H - 3, W, 3, "bg")
        c.rect(0, 0, 3, H, "bg")
        c.rect(W - 3, 0, 3, H, "bg")

    def figure(c, cx, top, sway, head_dy=0):
        c.rect(cx - 3 + sway, top + head_dy, 7, 7, "shade")
        c.px(cx - 3 + sway, top + head_dy, "city")
        c.px(cx + 3 + sway, top + head_dy, "city")
        c.rect(cx - 6 + sway, top + 8, 13, 5, "shade")
        c.rect(cx - 7, top + 13, 15, H - top - 13, "shade")

    def draw(c, f):
        for k in (0, 1):
            for bx, w, h, lights in blocks:
                x = bx + k * period - f
                c.rect(x, 38 - h, w, H - 38 + h, "city")
                for lx, ly in lights:
                    c.rect(x + lx, 38 - h + ly, 1, 2, "gold")
        c.rect(3, 7, W - 6, 1, "shade")
        phase = lambda p: round(math.sin(2 * math.pi * (f / 40 + p)))
        for cx in (20, 40, 61):
            c.rect(cx, 8, 1, 3, "shade")
            c.d.rectangle([cx - 1, 11, cx + 1, 13], outline=KEYS.index("shade"))
        looking_up = f < 26
        figure(c, 20, 25, phase(0))
        figure(c, 61, 23, phase(0.6))
        figure(c, 40, 29, phase(0.3), 0 if looking_up else 2)
        if not looking_up:
            c.rect(37, 41, 7, 8, "win_b")
        c.rect(39, 42, 3, 6, "gold")
        c.rect(0, 0, W, 3, "bg")
        c.rect(0, H - 3, W, 3, "bg")
        c.rect(0, 0, 3, H, "bg")
        c.rect(W - 3, 0, 3, H, "bg")
        c.frame()

    scene("metro", W, H, 4, n, 100, bg, draw)


# --- Discipline icons --------------------------------------------------------
CURSOR = ["g.....", "gg....", "ggg...", "gggg..", "ggggg.", "ggg...", "g.gg..", "...g.."]
BRACKET = ["...l", "..l.", ".l..", "l...", ".l..", "..l.", "...l"]


def disciplines():
    S, N = 16, 4

    def product(c, f):
        p = f / 28
        move = 0 if p < 0.45 else min(1, (p - 0.45) / 0.3) if p < 0.75 else max(0, 1 - (p - 0.75) / 0.2)
        ox, oy = round(-3 * move), round(-3 * move)
        for i in range(3, 13, 2):
            c.px(i, 3, "faint")
            c.px(i, 11, "faint")
        for i in range(3, 12, 2):
            c.px(3, i, "faint")
            c.px(12, i, "faint")
        c.rect(3 + ox, 3 + oy, 10, 9, "lilac")
        c.rect(5 + ox, 5 + oy, 4, 1, "bg")
        c.rect(5 + ox, 8 + oy, 6, 1, "bg")
        cx = 10 - round(4 * move)
        c.sprite(CURSOR, cx, 8 - round(4 * move), GOLD)

    scene("disc-product", S, S, N, 28, 110, lambda c: None, product)

    def engineering(c, f):
        c.sprite(BRACKET, 1, 4, {"l": "lilac"})
        c.sprite(BRACKET, 11, 4, {"l": "lilac"}, flip=True)
        if f < 6:
            c.line([(9, 3), (6, 12)], "gold")

    scene("disc-engineering", S, S, N, 12, 120, lambda c: None, engineering)

    def hardware(c, f):
        a = math.radians(110 * math.sin(2 * math.pi * f / 24))
        c.rect(7, 0, 2, 2, "pink" if f % 24 < 12 else "faint")
        c.d.ellipse([2, 4, 13, 15], fill=KEYS.index("bg2"), outline=KEYS.index("line"))
        c.d.ellipse([4, 6, 11, 13], fill=KEYS.index("lilac"))
        c.line([(7.5, 9.5), (round(7.5 + 3.5 * math.sin(a)), round(9.5 - 3.5 * math.cos(a)))], "bg")

    scene("disc-hardware", S, S, N, 24, 110, lambda c: None, hardware)

    def art(c, f):
        a = math.radians(f / 16 * 90 + 45)
        r = 6.5

        def corner(k, y):
            ang = a + k * math.pi / 2 - math.pi / 4
            return (round(7.5 + r * math.cos(ang)), round(y + r * 0.48 * math.sin(ang)))

        top = [corner(k, 5) for k in range(4)]
        bottom = [corner(k, 11) for k in range(4)]
        for k in range(4):
            m = (k + 0.5) * math.pi / 2 - math.pi / 4 + a
            if math.sin(m) > 0:
                j = (k + 1) % 4
                c.poly([top[k], top[j], bottom[j], bottom[k]], "lilac" if math.cos(m) > 0 else "pink")
        c.poly(top, "gold")

    scene("disc-art", S, S, N, 16, 130, lambda c: None, art)


# --- Cards -------------------------------------------------------------------
CARD_W, CARD_H, CARD_SCALE = 132, 80, 3
BIRD = [
    "...........ppppp....",
    "..........ppppppp...",
    "..........pppwspp...",
    "..........ppppppggg.",
    "..........pppppp....",
    "ll.....ppppppppp....",
    ".lll.ppppppppppp....",
    "..llllllllpppppp....",
    "...llllllllpppp.....",
    "....pllllllppp......",
    ".....ppppppp........",
    ".......g..g.........",
    ".......g..g.........",
]
BIRD_COLORS = {"p": "pink", "l": "lilac", "g": "gold", "w": "paper", "s": "shade"}
LEAF = ["..lll.", ".lllll", "llllll", ".lll.."]
LEAF_BIG = ["....llll..", "..llllllll", ".lllllllll", "lllllllll.", "lllllll...", ".lll......"]


def card(name, title, sub, n, ms, still, art):
    if text_width(sub) > CARD_W - 10:
        raise ValueError(f"{name}: subtitle is too wide")

    def bg(c):
        c.dither("bg2", lambda x, y: 0.8 - math.hypot((x - 66) / 66, (y - 26) / 34))
        c.frame()
        still(c)
        c.text(title, 6, 52, "text", 2)
        c.text(sub, 6, 70, "muted")

    scene(name, CARD_W, CARD_H, CARD_SCALE, n, ms, bg, art)


def cards():
    def titan(c, f):
        if f < 15:
            rise, closed = 16, False
        elif f < 23:
            rise, closed = round(16 * (23 - f) / 8), False
        elif f < 31:
            rise, closed = 0, True
        else:
            rise, closed = round(16 * min(1, (f - 31) / 7)), False
        c.rect(44, 22, 45, 27, "bg2")
        if not closed:
            c.poly([(44, 22), (88, 22), (66, 8)], "faint")
        c.rect(50, 24 - rise, 33, 16 + rise, "paper")  # always reaches below the V of the front flap
        c.d.rectangle([50, 24 - rise, 82, 39], outline=KEYS.index("paper_line"))
        for y, w in [(4, 24), (8, 16), (12, 20)]:
            c.rect(54, 24 - rise + y, w, 1, "paper_line")
        c.poly([(44, 22), (66, 36), (88, 22), (88, 48), (44, 48)], "lilac")
        if closed:
            c.poly([(44, 22), (88, 22), (66, 36)], "pink")
        if rise == 16:
            c.d.ellipse([92, 5, 100, 13], fill=KEYS.index("gold"))
            c.line([(94, 9), (95, 11), (98, 7)], "bg")

    card("card-titan", "Titan Email", "Email Designer", 40, 110, lambda c: None, titan)

    points = [(8, 28), (46, 28), (52, 28), (58, 12), (66, 44), (72, 20), (76, 28), (118, 28)]
    total = sum(math.dist(a, b) for a, b in zip(points, points[1:]))

    def beat_still(c):
        for x in range(8, 124, 13):
            for y in range(8, 49, 13):
                c.px(x, y, "faint")

    def pulse(c, f):
        if f < 16:
            progress = 1
        elif f < 20:
            progress = 0
        elif f < 37:
            progress = (f - 19) / 17
        else:
            progress = 1
        left = progress * total
        drawn = [points[0]]
        for a, b in zip(points, points[1:]):
            d = math.dist(a, b)
            if left >= d:
                drawn.append(b)
                left -= d
            else:
                t = left / d
                drawn.append((round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t)))
                break
        if progress > 0:
            c.line(drawn, "pink", 2)
        if progress == 1:
            radius = 3 + (f + 3) % 20 // 3 if f < 16 else 3
            if radius > 3:
                c.d.ellipse([118 - radius, 28 - radius, 118 + radius, 28 + radius], outline=KEYS.index("gold"))
            c.d.ellipse([116, 26, 120, 30], fill=KEYS.index("gold"))

    card("card-pulse", "Pulse", "Product intelligence", 40, 100, beat_still, pulse)

    def tiny_still(c):
        c.poly([(52, 38), (80, 38), (77, 49), (55, 49)], "bg2")
        c.line([(52, 38), (55, 49), (77, 49), (80, 38)], "line")

    def tiny(c, f):
        sway = round(1.6 * math.sin(2 * math.pi * f / 20))
        c.line([(66, 34), (66, 26), (66 + sway, 14)], "gold", 2)
        c.sprite(LEAF_BIG, 56 + sway, 8, {"l": "lilac"}, flip=True)
        c.sprite(LEAF_BIG, 68 + sway, 14, {"l": "pink"})
        c.rect(50, 34, 32, 4, "faint")
        blink = 34 <= f < 36
        for x in (60, 71):
            c.rect(x, 43 if blink else 42, 2, 1 if blink else 2, "text")
        c.rect(64, 46, 4, 1, "text")
        c.px(63, 45, "text")
        c.px(68, 45, "text")
        if f < 26:
            c.rect(86, 6, 20, 13, "paper")
            c.d.rectangle([86, 6, 105, 18], outline=KEYS.index("line"))
            c.poly([(88, 19), (85, 23), (92, 19)], "paper")
            c.text("hi", 92, 8, "shade")

    card("card-tiny", "Tiny", "A plant you can talk to", 40, 110, tiny_still, tiny)

    def bird_still(c):
        c.rect(6, 44, 120, 2, "gold")
        c.sprite(LEAF, 12, 40, {"l": "lilac"})
        c.sprite(LEAF, 112, 40, {"l": "lilac"}, flip=True)

    def birdie(c, f):
        left, right = 26, 84
        hop = 0
        if f < 12:
            x, flip = left, False
        elif f < 18:
            t = (f - 11) / 6
            x, hop, flip = round(left + (right - left) * t), round(8 * math.sin(math.pi * t)), False
        elif f < 24:
            x, flip = right, False
        elif f < 30:
            x, flip = right, True
        elif f < 36:
            t = (f - 29) / 6
            x, hop, flip = round(right + (left - right) * t), round(8 * math.sin(math.pi * t)), True
        else:
            x, flip = left, True
        if f == 47:
            flip = False
        tilt = 4 <= f < 9 or 25 <= f < 29
        c.sprite(BIRD, x, 31 - hop, BIRD_COLORS, flip=flip,
                 shift=(lambda j: (-1 if flip else 1) if tilt and j < 5 else 0))

    card("card-birdie", "Birdie", "A wildlife finder", 48, 110, bird_still, birdie)


# --- Terminal, footer --------------------------------------------------------
def terminal():
    W, H = 160, 14
    cmd = "cat contact.json"
    x0 = 28
    typed = [len(cmd)] * 18 + list(range(len(cmd) + 1)) + [len(cmd)] * 4
    prompt = text_width("$ ")

    def bg(c):
        c.frame()
        for x, col in [(6, "pink"), (11, "gold"), (16, "lilac")]:
            c.rect(x, 5, 3, 3, col)
        c.text("$", x0, 3, "gold")

    def draw(c, f):
        shown = cmd[:typed[f]]
        c.text(shown, x0 + prompt, 3, "text")
        if typed[f] < len(cmd) or f // 5 % 2 == 0:
            c.rect(x0 + prompt + text_width(shown) + 2, 3, 3, 7, "lilac")

    scene("terminal", W, H, 4, len(typed), 100, bg, draw)


def footer():
    HAND = [
        ".....g.g.....",
        "...g.g.g.g...",
        "...g.g.g.g...",
        "...g.g.g.g...",
        "...g.g.g.g.g.",
        "...ggggggg.g.",
        "...gggggggg..",
        "...ggggggg...",
        "...ggggggg...",
        "....ggggg....",
        ".....ggg.....",
    ]
    message = "thanks for scrolling"
    W, H = text_width(message) + 32, 20
    waves = [0, 2, 3, 2, 0, -2, -3, -2, 0, 2, 3, 2, 0, -2, -1] + [0] * 11

    def bg(c):
        c.frame()
        c.text(message, 24, 6, "text")

    def draw(c, f):
        lean = waves[f]
        c.sprite(HAND, 7, 4, GOLD, shift=lambda j: round(lean * (10 - j) / 10))

    scene("footer", W, H, 3, len(waves), 110, bg, draw)


# --- README ------------------------------------------------------------------
CONTACT = {
    "name": "Sajal Kumar",
    "role": "Designer and builder",
    "email": "isajalkumar247@gmail.com",
    "website": "https://sajalkumar.com",
    "socials": {
        "x": "https://x.com/deanimatedmonk",
        "linkedin": "https://www.linkedin.com/in/sajalkumar247/",
        "github": "https://github.com/theanimatedmonk",
    },
}
SITE = "https://sajalkumar.com"
ROLES = [
    ("Product Designer", "Core craft: flows, systems, polish"),
    ("Design Engineer", "Ships prototypes and Figma plugins in code"),
    ("Creative Technologist", "Works across AI, hardware and 3D"),
    ("Interaction Designer (hardware)", "Physical-digital interfaces"),
    ("3D Artist", "Blender modelling, real-time scenes in Rive"),
    ("Founding Designer", "Founding member at Pulse, took it from 0 to a $1.5M seed"),
]
DIVIDER = '<p align="center">. . . . : : : * : : : . . . .</p>'


def ascii_roles():
    lines = []
    for i in range(0, len(ROLES), 3):
        labels = [label for label, _ in ROLES[i:i + 3]]
        rule = "  ".join("+" + "-" * (len(label) + 2) + "+" for label in labels)
        lines += [rule, "  ".join(f"| {label} |" for label in labels), rule]
    return "\n".join(lines)


def pic(name, alt, width=None, height=None, href=None):
    """Both theme versions of an image; GitHub's CSS hides the one that doesn't match its theme.

    <picture> follows the operating system's theme, so dark GitHub on a light OS got the
    light images. These tags follow GitHub's own setting instead. The CSS matches links
    ending in the tag: GitHub wraps a bare image in such a link, but leaves an image that
    is already linked alone, so a linked image needs the tag on its own href.
    """
    size = (f' width="{width}"' if width else "") + (f' height="{height}"' if height else "")
    out = []
    for theme in THEMES:
        tag = f"#gh-{theme}-mode-only"
        image = f'<img src="assets/{name}-{theme}.gif{tag}" alt="{alt}"{size}>'
        out.append(f'<a href="{href}{tag}">{image}</a>' if href else image)
    return "".join(out)


def link(label, url):
    return f'<a href="{url}">{label}</a>'


def card_cell(name, alt, url, title, brief, result, links):
    res = f"<p><b>Key result.</b> {result}</p>" if result else ""
    links_html = " · ".join(link(a, b) for a, b in links)
    return (
        f'<td width="50%" valign="top">{pic(name, alt, width="100%", href=url)}'
        f"<h3>{title}</h3><p>{brief}</p>{res}<p>{links_html}</p></td>"
    )


def readme():
    role_rows = "\n".join(f"| {label} | {why} |" for label, why in ROLES)
    impact = [
        ("Media.net", "Product Designer", "Oct 2025 – present", [
            "<b>+7%</b> PLU conversion from the default-launcher onboarding redesign",
            "<b>~11%</b> fewer D0/D1 uninstalls",
            "<b>+5%</b> search engagement",
        ]),
        ("Pulse", "Founding Product Designer and Researcher", "Feb 2025 – Sep 2025", [
            "<b>$1.5M</b> seed from Endiya Partners, led the design behind it",
            "<b>6</b> first enterprise customers",
            "<b>4x</b> lead-to-PoC conversion",
        ]),
        ("Titan Email (Directi)", "Product Designer", "May 2023 – Jan 2025", [
            "<b>+20%</b> retention from Link and File Tracking",
            "<b>100+</b> plan upgrades in a month from Email Designer",
            "<b>2x</b> user base, helped by partner migration flows",
            "NPS <b>50+</b> and <b>4.5+</b> app store ratings",
        ]),
        ("Trell, Titan, Zeta (Directi)", "Design Intern", "2022 – 2023", ["Web and mobile product work"]),
    ]
    rows = ""
    for company, role, years, items in impact:
        cells = "<br>".join(items)
        rows += f"<tr><td width=\"38%\" valign=\"top\"><b>{company}</b><br>{role}<br><sub>{years}</sub></td><td valign=\"top\">{cells}</td></tr>\n"

    disc = [
        ("disc-product", "A pixel cursor drags a card into place", "Product design", "Flows, systems, polish"),
        ("disc-engineering", "Pixel code brackets blinking like a caret", "Engineering", "Prototypes and Figma plugins, in code"),
        ("disc-hardware", "A pixel knob turning while an LED pulses", "Hardware interactions", "Physical-digital interfaces"),
        ("disc-art", "A pixel cube rotating", "Art (3D)", "Blender modelling, real-time scenes in Rive"),
    ]

    def disc_cell(d):
        return f'<td width="50%" align="center">{pic(d[0], d[1], width=64, height=64)}<br><b>{d[2]}</b><br><sub>{d[3]}</sub></td>'

    titan = card_cell(
        "card-titan", "A pixel envelope opening as a letter slides up", f"{SITE}/email-designer", "Titan Email (Directi)",
        "Designed Email Designer (a block-based email builder), Link and File Tracking (Titan's top monetisation feature) and partner migration flows for GoDaddy.",
        "+20% retention; 100+ upgrades in a month; migration flows helped 2x the user base. Work I contributed to: Titan's GoDaddy pilot saw +76% ARPU, +39% trial-to-paid, 9x premium upgrades and a 65% NPS improvement (Titan's case study of the four-month pilot, as of Aug 2025).",
        [("Email Designer case study", f"{SITE}/email-designer"), ("Tracking case study", f"{SITE}/link-and-file-tracking"),
         ("GoDaddy case study", "https://titan.email/go-daddy-partners-with-titan/"), ("Titan", "https://titan.email")],
    )
    pulse = card_cell(
        "card-pulse", "A pixel heartbeat line drawing across, ending in a pulsing dot", f"{SITE}/pulse", "Pulse",
        "AI-native product intelligence and feedback triaging, built around agentic workflows. Led end-to-end design as a founding member.",
        "$1.5M seed from Endiya Partners; 6 enterprise customers (Zluri, Yellow AI, BrowserStack, MoEngage, Whatfix); 4x lead-to-PoC.",
        [("Case study", f"{SITE}/pulse")],
    )
    tiny = card_cell(
        "card-tiny", "A pixel sprout swaying while a speech bubble says hi", f"{SITE}/tiny", "Tiny",
        "<b>A plant you can talk to.</b> A multimodal, interactive plant experience.", "",
        [("Case study", f"{SITE}/tiny")],
    )
    birdie = card_cell(
        "card-birdie", "A pixel bird hopping along a branch and tilting its head", "https://github.com/theanimatedmonk/birdie", "Birdie",
        "<b>A wildlife finder.</b> An ESP32 microphone on the balcony streams audio to BirdNET, and each bird it hears shows up as an animated Rive card, with a radar and a logbook.", "",
        [("Repo", "https://github.com/theanimatedmonk/birdie")],
    )
    social = " / ".join(link(label, CONTACT["socials"][key]) for key, label in [("x", "X"), ("linkedin", "LinkedIn"), ("github", "GitHub")])
    hero_alt = "Hi, I'm Sajal. Designer and builder. AI, hardware, software, canvas: all just mediums."
    return f"""<!-- Written by tools/build.py; edit that. -->
<p align="center">{pic("hero", hero_alt)}</p>

<p align="center"><b>Designer and builder.</b> AI, hardware, software, a blank canvas: they're all just mediums.<br><a href="{SITE}">sajalkumar.com</a></p>

{DIVIDER}

<h2 align="center">Roles I fit</h2>

```text
{ascii_roles()}
```

<details>
<summary>Why these roles</summary>

| Role | Why it fits |
|---|---|
{role_rows}

</details>

{DIVIDER}

<h2 align="center">About me</h2>

<table>
<tr>
<td width="62%" valign="middle">

> I take my notes from history and philosophy as much as from design.
>
> If you're not trying to create something beautiful, what's the point of being a designer?
>
> AI, hardware, software, a blank canvas: they're all just mediums.

</td>
<td width="38%" align="center" valign="middle">{pic("metro", "A pixel metro window with silhouettes swaying, and one looking up from a phone", width="100%")}</td>
</tr>
</table>

<h3 align="center">Past roles and impact</h3>

<table>
<tr><th>Role</th><th>Impact</th></tr>
{rows}</table>

<p align="center">~4 years of experience. B.Tech, IIT Patna (2019 – 2023). CEED All India Rank 105; JEE top 1 percentile.</p>

<h3 align="center">Disciplines</h3>

<table align="center">
<tr>{disc_cell(disc[0])}{disc_cell(disc[1])}</tr>
<tr>{disc_cell(disc[2])}{disc_cell(disc[3])}</tr>
</table>

{DIVIDER}

<h2 align="center">Work highlights</h2>

<table>
<tr>
{titan}
{pulse}
</tr>
</table>

{DIVIDER}

<h2 align="center">Solo side quests</h2>

<table>
<tr>
{tiny}
{birdie}
</tr>
</table>

<p align="center">More: <a href="{SITE}/product-experiments">utility tools and experiments</a>.</p>

{DIVIDER}

<h2 align="center">Contact</h2>

<p align="center">{pic("terminal", "A pixel terminal typing: cat contact.json")}</p>

```json
{json.dumps(CONTACT, indent=2)}
```

<p align="center">{social}</p>

{DIVIDER}

<p align="center">{pic("footer", "A waving pixel hand, and: thanks for scrolling")}</p>
"""


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    for old in list(ASSETS.glob("*.svg")) + list(ASSETS.glob("*.gif")):
        old.unlink()
    hero(); metro(); disciplines(); cards(); terminal(); footer()
    (ROOT / "README.md").write_text(readme())
    sizes = sorted((p.stat().st_size, p.name) for p in ASSETS.glob("*.gif"))
    print(f"{len(sizes)} gifs, largest {sizes[-1][1]} {sizes[-1][0] // 1024} KB, all {sum(s for s, _ in sizes) // 1024} KB")
