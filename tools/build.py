#!/usr/bin/env python3
"""Builds the profile README: every animated SVG in assets/, then README.md.

GitHub strips scripts and styles from READMEs, so each animation is a
self-contained SVG with CSS keyframes inside. Text is converted to outlines,
because GitHub's image policy blocks fonts inside SVGs (embedded ones too).

Each SVG's resting styles are its final frame and keyframes only describe how it
gets there, so turning animation off for reduced motion leaves the finished pose.

Fonts (SIL Open Font License): Instrument Serif, DM Sans, JetBrains Mono.

Needs: pip install fonttools uharfbuzz.  Run: python3 tools/build.py
"""

import json
import math
import random
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = Path(__file__).resolve().parent / "fonts"

THEMES = {
    "dark": dict(bg="#0E1330", bg2="#1A2050", line="#2C3370", text="#F4F2FF", muted="#A9ADD8", faint="#3A4186",
                 gold="#F2C14E", lilac="#B9A6FF", pink="#FF8FB8", win_a="#2B3078", win_b="#6A4596", shade="#090C24",
                 paper="#F4F2FF", paper_line="#B9A6FF"),
    "light": dict(bg="#F7F5FF", bg2="#E9E5FF", line="#D3CDF4", text="#171A45", muted="#5A5D8A", faint="#C8C2EE",
                  gold="#B27C00", lilac="#6A4ED2", pink="#CE3C78", win_a="#CFC8FF", win_b="#FFD3E2", shade="#272A63",
                  paper="#FFFFFF", paper_line="#A796EC"),
}
EASE = "cubic-bezier(.45,0,.55,1)"
BACK = "cubic-bezier(.34,1.56,.64,1)"
REDUCE = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def num(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Font:
    def __init__(self, file):
        self.tt = TTFont(FONTS / file)
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONTS / file))))

    def _shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": False})
        pen_x = 0
        out = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], pen_x + pos.x_offset))
            pen_x += pos.x_advance
        return out, pen_x

    def width(self, text, size):
        return self._shape(text)[1] * size / self.upm

    def letters(self, text, size, x=0, y=0):
        """One outline per glyph, with its pen position on the line."""
        s = size / self.upm
        glyphs, _ = self._shape(text)
        out = []
        for name, gx in glyphs:
            pen = SVGPathPen(self.gs, ntos=num)
            self.gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x + gx * s, y)))
            out.append((pen.getCommands(), x + gx * s))
        return out

    def path(self, text, size, x=0, y=0):
        return "".join(d for d, _ in self.letters(text, size, x, y))


SERIF = Font("serif.ttf")
ITALIC = Font("serif-i.ttf")
SANS = Font("sans-500.ttf")
BOLD = Font("sans-600.ttf")
MONO = Font("mono-500.ttf")

written = {}


def save(name, w, h, css, body):
    """Writes name-dark.svg / name-light.svg. css and body are functions of the theme."""
    for theme, t in THEMES.items():
        c, b = css(t), body(t)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" viewBox="0 0 {num(w)} {num(h)}">'
            f"<style>{c}{REDUCE}</style>{b}</svg>"
        )
        (ASSETS / f"{name}-{theme}.svg").write_text(svg)
    written[name] = (w, h)


def sparkle(cx, cy, r, fill):
    k = r * 0.16
    return (
        f'<path fill="{fill}" d="M{num(cx)} {num(cy - r)}Q{num(cx + k)} {num(cy - k)} {num(cx + r)} {num(cy)}'
        f'Q{num(cx + k)} {num(cy + k)} {num(cx)} {num(cy + r)}Q{num(cx - k)} {num(cy + k)} {num(cx - r)} {num(cy)}'
        f'Q{num(cx - k)} {num(cy - k)} {num(cx)} {num(cy - r)}Z"/>'
    )


