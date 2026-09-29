"""Icon-based sticker styles — ~1,500 concepts × many looks, all in the brand's colours.

Sources (bundled or cached, all allow commercial use):
  - Phosphor icons (MIT), bundled in library/icons/ (regular, bold, thin, fill, duotone).
  - Microsoft Fluent Emoji 3D (MIT) — glossy 3D emoji, fetched on demand and cached.
  - Noto Animated Emoji (CC BY 4.0, credited in docs/CREDITS.md) — animated stickers.

Sticker names:  icon:<name>  3d:<concept>  anim:<concept|emoji>  stamp:<text>
Styles for icon stickers (ICON_STYLES): line, bold, thin, fill, duotone, chip, circle,
puffy, holo, retro, neon, cutout.
"""
import io, json, math, os, re, urllib.parse, urllib.request
from functools import lru_cache
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "library", "icons")
CACHE = os.path.join(ROOT, "library", "emoji-cache")
ICON_STYLES = ("line", "bold", "thin", "fill", "duotone", "chip", "circle", "puffy", "holo", "retro", "neon", "cutout")

# a few concept words people say that don't match Phosphor names/tags directly
ALIASES = {"money": "money", "cash": "money", "paid": "money", "pays": "money", "coffee": "coffee",
           "idea": "lightbulb", "tip": "lightbulb", "time": "clock", "hours": "clock", "love": "heart",
           "home": "house", "work": "briefcase", "email": "envelope-simple", "phone": "device-mobile",
           "growth": "trend-up", "grow": "trend-up", "sale": "tag", "shop": "shopping-bag", "baby": "baby",
           "kids": "baby", "mom": "baby", "gym": "barbell", "food": "fork-knife", "travel": "airplane-tilt",
           "sleep": "moon-stars", "morning": "sun-horizon", "night": "moon", "friends": "users-three",
           "party": "confetti", "win": "trophy", "goal": "target", "plan": "calendar-check", "study": "book-open"}


@lru_cache(maxsize=1)
def index():
    p = os.path.join(ICONS, "index.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def find(word, strict=False):
    """Best Phosphor icon name for a word, or None. strict=True (used for stickers nobody asked
    for) only accepts the icon's own name or a curated alias, never a loose tag match."""
    w = re.sub(r"[^a-z-]", "", word.lower())
    if not w:
        return None
    idx = index()
    if w in ALIASES and ALIASES[w] in idx:
        return ALIASES[w]
    for cand in (w, w.rstrip("s"), w[:-2] if w.endswith("es") else None):
        if cand and cand in idx:
            return cand
    if strict:
        return None
    for name, tags in idx.items():
        if w in tags or w.rstrip("s") in tags:
            return name
    return None


def _svg(name, weight):
    fn = os.path.join(ICONS, weight, f"{name}.svg")
    if not os.path.exists(fn):
        return None
    return open(fn).read()


def _render(svg, px, colour, second=None):
    from .stickers import svg_to_img
    svg = svg.replace('fill="currentColor"', f'fill="{colour}"')
    if second:  # duotone: the 20%-opacity layer becomes a solid second colour
        svg = re.sub(r'opacity="0\.2"', f'fill="{second}" opacity="1"', svg)
    return svg_to_img(svg, px)


def _pad(img, p):
    out = Image.new("RGBA", (img.width + 2 * p, img.height + 2 * p))
    out.alpha_composite(img, (p, p))
    return out


def _outline(img, colour, width):
    img = _pad(img, width + 4)
    a = img.split()[3].filter(ImageFilter.MaxFilter(width * 2 + 1))
    o = Image.new("RGBA", img.size, colour)
    o.putalpha(a)
    o.alpha_composite(img)
    return o


def _shadow(img, offset=(6, 10), blur=10, alpha=0.35, colour=(0, 0, 0)):
    img = _pad(img, blur * 2 + max(offset))
    sh = Image.new("RGBA", img.size, colour)
    sh.putalpha(img.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))
    out = Image.new("RGBA", img.size)
    out.alpha_composite(sh, offset)
    out.alpha_composite(img)
    return out


