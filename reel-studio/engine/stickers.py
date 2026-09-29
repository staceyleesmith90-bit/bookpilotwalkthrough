"""Sticker studio: an open, uncapped sticker library that restyles to any brand.

Stickers come from two places, and both are searched by concept tags:
  1. GENERATORS  - small functions that draw a sticker in code (below).
  2. library/stickers/*.svg - any SVG someone (or Claude) adds, with tags in
     library/stickers/index.json. Use colour placeholders {ink} {pop} {accent}
     {paper} and {stroke} so the sticker recolours to every pack.

When a reel needs a concept that doesn't exist yet, Claude draws a new SVG in
the same style (stroke-only, round caps, hand-drawn wobble), saves it to the
library with tags, and it's available to every future reel.
"""
import io, json, math, os, random, re
from PIL import Image, ImageDraw
from . import emoji

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library", "stickers")
GENERATORS = {}  # name -> (fn, tags)


def sticker(name, tags):
    def deco(fn):
        GENERATORS[name] = (fn, set(tags) | {name})
        return fn
    return deco


# ---------------------------------------------------------------- drawing kit
class Pen:
    """Stroke style for one pack: colours, weight, wobble and die-cut outline."""

    def __init__(self, pack, colour_key="accent", seed=0, style=None):
        s = pack.get("sticker", {})
        self.style = style or s.get("style", "doodle")
        col = pack["colors"][colour_key]
        self.ink = pack["colors"]["ink"] if pack["colors"]["ink"] != pack["colors"]["bg"] else "#1E1E1E"
        self.paper = pack["colors"]["paper"]
        self.w = s.get("stroke", 8)
        self.wob = s.get("wobble", 3)
        self.die_cut = s.get("die_cut", False)
        if self.style in ("flat", "retro"):
            # solid colour shapes with a dark outline (retro adds an offset shadow)
            self.c, self.fill, self.w, self.wob = _dark(self.paper, pack), col, max(self.w, 8), min(self.wob, 1.5)
        else:
            self.c = col
            self.fill = self.paper if s.get("fill") == "paper" else "none"
        self.r = random.Random(seed)

    def jitter(self, pts):
        return [(x + self.r.uniform(-self.wob, self.wob), y + self.r.uniform(-self.wob, self.wob)) for x, y in pts]

    def path(self, pts, closed=False, fill=None, width=None):
        pts = self.jitter(pts)
        if closed:
            pts = pts + pts[:1]
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for i in range(len(pts) - 1):
            p0 = pts[i - 1] if i else pts[i]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        return (f'<path d="{d}" stroke="{self.c}" stroke-width="{width or self.w}" '
                f'fill="{fill if fill is not None else "none"}"/>')

    def ellipse_pts(self, cx, cy, rx, ry, n=14, a0=0, a1=2 * math.pi):
        return [(cx + rx * math.cos(a), cy + ry * math.sin(a))
                for a in [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]]

    def svg(self, body, size=200):
        if self.style == "retro":  # hard offset shadow, 70s/80s poster feel
            shadow = re.sub(r'(stroke|fill)="(?!none)[^"]+"', lambda m: f'{m.group(1)}="{self.c}"', body)
            body = f'<g transform="translate(8,8)">{shadow}</g>' + body
        if self.die_cut:  # white "sticker" outline behind everything
            outline = re.sub(r'stroke="[^"]+"', f'stroke="{self.paper}"', body)
            outline = re.sub(r'stroke-width="([\d.]+)"',
                             lambda m: f'stroke-width="{float(m.group(1)) + 14}"', outline)
            body = outline + body
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 {size + 20} {size + 20}" '
                f'fill="none" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def _dark(paper, pack):
    """Outline colour for flat/retro stickers: the pack's darkest colour."""
    from .packs import _lum
    cols = [v for v in pack["colors"].values() if isinstance(v, str) and v.startswith("#")]
    return min(cols, key=_lum)