# --- Hero --------------------------------------------------------------------
def hero():
    W, H = 900, 220
    rnd = random.Random(7)
    name = "Hi, I'm Sajal."
    size = 70
    name_w = SERIF.width(name, size)
    x0 = (W - name_w) / 2 - 16
    glyphs = SERIF.letters(name, size, x0, 92)
    step, start = 0.09, 0.25
    typed = start + len(glyphs) * step
    tag = "Designer and builder."
    tag_x = (W - SANS.width(tag, 22)) / 2
    mediums = ["AI", "Hardware", "Software", "Canvas", "...all just mediums."]
    cycle_at = typed + 0.9
    slot = 2.5
    star_x = x0 + name_w + 26

    # The caret hops letter to letter, then bows out.
    stops = []
    for i, (_, gx) in enumerate(glyphs):
        px = (start + i * step) / (typed + 0.3) * 100
        stops.append(f"{px:.2f}%{{transform:translateX({num(gx - x0)}px);opacity:1}}")
    caret_kf = (
        f"0%{{transform:translateX(0);opacity:1}}{''.join(stops)}"
        f"99%{{transform:translateX({num(name_w + 4)}px);opacity:1}}100%{{transform:translateX({num(name_w + 4)}px);opacity:0}}"
    )

    def css(t):
        return (
            "@keyframes show{from{opacity:0}}"
            f"@keyframes caret{{{caret_kf}}}"
            "@keyframes up{from{opacity:0;transform:translateY(12px)}}"
            "@keyframes medium{0%{opacity:0;transform:translateY(10px)}3%,17%{opacity:1;transform:none}"
            "20%,100%{opacity:0;transform:translateY(-10px)}}"
            "@keyframes last{0%{opacity:0;transform:translateY(10px)}3%,17%{opacity:1;transform:none}"
            "20%,100%{opacity:0;transform:translateY(-10px)}}"
            "@keyframes twinkle{0%,100%{opacity:.15}50%{opacity:.9}}"
            f"@keyframes blink{{0%,100%{{transform:scale(1);opacity:1}}50%{{transform:scale(.55);opacity:.45}}}}"
            f"@keyframes pop{{from{{transform:scale(0)}}}}"
            f".l{{animation:show .01s steps(1) both}}"
            f".c{{opacity:0;animation:caret {typed + 0.3:.2f}s steps(1,end) both}}"
            f".t{{animation:up .7s {EASE} {typed + 0.15:.2f}s both}}"
            f".m{{opacity:0;animation:medium {slot * 5}s {EASE} infinite both}}"
            f".m.e{{opacity:1;animation-name:last}}"
            f".s{{animation:twinkle 3.4s {EASE} infinite}}"
            f".b{{transform-origin:{num(star_x)}px 52px;animation:pop .5s {BACK} {typed:.2f}s both}}"
            f".bb{{transform-origin:{num(star_x)}px 52px;animation:blink 2.6s {EASE} {typed + 0.5:.2f}s infinite}}"
        )

    def body(t):
        out = [
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient></defs>',
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="24" fill="url(#g)" stroke="{t["line"]}"/>',
        ]
        for _ in range(26):
            x, y = rnd.uniform(24, W - 24), rnd.uniform(18, H - 18)
            if 150 < x < 750 and 40 < y < 195:
                continue
            c = rnd.choice([t["lilac"], t["gold"], t["pink"]])
            out.append(f'<circle class="s" style="animation-delay:{rnd.uniform(-3.4, 0):.2f}s" cx="{num(x)}" cy="{num(y)}" r="{rnd.choice([1.2, 1.6, 2])}" fill="{c}"/>')
        for i, (d, _) in enumerate(glyphs):
            out.append(f'<path class="l" style="animation-delay:{start + i * step:.2f}s" fill="{t["text"]}" d="{d}"/>')
        out.append(f'<rect class="c" x="{num(x0)}" y="40" width="3" height="58" rx="1.5" fill="{t["gold"]}"/>')
        out.append(f'<g class="b"><g class="bb">{sparkle(star_x, 52, 15, t["gold"])}</g></g>')
        out.append(f'<path class="t" fill="{t["muted"]}" d="{SANS.path(tag, 22, tag_x, 135)}"/>')
        for i, m in enumerate(mediums):
            mx = (W - ITALIC.width(m, 34)) / 2
            cls = "m e" if i == len(mediums) - 1 else "m"
            out.append(f'<path class="{cls}" style="animation-delay:{cycle_at + i * slot:.2f}s" fill="{t["gold"] if i < 4 else t["pink"]}" d="{ITALIC.path(m, 34, mx, 184)}"/>')
        return "".join(out)

    save("hero", W, H, css, body)


# --- Role pills --------------------------------------------------------------
ROLES = [
    ("product-designer", "Product Designer", "Core craft: flows, systems, polish"),
    ("design-engineer", "Design Engineer", "Ships prototypes and Figma plugins in code"),
    ("creative-technologist", "Creative Technologist", "Works across AI, hardware and 3D"),
    ("interaction-designer", "Interaction Designer (hardware)", "Physical-digital interfaces"),
    ("3d-artist", "3D Artist", "Blender modelling, real-time scenes in Rive"),
    ("founding-designer", "Founding Designer", "Founding member at Pulse, took it from 0 to a $1.5M seed"),
]


def pills():
    for i, (slug, label, _) in enumerate(ROLES):
        size = 15
        w = BOLD.width(label, size) + 50
        H = 44
        pw, ph = w - 8, H - 8
        accent = ["gold", "lilac", "pink"][i % 3]

        def css(t, w=w, i=i):
            return (
                "@keyframes pop{from{opacity:0;transform:scale(.6)}70%{opacity:1;transform:scale(1.06)}}"
                f".p{{transform-origin:{num(w / 2)}px 22px;animation:pop .5s {EASE} {i * 0.12:.2f}s both}}"
            )

        def body(t, label=label, accent=accent, pw=pw, ph=ph):
            return (
                f'<g class="p"><rect x="4.5" y="4.5" width="{num(pw - 1)}" height="{ph - 1}" rx="{(ph - 1) / 2}" fill="{t["bg"]}" stroke="{t["line"]}"/>'
                f'<circle cx="23" cy="22" r="4.5" fill="{t[accent]}"/>'
                f'<path fill="{t["text"]}" d="{BOLD.path(label, size, 35, 27.2)}"/></g>'
            )

        save(f"role-{slug}", w, H, css, body)


