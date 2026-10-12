"""Grid card: a full-screen colour card with faint grid-paper lines where the words blur into focus —
a small lead-in, then one big word ("here's your / driver"). Cuts in over the talking for one beat.

In a plan: "do": ["gridcard:here's your|driver"]  (+ optional beat["gridcard"] = {"color": "#DE7461",
"font": "serif" | "sans"}). Text defaults to the beat's words; colour to the pack's pop colour.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
SANS = os.path.join(ROOT, "library", "fonts", "Montserrat-Variable.ttf")
SERIF_IT = os.path.join(ROOT, "library", "fonts", "PlayfairDisplay-Italic-Variable.ttf")
_CACHE = {}


def _hex(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def background(color):
    base = _hex(color)
    y = np.linspace(-1, 1, H)[:, None, None]; x = np.linspace(-1, 1, W)[None, :, None]
    glow = np.clip(1 - 0.55 * ((x - 0.35) ** 2 + (y + 0.1) ** 2), 0, 1)        # soft light from the upper right
    rgb = base * (0.9 + 0.22 * glow)
    rgb += np.random.default_rng(5).normal(0, 2.5, (H, W, 1))
    im = Image.fromarray(np.clip(rgb, 0, 255).astype("uint8")).convert("RGBA")
    grid = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(grid)
    for gx in range(0, W, 72):
        d.line((gx, 0, gx, H), fill=(255, 255, 255, 22), width=2)
    for gy in range(0, H, 72):
        d.line((0, gy, W, gy), fill=(255, 255, 255, 22), width=2)
    im.alpha_composite(grid)
    return im


def _word(text, font, p):
    asc, desc = font.getmetrics()
    w = int(font.getlength(text))
    layer = Image.new("RGBA", (w + 120, asc + desc + 120))
    ImageDraw.Draw(layer).text((60, 60), text, font=font, fill="#FFFFFF")
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.25)))
    out = Image.new("RGBA", layer.size)
    out.alpha_composite(sh, (0, 5)); out.alpha_composite(layer)
    if p < 1:
        out = out.filter(ImageFilter.GaussianBlur(16 * (1 - p)))
        out.putalpha(out.split()[3].point(lambda v: int(v * (0.2 + 0.8 * p))))
    return out


def frames(it, pack):
    """[(RGBA frame, seconds)]: the words blur in over ~1 s, then the card holds."""
    color = it.get("color") or pack["colors"].get("pop", "#DE7461")
    key = (it.get("lead", ""), it.get("big", ""), color, it.get("font", "serif"))
    if key in _CACHE:
        return _CACHE[key]
    bg = background(color)
    lead, big = it.get("lead", ""), it.get("big", "")
    f_lead = load_font(SANS, 54, 600)
    px = 190
    mk = lambda s: load_font(SERIF_IT, s, 800) if it.get("font", "serif") == "serif" else load_font(SANS, s, 800)
    f_big = mk(px)
    while big and f_big.getlength(big) > 900 and px > 80:
        px -= 8
        f_big = mk(px)
    out = []
    n = int(1.0 * FPS)
    for i in range(n + 1):
        t = i / FPS
        fr = bg.copy()
        p1 = min(max(t / 0.3, 0), 1)
        p2 = min(max((t - 0.35) / 0.4, 0), 1)
        cy = H * 0.47
        if lead and p1 > 0:
            L = _word(lead, f_lead, p1)
            fr.alpha_composite(L, (int(W / 2 - L.width / 2), int(cy - (big and px * 0.55 or 0) - L.height / 2 + (1 - p1) * 14)))
        if big and p2 > 0:
            B = _word(big, f_big, p2)
            rise = (1 - (1 - p2) ** 3)                      # rises from below into focus, like the reference
            fr.alpha_composite(B, (int(W / 2 - B.width / 2), int(cy + px * 0.12 - B.height / 2 + (1 - rise) * px * 0.45)))
        out.append((fr, 1 / FPS if i < n else 999.0))
    if len(_CACHE) > 12:
        _CACHE.clear()
    _CACHE[key] = out
    return out
