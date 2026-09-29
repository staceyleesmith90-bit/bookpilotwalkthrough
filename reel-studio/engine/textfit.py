"""Text that always fits its box.

Every piece of on-screen text (takeovers, captions, bubble text, hook banners)
goes through fit_text(): it wraps words, then finds the largest font size where
the whole block fits inside the box. Nothing is ever cropped or overflows.
"""
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont


WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold",
                700: "Bold", 800: "ExtraBold", 900: "Black"}


def _static_weight(path, weight):
    """For static fonts (Family-Bold.ttf…): use the sibling file closest to `weight`, if present."""
    import re as _re
    d, base = os.path.split(path)
    m = _re.match(r"(.+?)-(Thin|ExtraLight|Light|Regular|Medium|SemiBold|Bold|ExtraBold|Black)(\.\w+)$", base)
    if not m:
        return path
    fam, _, ext = m.groups()
    for w in sorted(WEIGHT_NAMES, key=lambda k: abs(k - weight)):
        cand = os.path.join(d, f"{fam}-{WEIGHT_NAMES[w]}{ext}")
        if os.path.exists(cand):
            return cand
    return path


@lru_cache(maxsize=256)
def load_font(path, size, weight=None):
    if weight and "Variable" not in path:
        path = _static_weight(path, weight)
    f = ImageFont.truetype(path, size)
    if weight and "Variable" in path:
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                name = a.get("name", b"")
                name = name.decode() if isinstance(name, bytes) else str(name)
                is_w = name.lower() in ("weight", "wght")
                v = weight if is_w else a.get("default", a["minimum"])
                vals.append(max(a["minimum"], min(a["maximum"], v)))
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    return f


def _wrap(words, font, max_w):
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def measure(lines, font, line_gap):
    lh = int(font.size * line_gap * 1.04)
    w = max((font.getlength(l) for l in lines), default=0)
    return w, lh * len(lines), lh


def fit_text(text, font_path, box_w, box_h, max_px=220, min_px=18,
             line_gap=1.08, weight=None, max_lines=None):
    """Largest size (binary search) where wrapped text fits box_w x box_h.

    Returns dict(lines, size, font, fits). fits=False means even min_px overflowed,
    so the caller should grow the container (see bubble_with_text).
    """
    words = text.split()
    lo, hi, best = min_px, max_px, None
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(font_path, mid, weight)
        lines = _wrap(words, font, box_w)
        w, h, _ = measure(lines, font, line_gap)
        ok = w <= box_w and h <= box_h and (max_lines is None or len(lines) <= max_lines)
        # a single word wider than the box can't wrap: treat as overflow
        ok = ok and all(font.getlength(l) <= box_w for l in lines)
        if ok:
            best, lo = dict(lines=lines, size=mid, font=font, fits=True), mid + 1
        else:
            hi = mid - 1
    if best:
        return best
    font = load_font(font_path, min_px, weight)
    return dict(lines=_wrap(words, font, box_w), size=min_px, font=font, fits=False)


def render_block(fit, color, line_gap=1.08, align="center", stroke=0, stroke_color=None):
    """Render a fit_text() result to a transparent RGBA image, tightly cropped."""
    font, lines = fit["font"], fit["lines"]
    w, h, lh = measure(lines, font, line_gap)
    pad = 8 + stroke
    asc, desc = font.getmetrics()
    im = Image.new("RGBA", (int(w) + pad * 2, int(h) + pad * 2 + asc + desc))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        lw = font.getlength(line)
        x = pad + {"center": (w - lw) / 2, "left": 0, "right": w - lw}[align]
        d.text((x, pad + i * lh), line, font=font, fill=color,
               stroke_width=stroke, stroke_fill=stroke_color)
    return im.crop(im.getbbox() or (0, 0, 1, 1))
