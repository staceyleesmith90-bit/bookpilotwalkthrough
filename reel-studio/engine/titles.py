"""Title designer: layered, animated titles (our own designs).

A title is a stack of layers — small tracked caps, a big script word laid over a serif word,
a date line, a pill tag, sparkles — each with its own font role, colour, effect and animation.
Fonts come from the pack's `title_fonts` (serif / script / sans), so every brand gets its own
pairing. Layers can sit BEHIND the person on video (`behind: true`).

Use in a plan:  "title": {"template": "with-me", "title": "A Day With Me",
                           "kicker": "mini vlog", "sub": "January 2026", "behind": false}
"""
import math, os
from PIL import Image, ImageDraw, ImageFilter
from . import stickers
from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_K = 1.0  # global size factor for the title being built (spec "size", default 1.3)

DEFAULT_TITLE_FONTS = {
    "serif": {"file": "library/fonts/BodoniModa-Variable.ttf", "weight": 500},
    "serif_bold": {"file": "library/fonts/AbrilFatface-Regular.ttf"},
    "script": {"file": "library/fonts/PinyonScript-Regular.ttf"},
    "brush": {"file": "library/fonts/KaushanScript-Regular.ttf"},
    "sans": {"file": "library/fonts/Montserrat-Variable.ttf", "weight": 600},
    "mono": {"file": "library/fonts/CourierPrime-Regular.ttf"},
}


def fonts_for(pack):
    f = dict(DEFAULT_TITLE_FONTS)
    f.update(pack.get("title_fonts", {}))
    for v in f.values():
        if not os.path.isabs(v["file"]):
            v["file"] = os.path.join(ROOT, v["file"])
    return f


# ---------------------------------------------------------------- drawing
def draw_text(text, font_spec, size, color, tracking=0.0, effect=None):
    """Text with letter-spacing (tracking, in em) and an optional effect:
    shadow (soft drop), glow, stroke (outline), sticker (thick paper outline)."""
    effect = effect or {}
    size = size * _K
    font = load_font(font_spec["file"], int(size), font_spec.get("weight"))
    track = tracking * size
    chars = list(text)
    widths = [font.getlength(c) for c in chars]
    total = sum(widths) + track * max(len(chars) - 1, 0)
    asc, desc = font.getmetrics()
    stroke = effect.get("stroke", 0)
    pad = int(size * 0.35) + stroke * 2 + (effect.get("sticker", 0) * 2)
    W, H = int(total) + pad * 2 + 4, asc + desc + pad * 2
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    x = pad
    for c, w in zip(chars, widths):
        d.text((x, pad), c, font=font, fill=color, stroke_width=stroke,
               stroke_fill=effect.get("stroke_color", "#000000"))
        x += w + track
    alpha = im.split()[3]
    layers = []
    if effect.get("sticker"):  # thick paper outline, like a die-cut sticker
        k = effect["sticker"]
        o = Image.new("RGBA", im.size, effect.get("sticker_color", "#FFFFFF"))
        o.putalpha(alpha.filter(ImageFilter.MaxFilter(k * 2 + 1)))
        layers.append(o)
    if effect.get("glow"):
        g = Image.new("RGBA", im.size, effect.get("glow_color", color))
        g.putalpha(alpha.filter(ImageFilter.GaussianBlur(size * 0.12)).point(lambda a: min(255, int(a * 1.6))))
        layers.append(g)
    if effect.get("shadow", True):
        s = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, effect.get("shadow_color", (0, 0, 0)))
        sh.putalpha(alpha.filter(ImageFilter.GaussianBlur(max(2, size * 0.05))).point(lambda a: int(a * effect.get("shadow_alpha", 0.45))))
        s.alpha_composite(sh, (int(size * 0.02), int(size * 0.04)))
        layers.append(s)
    out = Image.new("RGBA", im.size)
    for l in layers:
        out.alpha_composite(l)
    out.alpha_composite(im)
    bb = out.getbbox() or (0, 0, 1, 1)
    return out.crop(bb)


def shape(kind, w, h, color, stroke=4, fill=None):
    im = Image.new("RGBA", (int(w) + 12, int(h) + 12))
    d = ImageDraw.Draw(im)
    box = (6, 6, 6 + w, 6 + h)
    if kind == "oval":
        d.ellipse(box, outline=color, width=stroke, fill=fill)
    elif kind == "pill":
        d.rounded_rectangle(box, radius=h / 2, outline=color, width=stroke, fill=fill)
    elif kind == "line":
        d.line((6, 6 + h / 2, 6 + w, 6 + h / 2), fill=color, width=stroke)
    return im