# --- Metro -------------------------------------------------------------------
def metro():
    W, H = 320, 220
    rnd = random.Random(3)

    def css(t):
        return (
            "@keyframes pass{to{transform:translateX(-240px)}}"
            f"@keyframes sway{{0%,100%{{transform:rotate(-1.4deg)}}50%{{transform:rotate(1.4deg)}}}}"
            "@keyframes look{0%,62%{transform:rotate(15deg)}70%,88%{transform:rotate(-3deg)}96%,100%{transform:rotate(15deg)}}"
            "@keyframes glow{0%,62%{opacity:1}70%,88%{opacity:.35}96%,100%{opacity:1}}"
            ".city{animation:pass 7s linear infinite}"
            f".a{{transform-origin:78px 215px;animation:sway 3.6s {EASE} infinite}}"
            f".b{{transform-origin:160px 215px;animation:sway 3.6s {EASE} -1.1s infinite}}"
            f".c{{transform-origin:244px 215px;animation:sway 3.6s {EASE} -2.2s infinite}}"
            f".h{{transform:rotate(-3deg);transform-origin:160px 118px;animation:look 6s {EASE} infinite}}"
            f".g{{opacity:.35;animation:glow 6s {EASE} infinite}}"
        )

    def figure(cx, top, t, inner=""):
        return (
            f'<path fill="{t["shade"]}" d="M{cx - 34} 220V{top + 66}Q{cx - 34} {top + 44} {cx - 12} {top + 42}H{cx + 12}Q{cx + 34} {top + 44} {cx + 34} {top + 66}V220Z"/>'
            + inner
        )

    def body(t):
        blocks = []
        for k in range(2):
            x = 0
            r = random.Random(11)
            while x < 240:
                w, h = r.randint(26, 46), r.randint(34, 84)
                bx = x + k * 240
                blocks.append(f'<rect x="{bx}" y="{150 - h}" width="{w}" height="{h + 40}" fill="{t["shade"]}" opacity=".22"/>')
                for _ in range(2):
                    wx, wy = bx + r.randint(4, w - 9), 150 - h + r.randint(6, h - 8)
                    blocks.append(f'<rect x="{wx}" y="{wy}" width="4" height="5" fill="{t["gold"]}" opacity=".85"/>')
                x += w + r.randint(2, 8)
        rail = "".join(
            f'<path d="M{x} 30V46" stroke="{t["shade"]}" stroke-width="2.5"/><circle cx="{x}" cy="53" r="7" fill="none" stroke="{t["shade"]}" stroke-width="2.5"/>'
            for x in (78, 160, 244)
        )
        phone = (
            f'<rect class="g" x="150" y="152" width="20" height="26" rx="5" fill="{t["gold"]}" opacity=".35"/>'
            f'<rect x="155" y="156" width="10" height="17" rx="2.500" fill="{t["gold"]}"/>'
        )
        return (
            f'<defs><linearGradient id="w" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["win_a"]}"/><stop offset="1" stop-color="{t["win_b"]}"/></linearGradient>'
            f'<clipPath id="c"><rect x="14" y="14" width="292" height="192" rx="24"/></clipPath></defs>'
            f'<rect x=".5" y=".5" width="319" height="219" rx="24" fill="{t["bg"]}" stroke="{t["line"]}"/>'
            f'<g clip-path="url(#c)"><rect x="14" y="14" width="292" height="192" fill="url(#w)"/>'
            f'<g class="city">{"".join(blocks)}</g>'
            f'<path d="M14 30H306" stroke="{t["shade"]}" stroke-width="3"/>{rail}'
            f'<g class="a">{figure(78, 76, t, f"""<circle cx="78" cy="98" r="18" fill="{t["shade"]}"/>""")}</g>'
            f'<g class="c">{figure(244, 70, t, f"""<circle cx="244" cy="92" r="18" fill="{t["shade"]}"/>""")}</g>'
            f'<g class="b">{figure(160, 88, t, f"""<g class="h"><circle cx="160" cy="108" r="18" fill="{t["shade"]}"/></g>""")}{phone}</g></g>'
        )

    save("metro", W, H, css, body)


# --- Counters ----------------------------------------------------------------
COUNTERS = {
    "plu": [f"+{i}%" for i in range(8)],
    "uninstalls": [f"~{i}%" for i in range(12)],
    "search": [f"+{i}%" for i in range(6)],
    "seed": [f"${i / 10:.1f}M" for i in range(16)],
    "customers": [str(i) for i in range(7)],
    "poc": [f"{i}x" for i in range(5)],
    "retention": [f"+{i}%" for i in range(0, 21, 2)],
    "upgrades": [str(i) for i in range(0, 100, 10)] + ["100+"],
    "userbase": [f"{i}x" for i in range(3)],
    "nps": [str(i) for i in range(0, 50, 5)] + ["50+"],
    "rating": [f"{i / 2:.1f}" for i in range(9)] + ["4.5+"],
}


def counters():
    H = 24
    for name, frames in COUNTERS.items():
        w = max(BOLD.width(s, 17) for s in frames) + 2
        n = len(frames)

        def css(t, n=n):
            end = -(n - 1) * H
            return (
                f"@keyframes run{{from{{transform:translateY(0)}}}}"
                f".r{{transform:translateY({end}px);animation:run 1.4s steps({n - 1},end) .3s both}}"
            )

        def body(t, frames=frames):
            d = "".join(BOLD.path(s, 17, 1, 18 + i * H) for i, s in enumerate(frames))
            return f'<g class="r"><path fill="{t["gold"]}" d="{d}"/></g>'

        save(f"counter-{name}", w, H, css, body)


