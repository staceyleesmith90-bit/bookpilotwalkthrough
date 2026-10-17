"""Motion graphics in an app / UI style: pills that pop in, an app window that drops in, a multi-track
timeline, growing bars, a dial, a toggle and a button with a cursor click. Each one is drawn in the
brand's colours and fonts, and says which sound goes with each moment (the "motion" sound kit).

In a plan, on any beat:  "do": ["mg:pills"],  "mg": {"labels": ["cuts", "captions", "sfx"]}
Kinds and their settings (all optional):
  pills     labels[], tilt (degrees, default 8)
  window    image (file or clip.mp4@2.5), title, status ("agent is editing")
  timeline  tracks[] (default video/captions/sfx/music/overlays), labels[] (words on the overlay track)
  bars      bars: [{"label": "offline", "value": 20}, ...]  (values 0-100), title
  dial      label (big word), sub (small line), value (0-100)
  toggle    label ("airplane mode"), on (true)
  button    text ("Get on the waitlist")
Common: "y" (centre height, default 960), "bg" (a hex colour to fill the screen; default: over the video).
CLI preview: python -m engine mg-preview <kind> --set labels='["cuts","captions"]'
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
SANS = os.path.join(ROOT, "library", "fonts", "Montserrat-Variable.ttf")
KINDS = ("pills", "window", "timeline", "bars", "dial", "toggle", "button")
_CACHE = {}


# ---------------------------------------------------------------- helpers
def _rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _back(p):                                    # ease out with a small overshoot (pops)
    p = min(max(p, 0.0), 1.0)
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def _font(px, weight=700, path=SANS):
    return load_font(path, int(px), weight)


def _shadow(img, blur=18, alpha=0.28, dy=10):
    a = img.split()[3].point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", img.size, (30, 20, 25, 0))
    sh.putalpha(a)
    pad = blur * 2
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2 + dy))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)) if blur else sh, (pad, pad + dy))
    out.alpha_composite(img, (pad, pad))
    return out


def _paste(canvas, img, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    im = img
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _colors(pack):
    c = pack.get("colors", {})
    return {"pop": c.get("pop", "#E58FA6"), "accent": c.get("accent", "#C99E98"), "ink": c.get("ink", "#332829"),
            "paper": c.get("paper", "#FFFDFA"), "bg": c.get("bg", "#F5EFE6")}


def _photo(ref):
    from .scrapbook import _photo as sp
    return sp(ref)[0]


# ---------------------------------------------------------------- pieces
def pill(text, col, px=46):
    f = _font(px, 800)
    tw = f.getlength(text)
    h = int(px * 1.9)
    w = int(tw + px * 2.2)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=_rgb(col["paper"]))
    r = px * 0.22
    d.ellipse((px * 0.55 - r, h / 2 - r, px * 0.55 + r, h / 2 + r), fill=_rgb(col["pop"]))
    d.text((px * 1.05, h / 2), text, font=f, fill=_rgb(col["ink"]), anchor="lm")
    return _shadow(im, 14, 0.3, 8)


def window(col, image=None, title="", w=760):
    h = int(w * 0.66)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=(255, 255, 255, 255), outline=(225, 220, 220, 255), width=2)
    for k, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):       # window buttons
        d.ellipse((24 + k * 26, 22, 40 + k * 26, 38), fill=_rgb(c))
    if title:
        d.text((w / 2, 30), title, font=_font(20, 600), fill=_rgb(col["ink"], 170), anchor="mm")
    side = int(w * 0.2)                                             # sidebar with soft lines
    for k in range(7):
        y = 70 + k * 30
        d.rounded_rectangle((22, y, side - 20 - (k % 3) * 18, y + 12), 6, fill=(232, 228, 230, 255))
    d.rounded_rectangle((22, 70, side - 20, 82), 6, fill=_rgb(col["pop"], 150))
    right = int(w * 0.24)                                           # settings panel
    for k in range(9):
        y = 70 + k * 34
        d.rounded_rectangle((w - right + 10, y, w - 24, y + 10), 5, fill=(236, 232, 234, 255))
        if k % 3 == 0:
            d.rounded_rectangle((w - 66, y - 4, w - 30, y + 14), 9, fill=_rgb(col["pop"], 200))
    pw = w - side - right - 30
    ph = h - 100
    pv = (side + 10, 60, side + 10 + pw, 60 + ph)
    if image is not None:
        ph9 = ImageOps.fit(image.convert("RGB"), (int(ph * 9 / 16), ph), Image.LANCZOS)
        x0 = int(pv[0] + (pw - ph9.width) / 2)
        m = Image.new("L", ph9.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, ph9.width - 1, ph9.height - 1), 14, fill=255)
        im.paste(ph9, (x0, pv[1]), m)
    else:
        d.rounded_rectangle(pv, 14, fill=(244, 241, 242, 255))
    return im


def _tilt(img, k):
    """Perspective tilt (k=1 tilted back, k=0 flat) for a window dropping into place."""
    if k <= 0.01:
        return img
    w, h = img.size
    inset = w * 0.12 * k
    lift = h * 0.18 * k
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [(inset, lift), (w - inset, lift), (w, h), (0, h)]
    # solve the perspective coefficients mapping dst -> src
    import numpy as np
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    coeffs = np.linalg.solve(np.array(A, float), np.array(B, float))
    return img.transform((w, h), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)


def _wave(d, box, col, seed, a=255):
    x0, y0, x1, y1 = box
    rng = random.Random(seed)
    mid = (y0 + y1) / 2
    for x in range(int(x0) + 6, int(x1) - 4, 9):
        hh = (y1 - y0) * (0.12 + 0.38 * abs(math.sin(x * 0.07 + seed)) * rng.uniform(0.5, 1))
        d.rounded_rectangle((x, mid - hh, x + 4, mid + hh), 2, fill=_rgb(col, a))


# ---------------------------------------------------------------- the kinds: frame(t) + sound events
def _pills(spec, col):
    labels = spec.get("labels") or ["cuts", "captions", "overlays", "animations", "sfx"]
    tilt = float(spec.get("tilt", 8))
    rng = random.Random(7)
    cards = [pill(l, col) for l in labels]
    y0 = spec.get("y", 960) - (len(cards) - 1) * 70
    pos = [(560 + (k % 2) * 90 - 40 + rng.uniform(-20, 20), y0 + k * 140, rng.uniform(-tilt, tilt)) for k in range(len(cards))]
    gap = 0.28
    sfx = [(0.08 + k * gap, "pill_in") for k in range(len(cards))]

    def frame(t, cv):
        for k, (c, (x, y, r)) in enumerate(zip(cards, pos)):
            p = (t - 0.05 - k * gap) / 0.32
            if p > 0:
                _paste(cv, c, x, y + (1 - _ease(p)) * 40, _back(p) * 1.0, min(1, p * 3), r)
    return frame, sfx, 0.4 + len(cards) * gap


def _window(spec, col):
    img = _photo(spec["image"]) if spec.get("image") else None
    win = window(col, img, spec.get("title", ""))
    status = spec.get("status")
    st = pill(status, col, 30) if status else None
    sfx = [(0.42, "window_in")] + ([(0.9, "notify")] if status else [])
    cy = spec.get("y", 960)

    def frame(t, cv):
        p = _ease(t / 0.55)
        tilt = (1 - p)
        w2 = _shadow(_tilt(win, tilt), 30, 0.32, 18)
        _paste(cv, w2, 540, cy - (1 - p) * 260, 0.9 + 0.1 * p, min(1, t / 0.2))
        if st is not None and t > 0.85:
            q = (t - 0.85) / 0.3
            _paste(cv, st, 540, cy + win.height * 0.55 + 20, _back(q), min(1, q * 3))
    return frame, sfx, 1.3


def _timeline(spec, col):
    tracks = spec.get("tracks") or ["video", "captions", "sfx", "music", "overlays"]
    labels = spec.get("labels") or ["cuts", "captions", "sfx"]
    rowh, lw, x0, x1 = 118, 190, 40, 1040
    top = spec.get("y", 960) - len(tracks) * rowh / 2
    f_lab = _font(26, 800)
    f_clip = _font(30, 800)
    sfx = [(0.1 + k * 0.12, "tick") for k in range(len(tracks))] + [(0.6, "chart_grow")]

    def frame(t, cv):
        d = ImageDraw.Draw(cv)
        grow = _ease((t - 0.35) / 0.9)
        for k, name in enumerate(tracks):
            p = _ease((t - 0.05 - k * 0.12) / 0.35)
            if p <= 0:
                continue
            y = top + k * rowh + (1 - p) * 30
            a = int(255 * p)
            d.rounded_rectangle((x0, y + 8, x0 + lw, y + rowh - 8), 12, fill=_rgb(col["ink"], a))
            d.text((x0 + lw / 2, y + rowh / 2), name.upper(), font=f_lab, fill=_rgb("#FFFFFF", a), anchor="mm")
            right = x0 + lw + 12 + (x1 - x0 - lw - 12) * grow
            box = (x0 + lw + 12, y + 14, right, y + rowh - 14)
            if box[2] - box[0] < 8:
                continue
            if name.lower() in ("voice", "voiceover", "music", "sfx", "audio"):
                d.rounded_rectangle(box, 10, fill=_rgb(col["pop"], int(70 * p)))
                _wave(d, box, col["ink"], k, a)
            elif name.lower() == "overlays" or k == len(tracks) - 1:
                cx = box[0]
                for j, lab in enumerate(labels):
                    wdt = f_clip.getlength(lab) + 50
                    if cx + wdt > box[2]:
                        break
                    d.rounded_rectangle((cx, box[1], cx + wdt, box[3]), 10, fill=_rgb(col["pop"], a))
                    d.text((cx + wdt / 2, (box[1] + box[3]) / 2), lab, font=f_clip, fill=_rgb(col["ink"], a), anchor="mm")
                    cx += wdt + 10
            else:
                cx = box[0]
                while cx < box[2] - 20:
                    wdt = min(150, box[2] - cx)
                    d.rounded_rectangle((cx, box[1], cx + wdt - 8, box[3]), 10, fill=_rgb(col["accent"], int(200 * p)))
                    cx += wdt
        if t > 0.6:                                                  # playhead sweeping across
            px = x0 + lw + 12 + (x1 - x0 - lw - 12) * min(1, (t - 0.6) / 2.4)
            d.line((px, top - 20, px, top + len(tracks) * rowh + 10), fill=_rgb(col["ink"]), width=4)
            d.regular_polygon((px, top - 22, 12), 4, rotation=45, fill=_rgb(col["ink"]))
    return frame, sfx, 3.0


def _bars(spec, col):
    bars = spec.get("bars") or [{"label": "before", "value": 25}, {"label": "after", "value": 90}]
    title = spec.get("title", "")
    base_y, maxh = spec.get("y", 960) + 300, 560
    bw = 170
    xs = [540 + (k - (len(bars) - 1) / 2) * 280 for k in range(len(bars))]
    f_lab, f_val, f_t = _font(30, 700), _font(54, 800), _font(48, 800)
    sfx = [(0.25 + k * 0.25, "chart_grow") for k in range(len(bars))] + [(0.95 + 0.25 * len(bars), "tick")]

    def frame(t, cv):
        d = ImageDraw.Draw(cv)
        a0 = int(255 * _ease(t / 0.3))
        d.line((xs[0] - 160, base_y, xs[-1] + 160, base_y), fill=_rgb(col["ink"], a0), width=4)
        if title:
            d.text((540, base_y - maxh - 120), title, font=f_t, fill=_rgb(col["ink"], a0), anchor="mm")
        for k, (b, x) in enumerate(zip(bars, xs)):
            p = _ease((t - 0.25 - k * 0.25) / 0.7)
            hgt = maxh * max(0, min(100, float(b.get("value", 50)))) / 100 * p
            colr = col["pop"] if k == len(bars) - 1 else col["accent"]
            if hgt > 2:
                d.rounded_rectangle((x - bw / 2, base_y - hgt, x + bw / 2, base_y), 16, fill=_rgb(colr))
                d.rectangle((x - bw / 2, base_y - min(hgt, 16), x + bw / 2, base_y), fill=_rgb(colr))
            d.text((x, base_y + 40), str(b.get("label", "")).upper(), font=f_lab, fill=_rgb(col["ink"], a0), anchor="mm")
            if p > 0.05:
                d.text((x, base_y - hgt - 44), f"{int(float(b.get('value', 0)) * p)}", font=f_val,
                       fill=_rgb(col["ink"], int(255 * min(1, p * 2))), anchor="mm")
    return frame, sfx, 1.1 + 0.25 * len(bars)


def _dial(spec, col):
    label, sub = spec.get("label", ""), spec.get("sub", "")
    val = max(0, min(100, float(spec.get("value", 70))))
    cy = spec.get("y", 960)
    R = 330
    f_big, f_sub = _font(130, 900), _font(46, 700)
    n = 24
    sfx = [(0.05 + k * 0.03, "tick") for k in range(0, n, 4)] + [(0.95, "thump")]

    def frame(t, cv):
        d = ImageDraw.Draw(cv)
        for k in range(n):                                          # ticks draw on around the arc
            if t < 0.05 + k * 0.03:
                break
            ang = math.radians(-210 + 240 * k / (n - 1))
            r0 = R - (40 if k % 4 == 0 else 22)
            d.line((540 + math.cos(ang) * r0, cy + math.sin(ang) * r0, 540 + math.cos(ang) * R, cy + math.sin(ang) * R),
                   fill=_rgb(col["ink"]), width=8 if k % 4 == 0 else 4)
        p = _back((t - 0.3) / 0.75)                                 # needle sweeps with a little overshoot
        if t > 0.3:
            ang = math.radians(-210 + 240 * val / 100 * p)
            d.line((540, cy, 540 + math.cos(ang) * (R - 60), cy + math.sin(ang) * (R - 60)), fill=_rgb(col["ink"]), width=7)
            d.ellipse((540 - 18, cy - 18, 540 + 18, cy + 18), fill=_rgb(col["pop"]))
        if label and t > 0.75:
            q = _ease((t - 0.75) / 0.35)
            im = Image.new("RGBA", (1000, 180))
            ImageDraw.Draw(im).text((500, 90), label, font=f_big, fill=_rgb(col["pop"]), anchor="mm",
                                    stroke_width=4, stroke_fill=_rgb(col["ink"]))
            im = im.filter(ImageFilter.GaussianBlur(6 * (1 - q))) if q < 1 else im
            _paste(cv, im, 540, cy + 120 + (1 - q) * 40, 1.0, q)
        if sub and t > 1.0:
            q = _ease((t - 1.0) / 0.3)
            d.text((540, cy + 230), sub.upper(), font=f_sub, fill=_rgb(col["ink"], int(255 * q)), anchor="mm")
    return frame, sfx, 1.4


def _toggle(spec, col):
    label = spec.get("label", "")
    on = spec.get("on", True)
    cy = spec.get("y", 960)
    f = _font(44, 700)
    sfx = [(0.45, "toggle")]

    def frame(t, cv):
        a = _ease(t / 0.25)
        p = _ease((t - 0.35) / 0.25) if on else 1 - _ease((t - 0.35) / 0.25)
        w, h = 220, 124
        sw = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(sw)
        off, onc = (205, 200, 204, 255), _rgb(col["pop"])
        mix = tuple(int(off[i] + (onc[i] - off[i]) * p) for i in range(4))
        d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=mix)
        kx = 14 + (w - h) * p
        d.ellipse((kx, 12, kx + h - 24, h - 12), fill=(255, 255, 255, 255))
        _paste(cv, _shadow(sw, 12, 0.25, 6), 540, cy, 0.8 + 0.2 * _back(t / 0.3), a)
        if label:
            ImageDraw.Draw(cv).text((540, cy + 120), label, font=f, fill=_rgb(col["ink"], int(255 * a)), anchor="mm")
    return frame, sfx, 0.9


def _button(spec, col):
    text = spec.get("text", "Get on the waitlist")
    cy = spec.get("y", 1500)
    f = _font(44, 700)
    tw = f.getlength(text)
    bw, bh = int(tw + 110), 118
    btn = Image.new("RGBA", (bw, bh))
    d = ImageDraw.Draw(btn)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), bh // 2, fill=_rgb(col["pop"]))
    d.text((bw / 2, bh / 2), text, font=f, fill=(255, 255, 255, 255), anchor="mm")
    btn = _shadow(btn, 16, 0.3, 8)
    cur = Image.new("RGBA", (60, 80))
    ImageDraw.Draw(cur).polygon([(4, 4), (4, 64), (20, 50), (32, 76), (42, 71), (30, 46), (52, 46)],
                                fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=3)
    sfx = [(0.1, "pill_in"), (0.95, "click")]

    def frame(t, cv):
        press = 1 - 0.07 * math.sin(math.pi * min(1, max(0, (t - 0.9) / 0.2)))
        _paste(cv, btn, 540, cy, _back(t / 0.35) * press, min(1, t * 4))
        if t > 0.3:
            q = _ease((t - 0.3) / 0.6)
            cx, cyy = 540 + bw * 0.25 + (1 - q) * 260, cy + 20 + (1 - q) * 280
            _paste(cv, cur, cx, cyy, 0.95 if 0.9 < t < 1.1 else 1.0)
    return frame, sfx, 1.4


BUILDERS = {"pills": _pills, "window": _window, "timeline": _timeline, "bars": _bars, "dial": _dial,
            "toggle": _toggle, "button": _button}


def render(kind, spec, pack, dur=None):
    """-> {"frames": [(RGBA, seconds)], "x", "y" (centre of the cropped frames), "sfx": [(t, event)]}.
    Frames are cropped to what's drawn (light on memory); the last frame holds."""
    import json, hashlib
    if kind not in BUILDERS:
        raise ValueError(f"unknown motion graphic '{kind}' — one of {', '.join(KINDS)}")
    col = _colors(pack)
    key = hashlib.md5(json.dumps([kind, spec, col], sort_keys=True, default=str).encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    frame, sfx, anim = BUILDERS[kind](dict(spec or {}), col)
    n = int(math.ceil(anim * FPS)) + 1
    bg = spec.get("bg") if spec else None
    full = []
    for i in range(n):
        cv = Image.new("RGBA", (W, H), _rgb(bg) if bg else (0, 0, 0, 0))
        frame(i / FPS, cv)
        full.append(cv)
    box = None
    for fr in full:
        b = fr.getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    box = box or (0, 0, 2, 2)
    frames = [(fr.crop(box), 1 / FPS) for fr in full]
    frames[-1] = (frames[-1][0], 999.0)
    out = {"frames": frames, "x": (box[0] + box[2]) / 2, "y": (box[1] + box[3]) / 2, "sfx": sfx, "anim": anim}
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def preview(kind, spec, pack, times=(0.15, 0.4, 0.8, 9)):
    """A strip of moments (for the Studio and for checking a design)."""
    r = render(kind, spec, pack)
    tiles = []
    for t in times:
        acc, img = 0, r["frames"][-1][0]
        for f, d in r["frames"]:
            if acc + d > t:
                img = f
                break
            acc += d
        cv = Image.new("RGBA", (W, H), (120, 150, 190, 255))
        cv.alpha_composite(img, (int(r["x"] - img.width / 2), int(r["y"] - img.height / 2)))
        cv.thumbnail((270, 480))
        tiles.append(cv)
    strip = Image.new("RGBA", (270 * len(tiles), 480))
    for k, tl in enumerate(tiles):
        strip.alpha_composite(tl, (k * 270, 0))
    return strip.convert("RGB")