# ---------------------------------------------------------------- base set
# These are starters, not a limit. Claude adds more generators or SVGs freely.
@sticker("sparkle", ["shine", "new", "magic", "wow", "result", "glow", "win"])
def sparkle(p):
    pts = [(100 + (80 if i % 2 == 0 else 18) * math.cos(i * math.pi / 4 - math.pi / 2),
            100 + (80 if i % 2 == 0 else 18) * math.sin(i * math.pi / 4 - math.pi / 2)) for i in range(8)]
    return p.svg(p.path(pts, closed=True, fill=p.fill) + p.path([(160, 38), (160, 62)]) + p.path([(148, 50), (172, 50)]))


@sticker("arrow", ["look", "point", "this", "here", "direction", "next", "up", "growth"])
def arrow(p):
    return p.svg(p.path([(30, 165), (60, 115), (110, 92), (165, 62)]) + p.path([(135, 50), (168, 60), (150, 90)]))


@sticker("underline", ["emphasis", "important", "key"])
def underline(p):
    return p.svg(p.path([(15, 120), (60, 110), (110, 116), (160, 104), (190, 108), (185, 118), (120, 128), (60, 124), (30, 130)], width=p.w + 2))


@sticker("circle", ["highlight", "focus", "this"])
def circle(p):
    return p.svg(p.path(p.ellipse_pts(100, 100, 82, 56, 16, -0.3, 2 * math.pi + 0.5)))


@sticker("heart", ["love", "family", "kids", "care", "favourite", "favorite", "grateful"])
def heart(p):
    return p.svg(p.path([(100, 170), (40, 110), (40, 60), (75, 45), (100, 75), (125, 45), (160, 60), (160, 110)], closed=True, fill=p.fill))


@sticker("clock", ["time", "hours", "minutes", "late", "fast", "slow", "schedule", "deadline"])
def clock(p):
    face = p.path(p.ellipse_pts(100, 105, 70, 70, 16), closed=True, fill=p.fill)
    hands = p.path([(100, 105), (100, 65)]) + p.path([(100, 105), (130, 118)])
    ticks = "".join(p.path([(100 + 58 * math.cos(a), 105 + 58 * math.sin(a)), (100 + 64 * math.cos(a), 105 + 64 * math.sin(a))], width=p.w * .6)
                    for a in [0, math.pi / 2, math.pi, 3 * math.pi / 2])
    bells = p.path([(55, 50), (70, 38)]) + p.path([(145, 50), (130, 38)])
    return p.svg(face + ticks + hands + bells)


@sticker("coffee", ["coffee", "morning", "tea", "cup", "latte", "break", "tired"])
def coffee(p):
    cup = p.path([(45, 90), (155, 90), (145, 160), (125, 175), (75, 175), (55, 160)], closed=True, fill=p.fill)
    handle = p.path(p.ellipse_pts(158, 122, 22, 22, 9, -math.pi / 2, math.pi / 2))
    steam = "".join(p.path([(x, 75), (x - 8, 60), (x + 6, 45), (x - 4, 28)], width=p.w * .75) for x in (78, 100, 122))
    return p.svg(cup + handle + steam)


@sticker("money", ["money", "income", "paid", "price", "cash", "dollar", "rand", "sale", "profit", "earn", "cost", "pays"])
def money(p):
    coin = p.path(p.ellipse_pts(100, 100, 75, 75, 16), closed=True, fill=p.fill)
    inner = p.path(p.ellipse_pts(100, 100, 58, 58, 14), closed=True, width=p.w * .5)
    s = p.path([(122, 72), (100, 64), (80, 74), (84, 94), (116, 106), (120, 126), (100, 136), (76, 128)])
    bar = p.path([(100, 52), (100, 148)], width=p.w * .8)
    return p.svg(coin + inner + s + bar)


@sticker("lightbulb", ["idea", "tip", "hack", "learn", "smart", "think", "secret", "trick"])
def lightbulb(p):
    bulb = p.path([(80, 140), (70, 115), (55, 90), (58, 60), (80, 38), (120, 38), (142, 60), (145, 90), (130, 115), (120, 140)], fill=p.fill)
    base = p.path([(82, 152), (118, 152)]) + p.path([(86, 166), (114, 166)])
    rays = "".join(p.path([(100 + 88 * math.cos(a), 88 + 88 * math.sin(a)), (100 + 100 * math.cos(a), 88 + 100 * math.sin(a))], width=p.w * .7)
                   for a in [-math.pi / 2, -math.pi / 4, -3 * math.pi / 4, 0, math.pi])
    return p.svg(bulb + base + rays)