def pin_icon(size, color):
    im = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(im)
    r = size * 0.32
    d.ellipse((size / 2 - r, size * 0.08, size / 2 + r, size * 0.08 + 2 * r), fill=color)
    d.polygon([(size / 2 - r * 0.8, size * 0.08 + r * 1.3), (size / 2 + r * 0.8, size * 0.08 + r * 1.3),
               (size / 2, size * 0.95)], fill=color)
    d.ellipse((size / 2 - r * 0.38, size * 0.08 + r * 0.62, size / 2 + r * 0.38, size * 0.08 + r * 1.38), fill="#FFFFFF")
    return im


def _pill_tag(text, f, color_bg, color_text, size=30):
    t = draw_text(text, f["sans"], size, color_text, 0.02, {"shadow": False})
    w, h = t.width + size * 2.6, t.height + size * 0.9
    base = shape("pill", w, h, color_bg, stroke=0, fill=color_bg)
    d = ImageDraw.Draw(base)
    cy = 6 + h / 2
    d.ellipse((6 + size * 0.45, cy - size * 0.32, 6 + size * 1.1, cy + size * 0.32), outline=color_text, width=2)
    d.text((6 + size * 0.62, cy - size * 0.42), "+", fill=color_text, font=load_font(f["sans"]["file"], int(size * 0.7), 500))
    d.ellipse((6 + w - size * 1.05, cy - size * 0.3, 6 + w - size * 0.45, cy + size * 0.3), fill="#E94B8A")
    base.alpha_composite(t, (int(6 + size * 1.35), int(cy - t.height / 2)))
    return base


# ---------------------------------------------------------------- templates
# Each returns a list of layers: dict(img, dx, dy, anim, delay, behind, rotate)
# dx/dy are offsets of the layer centre from the title centre (px at 1080 wide).

def _c(pack, key, default):
    return pack["colors"].get(key, default)