# --- Discipline icons --------------------------------------------------------
def disciplines():
    S = 48

    def product_css(t):
        return (
            "@keyframes drag{0%,12%{transform:translate(-13px,-12px)}55%,100%{transform:none}}"
            "@keyframes snap{0%,55%{transform:scale(1)}62%{transform:scale(.92)}70%,100%{transform:scale(1)}}"
            "@keyframes hand{0%,12%{transform:translate(-13px,-12px)}55%{transform:none}70%,88%{transform:translate(9px,8px)}100%{transform:translate(-13px,-12px)}}"
            f".k{{animation:drag 3.4s {EASE} infinite}}.kk{{transform-origin:30px 30px;animation:snap 3.4s {EASE} infinite}}"
            f".u{{transform:translate(9px,8px);animation:hand 3.4s {EASE} infinite}}"
        )

    def product_body(t):
        return (
            f'<rect x="19" y="20" width="23" height="20" rx="4" fill="none" stroke="{t["faint"]}" stroke-width="1.6" stroke-dasharray="3 3"/>'
            f'<g class="k"><g class="kk"><rect x="19" y="20" width="23" height="20" rx="4" fill="{t["lilac"]}"/>'
            f'<rect x="23" y="25" width="10" height="2.4" rx="1.2" fill="{t["bg"]}"/><rect x="23" y="30" width="15" height="2.4" rx="1.2" fill="{t["bg"]}"/></g></g>'
            f'<g class="u"><path d="M28 28l0 15 4-3.6 2.8 6 3-1.4-2.8-5.8 5.2-.4z" fill="{t["gold"]}" stroke="{t["bg"]}" stroke-width="1.2" stroke-linejoin="round"/></g>'
        )

    save("disc-product", S, S, product_css, product_body)

    def code_css(t):
        return "@keyframes caret{0%,49%{opacity:1}50%,100%{opacity:.15}}.s{animation:caret 1.4s steps(1,end) infinite}"

    def code_body(t):
        common = 'fill="none" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"'
        return (
            f'<path {common} stroke="{t["lilac"]}" d="M16 14 6 24l10 10"/>'
            f'<path {common} stroke="{t["lilac"]}" d="M32 14l10 10-10 10"/>'
            f'<path class="s" {common} stroke="{t["gold"]}" d="M27.500 10 20.500 38"/>'
        )

    save("disc-engineering", S, S, code_css, code_body)

    def knob_css(t):
        return (
            f"@keyframes turn{{0%,100%{{transform:rotate(-110deg)}}50%{{transform:rotate(110deg)}}}}"
            f"@keyframes led{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}"
            f".n{{transform-origin:24px 28px;animation:turn 3s {EASE} infinite}}.d{{animation:led 3s {EASE} infinite}}"
        )

    def knob_body(t):
        return (
            f'<circle class="d" cx="24" cy="6" r="6" fill="{t["pink"]}" opacity=".35"/><circle class="d" cx="24" cy="6" r="3" fill="{t["pink"]}"/>'
            f'<circle cx="24" cy="28" r="17" fill="{t["bg2"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
            f'<g class="n"><circle cx="24" cy="28" r="12.500" fill="{t["lilac"]}"/><rect x="22.500" y="17.500" width="3" height="8" rx="1.5" fill="{t["bg"]}"/></g>'
        )

    save("disc-hardware", S, S, knob_css, knob_body)

    frames = 16
    def cube_css(t):
        on = 100 / frames
        return (
            f"@keyframes f{{0%,{on:.2f}%{{opacity:1}}{on + 0.01:.2f}%,100%{{opacity:0}}}}"
            ".f{opacity:0;animation:f 3.2s steps(1,end) infinite}.f0{opacity:1}"
        )

    def cube_body(t):
        out = []
        r = 15.5
        for i in range(frames):
            a = math.radians(i / frames * 90 + 45)  # starts three-quarter on, so the still pose reads as a cube
            def corner(k, y):
                ang = a + k * math.pi / 2 - math.pi / 4
                return 24 + r * math.cos(ang), y + r * 0.48 * math.sin(ang)
            top, bot = [corner(k, 14) for k in range(4)], [corner(k, 33) for k in range(4)]
            faces = []
            for k in range(4):
                m = (k + 0.5) * math.pi / 2 - math.pi / 4 + a
                if math.sin(m) > 0:  # faces the viewer
                    j = (k + 1) % 4
                    pts = [top[k], top[j], bot[j], bot[k]]
                    shade = t["lilac"] if math.cos(m) > 0 else t["pink"]
                    faces.append((pts, shade))
            poly = lambda pts, c: f'<polygon points="{" ".join(num(x) + "," + num(y) for x, y in pts)}" fill="{c}" stroke="{t["bg"]}" stroke-width=".8" stroke-linejoin="round"/>'
            body = "".join(poly(p, c) for p, c in faces) + poly(top, t["gold"])
            out.append(f'<g class="f f{i}" style="animation-delay:{-(frames - i) / frames * 3.2:.2f}s">{body}</g>')
        return "".join(out)

    save("disc-art", S, S, cube_css, cube_body)


# --- Cards -------------------------------------------------------------------
def card(name, title, sub, css_extra, art):
    W, H = 420, 260

    def css(t):
        return (
            f"@keyframes breathe{{0%,100%{{opacity:.6}}50%{{opacity:1}}}}.glow{{animation:breathe 3s {EASE} infinite}}"
            + css_extra(t)
        )

    def body(t):
        return (
            f'<defs><radialGradient id="o"><stop offset="0" stop-color="{t["lilac"]}" stop-opacity=".34"/><stop offset="1" stop-color="{t["lilac"]}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="{t["bg"]}" stroke="{t["line"]}"/>'
            f'<ellipse class="glow" cx="210" cy="96" rx="190" ry="110" fill="url(#o)"/>'
            + art(t)
            + f'<path fill="{t["text"]}" d="{SERIF.path(title, 32, 28, 218)}"/>'
            f'<path fill="{t["muted"]}" d="{SANS.path(sub, 14, 28, 241)}"/>'
        )

    save(name, W, H, css, body)


