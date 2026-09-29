"""Camera moves (zooms) and transitions, applied to the video frame before graphics are drawn
(so text and stickers stay crisp while the footage moves — like CapCut).

Zoom types (timeline "zooms": [{start, end, type, scale, cx, cy}]):
  punch  instant zoom for emphasis            push   slow push-in (Ken Burns)
  pull   slow zoom-out / reveal               whip   fast eased zoom that lands and holds
  shake  camera shake on impact               pulse  quick in-out beat bump
  focus  zoom towards a point (cx, cy)        drift  slow sideways pan

Transition types (timeline "transitions": [{t, type, dur}]):
  flash · dip-black · dip-white · whip · zoom-blur · glitch · light-leak · pixelate ·
  spin · blur · shape-wipe (brand colour) · rgb-split · film-burn
"""
import math, random
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ZOOMS = ("punch", "push", "pull", "whip", "shake", "pulse", "focus", "drift")
TRANSITIONS = ("flash", "dip-black", "dip-white", "whip", "zoom-blur", "glitch", "light-leak", "pixelate",
               "spin", "blur", "shape-wipe", "rgb-split", "film-burn")


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def _ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def zoom_state(z, t, W, H):
    """(scale, centre_x, centre_y) for zoom z at time t, in frame pixels."""
    a, b = z["start"], z["end"]
    if not (a <= t < b):
        return None
    s = z.get("scale", 1.15)
    kind = z.get("type", "punch")
    p = (t - a) / max(b - a, 1e-3)
    cx, cy = W / 2, H / 2
    if z.get("cx") is not None:
        cx, cy = z["cx"] * W / 1080, z["cy"] * H / 1920
    if kind == "punch":
        k = s
    elif kind == "push":
        k = 1 + (s - 1) * _ease(p)
    elif kind == "pull":
        k = s - (s - 1) * _ease(p)
    elif kind == "whip":
        k = 1 + (s - 1) * _ease_out((t - a) / 0.22)
    elif kind == "pulse":
        k = 1 + (s - 1) * math.sin(math.pi * min((t - a) / 0.35, 1))
    elif kind == "shake":
        k = 1.06
        amp = 14 * (1 - p) * W / 1080
        cx += amp * math.sin(t * 61)
        cy += amp * math.cos(t * 47)
    elif kind == "focus":
        k = 1 + (s - 1) * _ease_out((t - a) / 0.5)
        cx = W / 2 + (cx - W / 2) * _ease_out((t - a) / 0.5)
        cy = H / 2 + (cy - H / 2) * _ease_out((t - a) / 0.5)
    elif kind == "drift":
        k = s
        cx = W / 2 + (W * 0.04) * (p - 0.5)
    else:
        k = s
    return k, cx, cy


def apply_zoom(frame, k, cx, cy):
    """Smooth sub-pixel zoom around (cx, cy), never showing outside the frame."""
    W, H = frame.size
    k = max(k, 1.0)
    half_w, half_h = W / 2 / k, H / 2 / k
    cx = min(max(cx, half_w), W - half_w)
    cy = min(max(cy, half_h), H - half_h)
    # sub-pixel crop box scaled back to full size (fast path of Pillow's resize)
    return frame.resize((W, H), Image.BILINEAR, box=(cx - half_w, cy - half_h, cx + half_w, cy + half_h))


def _blend(a, b, k):
    return Image.blend(a, b, max(0.0, min(1.0, k)))


