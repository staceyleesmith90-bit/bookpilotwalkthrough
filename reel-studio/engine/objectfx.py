"""Object effects: a real-looking thing does something around the person — the list (or any lines) is printed,
punched, slapped on or stamped instead of shown as flat pills. All drawn by the studio itself (no image
generator, no Canva): paper grain, embossed tape, curled sticky-note corners, rubber-stamp ink.

Registered as scene effects (engine/scenefx.py), so a plan beat uses them like any other:
    {"do": ["scene:label_tape"], "scene": {"items": ["step one", "step two"]}}

Common options (all optional):
  items     ["line one", "line two", ...]   what gets printed / punched / written
  behind    true      the object goes behind the person (cut-out on top); false = in front
  x, y      0-1       pin the object's centre (default: placed around the head, off the face)
  step      0.45      seconds between lines
  color     "#D7263D" tape / ink colour (default: the brand's pop colour where it makes sense)

  receipt_print   title "TO DO", footer "THANK YOU" — a printer slot above the head prints the lines, then it tears off
  label_tape      tape strips punch in one by one and stack (upper case, embossed)
  sticky_notes    colors [...] — notes slap on in an arch around the head, one line each
  stamp_card      mark "DONE" — an index card with the lines handwritten, a rubber stamp thunks each one
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = lambda n: os.path.join(ROOT, "library", "fonts", n)
_C = {}


def _f(name, px, weight=None):
    key = (name, int(px), weight)
    if key not in _C:
        _C[key] = load_font(FONT(name), max(8, int(px)), weight) if weight else load_font(FONT(name), max(8, int(px)))
    return _C[key]


def _rgb(h, a=255):
    if isinstance(h, (list, tuple)):
        return tuple(int(v) for v in h[:3]) + (a,)
    h = str(h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _seg(lt, a, b):
    return min(max((lt - a) / max(b - a, 1e-6), 0.0), 1.0)


def _ease(x):
    return 1 - (1 - x) ** 3


def _back(x):
    if x <= 0:
        return 0.0
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _grain(im, amount=10, seed=1):
    """Paper grain: soft noise on the opaque pixels."""
    a = np.asarray(im).astype(np.int16)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amount, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def _shadow(im, blur, alpha=0.35, dy=6):
    pad = blur * 2 + abs(dy)
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2))
    sh = Image.new("RGBA", im.size, (0, 0, 0, int(255 * alpha)))
    sh.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    out.alpha_composite(sh, (pad, pad + dy))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def _paste(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _items(spec):
    return [str(s) for s in (spec.get("items") or ["This is step one", "This is step two", "One more thing"])]


def _anchor(spec, ctx, frame, t, default):
    """Where the object sits: pinned (x, y) or placed from the head (hx, hy, r) by `default`."""
    hx, hy, r = ctx.head(ctx.mask(frame, t))
    if spec.get("x") is not None:
        return float(spec["x"]) * ctx.W, float(spec.get("y", 0.25)) * ctx.H, hx, hy, r
    x, y = default(hx, hy, r)
    return x, y, hx, hy, r


def _finish(frame, layer, spec, ctx, t):
    """Object layer onto the frame; behind = the person is put back on top (the object goes behind you)."""
    out = frame.copy()
    out.alpha_composite(layer)
    if spec.get("behind", True):
        person = frame.copy()
        person.putalpha(ctx.mask(frame, t))
        out.alpha_composite(person)
    return out


# ---------------------------------------------------------------- receipt printout
def _receipt(items, u, title, footer, seed=3):
    fm, fb = _f("CourierPrime-Regular.ttf", 30 * u), _f("CourierPrime-Regular.ttf", 40 * u)
    w = int(430 * u)
    lines = [("big", title), ("dash", ""), ("small", "QTY  ITEM")] + \
            [("item", f"1x   {s.upper()}") for s in items] + [("dash", ""), ("small", f"ITEMS: {len(items)}"), ("big", footer)]
    lh = 46 * u
    h = int(60 * u + len(lines) * lh + 40 * u)
    im = Image.new("RGBA", (w, h), (250, 248, 242, 255))
    d = ImageDraw.Draw(im)
    y = 40 * u
    for kind, text in lines:
        if kind == "dash":
            d.text((w / 2, y + lh / 2), "-" * 24, font=fm, fill=(60, 60, 60, 255), anchor="mm")
        elif kind == "big":
            d.text((w / 2, y + lh / 2), text, font=fb, fill=(30, 30, 30, 255), anchor="mm")
        else:
            wrapped = text if fm.getlength(text) < w - 50 * u else text[:int(len(text) * (w - 60 * u) / fm.getlength(text))] + "."
            d.text((26 * u, y + lh / 2), wrapped, font=fm, fill=(35, 35, 35, 255), anchor="lm")
        y += lh
    # torn zig-zag bottom edge
    zz = int(14 * u)
    mask = Image.new("L", (w, h), 255)
    md = ImageDraw.Draw(mask)
    pts = [(0, h)]
    for i in range(0, w + zz, zz):
        pts.append((i, h - (zz if (i // zz) % 2 else 0)))
    pts.append((w, h))
    md.polygon(pts, fill=0)
    im.putalpha(mask)
    return _grain(im, 7, seed), [40 * u + (i + 3) * lh + lh for i in range(len(items))], h


def fx_receipt_print(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    items = _items(spec)
    step = float(spec.get("step", 0.42))
    x, y, hx, hy, r = _anchor(spec, ctx, frame, t, lambda hx, hy, r: (hx, max(H * 0.07, hy - r * 2.9)))
    key = ("receipt", tuple(items), round(u, 3), spec.get("title"), spec.get("footer"))
    if key not in ctx._store:
        ctx._store[key] = _receipt(items, u, spec.get("title", "TO DO"), spec.get("footer", "THANK YOU"))
    rec, ends, full = ctx._store[key]
    x = min(max(x, rec.width / 2 + 30 * u), W - rec.width / 2 - 30 * u)
    lay = Image.new("RGBA", (W, H))
    slot_w, slot_h = rec.width + 70 * u, 46 * u
    k_in = _ease(_seg(lt, 0.0, 0.3))                      # the printer drops in
    sy = y - (1 - k_in) * 200 * u
    # paper: grows line by line, then tears off and falls
    t_print = 0.35
    shown = 70 * u
    for i, e in enumerate(ends):
        shown = max(shown, e * _ease(_seg(lt, t_print + i * step, t_print + i * step + step * 0.8)) if lt > t_print + i * step else shown)
    t_done = t_print + len(ends) * step + 0.25
    shown = shown + (full - ends[-1]) * _ease(_seg(lt, t_done - 0.2, t_done + 0.2)) if lt > t_done - 0.2 else shown
    fall = _seg(lt, max(t_done + 0.55, dur - 0.55), dur)
    crop = rec.crop((0, 0, rec.width, int(min(shown, full))))
    crop = _shadow(crop, int(8 * u), 0.28, int(4 * u))
    pad = (crop.width - rec.width) // 2
    if lt > 0.3:                                          # paper only once the printer is in place
        lay.alpha_composite(crop, (int(x - crop.width / 2), int(sy + slot_h * 0.5 - pad + fall * H * 0.6)))
    # the printer slot on top
    sl = Image.new("RGBA", (int(slot_w), int(slot_h)))
    d = ImageDraw.Draw(sl)
    d.rounded_rectangle((0, 0, slot_w - 1, slot_h - 1), int(14 * u), fill=(236, 236, 238, 255))
    d.rounded_rectangle((0, slot_h * 0.55, slot_w - 1, slot_h - 1), int(10 * u), fill=(206, 206, 212, 255))
    d.rounded_rectangle((26 * u, slot_h * 0.62, slot_w - 26 * u, slot_h * 0.8), int(4 * u), fill=(40, 40, 46, 255))
    d.ellipse((slot_w - 30 * u, 10 * u, slot_w - 18 * u, 22 * u),
              fill=(90, 200, 120, 255) if lt % 0.4 < 0.25 or lt > t_done else (60, 120, 80, 255))
    _paste(lay, _shadow(sl, int(10 * u), 0.3, int(6 * u)), x, sy, 1.0, k_in)
    return _finish(frame, lay, spec, ctx, t)


# ---------------------------------------------------------------- label tape
def _tape(text, u, col, seed):
    f = _f("Poppins-Bold.ttf", 40 * u)
    txt = text.upper()
    w, h = int(f.getlength(txt) + 70 * u), int(70 * u)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    cut = 10 * u
    d.polygon([(cut, 0), (w, 0), (w - cut, h), (0, h)], fill=col)         # tape cut at an angle at both ends
    hl = Image.new("RGBA", (w, h))
    ImageDraw.Draw(hl).rectangle((0, 0, w, h * 0.3), fill=(255, 255, 255, 34))
    im.alpha_composite(Image.composite(hl, Image.new("RGBA", (w, h)), im.split()[3]))
    # embossed letters: dark shadow below-right, white raised letters, soft highlight above-left
    d.text((w / 2 + 2 * u, h / 2 + 3 * u), txt, font=f, fill=(0, 0, 0, 90), anchor="mm")
    d.text((w / 2 - 1 * u, h / 2 - 1 * u), txt, font=f, fill=(255, 255, 255, 120), anchor="mm")
    d.text((w / 2, h / 2), txt, font=f, fill=(250, 246, 240, 255), anchor="mm")
    return _shadow(_grain(im, 6, seed), int(7 * u), 0.35, int(5 * u))


def fx_label_tape(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    items = _items(spec)
    step = float(spec.get("step", 0.45))
    col = _rgb(spec.get("color") or "#D7263D")
    gap = 82 * u
    x, y, hx, hy, r = _anchor(spec, ctx, frame, t,
                              lambda hx, hy, r: (hx, max(H * 0.08, hy - r * 1.05 - len(items) * gap)))
    lay = Image.new("RGBA", (W, H))
    rnd = random.Random(7)
    for i, s in enumerate(items):
        key = ("tape", s, round(u, 3), col)
        if key not in ctx._store:
            ctx._store[key] = _tape(s, u, col, i + 1)
        im = ctx._store[key]
        st = 0.15 + i * step
        k = _seg(lt, st, st + 0.22)
        if k <= 0:
            continue
        out_k = _seg(lt, dur - 0.3, dur)
        rot = rnd.uniform(-5, 5)
        cx = min(max(x + rnd.uniform(-0.06, 0.06) * W, im.width / 2), W - im.width / 2)
        # punched out: shoots out sideways, overshoots, settles on the stack
        sx = cx + (1 - _ease(k)) * (W * 0.5) * (1 if i % 2 else -1)
        _paste(lay, im, sx, y + i * gap - out_k * H * 0.04, _back(k) * 0.15 + 0.85 if k < 1 else 1.0, 1 - out_k, rot)
    return _finish(frame, lay, spec, ctx, t)


# ---------------------------------------------------------------- sticky notes
NOTE_COLORS = ["#FFE873", "#FFB3C7", "#A8E0FF", "#B8F2A6", "#FFC98B"]


def _note(text, u, col, seed):
    s = int(220 * u)
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    c = _rgb(col)
    d.rectangle((0, 0, s, s), fill=c)
    # sticky band at the top + curled bottom-right corner
    d.rectangle((0, 0, s, s * 0.12), fill=tuple(max(0, v - 14) for v in c[:3]) + (255,))
    curl = int(s * 0.2)
    d.polygon([(s, s - curl), (s, s), (s - curl, s)], fill=(0, 0, 0, 0))
    d.polygon([(s, s - curl), (s - curl * 0.85, s - curl * 0.85), (s - curl, s)],
              fill=tuple(max(0, v - 40) for v in c[:3]) + (255,))
    f = _f("Caveat-Variable.ttf", 46 * u, 700)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        tt = (cur + " " + w_).strip()
        if f.getlength(tt) <= s * 0.84 or not cur:
            cur = tt
        else:
            lines.append(cur); cur = w_
    lines.append(cur)
    lh = 48 * u
    y0 = s * 0.56 - len(lines) * lh / 2
    for i, ln in enumerate(lines[:4]):
        d.text((s / 2, y0 + i * lh + lh / 2), ln, font=f, fill=(40, 34, 30, 255), anchor="mm")
    return _shadow(_grain(im, 6, seed), int(9 * u), 0.32, int(7 * u))


def fx_sticky_notes(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    items = _items(spec)
    step = float(spec.get("step", 0.4))
    cols = spec.get("colors") or NOTE_COLORS
    x, y, hx, hy, r = _anchor(spec, ctx, frame, t, lambda hx, hy, r: (hx, hy))
    lay = Image.new("RGBA", (W, H))
    n = len(items)
    rad = max(r * 2.35, W * 0.3)
    rnd = random.Random(5)
    for i, s in enumerate(items):
        key = ("note", s, round(u, 3), cols[i % len(cols)])
        if key not in ctx._store:
            ctx._store[key] = _note(s, u, cols[i % len(cols)], i + 2)
        im = ctx._store[key]
        a = math.radians(200 - (220 * i / max(n - 1, 1)) if n > 1 else 90)     # left → over the top → right
        cx = min(max(x + math.cos(a) * rad, im.width / 2), W - im.width / 2)
        cy = min(max(y - abs(math.sin(a)) * rad * 0.95, im.height / 2 + H * 0.04), H - im.height / 2)
        st = 0.12 + i * step
        k = _seg(lt, st, st + 0.18)
        if k <= 0:
            continue
        out_k = _seg(lt, dur - 0.25, dur)
        scale = 1.0 + (1 - _ease(k)) * 0.45                                        # slapped on: big → flat
        _paste(lay, im, cx, cy, scale * (1 - out_k * 0.3), min(1.0, k * 3) * (1 - out_k), rnd.uniform(-9, 9))
    return _finish(frame, lay, spec, ctx, t)


# ---------------------------------------------------------------- stamp card
def _card(items, u, seed):
    w = int(560 * u)
    lh = 64 * u
    h = int(90 * u + len(items) * lh + 40 * u)
    im = Image.new("RGBA", (w, h), (252, 250, 244, 255))
    d = ImageDraw.Draw(im)
    for i in range(int(h / lh) + 1):
        yy = 90 * u + i * lh
        d.line((0, yy, w, yy), fill=(150, 185, 225, 255), width=max(1, int(2 * u)))
    d.line((0, 58 * u, w, 58 * u), fill=(226, 112, 112, 255), width=max(1, int(3 * u)))
    d.line((64 * u, 0, 64 * u, h), fill=(226, 112, 112, 160), width=max(1, int(2 * u)))
    f = _f("Caveat-Variable.ttf", 50 * u, 700)
    rows = []
    for i, s in enumerate(items):
        yy = 90 * u + i * lh - 6 * u
        d.text((84 * u, yy), s, font=f, fill=(38, 44, 70, 255), anchor="ls")
        rows.append((min(84 * u + f.getlength(s) + 90 * u, w - 80 * u), yy - lh * 0.32))
    return _shadow(_grain(im, 6, seed), int(10 * u), 0.3, int(7 * u)), rows


def _mark(text, u, col, seed):
    f = _f("Poppins-Bold.ttf", 34 * u)
    w, h = int(f.getlength(text) + 36 * u), int(60 * u)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((3 * u, 3 * u, w - 3 * u, h - 3 * u), int(8 * u), outline=col, width=max(2, int(4 * u)))
    d.text((w / 2, h / 2), text, font=f, fill=col, anchor="mm")
    rng = np.random.default_rng(seed)                     # patchy rubber-stamp ink
    a = np.asarray(im).copy()
    holes = rng.random(a.shape[:2]) < 0.16
    a[..., 3] = np.where(holes, (a[..., 3] * 0.25).astype(np.uint8), a[..., 3])
    return Image.fromarray(a, "RGBA").filter(ImageFilter.GaussianBlur(0.6 * u))


def _stamp_tool(u, col):
    w, h = int(120 * u), int(170 * u)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.3, 0, w * 0.7, h * 0.26), fill=(150, 98, 58, 255))                 # knob
    d.rectangle((w * 0.42, h * 0.2, w * 0.58, h * 0.6), fill=(124, 80, 46, 255))         # handle
    d.rounded_rectangle((w * 0.08, h * 0.56, w * 0.92, h * 0.86), int(8 * u), fill=(170, 118, 72, 255))   # block
    d.rectangle((w * 0.12, h * 0.86, w * 0.88, h * 0.97), fill=col)                    # rubber
    return _shadow(im, int(9 * u), 0.35, int(8 * u))


def fx_stamp_card(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    items = _items(spec)
    step = float(spec.get("step", 0.55))
    col = _rgb(spec.get("color") or "#D23A3A", 235)
    key = ("card", tuple(items), round(u, 3))
    if key not in ctx._store:
        ctx._store[key] = _card(items, u, 4)
    card, rows = ctx._store[key]
    x, y, hx, hy, r = _anchor(spec, ctx, frame, t, lambda hx, hy, r: (hx, max(H * 0.06 + card.height / 2, hy - r * 1.1 - card.height / 2)))
    x = min(max(x, card.width / 2), W - card.width / 2)
    lay = Image.new("RGBA", (W, H))
    k_in = _ease(_seg(lt, 0.0, 0.3))
    out_k = _seg(lt, dur - 0.3, dur)
    canvas = card.copy()
    mark = _mark(str(spec.get("mark", "DONE")), u, col, 9)
    pad = (card.width - int(560 * u)) / 2
    tool = _stamp_tool(u, col)
    tool_pos = None
    for i, (mx, my) in enumerate(rows):
        st = 0.45 + i * step
        if lt >= st + 0.18:
            _paste(canvas, mark, mx + pad, my + pad, 1.0, 1.0, -8 + 5 * ((i * 37) % 3))
        if st - 0.2 <= lt < st + 0.4:                   # the stamp comes down, presses, lifts
            down = _seg(lt, st - 0.2, st) - _seg(lt, st + 0.2, st + 0.4)
            tool_pos = (mx + pad, my + pad - tool.height * 0.42 - (1 - down) * 120 * u, 1 - 0.06 * _seg(lt, st, st + 0.08))
    cx, cy = x, y + (1 - k_in) * -H * 0.3 - out_k * H * 0.05
    _paste(lay, canvas, cx, cy, 1.0, k_in * (1 - out_k), -3)
    if tool_pos and out_k <= 0:
        tx, ty, sq = tool_pos
        _paste(lay, tool, cx - card.width / 2 + tx, cy - card.height / 2 + ty, sq, 1.0, 0)
    return _finish(frame, lay, spec, ctx, t)


EFFECTS = {"receipt_print": fx_receipt_print, "label_tape": fx_label_tape, "sticky_notes": fx_sticky_notes,
           "stamp_card": fx_stamp_card}
LABELS = {"receipt_print": "Receipt Printout", "label_tape": "Label Tape", "sticky_notes": "Sticky Notes",
          "stamp_card": "Stamp Card"}
ABOUT = {"receipt_print": "A printer slot above your head prints your list line by line, then the receipt tears off.",
         "label_tape": "Embossed label-tape strips punch out one by one and stack behind your head.",
         "sticky_notes": "Sticky notes slap on in an arch around your head, one line on each.",
         "stamp_card": "Your list handwritten on an index card; a rubber stamp thunks DONE onto every line."}
DUR = {"receipt_print": 3.2, "label_tape": 2.8, "sticky_notes": 2.6, "stamp_card": 3.4}


def sound_times(fx, spec, dur):
    """[(seconds into the effect, event, gain)] — one sound per line, timed to the drawing."""
    n = len(_items(spec or {}))
    if fx == "receipt_print":
        st = float((spec or {}).get("step", 0.42))
        return [(0.0, "slide", 0.6)] + [(0.35 + i * st, "type_key", 0.8) for i in range(n)] + \
               [(0.36 + i * st + 0.12, "type_key", 0.6) for i in range(n)] + [(max(dur - 0.55, 0.4 + n * st), "swish", 0.8)]
    if fx == "label_tape":
        st = float((spec or {}).get("step", 0.45))
        return [(0.15 + i * st, "click", 1.0) for i in range(n)] + [(0.2 + i * st, "thump", 0.5) for i in range(n)]
    if fx == "sticky_notes":
        st = float((spec or {}).get("step", 0.4))
        return [(0.12 + i * st, "page", 0.8) for i in range(n)] + [(0.16 + i * st, "thump", 0.6) for i in range(n)]
    if fx == "stamp_card":
        st = float((spec or {}).get("step", 0.55))
        return [(0.0, "page", 0.7)] + [(0.45 + i * st, "slam", 0.7) for i in range(n)]
    return []