def cards():
    def env_css(t):
        d = f"4s {EASE} infinite"
        return (
            "@keyframes closed{0%,6%{transform:scaleY(1)}16%,84%{transform:scaleY(0)}94%,100%{transform:scaleY(1)}}"
            "@keyframes open{0%,14%{transform:scaleY(0)}24%,76%{transform:scaleY(1)}86%,100%{transform:scaleY(0)}}"
            "@keyframes letter{0%,20%{transform:translateY(0)}44%,70%{transform:translateY(-54px)}84%,100%{transform:translateY(0)}}"
            "@keyframes ping{0%,40%{transform:scale(0)}50%,68%{transform:scale(1)}76%,100%{transform:scale(0)}}"
            f".fc{{transform:scaleY(0);transform-origin:210px 72px;animation:closed {d}}}"
            f".fo{{transform-origin:210px 72px;animation:open {d}}}"
            f".lt{{transform:translateY(-54px);animation:letter {d}}}"
            f".pg{{transform-origin:262px 28px;animation:ping {d}}}"
        )

    def env_art(t):
        lines = "".join(f'<rect x="166" y="{y}" width="{w}" height="4" rx="2" fill="{t["paper_line"]}"/>' for y, w in [(90, 88), (101, 64), (112, 76)])
        return (
            f'<rect x="136" y="72" width="148" height="94" rx="8" fill="{t["bg2"]}"/>'
            f'<path class="fo" d="M136 72H284L210 24Z" fill="{t["faint"]}"/>'
            f'<g class="lt"><rect x="152" y="80" width="116" height="84" rx="6" fill="{t["paper"]}"/>{lines}</g>'
            f'<path d="M136 72L210 124 284 72V158a8 8 0 0 1-8 8H144a8 8 0 0 1-8-8Z" fill="{t["lilac"]}"/>'
            f'<path class="fc" d="M136 72H284L210 124Z" fill="{t["pink"]}"/>'
            f'<g class="pg"><circle cx="262" cy="28" r="9" fill="{t["gold"]}"/><path d="M258 28l3 3 5-6" fill="none" stroke="{t["bg"]}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></g>'
        )

    card("card-titan", "Titan Email", "Email Designer, tracking, partner migration", env_css, env_art)

    def beat_css(t):
        d = f"3.6s {EASE} infinite"
        return (
            "@keyframes draw{0%{stroke-dashoffset:1;opacity:1}55%,84%{stroke-dashoffset:0;opacity:1}96%,100%{stroke-dashoffset:0;opacity:0}}"
            "@keyframes dot{0%,50%{transform:scale(0)}58%{transform:scale(1.3)}66%{transform:scale(1)}74%{transform:scale(1.3)}84%{transform:scale(1)}96%,100%{transform:scale(0)}}"
            "@keyframes ring{0%,54%{transform:scale(.4);opacity:0}58%{opacity:.7}84%,100%{transform:scale(2.6);opacity:0}}"
            f".ln{{stroke-dasharray:1;animation:draw {d}}}"
            f".dt{{transform-origin:356px 104px;animation:dot {d}}}"
            f".rg{{opacity:0;transform-origin:356px 104px;animation:ring {d}}}"
        )

    def beat_art(t):
        grid = "".join(f'<circle cx="{x}" cy="{y}" r="1.1" fill="{t["faint"]}"/>' for x in range(54, 380, 26) for y in range(44, 170, 26))
        return (
            grid
            + f'<path class="ln" pathLength="1" d="M56 104H150L166 104 182 58 204 156 222 84 234 104H356" fill="none" stroke="{t["pink"]}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle class="rg" cx="356" cy="104" r="8" fill="none" stroke="{t["gold"]}" stroke-width="2"/>'
            f'<circle class="dt" cx="356" cy="104" r="7" fill="{t["gold"]}"/>'
        )

    card("card-pulse", "Pulse", "AI-native product intelligence", beat_css, beat_art)

    def sprout_css(t):
        return (
            f"@keyframes sw{{0%,100%{{transform:rotate(-6deg)}}50%{{transform:rotate(6deg)}}}}"
            "@keyframes hi{0%,18%{transform:scale(0)}26%{transform:scale(1.1)}30%,74%{transform:scale(1)}82%,100%{transform:scale(0)}}"
            f"@keyframes bl{{0%,92%,100%{{transform:scaleY(1)}}96%{{transform:scaleY(.1)}}}}"
            f".sp{{transform-origin:210px 126px;animation:sw 3.2s {EASE} infinite}}"
            f".bb{{transform-origin:244px 72px;animation:hi 4s {EASE} infinite}}"
            f".ey{{transform-origin:210px 150px;animation:bl 4s linear infinite}}"
        )

    def sprout_art(t):
        hi = BOLD.path("hi", 19, 266, 58)
        return (
            f'<g class="sp"><path d="M210 128C210 104 206 90 210 66" fill="none" stroke="{t["gold"]}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M210 72C192 72 176 62 170 42 192 40 208 52 210 72Z" fill="{t["lilac"]}"/>'
            f'<path d="M210 90C226 90 240 80 248 62 226 60 212 72 210 90Z" fill="{t["pink"]}"/></g>'
            f'<path d="M172 136H248L240 180a7 7 0 0 1-7 6H187a7 7 0 0 1-7-6Z" fill="{t["bg2"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
            f'<rect x="166" y="124" width="88" height="16" rx="6" fill="{t["faint"]}"/>'
            f'<g class="ey"><circle cx="198" cy="154" r="3" fill="{t["text"]}"/><circle cx="222" cy="154" r="3" fill="{t["text"]}"/></g>'
            f'<path d="M203 163q7 7 14 0" fill="none" stroke="{t["text"]}" stroke-width="2.2" stroke-linecap="round"/>'
            f'<g class="bb"><path d="M262 34H292a12 12 0 0 1 12 12V56a12 12 0 0 1-12 12H266L250 80 254 64A12 12 0 0 1 250 56V46a12 12 0 0 1 12-12Z" fill="{t["paper"]}" stroke="{t["line"]}"/>'
            f'<path fill="{t["bg"] if t["paper"] != "#FFFFFF" else t["text"]}" d="{hi}"/></g>'
        )

    card("card-tiny", "Tiny", "A plant you can talk to", sprout_css, sprout_art)

    def bird_css(t):
        d = f"4s {EASE} infinite"
        hop_right = "10%{transform:translateX(-46px)}16%{transform:translate(0,-24px)}22%{transform:translateX(46px)}"
        return (
            "@keyframes mv{0%,10%{transform:translate(-46px,0)}16%{transform:translate(0,-26px)}22%,50%{transform:translate(46px,0)}"
            "56%{transform:translate(0,-26px)}62%,100%{transform:translate(-46px,0)}}"
            "@keyframes fl{0%,45%{transform:scaleX(1)}49%,92%{transform:scaleX(-1)}96%,100%{transform:scaleX(1)}}"
            "@keyframes tl{0%,26%{transform:rotate(0)}30%,40%{transform:rotate(-22deg)}44%,66%{transform:rotate(0)}70%,82%{transform:rotate(16deg)}86%,100%{transform:rotate(0)}}"
            f".mv{{transform:translate(-46px,0);animation:mv {d}}}"
            f".fl{{transform-origin:210px 110px;animation:fl {d}}}"
            f".tl{{transform-origin:232px 88px;animation:tl {d}}}"
        )

    def bird_art(t):
        leaf = lambda x, y, r: f'<path transform="rotate({r} {x} {y})" d="M{x} {y}c10-12 26-12 34 0-10 10-24 10-34 0Z" fill="{t["lilac"]}" opacity=".85"/>'
        return (
            f'<path d="M42 164C120 146 280 142 380 158" fill="none" stroke="{t["gold"]}" stroke-width="7" stroke-linecap="round"/>'
            + leaf(70, 156, -34) + leaf(338, 152, 26) + leaf(300, 150, -52)
            + f'<g class="mv"><g class="fl">'
            f'<path d="M196 136v14M216 136v14" stroke="{t["gold"]}" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M180 112 146 98 158 124Z" fill="{t["lilac"]}"/>'
            f'<ellipse cx="206" cy="116" rx="33" ry="26" fill="{t["pink"]}"/>'
            f'<path d="M180 108c10-8 30-6 36 6-8 12-28 14-36-6Z" fill="{t["lilac"]}"/>'
            f'<g class="tl"><circle cx="232" cy="90" r="19" fill="{t["pink"]}"/>'
            f'<circle cx="238" cy="86" r="4.5" fill="{t["paper"]}"/><circle cx="239" cy="86" r="2.3" fill="{t["shade"]}"/>'
            f'<path d="M250 86 268 92 250 98Z" fill="{t["gold"]}"/></g></g></g>'
        )

    card("card-birdie", "Birdie", "A wildlife finder", bird_css, bird_art)