def _mix(hex_a, hex_b, k):
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def _gloss(img):
    """Puffy highlight: a soft white sheen on the upper part of the shape."""
    a = img.split()[3]
    w, h = img.size
    grad = Image.linear_gradient("L").resize((w, h)).transpose(Image.FLIP_TOP_BOTTOM)
    sheen = Image.new("RGBA", img.size, (255, 255, 255, 0))
    inner = a.filter(ImageFilter.MinFilter(max(3, (w // 18) | 1))).filter(ImageFilter.GaussianBlur(w / 40))
    sheen.putalpha(ImageChops.multiply(inner, grad.point(lambda v: int(max(0, v - 120) * 0.9))))
    out = img.copy()
    out.alpha_composite(sheen)
    # rim shade at the bottom for depth
    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    edge = ImageChops.subtract(a, a.filter(ImageFilter.MinFilter(max(3, (w // 30) | 1))))
    shade.putalpha(ImageChops.multiply(edge, grad.transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * 0.35))))
    out.alpha_composite(shade)
    return out


def _holo(img):
    """Holographic fill: pastel rainbow diagonal gradient inside the shape."""
    w, h = img.size
    grad = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(grad)
    stops = [(255, 179, 222), (183, 164, 255), (148, 222, 255), (178, 255, 214), (255, 243, 176), (255, 179, 222)]
    for x in range(-h, w):
        k = (x + h) / (w + h) * (len(stops) - 1)
        i = min(int(k), len(stops) - 2)
        f = k - i
        c = tuple(int(stops[i][j] + (stops[i + 1][j] - stops[i][j]) * f) for j in range(3))
        d.line((x, 0, x + h, h), fill=c + (255,), width=2)
    grad.putalpha(img.split()[3])
    return _gloss(grad)


def icon_sticker(name, pack, px, style="chip", colour_key="pop"):
    c = pack["colors"]
    col, alt = c.get(colour_key, c["pop"]), c.get("accent" if colour_key == "pop" else "pop", c["accent"])
    paper = c.get("paper", "#FFFFFF")
    from .packs import _lum
    dark = min([v for v in c.values() if isinstance(v, str) and v.startswith("#")], key=_lum)
    weight = {"line": "regular", "bold": "bold", "thin": "thin", "neon": "thin", "duotone": "duotone",
              "circle": "duotone", "cutout": "bold"}.get(style, "fill")
    svg = _svg(name, weight)
    if svg is None:
        return None
    if style in ("line", "bold", "thin", "fill"):
        return _shadow(_render(svg, px, col), (3, 5), 6, 0.25)
    if style == "duotone":
        return _shadow(_render(svg, px, dark, second=col), (3, 5), 6, 0.2)
    if style == "cutout":  # classic die-cut sticker: bold icon, thick paper edge, soft shadow
        return _shadow(_outline(_render(svg, int(px * 0.8), col), paper, max(6, px // 18)), (4, 8), 8, 0.3)
    if style == "chip":  # app-icon style: white glyph on a rounded colour tile
        tile = Image.new("RGBA", (px, px))
        ImageDraw.Draw(tile).rounded_rectangle((0, 0, px - 1, px - 1), radius=px * 0.26, fill=col)
        glyph = _render(svg, int(px * 0.58), paper)
        tile.alpha_composite(glyph, ((px - glyph.width) // 2, (px - glyph.height) // 2))
        return _shadow(_gloss(tile), (0, 10), 12, 0.3)
    if style == "circle":  # duotone glyph in a paper circle with a colour ring
        disc = Image.new("RGBA", (px, px))
        ImageDraw.Draw(disc).ellipse((2, 2, px - 3, px - 3), fill=paper, outline=col, width=max(4, px // 22))
        glyph = _render(svg, int(px * 0.6), dark, second=col)
        disc.alpha_composite(glyph, ((px - glyph.width) // 2, (px - glyph.height) // 2))
        return _shadow(disc, (0, 8), 10, 0.25)
    if style == "puffy":  # 3D-ish puffy vinyl sticker
        body = _render(svg, int(px * 0.82), col)
        return _shadow(_outline(_gloss(body), paper, max(7, px // 16)), (0, 10), 12, 0.3)
    if style == "holo":
        body = _holo(_render(svg, int(px * 0.82), "#FFFFFF"))
        return _shadow(_outline(body, paper, max(6, px // 18)), (0, 8), 10, 0.28)
    if style == "retro":  # flat colour + dark outline + hard offset shadow
        body = _outline(_render(svg, int(px * 0.82), col), dark, max(3, px // 45))
        hard = Image.new("RGBA", body.size, dark)
        hard.putalpha(body.split()[3])
        out = Image.new("RGBA", (body.width + 12, body.height + 12))
        out.alpha_composite(hard, (10, 10))
        out.alpha_composite(body)
        return out
    if style == "neon":
        from .stickers import _glow
        return _glow(_render(svg, int(px * 0.85), col), col)
    return _render(svg, px, col)


# ---------------------------------------------------------------- 3D + animated emoji
def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "reel-studio"}), timeout=20) as r:
        return r.read()


def fluent3d(concept, px):
    from .emoji import NAMES
    name = NAMES.get(concept.lower(), concept)
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, "3d_" + re.sub(r"[^a-z0-9]+", "_", name.lower()) + ".png")
    if not os.path.exists(cache):
        base = name.lower().replace(" ", "_").replace("-", "_")
        folder = urllib.parse.quote(name)
        for url in (f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{folder}/3D/{base}_3d.png",
                    f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{folder}/Default/3D/{base}_3d_default.png"):
            try:
                open(cache, "wb").write(_get(url))
                break
            except Exception:
                continue
    if not os.path.exists(cache):
        return None
    img = Image.open(cache).convert("RGBA")
    img = img.resize((px, int(img.height * px / img.width)), Image.LANCZOS)
    return _shadow(img, (0, 10), 12, 0.25)


# concept -> emoji character for the animated set
ANIM = {"fire": "🔥", "love": "😍", "heart": "❤️", "party": "🎉", "laugh": "😂", "wow": "🤩", "sparkles": "✨",
        "coffee": "☕", "money": "💸", "rocket": "🚀", "cry": "😭", "think": "🤔", "clap": "👏", "100": "💯",
        "eyes": "👀", "cool": "😎", "shock": "😱", "sun": "☀️", "star": "⭐", "check": "✅", "idea": "💡",
        "muscle": "💪", "wave": "👋", "sleep": "😴", "hug": "🤗", "ok": "👌", "pray": "🙏", "gift": "🎁"}


@lru_cache(maxsize=64)
def animated(key, px):
    """List of (RGBA frame, seconds) for an animated emoji (Noto Animated Emoji, CC BY 4.0)."""
    ch = ANIM.get(key.lower(), key)
    cps = "_".join(f"{ord(c):x}" for c in ch if ord(c) != 0xFE0F)
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, f"anim_{cps}.webp")
    if not os.path.exists(cache):
        try:
            open(cache, "wb").write(_get(f"https://fonts.gstatic.com/s/e/notoemoji/latest/{cps}/512.webp"))
        except Exception:
            return []
    im = Image.open(cache)
    frames = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        f = im.convert("RGBA").resize((px, px), Image.LANCZOS)
        frames.append((f, (im.info.get("duration") or 40) / 1000))
    return frames


def stamp(text, pack, px=300, colour_key="pop", font=None):
    """Round rubber-stamp sticker with text around the ring."""
    from .textfit import load_font
    c = pack["colors"]
    col = c.get(colour_key, c["pop"])
    img = Image.new("RGBA", (px, px))
    d = ImageDraw.Draw(img)
    w = max(4, px // 40)
    d.ellipse((w, w, px - w, px - w), outline=col, width=w)
    d.ellipse((px * 0.2, px * 0.2, px * 0.8, px * 0.8), outline=col, width=max(2, w // 2))
    spec = font or pack["fonts"]["main"]
    font = load_font(spec["file"], int(px * 0.1), spec.get("weight"))
    txt = (text.upper() + " • ") * 3
    r = px * 0.38
    n = len(txt)
    for i, ch in enumerate(txt[: max(1, int(n * 0.98))]):
        ang = -90 + 360 * i / n
        glyph = Image.new("RGBA", (int(px * 0.14), int(px * 0.14)))
        ImageDraw.Draw(glyph).text((glyph.width / 2, glyph.height / 2), ch, font=font, fill=col, anchor="mm")
        glyph = glyph.rotate(-ang - 90, resample=Image.BICUBIC)
        x = px / 2 + r * math.cos(math.radians(ang)) - glyph.width / 2
        y = px / 2 + r * math.sin(math.radians(ang)) - glyph.height / 2
        img.alpha_composite(glyph, (int(x), int(y)))
    star = [(px / 2 + (px * (0.14 if k % 2 == 0 else 0.06)) * math.cos(math.pi * k / 5 - math.pi / 2),
             px / 2 + (px * (0.14 if k % 2 == 0 else 0.06)) * math.sin(math.pi * k / 5 - math.pi / 2)) for k in range(10)]
    d.polygon(star, fill=col)
    return img.rotate(-12, resample=Image.BICUBIC, expand=True)