def transition(frame, tr, t, pack_colour="#FFFFFF"):
    """Apply one transition centred on tr['t'] (±dur/2)."""
    d = tr.get("dur", 0.36)
    x = (t - tr["t"]) / (d / 2)            # -1 .. 1 across the transition
    if abs(x) >= 1:
        return frame
    k = 1 - abs(x)                          # 0 -> 1 (peak at the cut) -> 0
    W, H = frame.size
    kind = tr["type"]
    if kind == "flash":
        return _blend(frame, Image.new("RGBA", frame.size, "#FFFFFF"), k ** 1.5)
    if kind in ("dip-black", "dip-white"):
        return _blend(frame, Image.new("RGBA", frame.size, "#000000" if kind == "dip-black" else "#FFFFFF"), _ease(k))
    if kind == "whip":
        n = max(1, int(24 * k * W / 1080))
        small = frame.resize((max(1, W // (1 + n)), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        shift = int((x if x < 0 else x) * W * 0.25 * k)
        out = ImageChops.offset(small, shift, 0)
        return out
    if kind == "zoom-blur":
        out = frame.copy()
        for i in range(1, 5):
            s = 1 + 0.06 * i * k
            z = apply_zoom(frame, s, W / 2, H / 2)
            out = _blend(out, z, 0.35)
        return out
    if kind in ("glitch", "rgb-split"):
        arr = np.asarray(frame).copy()
        off = int(18 * k * W / 1080)
        arr[..., 0] = np.roll(arr[..., 0], off, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -off, axis=1)
        if kind == "glitch":
            rng = random.Random(int(t * 30))
            for _ in range(int(6 * k)):
                y0 = rng.randrange(0, H - 20)
                h = rng.randrange(8, max(9, H // 12))
                arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], rng.randrange(-60, 60), axis=1)
        return Image.fromarray(arr, "RGBA")
    if kind == "light-leak":
        leak = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(leak)
        cxl = W * (0.2 + 0.6 * (x + 1) / 2)
        for i, (r, col) in enumerate([(0.9, (255, 120, 60)), (0.6, (255, 180, 90)), (0.35, (255, 235, 170))]):
            rr = r * W
            dr.ellipse((cxl - rr, H * 0.3 - rr, cxl + rr, H * 0.3 + rr), fill=col + (int(110 * k),))
        leak = leak.filter(ImageFilter.GaussianBlur(W / 10))
        return ImageChops.screen(frame, leak)
    if kind == "film-burn":
        burn = Image.new("RGBA", frame.size, (255, 140, 40, 0))
        mask = Image.linear_gradient("L").resize((W, H)).rotate(90 * (1 if x < 0 else -1))
        burn.putalpha(mask.point(lambda v: int(v * k)))
        return ImageChops.screen(frame, burn)
    if kind == "pixelate":
        n = max(1, int(40 * k))
        return frame.resize((max(1, W // n), max(1, H // n)), Image.NEAREST).resize((W, H), Image.NEAREST)
    if kind == "spin":
        return frame.rotate(12 * x * k, resample=Image.BILINEAR).filter(ImageFilter.GaussianBlur(6 * k))
    if kind == "blur":
        return frame.filter(ImageFilter.GaussianBlur(18 * k * W / 1080))
    if kind == "shape-wipe":  # brand-colour circle grows to cover the cut, then opens
        out = frame.copy()
        r = math.hypot(W, H) / 2 * _ease(k)
        ImageDraw.Draw(out).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=pack_colour)
        return out
    return frame


def apply(frame, t, zooms, transitions, pack_colour):
    for z in zooms:
        st = zoom_state(z, t, *frame.size)
        if st:
            frame = apply_zoom(frame, *st)
    for tr in transitions:
        if abs(t - tr["t"]) < tr.get("dur", 0.36) / 2:
            frame = transition(frame, tr, t, pack_colour)
    return frame


# ---------------------------------------------------------------- layouts (framed card)
def _round_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


_MASKS = {}


def apply_layouts(frame, t, layouts, pack_colour):
    """Framed card: the footage shrinks into a rounded card (brand-colour edge, soft shadow) over a
    blurred, darkened copy of itself — room for text and pop-up cards around it. Eases in/out."""
    for lay in layouts:
        a, b = lay["start"], lay["end"]
        if not (a <= t < b):
            continue
        W, H = frame.size
        p = min((t - a) / 0.35, 1.0, (b - t) / 0.3)
        p = 1 - (1 - max(p, 0)) ** 3
        s = 1 - (1 - lay.get("scale", 0.66)) * p
        if s > 0.995:
            return frame
        cy = H / 2 + (lay.get("cy", 0.41) * H - H / 2) * p
        small = frame.resize((W // 10, H // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
        bg = small.resize((W, H), Image.BILINEAR)
        bg = Image.blend(bg, Image.new("RGBA", (W, H), (8, 10, 24, 255)), 0.45)
        fw, fh = int(W * s), int(H * s)
        card = frame.resize((fw, fh), Image.BILINEAR)
        r = int(48 * p * W / 1080)
        key = (fw, fh, r)
        if key not in _MASKS:
            _MASKS.clear()
            _MASKS[key] = _round_mask(fw, fh, max(r, 1))
        mask = _MASKS[key]
        x0, y0 = int(W / 2 - fw / 2), int(cy - fh / 2)
        sh = Image.new("RGBA", (fw + 80, fh + 80))
        sh.paste((0, 0, 0, int(150 * p)), (40, 50, 40 + fw, 50 + fh), mask)
        bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)), (x0 - 40, y0 - 40))
        edge = Image.new("RGBA", (fw + 10, fh + 10))
        ImageDraw.Draw(edge).rounded_rectangle((0, 0, fw + 9, fh + 9), radius=r + 5,
                                               outline=pack_colour, width=max(3, int(5 * p)))
        bg.paste(card, (x0, y0), mask)
        bg.alpha_composite(edge, (x0 - 5, y0 - 5))
        return bg
    return frame