# --- Terminal, divider, footer -----------------------------------------------
def terminal():
    W, H = 640, 54
    cmd = "cat contact.json"
    prompt_w = MONO.width("$ ", 16)
    x0 = 92
    glyphs = MONO.letters(cmd, 16, x0 + prompt_w, 33)
    step, start = 0.075, 0.5
    end = start + len(glyphs) * step
    cw = MONO.width("a", 16)

    def css(t):
        stops = "".join(
            f"{(start + i * step) / end * 100:.2f}%{{transform:translateX({num(i * cw)}px)}}" for i in range(len(glyphs))
        )
        return (
            "@keyframes show{from{opacity:0}}"
            f"@keyframes hop{{0%{{transform:translateX(0)}}{stops}100%{{transform:translateX({num(len(glyphs) * cw)}px)}}}}"
            "@keyframes blink{50%{opacity:0}}"
            f".l{{animation:show .01s steps(1) both}}"
            f".c{{transform:translateX({num(len(glyphs) * cw)}px);animation:hop {end:.2f}s steps(1,end) both}}"
            f".cc{{animation:blink 1.1s steps(1,end) {end:.2f}s infinite}}"
        )

    def body(t):
        dots = "".join(f'<circle cx="{x}" cy="27" r="5" fill="{t[c]}"/>' for x, c in [(24, "pink"), (42, "gold"), (60, "lilac")])
        letters = "".join(f'<path class="l" style="animation-delay:{start + i * step:.3f}s" fill="{t["text"]}" d="{d}"/>' for i, (d, _) in enumerate(glyphs))
        return (
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{t["bg"]}" stroke="{t["line"]}"/>{dots}'
            f'<path fill="{t["gold"]}" d="{MONO.path("$", 16, x0, 33)}"/>{letters}'
            f'<g class="c"><rect class="cc" x="{num(x0 + prompt_w + 1)}" y="19" width="9" height="18" rx="1" fill="{t["lilac"]}"/></g>'
        )

    save("terminal", W, H, css, body)


def divider():
    W, H = 900, 24
    rnd = random.Random(5)

    def css(t):
        return f"@keyframes tw{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}.d{{animation:tw 3s {EASE} infinite}}.s{{transform-origin:450px 12px;animation:tw 3s {EASE} infinite}}"

    def body(t):
        out = []
        for i in range(-28, 29):
            if abs(i) < 2:
                continue
            x = 450 + i * 15
            c = rnd.choice([t["faint"], t["lilac"], t["faint"], t["pink"], t["gold"]])
            fade = 1 - abs(i) / 34
            out.append(f'<g opacity="{fade:.2f}"><circle class="d" style="animation-delay:{rnd.uniform(-3, 0):.2f}s" cx="{x}" cy="12" r="1.8" fill="{c}"/></g>')
        out.append(f'<g class="s">{sparkle(450, 12, 9, t["gold"])}</g>')
        return "".join(out)

    save("divider", W, H, css, body)