@sticker("check", ["done", "yes", "easy", "works", "step", "complete", "approved"])
def check(p):
    return p.svg(p.path([(40, 105), (85, 150), (165, 50)], width=p.w + 4))


@sticker("phone", ["phone", "instagram", "app", "social", "post", "scroll", "dm", "text"])
def phone(p):
    body = p.path([(65, 25), (135, 25), (145, 35), (145, 170), (135, 180), (65, 180), (55, 170), (55, 35)], closed=True, fill=p.fill)
    return p.svg(body + p.path([(88, 40), (112, 40)], width=p.w * .6) + p.path([(92, 162), (108, 162)], width=p.w * .6))


@sticker("camera", ["camera", "film", "video", "record", "reel", "content", "shoot", "photo"])
def camera(p):
    body = p.path([(30, 70), (70, 70), (82, 50), (118, 50), (130, 70), (170, 70), (170, 160), (30, 160)], closed=True, fill=p.fill)
    lens = p.path(p.ellipse_pts(100, 113, 30, 30, 12), closed=True)
    return p.svg(body + lens + p.path([(148, 88), (152, 88)]))


@sticker("star", ["star", "best", "favourite", "review", "top", "rating"])
def star(p):
    pts = [(100 + (82 if i % 2 == 0 else 34) * math.cos(i * math.pi / 5 - math.pi / 2),
            105 + (82 if i % 2 == 0 else 34) * math.sin(i * math.pi / 5 - math.pi / 2)) for i in range(10)]
    return p.svg(p.path(pts, closed=True, fill=p.fill))


@sticker("thought-bubble", ["thought", "wonder", "hmm", "question", "maybe"])
def thought_bubble(p):
    return p.svg(bubble_shape(p, 200, 150))


def bubble_shape(p, w, h):
    """Cloud-shaped bubble sized w x h (tail included). Scales to fit any text."""
    cx, cy, rx, ry = w / 2, h * 0.42, w * 0.40, h * 0.30
    n = 9
    lobes = ""
    for i in range(n):
        a = 2 * math.pi * i / n
        r = min(rx, ry) * p.r.uniform(0.42, 0.55)
        lobes += p.path(p.ellipse_pts(cx + rx * math.cos(a), cy + ry * math.sin(a), r, r, 10), closed=True, fill=p.paper)
    core = f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{p.paper}"/>'
    tail = (p.path(p.ellipse_pts(w * .28, h * .86, h * .06, h * .06, 8), closed=True, fill=p.paper, width=p.w * .8) +
            p.path(p.ellipse_pts(w * .20, h * .97, h * .035, h * .035, 8), closed=True, fill=p.paper, width=p.w * .6))
    return lobes + core + tail


# ---------------------------------------------------------------- library + search
def _svg_library():
    idx_path = os.path.join(LIB, "index.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    return {name: set(meta.get("tags", [])) | {name} for name, meta in idx.items()
            if os.path.exists(os.path.join(LIB, f"{name}.svg"))}


def all_stickers():
    items = {n: t for n, (_, t) in GENERATORS.items()}
    items.update(_svg_library())
    return items


def find(concept, icons=True, strict=False):
    """Best sticker for a concept word: our drawn set first, then ~1,500 icons.
    None means nothing fits (=> Claude draws a new one)."""
    c = concept.lower().rstrip("s")
    for name, tags in all_stickers().items():
        if c == name or c in {t.rstrip("s") for t in tags}:
            return name
    if icons:
        from .iconstickers import find as ifind
        hit = ifind(concept, strict=strict)
        if hit:
            return "icon:" + hit
    return None


def plan_for_lines(lines, max_per_reel=6):
    """Auto-sticker planner: picks stickers from the words people actually say.

    This is the fallback the engine uses on its own. In the full flow Claude
    reads the script, picks moments with meaning, and extends this plan with new
    drawings for anything the library doesn't have yet.
    """
    plan, used = [], set()
    for i, line in enumerate(lines):
        for word in re.findall(r"[a-zA-Z']+", line.lower()):
            name = find(word)
            if name and name not in used:
                plan.append((i, name, word))
                used.add(name)
                break
        if len(plan) >= max_per_reel:
            break
    return plan