def t_with_me(p, f, title, kicker="mini vlog", sub="", **_):
    """Tracked serif caps kicker · huge overlapping script (2 lines) · small serif date."""
    ink = _c(p, "title_ink", "#FFFFFF")
    words = title.split()
    mid = max(1, len(words) // 2)
    l1, l2 = " ".join(words[:mid]), " ".join(words[mid:]) or ""
    L = [dict(img=draw_text(kicker.upper(), f["serif"], 44, ink, 0.12), dy=-190, anim="fadeup", delay=0.0)]
    L.append(dict(img=draw_text(l1, f["script"], 190, ink, 0.0), dx=-40, dy=-60, anim="write", delay=0.15))
    if l2:
        L.append(dict(img=draw_text(l2, f["script"], 190, ink, 0.0), dx=40, dy=85, anim="write", delay=0.55))
    if sub:
        L.append(dict(img=draw_text(sub, f["serif"], 50, ink, 0.03), dy=215, anim="fadeup", delay=0.9))
    return L


def t_diary(p, f, title="A day in my life", kicker="visual diary", **_):
    """Small tracked sans kicker · serif caps line · script line tucked below, overlapping."""
    ink = _c(p, "title_ink", "#FFFFFF")
    words = title.split()
    cut = max(1, len(words) - 2)
    top, script = " ".join(words[:cut]), " ".join(words[cut:])
    return [dict(img=draw_text(kicker.upper(), f["sans"], 30, ink, 0.25), dy=-150, anim="track", delay=0),
            dict(img=draw_text(top.upper(), f["serif"], 130, ink, 0.01), dy=-45, anim="fadeup", delay=0.15),
            dict(img=draw_text(script.lower(), f["script"], 150, ink, 0), dx=-30, dy=70, anim="write", delay=0.45, rotate=-4)]


def t_mini(p, f, title="Mini Vlog", **_):
    """Two words: serif on top, script below crossing it."""
    ink = _c(p, "title_ink", "#FFFFFF")
    a, _, b = title.partition(" ")
    return [dict(img=draw_text(a, f["serif"], 150, ink, 0.0), dx=-10, dy=-55, anim="fadeup", delay=0),
            dict(img=draw_text(b or a, f["script"], 160, ink, 0), dx=30, dy=45, anim="write", delay=0.35, rotate=-6)]


def t_episode(p, f, title="Today Activity", kicker="mini vlog", tag="Eps #1", location="", **_):
    """Oval badge · brush script 2 lines · rotated episode tag · pin + location."""
    ink = _c(p, "title_ink", "#FFFFFF")
    k = draw_text(kicker.upper(), f["sans"], 34, ink, 0.02, {"shadow": False})
    oval = shape("oval", k.width + 70, k.height + 44, ink, stroke=5)
    oval.alpha_composite(k, ((oval.width - k.width) // 2, (oval.height - k.height) // 2))
    words = title.split()
    mid = max(1, len(words) // 2)
    L = [dict(img=oval, dy=-250, anim="pop", delay=0),
         dict(img=draw_text(" ".join(words[:mid]), f["brush"], 170, ink), dx=-50, dy=-95, anim="write", delay=0.2),
         dict(img=draw_text(" ".join(words[mid:]), f["brush"], 170, ink), dx=10, dy=60, anim="write", delay=0.5)]
    if tag:
        L.append(dict(img=draw_text(tag, f["brush"], 60, ink), dx=300, dy=-20, anim="pop", delay=0.8, rotate=-12))
    if location:
        loc = draw_text(location.upper(), f["sans"], 34, ink, 0.03)
        pin = pin_icon(int(40 * _K), _c(p, "pop", "#E94B4B"))
        row = Image.new("RGBA", (pin.width + 12 + loc.width, max(pin.height, loc.height)))
        row.alpha_composite(pin, (0, (row.height - pin.height) // 2))
        row.alpha_composite(loc, (pin.width + 12, (row.height - loc.height) // 2))
        L.append(dict(img=row, dy=200, anim="fadeup", delay=0.9))
    return L


def t_sparkle(p, f, title="Life Update", tag="", **_):
    """Chunky serif word in pop colour + script word overlapping · stars · optional pill tag."""
    pop = _c(p, "pop", "#F59AC8")
    words = title.split()
    a, b = words[0], " ".join(words[1:]) or words[0]
    L = [dict(img=draw_text(a, f["serif_bold"], 150, pop, 0, {"sticker": 7, "sticker_color": "#FFFFFF", "shadow_alpha": 0.3}),
              dx=-60, dy=-90, anim="pop", delay=0),
         dict(img=draw_text(b, f["script"], 190, "#FFFFFF", 0, {"stroke": 3, "stroke_color": "#5B2A3A", "glow": True,
                                                                    "glow_color": "#FFD6E8"}),
              dx=40, dy=40, anim="write", delay=0.3)]
    starpack = dict(p, sticker=dict(p.get("sticker", {}), style="flat", die_cut=True))
    for i, (dx, dy, s, col) in enumerate([(250, -160, 140, "pop"), (-300, 20, 110, "paper"), (270, 110, 120, "pop")]):
        img = stickers.render("star", starpack, int(s * _K), "accent" if col == "pop" else "paper", seed=i)
        L.append(dict(img=img, dx=dx, dy=dy, anim="pop", delay=0.6 + i * 0.12, rotate=[12, -10, 8][i], float=True))
    if tag:
        L.append(dict(img=_pill_tag(tag, f, "#FFFFFF", "#8A2B55"), dy=170, anim="slide", delay=0.8))
    return L


def t_headline(p, f, title="Today", script="vlog", **_):
    """Huge serif caps (goes behind the person when behind=true) + a script word crossing it."""
    ink = _c(p, "title_ink", "#FFFFFF")
    return [dict(img=draw_text(title.upper(), f["serif"], 210, ink, 0.02, {"shadow_alpha": 0.25}), dy=-20,
                 anim="scale", delay=0),
            dict(img=draw_text(script, f["script"], 170, _c(p, "title_accent", ink), 0, {"shadow_alpha": 0.55}),
                 dx=150, dy=105, anim="write", delay=0.45, rotate=-6, behind=False)]


def t_slice(p, f, title="Slice of Weekend", **_):
    """Light serif lead-in + bold serif word."""
    ink = _c(p, "title_ink", "#FFFFFF")
    words = title.split()
    lead, main = " ".join(words[:-1]), words[-1]
    return [dict(img=draw_text(lead, f["serif"], 80, ink, 0.01), dx=-40, dy=-55, anim="fadeup", delay=0),
            dict(img=draw_text(main, f["serif_bold"], 130, ink, 0.0), dy=40, anim="fadeup", delay=0.25)]


def t_location(p, f, title="Cape Town", sub="", **_):
    """Lower-third: pin · place in tracked caps · thin line · date."""
    ink = _c(p, "title_ink", "#FFFFFF")
    loc = draw_text(title.upper(), f["sans"], 52, ink, 0.18)
    pin = pin_icon(int(58 * _K), _c(p, "pop", "#E94B4B"))
    L = [dict(img=pin, dx=(-loc.width / 2 - pin.width * 0.8) / _K, dy=0, anim="drop", delay=0),
         dict(img=loc, dy=0, anim="track", delay=0.1),
         dict(img=shape("line", loc.width, 4, ink, stroke=3), dy=50, anim="wipe", delay=0.35)]
    if sub:
        L.append(dict(img=draw_text(sub, f["serif"], 40, ink, 0.05), dy=95, anim="fadeup", delay=0.5))
    return L


def t_chapter(p, f, title="Morning routine", kicker="part one", number="01", **_):
    """Big outlined number · tracked kicker · script chapter name."""
    ink = _c(p, "title_ink", "#FFFFFF")
    num = draw_text(number, f["serif_bold"], 260, (0, 0, 0, 0), 0, {"stroke": 4, "stroke_color": ink, "shadow": False})
    return [dict(img=num, dy=-80, anim="scale", delay=0),
            dict(img=draw_text(kicker.upper(), f["sans"], 30, ink, 0.3), dy=85, anim="track", delay=0.2),
            dict(img=draw_text(title, f["script"], 130, ink), dy=170, anim="write", delay=0.4)]


def t_typed(p, f, title="POV: you finally have time", kicker="", **_):
    """Typewriter lines on a soft paper strip — each line types on (with key clicks)."""
    ink = _c(p, "typed_ink", "#1E1E1E")
    paper = _c(p, "typed_paper", "#FFFFFF")
    L, words, lines, cur = [], title.split(), [], ""
    for w in words:  # ~18 characters per line
        if len(cur) + len(w) + 1 > 18 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y0 = -(len(lines) - 1) * 45
    delay = 0.0
    for i, ln in enumerate(lines):
        txt = draw_text(ln, f["mono"], 64, ink, 0.0, {"shadow": False})
        strip = Image.new("RGBA", (txt.width + int(40 * _K), txt.height + int(26 * _K)), paper)
        strip.alpha_composite(txt, (int(20 * _K), int(13 * _K)))
        dur = 0.055 * len(ln)
        L.append(dict(img=strip, dx=0, dy=y0 + i * 90, anim="type", delay=delay, type_dur=dur, chars=len(ln)))
        delay += dur + 0.12
    if kicker:
        L.insert(0, dict(img=draw_text(kicker.upper(), f["sans"], 28, _c(p, "title_ink", "#FFFFFF"), 0.3),
                         dy=y0 - 90, anim="fadeup", delay=0))
    return L


def t_tag(p, f, title="GRWM for School", sub="", **_):
    """Quiet vlog label: small bold sans + a coloured typewriter date line, both typed on.
    Sits mid-screen for the whole reel (aesthetic GRWM / day-in-my-life edits)."""
    ink = _c(p, "title_ink", "#FFFFFF")
    sh = {"shadow": True}
    L = [dict(img=draw_text(title, dict(f["sans"], weight=700), 36, ink, 0.0, dict(sh, shadow_alpha=0.6)), dy=-16, anim="type", delay=0.0,
              type_dur=0.05 * len(title), chars=len(title))]
    if sub:
        L.append(dict(img=draw_text(sub, f["mono"], 23, _c(p, "accent", "#FF8FC7"), -0.02, dict(sh, shadow_alpha=0.6)), dy=24,
                      anim="type", delay=0.05 * len(title) + 0.15, type_dur=0.045 * len(sub), chars=len(sub)))
    return L


TEMPLATES = {
    "tag": (t_tag, "quiet vlog label held all reel: small bold title + coloured typewriter date — 'GRWM for School'"),
    "typed": (t_typed, "typewriter lines on paper strips that type on with key clicks — 'POV: …'"),
    "with-me": (t_with_me, "script title over two lines with a tracked kicker and a date — 'A Day With Me'"),
    "diary": (t_diary, "tracked kicker, serif caps and a script line tucked under — 'A DAY IN my life'"),
    "mini": (t_mini, "two words: serif over script — 'Mini Vlog'"),
    "episode": (t_episode, "oval badge, brush script, rotated 'Eps #1', location pin — 'Today Activity'"),
    "sparkle": (t_sparkle, "chunky pop-colour serif + glowing script + stars + pill tag — 'Life Update'"),
    "headline": (t_headline, "huge serif caps (can go behind you) + small script — 'TODAY vlog'"),
    "slice": (t_slice, "light serif lead-in + bold serif word — 'Slice of Weekend'"),
    "location": (t_location, "pin + tracked place name + line + date — a lower third"),
    "chapter": (t_chapter, "big outline number + kicker + script chapter name — '01 morning routine'"),
}


def build(spec, pack):
    """spec: {"template", "title", ...fields}. Returns layers (images cached)."""
    global _K
    _K = float(spec.get("size", 1.3))
    if spec.get("ink"):  # e.g. dark titles on a light faceless background
        pack = dict(pack, colors=dict(pack["colors"], title_ink=spec["ink"]))
    fn = TEMPLATES[spec.get("template", "with-me")][0]
    fields = {k: v for k, v in spec.items() if k not in ("template", "behind", "size", "ink", "max_width")}
    layers = fn(pack, fonts_for(pack), **fields)
    for l in layers:
        l["dx"] = l.get("dx", 0) * _K
        l["dy"] = l.get("dy", 0) * _K
        l.setdefault("delay", 0)
        l.setdefault("anim", "fadeup")
        if spec.get("behind") and l.get("behind") is None:
            l["behind"] = l is layers[0] or l.get("anim") == "scale"
    # never wider than the safe area: shrink the whole title evenly if needed
    comp, _ = composite(layers)
    max_w = spec.get("max_width", 940)
    if comp.width > max_w:
        k = max_w / comp.width
        for l in layers:
            im = l["img"]
            l["img"] = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
            l["dx"] *= k
            l["dy"] *= k
    return layers


def composite(layers, scale=1.0):
    """All layers at their final state, as one image (for the editor and covers)."""
    boxes = []
    for l in layers:
        im = l["img"].rotate(-l.get("rotate", 0), expand=True, resample=Image.BICUBIC) if l.get("rotate") else l["img"]
        boxes.append((im, l["dx"] - im.width / 2, l["dy"] - im.height / 2))
    x0 = min(b[1] for b in boxes)
    y0 = min(b[2] for b in boxes)
    x1 = max(b[1] + b[0].width for b in boxes)
    y1 = max(b[2] + b[0].height for b in boxes)
    out = Image.new("RGBA", (int(x1 - x0) + 2, int(y1 - y0) + 2))
    for im, x, y in boxes:
        out.alpha_composite(im, (int(x - x0), int(y - y0)))
    # centre offset of the composite relative to the title centre
    return out, ((x0 + x1) / 2, (y0 + y1) / 2)


# ---------------------------------------------------------------- animation
def _ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _ease_back(p):
    p = min(max(p, 0.0), 1.0)
    return 1 + 2.70158 * (p - 1) ** 3 + 1.70158 * (p - 1) ** 2


def layer_state(l, lt, remaining):
    """(img, dx, dy, alpha, scale) for a layer lt seconds after the title started."""
    t = lt - l["delay"]
    if t < 0:
        return None
    img, dx, dy, a, s = l["img"], 0.0, 0.0, 1.0, 1.0
    anim = l["anim"]
    if anim == "fadeup":
        a, dy = _ease_out(t / 0.5), (1 - _ease_out(t / 0.6)) * 40
    elif anim == "write":  # handwriting reveal, left to right with a soft feathered edge
        p = _ease_out(t / 0.9)
        if p < 1:
            import numpy as np
            w, h = img.size
            feather = max(4, w // 12)
            edge = p * (w + feather)
            ramp = np.clip((edge - np.arange(w)) / feather, 0, 1)
            a_src = np.asarray(img.split()[3], dtype=np.float32)
            img = img.copy()
            img.putalpha(Image.fromarray((a_src * ramp[None, :]).astype(np.uint8), "L"))
        a = min(1, t / 0.15)
    elif anim == "type":
        p = min(1, t / max(0.3, l.get("type_dur", 0.8)))
        w = max(1, int(img.width * p))
        img = img.crop((0, 0, w, img.height))
        dx = -(l["img"].width - w) / 2
    elif anim == "pop":
        s = _ease_back(t / 0.35)
    elif anim == "scale":
        s, a = 1.12 - 0.12 * _ease_out(t / 0.8), _ease_out(t / 0.5)
    elif anim == "track":  # letters drift apart into place
        a, s = _ease_out(t / 0.6), 0.92 + 0.08 * _ease_out(t / 0.9)
    elif anim == "slide":
        a, dy = _ease_out(t / 0.35), (1 - _ease_out(t / 0.45)) * 80
    elif anim == "drop":
        dy, a = -(1 - _ease_back(t / 0.45)) * 120, min(1, t / 0.15)
    elif anim == "wipe":
        p = _ease_out(t / 0.5)
        w = max(1, int(img.width * p))
        img = img.crop((0, 0, w, img.height))
        dx = -(l["img"].width - w) / 2
    if l.get("float"):
        dy += math.sin(lt * 2.2 + l["dx"] * 0.01) * 6
    if remaining < 0.3:
        a *= max(remaining / 0.3, 0)
    return img, dx, dy, a, s
