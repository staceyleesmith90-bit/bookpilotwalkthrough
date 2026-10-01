"""Premium sticker kit — the look of high-end reels, not kids' stickers.

What makes stickers look cheap: thick white die-cut borders, flat clip-art, rainbow colours,
too many of them. What premium reels use instead (Apple/luxury/"aesthetic" edits):

  glass chip   frosted panel (the video behind is blurred live), dark 30% tint, hairline
               light edge, soft deep shadow, clean medium-weight type + a brand-colour dot
  glass icon   a thin line icon on a frosted glass circle
  callout      a dot on the product, a hairline leader line and a small tracked-caps label
               (+ optional light sub-line) — the "product annotation" look
  serif word   one elegant italic serif word with a soft shadow and a tiny brand sparkle

Glass items carry a mask in img.info["glass"]; the renderer blurs the frame behind that mask
every frame, so the glass really shows the moving video through it.
"""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TINT = (14, 14, 20, 92)          # dark glass reads on bright AND dark footage
EDGE = (255, 255, 255, 110)
TEXT = (255, 255, 255, 255)


def _font(pack, role, size, weight=None):
    from .textfit import load_font
    f = pack["fonts"].get(role) or pack["fonts"]["main"]
    return load_font(f["file"], int(size), weight or f.get("weight"))


def _clean_sans(pack, size, weight=600):
    """Medium-weight clean sans for glass text (the brand's caption font, lighter)."""
    from .textfit import load_font
    f = pack["fonts"].get("caption") or pack["fonts"]["main"]
    return load_font(f["file"], int(size), weight)


def _soft_shadow(img, offset=(0, 14), blur=26, alpha=0.35, pad=60):
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
    sh.putalpha(img.split()[3].point(lambda v: int(v * alpha)))
    layer = Image.new("RGBA", out.size)
    layer.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(img, (pad, pad))
    return out, pad


def _glass_panel(w, h, radius):
    panel = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(panel)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=TINT)
    # top sheen
    sheen = Image.new("RGBA", (w, h))
    sd = ImageDraw.Draw(sheen)
    for i in range(int(h * 0.5)):
        a = int(34 * (1 - i / (h * 0.5)))
        sd.line((0, i, w, i), fill=(255, 255, 255, a))
    m = Image.new("L", (w, h))
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    sheen.putalpha(Image.fromarray(__import__("numpy").minimum(
        __import__("numpy").asarray(sheen.split()[3]), __import__("numpy").asarray(m))))
    panel.alpha_composite(sheen)
    d.rounded_rectangle((1, 1, w - 2, h - 2), radius=radius, outline=EDGE, width=2)
    return panel, m


def _finish_glass(panel, mask):
    """Add the deep soft shadow and record where the live backdrop blur goes."""
    out, pad = _soft_shadow(panel, (0, 10), 16, 0.35, pad=34)
    gm = Image.new("L", out.size)
    gm.paste(mask, (pad, pad))
    out.info["glass"] = gm
    return out