def footer():
    text = "thanks for scrolling"
    tw = ITALIC.width(text, 30)
    W, H = tw + 90, 84

    def css(t):
        return (
            "@keyframes wave{0%,55%,100%{transform:rotate(0)}10%{transform:rotate(16deg)}20%{transform:rotate(-9deg)}"
            "30%{transform:rotate(14deg)}40%{transform:rotate(-5deg)}}"
            f".w{{transform-origin:33px 62px;animation:wave 2.8s {EASE} infinite}}"
        )

    def body(t):
        fingers = "".join(
            f'<path d="M{x} 42L{x2} {y}" stroke="{t["gold"]}" stroke-width="7.5" stroke-linecap="round"/>'
            for x, x2, y in [(22, 17, 24), (29, 27, 15), (36, 37, 16), (43, 47, 25)]
        )
        return (
            f'<g class="w">{fingers}<path d="M18 46L9 36" stroke="{t["gold"]}" stroke-width="7.5" stroke-linecap="round"/>'
            f'<path d="M17 38H48V50Q48 67 33 67 17 67 17 50Z" fill="{t["gold"]}"/></g>'
            f'<path fill="{t["text"]}" d="{ITALIC.path(text, 30, 72, 52)}"/>'
        )

    save("footer", W, H, css, body)


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
ICONS = {
    "x": "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "github": "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12",
}


def icons():
    for name, d in ICONS.items():
        def body(t, d=d):
            return f'<svg x="4" y="4" width="20" height="20" viewBox="0 0 24 24"><path fill="{t["text"]}" d="{d}"/></svg>'
        save(f"icon-{name}", 28, 28, lambda t: "", body)


def pic(name, alt, width=None, height=None, extra=""):
    size = (f' width="{width}"' if width else "") + (f' height="{height}"' if height else "")
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">'
        f'<img src="assets/{name}-dark.svg" alt="{alt}"{size}{extra}></picture>'
    )


def count(name, alt):
    w, h = written[f"counter-{name}"]
    return pic(f"counter-{name}", alt, width=round(w * 0.82), height=round(h * 0.82), extra=' align="absmiddle"')


def icon_pic(name, label):
    return pic(f"icon-{name}", label, width=28, height=28, extra=' align="absmiddle"')


def divider_md():
    return f'<p align="center">{pic("divider", "A twinkling dotted divider", width="100%")}</p>'


def link(label, url):
    return f'<a href="{url}">{label}</a>'


def card_cell(name, alt, url, title, brief, result, links):
    res = f"<p><b>Key result.</b> {result}</p>" if result else ""
    links_html = " · ".join(link(a, b) for a, b in links)
    return (
        f'<td width="50%" valign="top"><a href="{url}">{pic(name, alt, width="100%")}</a>'
        f"<h3>{title}</h3><p>{brief}</p>{res}<p>{links_html}</p></td>"
    )


