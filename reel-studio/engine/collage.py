"""Paper collage look: painted stripes, a torn-paper cut-out of the person, a big soft serif title with a
handwritten kicker, typewriter label strips and halftone (or colour) paper cut-out stickers that pop in
with a stop-motion jitter. Used by the "collage" scene effect (engine/scenefx.py).

spec (all optional):
  stripes   ["#F29BB2", "#EE7F62"]          two stripe colours
  kicker    "Hi, we're"                      handwritten line above the title
  title     "Besties"                        big serif word
  title_y   0.2                              title height (0-1 of the screen)
  labels    ["(very) nervous", {"text": "...", "x": .3, "y": .7, "rot": -5}]
  stickers  [{"emoji": "Mirror ball", "x": .8, "y": .45, "size": .26, "look": "halftone"|"colour", "rot": 8}]
  overlay   false  true = draw on the video itself (no stripes / cut-out / title): stickers, labels, song card
  song      {"title": "Bestie, Hold My Hand", "artist": "...", "art": "path.png", "x": .5, "y": .16}
  stickers  can also be {"image": "path/to/sticker.png", ...} (ready-made die-cut art)
  person    true   cut the person out (false = keep the whole picture as a torn photo)
  person_scale 0.76, person_x 0.5, person_y 1.0   size of the cut-out and where its bottom-centre sits
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = lambda n: os.path.join(ROOT, "library", "fonts", n)
PAPER = (251, 248, 240, 255)
_CACHE = {}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def stripes(W, H, c1, c2, seed=3):
    key = ("stripes", W, H, c1, c2)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    sw = W / 13.5
    y = np.arange(H)[:, None]
    x = np.arange(W)[None, :]
    wob = (np.sin(y / H * 9 + 1.3) * 3 + np.sin(y / H * 27) * 1.5) * (W / 1080)       # hand-painted edges
    band = (((x + wob) / sw).astype(int) % 2).astype(np.float32)
    a, b = np.array(_rgb(c1), np.float32), np.array(_rgb(c2), np.float32)
    img = a[None, None] * (1 - band[..., None]) + b[None, None] * band[..., None]
    grain = rng.normal(0, 7, (H // 2, W // 2)).astype(np.float32)
    grain = np.asarray(Image.fromarray(grain).resize((W, H), Image.BILINEAR))
    streak = np.asarray(Image.fromarray(rng.normal(0, 6, (H // 40, W // 2)).astype(np.float32)).resize((W, H), Image.BILINEAR))
    img = np.clip(img + (grain + streak)[..., None], 0, 255).astype(np.uint8)
    out = Image.fromarray(img, "RGB").convert("RGBA")
    _CACHE[key] = out
    return out


def torn(alpha, px, seed=1):
    """Grow an alpha shape by ~px with a rough torn-paper edge."""
    s = 2
    small = alpha.resize((max(1, alpha.width // s), max(1, alpha.height // s)), Image.BILINEAR)
    grown = np.asarray(small.filter(ImageFilter.GaussianBlur(px / s * 0.55)), np.float32) / 255
    rng = np.random.default_rng(seed)
    n = rng.random((max(2, small.height // 6), max(2, small.width // 6))).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize(small.size, Image.BICUBIC), np.float32)
    thr = 0.12 + 0.12 * n
    m = (grown > thr).astype(np.uint8) * 255
    return Image.fromarray(m, "L").resize(alpha.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))


def shadow_under(layer, blur=10, dy=8, alpha=0.32):
    a = layer.split()[3].point(lambda v: int(v * alpha)).filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", layer.size, (40, 20, 20, 0))
    sh.putalpha(a)
    out = Image.new("RGBA", layer.size)
    out.alpha_composite(sh, (0, dy))
    out.alpha_composite(layer)
    return out


def halftone(img, cell=7):
    """Black-and-white newspaper print of an RGBA image (dots sized by darkness)."""
    g = np.asarray(ImageOps.autocontrast(img.convert("L"), cutoff=2), np.float32) / 255
    a = np.asarray(img.split()[3], np.float32) / 255
    H, W = g.shape
    S = 3                                              # draw big, shrink = smooth dots
    out = Image.new("L", (W * S, H * S), 255)
    d = ImageDraw.Draw(out)
    for yy in range(0, H, cell):
        off = (cell // 2) if (yy // cell) % 2 else 0
        for xx in range(off, W, cell):
            blk = g[yy:yy + cell, xx:xx + cell]
            ab = a[yy:yy + cell, xx:xx + cell]
            if blk.size == 0 or ab.mean() < 0.3:
                continue
            dark = 1 - blk.mean()
            r = cell * S * 0.72 * math.sqrt(max(dark * 1.15 - 0.04, 0))
            cx, cy = (xx + cell / 2) * S, (yy + cell / 2) * S
            if r > 0.6:
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=20)
    ink = out.resize((W, H), Image.LANCZOS)
    res = Image.new("RGBA", (W, H), PAPER)
    res.putalpha(img.split()[3])
    black = Image.new("RGBA", (W, H), (22, 20, 20, 255))
    black.putalpha(Image.fromarray((np.asarray(ink, np.float32) * -1 + 255).astype(np.uint8)).point(lambda v: v) )
    blk_a = np.minimum(np.asarray(black.split()[3]), np.asarray(img.split()[3]))
    black.putalpha(Image.fromarray(blk_a))
    res.alpha_composite(black)
    return res


def image_sticker(path, px):
    """A ready-made sticker image (already die-cut, e.g. generated for the reel), sized and shadowed."""
    key = ("img", path, px)
    if key not in _CACHE:
        p = path if os.path.isabs(path) else os.path.join(ROOT, path)
        im = Image.open(p).convert("RGBA")
        im = im.resize((px, max(1, int(im.height * px / im.width))), Image.LANCZOS)
        _CACHE[key] = shadow_under(im, blur=max(4, px // 22), dy=max(3, px // 30))
    return _CACHE[key]


def song_card(title, artist, px, art=None, lt=0.0):
    """A "now playing" music card: art, song title, artist, bouncing equaliser and a progress bar."""
    ft = load_font(FONT("Baloo2-Variable.ttf"), int(px * 0.95), 800)
    fa = load_font(FONT("Nunito-Variable.ttf"), int(px * 0.6), 700)
    h = int(px * 3.1)
    a = int(h - px * 0.8)
    x0 = int(px * 0.6 + a)
    w = int(x0 + max(ft.getlength(title), fa.getlength(artist)) + px * 2.6)
    card = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, h - 1), int(px * 0.7), fill=PAPER)
    if art:
        im = image_sticker(art, a)
        card.alpha_composite(im, (int(px * 0.35), int((h - im.height) / 2)))
    d.text((x0, px * 0.45), title, font=ft, fill=(59, 42, 58, 255))
    d.text((x0, px * 1.5), artist, font=fa, fill=(59, 42, 58, 170))
    bw = int(px * 0.2)
    for i in range(4):                                    # equaliser
        hh = px * (0.35 + 0.45 * abs(math.sin(lt * 7 + i * 1.7)))
        x = w - px * 1.5 + i * bw * 1.6
        d.rounded_rectangle((x, px * 1.3 - hh / 2, x + bw, px * 1.3 + hh / 2), bw // 2, fill=(242, 120, 92, 255))
    py = h - px * 0.65
    d.rounded_rectangle((x0, py, w - px * 0.6, py + px * 0.16), int(px * 0.08), fill=(59, 42, 58, 40))
    q = min(1.0, 0.25 + lt * 0.12)
    d.rounded_rectangle((x0, py, x0 + (w - px * 0.6 - x0) * q, py + px * 0.16), int(px * 0.08), fill=(242, 120, 92, 255))
    return shadow_under(card, blur=max(6, px // 3), dy=max(4, px // 4), alpha=0.25)


def cutout_sticker(emoji, px, look="halftone", seed=1):
    key = ("st", emoji, px, look, seed)
    if key in _CACHE:
        return _CACHE[key]
    from .iconstickers import fluent3d
    im = fluent3d(emoji, int(px * 0.86))
    if im is None:
        return None
    pad = int(px * 0.12)
    base = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad))
    base.alpha_composite(im, (pad, pad))
    a = base.split()[3].point(lambda v: 255 if v > 90 else 0)
    art = base.copy()
    art.putalpha(a)
    if look == "halftone":
        art = halftone(art, cell=max(4, px // 34))
    paper = Image.new("RGBA", base.size, PAPER)
    paper.putalpha(torn(a, px * 0.055, seed))
    paper.alpha_composite(art)
    out = shadow_under(paper, blur=max(4, px // 22), dy=max(3, px // 30))
    _CACHE[key] = out
    return out


def label(text, px, seed=1):
    key = ("lab", text, px, seed)
    if key in _CACHE:
        return _CACHE[key]
    f = load_font(FONT("CourierPrime-Regular.ttf"), px)
    tw = f.getlength(text)
    w, h = int(tw + px * 1.1), int(px * 1.75)
    strip = Image.new("RGBA", (w, h), PAPER)
    rng = random.Random(seed)
    m = Image.new("L", (w, h), 0)
    pts = [(rng.uniform(0, 3), rng.uniform(0, 3)), (w - rng.uniform(0, 3), rng.uniform(0, 3)),
           (w - rng.uniform(0, 3), h - rng.uniform(0, 3)), (rng.uniform(0, 3), h - rng.uniform(0, 3))]
    ImageDraw.Draw(m).polygon(pts, fill=255)
    strip.putalpha(m)
    ImageDraw.Draw(strip).text((w / 2, h / 2 + px * 0.05), text, font=f, fill=(24, 22, 22, 255), anchor="mm")
    out = shadow_under(strip, blur=max(4, px // 6), dy=max(3, px // 9), alpha=0.28)
    _CACHE[key] = out
    return out


def title(kicker, word, px, ink="#F7EE8E"):
    key = ("title", kicker, word, px, ink)
    if key in _CACHE:
        return _CACHE[key]
    fb = load_font(FONT("DMSerifDisplay-Regular.ttf"), px)
    fk = load_font(FONT("Caveat-Variable.ttf"), int(px * 0.42), 700)
    tw = fb.getlength(word)
    kw = fk.getlength(kicker) if kicker else 0
    W = int(max(tw, kw) + px * 0.4)
    H = int(px * 1.55 + (px * 0.42 if kicker else 0))
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    y0 = px * 0.45 if kicker else px * 0.1
    col = _rgb(ink) + (255,)
    d.text((W / 2 + 2, y0 + 4), word, font=fb, fill=(160, 70, 60, 90), anchor="mt")        # soft print shadow
    d.text((W / 2, y0), word, font=fb, fill=col, anchor="mt")
    if kicker:
        d.text((W * 0.22, px * 0.05), kicker, font=fk, fill=col, anchor="lt")
    _CACHE[key] = im
    return im


def _pop(lt, t0, dur=0.28):
    p = min(max((lt - t0) / dur, 0), 1)
    if p <= 0:
        return 0.0
    c = 1.9
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def _paste(canvas, im, cx, cy, scale, rot):
    if scale <= 0.02:
        return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


DEFAULT_STICKERS = [{"emoji": "Mirror ball", "x": 0.8, "y": 0.42, "size": 0.27, "rot": -6},
                    {"emoji": "Double exclamation mark", "x": 0.2, "y": 0.4, "size": 0.18, "look": "colour", "rot": 10},
                    {"emoji": "Tulip", "x": 0.18, "y": 0.66, "size": 0.2, "rot": -12},
                    {"emoji": "Blossom", "x": 0.62, "y": 0.7, "size": 0.2, "look": "colour", "rot": 8}]


def draw(frame, mask, lt, spec, W, H, colors):
    """One frame of the collage over `frame` (RGBA) with the person mask (L)."""
    u = W / 1080
    overlay = spec.get("overlay", False)                 # on the video itself: no stripes, no cut-out, no title
    st = spec.get("stripes") or [colors.get("pink", "#F29BB2"), colors.get("pop", "#EE7F62")]
    out = frame.copy() if overlay else stripes(W, H, st[0], st[1]).copy()
    step = int(lt * 12)                                     # stop-motion: things "boil" 12 times a second
    jit = lambda k: (random.Random(step * 31 + k).uniform(-1.2, 1.2), random.Random(step * 17 + k).uniform(-2.5, 2.5) * u)
    tk = 0.0
    if spec.get("title", None if overlay else "Besties"):
        im = title(spec.get("kicker", "Hi, we're"), spec.get("title", "Besties"), int(spec.get("title_px", 250) * u),
                   spec.get("ink", "#F7EE8E"))
        if im.width > W * 0.94:
            im = im.resize((int(W * 0.94), int(im.height * W * 0.94 / im.width)), Image.LANCZOS)
        k = _pop(lt, 0.02, 0.32)
        _paste(out, im, W / 2, H * spec.get("title_y", 0.2), k, jit(0)[0] * 0.5)
        tk = 0.1
    stickers = spec.get("stickers", DEFAULT_STICKERS)
    behind = [s for s in stickers if s.get("behind", True)]
    front = [s for s in stickers if not s.get("behind", True)]

    def put_stickers(lst, k0):
        for i, s in enumerate(lst):
            px = int(s.get("size", 0.22) * W)
            im = image_sticker(s["image"], px) if s.get("image") else cutout_sticker(s["emoji"], px, s.get("look", "halftone"), seed=i + 3)
            if im is None:
                continue
            k = _pop(lt, tk + 0.1 + 0.09 * (i + k0))
            r, dy = jit(10 + i + k0)
            _paste(out, im, s["x"] * W, s["y"] * H + dy, k, s.get("rot", 0) + r)
    put_stickers(behind, 0)
    if spec.get("person", True) and mask is not None and not overlay:
        k = float(spec.get("person_scale", 0.76))            # the person smaller, standing on the bottom edge
        k *= 0.92 + 0.08 * _pop(lt, 0.0, 0.35)
        px, py = spec.get("person_x", 0.5) * W, spec.get("person_y", 1.0) * H
        p = frame.copy()
        p.putalpha(mask)
        if abs(k - 1) > 0.01:
            p = p.transform((W, H), Image.AFFINE, (1 / k, 0, W / 2 - px / k, 0, 1 / k, H - py / k), resample=Image.BILINEAR)
        a = p.split()[3]
        rim = torn(a, 20 * u, seed=7)
        white = Image.new("RGBA", (W, H), PAPER)
        white.putalpha(rim)
        out.alpha_composite(shadow_under(white, blur=int(16 * u), dy=int(10 * u), alpha=0.3))
        out.alpha_composite(p)
    put_stickers(front, len(behind))
    if spec.get("song"):                                  # "now playing" card
        sg = spec["song"]
        im = song_card(sg.get("title", ""), sg.get("artist", ""), int(sg.get("px", 44) * u), sg.get("art"), lt)
        if im.width > W * 0.92:
            im = im.resize((int(W * 0.92), int(im.height * W * 0.92 / im.width)), Image.LANCZOS)
        k = _pop(lt, sg.get("at", 0.15), 0.35)
        _paste(out, im, sg.get("x", 0.5) * W, sg.get("y", 0.16) * H, k, sg.get("rot", -2))
    labels = spec.get("labels", [])
    spots = [(0.62, 0.33, 6), (0.3, 0.74, -5), (0.66, 0.62, 4), (0.4, 0.5, -3)]
    for i, l in enumerate(labels):
        l = {"text": l} if isinstance(l, str) else l
        x, y, rot = l.get("x", spots[i % 4][0]), l.get("y", spots[i % 4][1]), l.get("rot", spots[i % 4][2])
        im = label(l["text"], int(l.get("px", 52) * u), seed=i + 1)
        k = _pop(lt, l.get("at", tk + 0.35 + 0.16 * i))
        r, dy = jit(40 + i)
        _paste(out, im, x * W, y * H + dy, k, rot + r * 0.6)
    return out


def element_times(spec):
    """When each piece lands (for the pop sounds)."""
    tk = 0.1 if spec.get("title", None if spec.get("overlay") else "Besties") else 0.0
    n_st = len(spec.get("stickers", DEFAULT_STICKERS))
    ts = [0.02] if tk else []
    ts += [tk + 0.1 + 0.09 * i for i in range(n_st)]
    ts += [(l.get("at") if isinstance(l, dict) and "at" in l else tk + 0.35 + 0.16 * i) for i, l in enumerate(spec.get("labels", []))]
    if spec.get("song"):
        ts.append(spec["song"].get("at", 0.15))
    return sorted(ts)