STYLES = ("doodle", "flat", "retro", "neon", "emoji",  # drawn / emoji
          "line", "bold", "thin", "fill", "duotone", "chip", "circle", "puffy", "holo", "cutout")  # icon styles


def sticker_font(pack, kind="lettering", font=None):
    """The font for words on stickers. This sticker's own choice (timeline "font") wins, then the
    brand's sticker font (pack sticker.font for lettered stickers, sticker.label_font for badges and
    stamps), otherwise automatic: the brand's script font for lettering, its main font for labels.
    Choices can be a brand role ("script", "serif", "sans", "main"…), an uploaded font name, or a path."""
    from . import titles
    from .packs import resolve_font
    st = pack.get("sticker", {})
    spec = resolve_font(pack, font) or resolve_font(pack, st.get("font" if kind == "lettering" else "label_font"))
    if spec:
        return spec
    tf = titles.fonts_for(pack)
    # lettering needs weight to read on video: the brand's brush script, else its script
    return tf.get("brush", tf["script"]) if kind == "lettering" else pack["fonts"]["main"]


def render(name, pack, px, colour_key="accent", seed=0, style=None, font=None):
    """Render any sticker at px wide, in the pack's colours and sticker style.

    name: a generator, a library SVG, 'emoji:<concept|name|char>' or 'badge:<text>'.
    style: override the pack style (doodle | flat | retro | neon | emoji).
    """
    style = style or pack.get("sticker", {}).get("style", "doodle")
    from . import iconstickers as ic
    if style == "glass":  # the premium kit: frosted glass, serif words — never clip-art
        from . import premium
        ck = colour_key if colour_key in pack["colors"] else "pop"
        if name.startswith("badge:"):
            return premium.glass_chip(name[6:], pack, px, ck)
        if name.startswith("stamp:"):
            return premium.glass_chip(name[6:], pack, px, ck)
        if name.startswith("custom:"):
            _log_request(name[7:])
            return premium.serif_word(name[7:], pack, px, ck, font)
        if name.startswith(("3d:", "anim:", "emoji:")):
            pass                                    # explicit asks still render as asked
        else:
            icon = name[5:] if name.startswith("icon:") else ic.find(name)
            if icon:
                return premium.glass_icon(icon, pack, int(px * 0.8), ck)
            return premium.serif_word(name.replace("-", " "), pack, px, ck, font)
    if name.startswith("icon:"):
        st = style if style in ic.ICON_STYLES else "cutout"
        return ic.icon_sticker(name[5:], pack, px, st, colour_key if colour_key in pack["colors"] else "pop")
    if name.startswith("3d:"):
        return ic.fluent3d(name[3:], px)
    if name.startswith("anim:"):
        fr = ic.animated(name[5:], px)
        return fr[0][0] if fr else None
    if name.startswith("stamp:"):
        return ic.stamp(name[6:], pack, px, colour_key if colour_key in pack["colors"] else "pop",
                        font=sticker_font(pack, "label", font))
    if style in ic.ICON_STYLES and name not in GENERATORS and not name.startswith(("badge:", "emoji:")):
        found = ic.find(name)
        if found:
            return ic.icon_sticker(found, pack, px, style, colour_key if colour_key in pack["colors"] else "pop")
    if name.startswith("badge:"):
        return badge(name[6:], pack, px=px, colour_key=colour_key, font=font)
    if name.startswith("emoji:") or (style == "emoji" and emoji.get_svg(name)):
        svg_text = emoji.get_svg(name.split(":", 1)[-1])
        if not svg_text:
            return None
        img = svg_to_img(svg_text, px)
        return _outline(img, pack["colors"]["paper"], 10) if pack.get("sticker", {}).get("die_cut") else img
    pen = Pen(pack, colour_key, seed, style if style != "emoji" else None)
    if name.startswith("custom:"):
        return custom_sticker(name[7:], pack, px, colour_key, font)
    if name in GENERATORS:
        svg_text = GENERATORS[name][0](pen)
    elif not os.path.exists(os.path.join(LIB, f"{name}.svg")):
        # not in our drawings: try the icon library, else make a custom sticker right now
        from . import iconstickers as ic2
        hit = ic2.find(name)
        if hit:
            st = style if style in ic2.ICON_STYLES else "cutout"
            return ic2.icon_sticker(hit, pack, px, st, colour_key if colour_key in pack["colors"] else "pop")
        return custom_sticker(name, pack, px, colour_key, font)
    else:
        raw = open(os.path.join(LIB, f"{name}.svg")).read()
        fill = pen.fill if pen.fill != "none" else pack["colors"]["paper"]
        svg_text = (raw.replace("{ink}", pack["colors"]["ink"]).replace("{pop}", pack["colors"]["pop"])
                    .replace("{accent}", pen.c).replace("{paper}", fill)
                    .replace("{stroke}", str(pen.w)))
    img = svg_to_img(svg_text, px)
    if pen.style == "neon":
        img = _glow(img, pack["colors"][colour_key])
    return img