def readme():
    role_row = " ".join(pic(f"role-{s}", l, height=44) for s, l, _ in ROLES)
    role_rows = "\n".join(f"| {l} | {w} |" for _, l, w in ROLES)
    impact = [
        ("Media.net", "Product Designer", "Oct 2025 – present", [
            (count("plu", "+7%"), "PLU conversion from the default-launcher onboarding redesign"),
            (count("uninstalls", "~11%"), "fewer D0/D1 uninstalls"),
            (count("search", "+5%"), "search engagement"),
        ]),
        ("Pulse", "Founding Product Designer and Researcher", "Feb 2025 – Sep 2025", [
            (count("seed", "$1.5M"), "seed from Endiya Partners, led the design behind it"),
            (count("customers", "6"), "first enterprise customers"),
            (count("poc", "4x"), "lead-to-PoC conversion"),
        ]),
        ("Titan Email (Directi)", "Product Designer", "May 2023 – Jan 2025", [
            (count("retention", "+20%"), "retention from Link and File Tracking"),
            (count("upgrades", "100+"), "plan upgrades in a month from Email Designer"),
            (count("userbase", "2x"), "user base, helped by partner migration flows"),
            (f'NPS {count("nps", "50+")}', f'and {count("rating", "4.5+")} app store ratings'),
        ]),
        ("Trell, Titan, Zeta (Directi)", "Design Intern", "2022 – 2023", [("", "Web and mobile product work")]),
    ]
    rows = ""
    for company, role, years, items in impact:
        cells = "<br>".join(f"{a} {b}".strip() for a, b in items)
        rows += f"<tr><td width=\"38%\" valign=\"top\"><b>{company}</b><br>{role}<br><sub>{years}</sub></td><td valign=\"top\">{cells}</td></tr>\n"

    disc = [
        ("disc-product", "A cursor drags a card into place", "Product design", "Flows, systems, polish"),
        ("disc-engineering", "Code brackets blinking like a caret", "Engineering", "Prototypes and Figma plugins, in code"),
        ("disc-hardware", "A knob turning while an LED pulses", "Hardware interactions", "Physical-digital interfaces"),
        ("disc-art", "A low-poly cube rotating", "Art (3D)", "Blender modelling, real-time scenes in Rive"),
    ]
    def disc_cell(d):
        return f'<td width="50%" align="center">{pic(d[0], d[1], width=48, height=48)}<br><b>{d[2]}</b><br><sub>{d[3]}</sub></td>'

    titan = card_cell(
        "card-titan", "An envelope opening as a letter slides up", f"{SITE}/email-designer", "Titan Email (Directi)",
        "Designed Email Designer (a block-based email builder), Link and File Tracking (Titan's top monetisation feature) and partner migration flows for GoDaddy.",
        "+20% retention; 100+ upgrades in a month; migration flows helped 2x the user base. Work I contributed to: Titan's GoDaddy pilot saw +76% ARPU, +39% trial-to-paid, 9x premium upgrades and a 65% NPS improvement (Titan's case study of the four-month pilot, as of Aug 2025).",
        [("Email Designer case study", f"{SITE}/email-designer"), ("Tracking case study", f"{SITE}/link-and-file-tracking"),
         ("GoDaddy case study", "https://titan.email/go-daddy-partners-with-titan/"), ("Titan", "https://titan.email")],
    )
    pulse = card_cell(
        "card-pulse", "A heartbeat line drawing across, ending in a pulsing dot", f"{SITE}/pulse", "Pulse",
        "AI-native product intelligence and feedback triaging, built around agentic workflows. Led end-to-end design as a founding member.",
        "$1.5M seed from Endiya Partners; 6 enterprise customers (Zluri, Yellow AI, BrowserStack, MoEngage, Whatfix); 4x lead-to-PoC.",
        [("Case study", f"{SITE}/pulse")],
    )
    tiny = card_cell(
        "card-tiny", "A sprout swaying while a speech bubble says hi", f"{SITE}/tiny", "Tiny",
        "<b>A plant you can talk to.</b> A multimodal, interactive plant experience.", "",
        [("Case study", f"{SITE}/tiny")],
    )
    birdie = card_cell(
        "card-birdie", "A small bird hopping along a branch and tilting its head", "https://github.com/theanimatedmonk/birdie", "Birdie",
        "<b>A wildlife finder.</b> An ESP32 microphone on the balcony streams audio to BirdNET, and each bird it hears shows up as an animated Rive card, with a radar and a logbook.", "",
        [("Repo", "https://github.com/theanimatedmonk/birdie")],
    )
    plain_impact = (
        "- **Media.net:** +7% PLU conversion from the default-launcher onboarding redesign; ~11% fewer D0/D1 uninstalls; +5% search engagement\n"
        "- **Pulse:** led design behind a $1.5M seed from Endiya Partners; first 6 enterprise customers; 4x lead-to-PoC conversion\n"
        "- **Titan Email:** +20% retention from Link and File Tracking; 100+ plan upgrades in a month from Email Designer; partner migration flows that helped 2x the user base; NPS 50+ and 4.5+ app store ratings"
    )
    social = "&nbsp;&nbsp;".join(
        f'<a href="{CONTACT["socials"][k]}">{icon_pic(k, label)}</a> <a href="{CONTACT["socials"][k]}">{label}</a>'
        for k, label in [("x", "X"), ("linkedin", "LinkedIn"), ("github", "GitHub")]
    )
    hero_alt = "Hi, I'm Sajal. Designer and builder. AI, hardware, software, canvas: all just mediums."
    return f"""<!-- Written by tools/build.py; edit that. -->
<p align="center">{pic("hero", hero_alt, width="100%")}</p>

<p align="center"><b>Designer and builder.</b> AI, hardware, software, a blank canvas: they're all just mediums.<br><a href="{SITE}">sajalkumar.com</a></p>

{divider_md()}

<h2 align="center">Roles I fit</h2>

<p align="center">{role_row}</p>

<details>
<summary>Why these roles</summary>

| Role | Why it fits |
|---|---|
{role_rows}

</details>

{divider_md()}

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
<td width="38%" align="center" valign="middle">{pic("metro", "A metro window with silhouettes swaying, and one looking up from a phone", width="100%")}</td>
</tr>
</table>

<h3 align="center">Past roles and impact</h3>

<table>
<tr><th>Role</th><th>Impact</th></tr>
{rows}</table>

<p align="center">~4 years of experience. B.Tech, IIT Patna (2019 – 2023). CEED All India Rank 105; JEE top 1 percentile.</p>

<details>
<summary>Impact as plain text</summary>

{plain_impact}

</details>

<h3 align="center">Disciplines</h3>

<table align="center">
<tr>{disc_cell(disc[0])}{disc_cell(disc[1])}</tr>
<tr>{disc_cell(disc[2])}{disc_cell(disc[3])}</tr>
</table>

{divider_md()}

<h2 align="center">Work highlights</h2>

<table>
<tr>
{titan}
{pulse}
</tr>
</table>

{divider_md()}

<h2 align="center">Solo side quests</h2>

<table>
<tr>
{tiny}
{birdie}
</tr>
</table>

<p align="center">More: <a href="{SITE}/product-experiments">utility tools and experiments</a>.</p>

{divider_md()}

<h2 align="center">Contact</h2>

<p align="center">{pic("terminal", "A terminal typing: cat contact.json", width="100%")}</p>

```json
{json.dumps(CONTACT, indent=2)}
```

<p align="center">{social}</p>

{divider_md()}

<p align="center">{pic("footer", "A waving hand, and: thanks for scrolling")}</p>
"""


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    hero(); pills(); metro(); counters(); disciplines(); cards(); terminal(); divider(); footer(); icons()
    (ROOT / "README.md").write_text(readme())
    sizes = sorted((p.stat().st_size, p.name) for p in ASSETS.glob("*.svg"))
    print(f"{len(sizes)} svgs, largest {sizes[-1][1]} {sizes[-1][0] // 1024} KB, "
          f"one theme {sum(s for s, n in sizes if '-dark' in n) // 1024} KB, all {sum(s for s, _ in sizes) // 1024} KB")