def glass_chip(text, pack, px=320, colour_key="pop", sub=None, max_w=900):
    """Frosted pill with a brand-colour dot: 'ULTRA THIN', 'Best in China', '$49'.
    Never wider than max_w: long text gets a smaller size."""
    label = text.upper() if len(text) <= 18 else text
    size = px * 0.2
    probe = _clean_sans(pack, size, 650)
    natural = probe.getlength(label) + size * 0.08 * len(label) + size * 3
    if natural > max_w:
        size *= max_w / natural
        px = size / 0.2
    f = _clean_sans(pack, size, 650)
    tw = f.getlength(label) + size * 0.08 * len(label)          # tracked
    sf = _clean_sans(pack, size * 0.62, 450) if sub else None
    sw = sf.getlength(sub) if sub else 0
    h = int(size * (2.3 if not sub else 3.3))
    dot = size * 0.55
    w = int(max(tw, sw) + dot + size * 2.4)
    panel, mask = _glass_panel(w, h, h // 2 if not sub else int(size * 0.9))
    d = ImageDraw.Draw(panel)
    colour = pack["colors"].get(colour_key, pack["colors"]["pop"])
    cx = size * 1.0
    cy = h / 2 if not sub else size * 1.25
    d.ellipse((cx, cy - dot / 2, cx + dot, cy + dot / 2), fill=colour)
    x = cx + dot + size * 0.55
    for ch in label:                                             # tracked caps
        d.text((x, cy), ch, font=f, fill=TEXT, anchor="lm")
        x += f.getlength(ch) + size * 0.08
    if sub:
        d.text((cx + dot + size * 0.55, cy + size * 1.25), sub, font=sf, fill=(255, 255, 255, 200), anchor="lm")
    return _finish_glass(panel, mask)


def glass_icon(icon, pack, px=240, colour_key="pop"):
    """A line icon on a frosted circle, with a small brand-colour ring accent."""
    from .iconstickers import _svg, _render
    svg = _svg(icon, "regular") or _svg(icon, "bold")
    d = int(px)
    panel, mask = _glass_panel(d, d, d // 2)
    if svg:
        glyph = _render(svg, int(d * 0.46), "#FFFFFF")
        panel.alpha_composite(glyph, ((d - glyph.width) // 2, (d - glyph.height) // 2))
    colour = pack["colors"].get(colour_key, pack["colors"]["pop"])
    ImageDraw.Draw(panel).arc((6, 6, d - 7, d - 7), start=200, end=290, fill=colour, width=max(3, d // 40))
    return _finish_glass(panel, mask)


def callout_up(text, pack, sub=None, length=160, px=320, colour_key="pop"):
    """Vertical callout for tight spots: dot on the product, hairline up, label centred above."""
    size = px * 0.17
    f = _clean_sans(pack, size, 650)
    sf = _clean_sans(pack, size * 0.7, 400) if sub else None
    label = text.upper()
    tw = f.getlength(label) + size * 0.1 * len(label)
    sw = sf.getlength(sub) if sub else 0
    colour = pack["colors"].get(colour_key, pack["colors"]["pop"])
    dot = int(size * 0.7)
    th = int(size * (2.4 if sub else 1.4))
    w, h = int(max(tw, sw) + size), int(th + length + dot * 2 + size * 0.3)
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    x = (w - tw) / 2
    for ch in label:
        d.text((x, size * 0.7), ch, font=f, fill=TEXT, anchor="lm")
        x += f.getlength(ch) + size * 0.1
    if sub:
        d.text((w / 2, size * 1.85), sub, font=sf, fill=(255, 255, 255, 215), anchor="mm")
    cx, top, cy = w / 2, th + size * 0.2, h - dot
    d.line((cx, top, cx, cy - dot), fill=(255, 255, 255, 235), width=max(2, int(size * 0.07)))
    d.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=(255, 255, 255, 90))
    d.ellipse((cx - dot * 0.55, cy - dot * 0.55, cx + dot * 0.55, cy + dot * 0.55), fill=colour)
    out, pad = _soft_shadow(img, (0, 3), 6, 0.55, pad=20)
    out.info["anchor"] = (pad + cx, pad + cy)
    return out


def callout(text, pack, sub=None, length=220, side="right", px=320, colour_key="pop", max_w=None):
    """Product annotation: ● ——— LABEL. The anchor dot is the image's left (or right) centre;
    the item's 'anchor' field tells the planner where the dot should sit. max_w: room from the
    dot to the screen edge — if the label doesn't fit, it goes above the dot instead (callout_up)."""
    if side == "up":
        return callout_up(text, pack, sub, 150, px, colour_key)
    size = px * 0.17
    if max_w:
        probe = _clean_sans(pack, size, 650)
        need = size * 1.4 + length + probe.getlength(text.upper()) + size * 0.1 * len(text) + size
        if need > max_w:
            return callout_up(text, pack, sub, 150, px, colour_key)
    f = _clean_sans(pack, size, 650)
    sf = _clean_sans(pack, size * 0.7, 400) if sub else None
    label = text.upper()
    tw = f.getlength(label) + size * 0.1 * len(label)
    sw = sf.getlength(sub) if sub else 0
    colour = pack["colors"].get(colour_key, pack["colors"]["pop"])
    dot = int(size * 0.7)
    w = int(dot * 2 + length + max(tw, sw) + size)
    h = int(size * (3.2 if sub else 2.2))
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    cy = size * 1.1
    d.ellipse((0, cy - dot, dot * 2, cy + dot), fill=(255, 255, 255, 90))           # halo
    d.ellipse((dot * 0.45, cy - dot * 0.55, dot * 1.55, cy + dot * 0.55), fill=colour)
    d.line((dot * 2 + 4, cy, dot * 2 + length, cy), fill=(255, 255, 255, 235), width=max(2, int(size * 0.07)))
    x = dot * 2 + length + size * 0.4
    for ch in label:
        d.text((x, cy), ch, font=f, fill=TEXT, anchor="lm")
        x += f.getlength(ch) + size * 0.1
    if sub:
        d.text((dot * 2 + length + size * 0.4, cy + size * 1.2), sub, font=sf, fill=(255, 255, 255, 215), anchor="lm")
    if side == "left":
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        # re-draw text un-mirrored
        img2 = Image.new("RGBA", img.size)
        mirrored_line = img.crop((w - int(dot * 2 + length), 0, w, h))
        img2.alpha_composite(mirrored_line, (w - mirrored_line.width, 0))
        d2 = ImageDraw.Draw(img2)
        x = w - (dot * 2 + length) - size * 0.4 - tw
        for ch in label:
            d2.text((x, cy), ch, font=f, fill=TEXT, anchor="lm")
            x += f.getlength(ch) + size * 0.1
        if sub:
            d2.text((w - (dot * 2 + length) - size * 0.4 - sw, cy + size * 1.2), sub, font=sf,
                    fill=(255, 255, 255, 215), anchor="lm")
        img = img2
    out, pad = _soft_shadow(img, (0, 3), 6, 0.55, pad=20)
    out.info["anchor"] = (pad + (dot if side == "right" else w - dot), pad + cy)
    return out


def serif_word(text, pack, px=320, colour_key="pop", font=None):
    """One elegant italic serif word/phrase, soft shadow, tiny brand sparkle. No white border."""
    from .textfit import load_font
    from .packs import resolve_font
    spec = resolve_font(pack, font) if font else None
    if not spec:
        it = os.path.join(ROOT, "library", "fonts", "PlayfairDisplay-Italic-Variable.ttf")
        spec = {"file": it, "weight": 600} if os.path.exists(it) else pack["fonts"]["main"]
    f = load_font(spec["file"], int(px * 0.42), spec.get("weight"))
    tw = int(f.getlength(text))
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (tw + int(px * 0.25), asc + desc + int(px * 0.12)))
    d = ImageDraw.Draw(img)
    d.text((0, int(px * 0.1)), text, font=f, fill=TEXT)
    colour = pack["colors"].get(colour_key, pack["colors"]["pop"])
    sx, sy, r = img.width - px * 0.1, px * 0.1, px * 0.07          # four-point sparkle
    d.polygon([(sx, sy - r), (sx + r * 0.25, sy - r * 0.25), (sx + r, sy), (sx + r * 0.25, sy + r * 0.25),
               (sx, sy + r), (sx - r * 0.25, sy + r * 0.25), (sx - r, sy), (sx - r * 0.25, sy - r * 0.25)],
              fill=colour)
    out, _ = _soft_shadow(img, (0, 4), 10, 0.5, pad=30)
    return out


def photo_card(img, px=380, label=None, pack=None, rotate=0):
    """Pop-up photo card: white border, rounded, soft shadow, optional label pill underneath."""
    im = img.convert("RGBA")
    im.thumbnail((px, int(px * 1.4)))
    b = max(10, px // 30)
    w, h = im.width + b * 2, im.height + b * 2
    card = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=b * 2, fill="#FFFFFF")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=b, fill=255)
    card.paste(im, (b, b), m)
    if label and pack:
        f = _clean_sans(pack, px * 0.075, 650)
        tw = int(f.getlength(label.upper())) + b * 3
        ext = Image.new("RGBA", (max(w, tw), h + int(px * 0.16)))
        ext.alpha_composite(card, ((ext.width - w) // 2, 0))
        dd = ImageDraw.Draw(ext)
        col = pack["colors"].get("pop", "#1E63FF")
        y = h - b
        dd.rounded_rectangle(((ext.width - tw) / 2, y, (ext.width + tw) / 2, y + px * 0.13), radius=int(px * 0.065), fill=col)
        dd.text((ext.width / 2, y + px * 0.065), label.upper(), font=f, fill="#FFFFFF", anchor="mm")
        card = ext
    if rotate:
        card = card.rotate(rotate, expand=True, resample=Image.BICUBIC)
    out, _ = _soft_shadow(card, (0, 12), 18, 0.4, pad=36)
    return out


def label(text, pack, px=64, style="label", max_w=900):
    """CapCut-style text box: the look of CapCut's 'text with background' — a clean rounded box
    hugging bold text. style: "label" (white box, near-black text), "pop" (brand colour box,
    white text), "dark" (near-black box, white text). No glass, no gloss: flat, crisp, native."""
    from .textfit import load_font
    c = pack["colors"]
    fill, ink = {"label": ("#FFFFFF", c.get("ink", "#111111")),
                 "pop": (c.get("pop", "#1E63FF"), "#FFFFFF"),
                 "dark": ("#111111", "#FFFFFF")}.get(style, ("#FFFFFF", "#111111"))
    bold = os.path.join(ROOT, "library", "fonts", "Poppins-Bold.ttf")
    f = pack["fonts"].get("caption") or pack["fonts"]["main"]
    font_file = bold if "poppins" in os.path.basename(f["file"]).lower() else f["file"]
    size = int(px)
    font = load_font(font_file, size)
    while font.getlength(text) > max_w - size and size > 24:
        size -= 2
        font = load_font(font_file, size)
    asc, desc = font.getmetrics()
    padx, pady = int(size * 0.42), int(size * 0.22)
    w = int(font.getlength(text)) + padx * 2
    h = asc + desc + pady * 2
    box = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=int(h * 0.28), fill=fill)
    d.text((padx, pady - int(desc * 0.15)), text, font=font, fill=ink)
    out, _ = _soft_shadow(box, offset=(0, 6), blur=12, alpha=0.22, pad=24)
    return out