def _outline(img, colour, width):
    from PIL import ImageFilter
    pad = width * 2
    base = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2))
    base.alpha_composite(img, (pad, pad))
    alpha = base.split()[3].filter(ImageFilter.MaxFilter(width * 2 + 1))
    out = Image.new("RGBA", base.size, colour)
    out.putalpha(alpha)
    out.alpha_composite(base)
    return out


def _glow(img, colour):
    from PIL import ImageFilter
    pad = 30
    base = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2))
    base.alpha_composite(img, (pad, pad))
    glow = Image.new("RGBA", base.size, colour)
    glow.putalpha(base.split()[3].filter(ImageFilter.GaussianBlur(14)))
    out = Image.new("RGBA", base.size)
    for _ in range(2):
        out.alpha_composite(glow)
    # bright core
    core = Image.new("RGBA", base.size, "#FFFFFF")
    core.putalpha(base.split()[3].point(lambda a: int(a * 0.55)))
    out.alpha_composite(base)
    out.alpha_composite(core)
    return out


REQUESTS = os.path.join(LIB, "requests.json")


def custom_sticker(text, pack, px=300, colour_key="pop", font=None):
    """Never 'no sticker': when a concept isn't in the library, Reel Studio makes one on the spot —
    the word hand-lettered in the brand's script font, die-cut, with a little sparkle — and logs the
    concept so Claude draws a proper illustrated sticker for next time (library/stickers/requests.json)."""
    from . import titles
    from .iconstickers import _outline, _shadow
    word = text.replace("-", " ").replace("_", " ").strip()
    c = pack["colors"]
    col = c.get(colour_key, c["pop"])
    f = sticker_font(pack, "lettering", font)
    old_k = titles._K
    titles._K = 1.0
    try:
        lettering = titles.draw_text(word, f, px * 0.42, col, 0, {"shadow": False})
    finally:
        titles._K = old_k
    lettering.thumbnail((int(px * 1.25), int(px * 0.7)))
    spark = svg_to_img(sparkle(Pen(dict(pack, sticker=dict(pack.get("sticker", {}), style="flat")), "accent", 3)), int(px * 0.28))
    canvas = Image.new("RGBA", (lettering.width + spark.width // 2 + 10, lettering.height + spark.height // 2 + 10))
    canvas.alpha_composite(lettering, (0, spark.height // 2))
    canvas.alpha_composite(spark, (canvas.width - spark.width, 0))
    img = _shadow(_outline(canvas, c.get("paper", "#FFFFFF"), max(6, px // 22)), (0, 6), 8, 0.28)
    _log_request(word)
    return img


def _log_request(word):
    try:
        req = json.load(open(REQUESTS)) if os.path.exists(REQUESTS) else {}
        req[word] = req.get(word, 0) + 1
        json.dump(req, open(REQUESTS, "w"), indent=1)
    except OSError:
        pass


BADGE_SHAPES = ("burst", "pill", "tag", "circle")


def badge(text, pack, shape="burst", px=320, colour_key="pop", font=None):
    """A label sticker with text inside: 'NEW', 'TIP #1', '$2,000', 'FREE', 'STEP 2'.
    Text always fits (textfit)."""
    from . import textfit
    from .packs import contrast
    if shape == "glass":
        from .premium import glass_chip
        return glass_chip(text, pack, px, colour_key)
    fill = pack["colors"][colour_key]
    ink = _dark(pack["colors"]["paper"], pack)
    txt_col = ink if contrast(ink, fill) >= contrast(pack["colors"]["paper"], fill) else pack["colors"]["paper"]
    if shape == "chip":  # modern die-cut pill: brand colour, bold text, white edge, soft shadow + gloss
        from . import textfit
        from .iconstickers import _outline, _shadow
        f = sticker_font(pack, "label", font)
        white = "#FFFFFF"
        tcol = white if contrast(white, fill) >= contrast(ink, fill) else ink
        fit = textfit.fit_text(text.upper(), f["file"], px * 1.5, px * 0.26, max_px=int(px * 0.24), min_px=14,
                               weight=f.get("weight"), max_lines=1)
        t = textfit.render_block(fit, tcol)
        h = int(t.height + px * 0.2)
        w = int(t.width + px * 0.3)
        body = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(body)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=fill)
        gloss = Image.new("RGBA", (w, h))
        ImageDraw.Draw(gloss).rounded_rectangle((h * 0.18, h * 0.1, w - h * 0.18, h * 0.42), radius=h // 5,
                                                fill=(255, 255, 255, 60))
        body.alpha_composite(gloss)
        body.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
        return _shadow(_outline(body, white, max(6, px // 28)), (0, 6), 8, 0.3)
    if shape == "burst":
        n, pts = 16, []
        for i in range(n * 2):
            r = 96 if i % 2 == 0 else 80
            a = math.pi * i / n
            pts.append(f"{100 + r * math.cos(a):.1f},{100 + r * math.sin(a):.1f}")
        body = f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{ink}" stroke-width="5"/>'
        box, h = (200, 200), 200
        text_box = (110, 80)
    elif shape == "circle":
        body = f'<circle cx="100" cy="100" r="92" fill="{fill}" stroke="{ink}" stroke-width="5"/>'
        box, h, text_box = (200, 200), 200, (130, 90)
    else:
        h = 90
        notch = '' if shape == "pill" else f'<circle cx="26" cy="{h/2}" r="7" fill="{pack["colors"]["paper"]}"/>'
        rx = h / 2 if shape == "pill" else 12
        body = (f'<rect x="3" y="3" width="194" height="{h - 6}" rx="{rx}" fill="{fill}" stroke="{ink}" '
                f'stroke-width="5"/>{notch}')
        box, text_box = (200, h), (150 if shape == "tag" else 165, h * 0.62)
    svg_text = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {box[0]} {box[1]}">{body}</svg>')
    img = svg_to_img(svg_text, px, int(px * box[1] / box[0]))
    f = sticker_font(pack, "label", font)
    k = px / box[0]
    fit = textfit.fit_text(text.upper() if f.get("case") == "upper" else text, f["file"],
                           text_box[0] * k, text_box[1] * k, max_px=int(px * 0.3), min_px=14,
                           weight=f.get("weight"), max_lines=2)
    t = textfit.render_block(fit, txt_col)
    x_off = 8 * k if shape == "tag" else 0
    img.alpha_composite(t, (int((img.width - t.width) / 2 + x_off), int((img.height - t.height) / 2)))
    return img


def svg_to_img(svg_text, px_w, px_h=None):
    """SVG -> RGBA image. Uses resvg (prebuilt for Windows and Mac, no system libraries);
    falls back to CairoSVG where resvg isn't installed."""
    try:
        import resvg_py
        kw = {"width": int(px_w)}
        if px_h:
            kw["height"] = int(px_h)
        png = bytes(resvg_py.svg_to_bytes(svg_string=svg_text, **kw))
    except ImportError:
        import cairosvg
        png = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=px_w, output_height=px_h)
    return Image.open(io.BytesIO(png)).convert("RGBA")
