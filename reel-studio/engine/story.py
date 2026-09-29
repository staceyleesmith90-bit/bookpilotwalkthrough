"""Comment hooks + brand-story motion pieces (studied from top CapCut brand edits).

comment  a TikTok-style "Reply to @user's comment" bubble — ONLY with a real comment the user
         gives us (their handle + words). Never invent comments or present fake ones as real.
story    full-frame brand-story pieces for faceless reels:
         word    a giant single word on a full brand-colour field ("FAILURE." / "EVERYWHERE")
         year    a boxed year with a small label ("IN THE YEAR OF" + 1886)
         person  a black-and-white cut-out photo with a name tag (user's own photo)
         logo    logo reveal on the brand background
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISPLAY = os.path.join(ROOT, "library", "fonts", "BebasNeue-Regular.ttf")
W, H = 1080, 1920


def comment_bubble(handle, text, pack, px=620, reply=True):
    from .textfit import load_font, fit_text, render_block
    c = pack["colors"]
    f_small = load_font(pack["fonts"].get("caption", pack["fonts"]["main"])["file"], int(px * 0.045), 600)
    body_font = pack["fonts"].get("caption", pack["fonts"]["main"])
    fit = fit_text(text, body_font["file"], px * 0.78, px * 0.4, max_px=int(px * 0.065), min_px=22, weight=500)
    body = render_block(fit, "#161823")
    head_h = int(px * 0.09)
    h = int(head_h + body.height + px * 0.1)
    card = Image.new("RGBA", (px, h))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, px - 1, h - 1), radius=int(px * 0.05), fill="#FFFFFF")
    av = int(px * 0.07)
    x0 = int(px * 0.05)
    d.ellipse((x0, int(px * 0.035), x0 + av, int(px * 0.035) + av), fill=c.get("pop", "#1E63FF"))
    ini = handle.lstrip("@")[:1].upper() or "?"
    d.text((x0 + av / 2, int(px * 0.035) + av / 2), ini, font=f_small, fill="#FFFFFF", anchor="mm")
    label = (f"Reply to {handle}'s comment" if reply else handle)
    d.text((x0 + av + px * 0.03, int(px * 0.035) + av / 2), label, font=f_small, fill="#6B6F7B", anchor="lm")
    card.alpha_composite(body, (x0, head_h + int(px * 0.035)))
    sh = Image.new("RGBA", (px + 60, h + 60))
    m = Image.new("L", (px, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, px - 1, h - 1), radius=int(px * 0.05), fill=110)
    sh.paste((0, 0, 0, 255), (30, 38, 30 + px, 38 + h), m)
    out = sh.filter(ImageFilter.GaussianBlur(14))
    out.alpha_composite(card, (30, 30))
    return out


def _field(colour):
    return Image.new("RGBA", (W, H), colour)


def _contrast_ink(bg):
    from .packs import contrast
    return "#FFFFFF" if contrast("#FFFFFF", bg) >= contrast("#111111", bg) else "#111111"


def story_card(it, pack):
    from .textfit import load_font
    c = pack["colors"]
    kind = it.get("kind", "word")
    bg = c.get(it.get("bg", "pop"), c["pop"])
    card = _field(bg)
    d = ImageDraw.Draw(card)
    ink = _contrast_ink(bg)
    if kind == "word":
        word = it["text"].upper()
        size = 420
        f = load_font(DISPLAY, size)
        while f.getlength(word) > 920 and size > 120:
            size -= 20
            f = load_font(DISPLAY, size)
        d.text((W / 2, H / 2), word, font=f, fill=ink, anchor="mm")
    elif kind == "year":
        small = load_font(DISPLAY, 110)
        big = load_font(DISPLAY, 330)
        d.text((W / 2, H * 0.4), (it.get("label") or "IN THE YEAR OF").upper(), font=small, fill=ink, anchor="mm")
        yw = big.getlength(it["text"]) + 80
        box_col = c.get("paper", "#FFFFFF") if bg != c.get("paper") else c["pop"]
        d.rectangle((W / 2 - yw / 2, H * 0.47, W / 2 + yw / 2, H * 0.47 + 300), fill=box_col)
        d.text((W / 2, H * 0.47 + 150), it["text"], font=big, fill=_contrast_ink(box_col), anchor="mm")
    elif kind == "person":
        photo = Image.open(os.path.join(ROOT, it["file"])).convert("RGBA")
        photo = ImageOps.grayscale(photo.convert("RGB")).convert("RGBA")
        photo.thumbnail((760, 900))
        card.alpha_composite(photo, ((W - photo.width) // 2, int(H * 0.2)))
        f = load_font(DISPLAY, 150)
        d.text((W / 2, int(H * 0.2) + photo.height + 110), it["text"].upper(), font=f, fill=ink, anchor="mm")
        if it.get("label"):
            fs = load_font(DISPLAY, 70)
            d.text((W / 2, int(H * 0.2) + photo.height + 210), it["label"].upper(), font=fs, fill=ink, anchor="mm")
    elif kind == "logo":
        card = _field(c.get("paper", "#FFFFFF"))
        lf = (pack.get("logo") or {}).get("file") if isinstance(pack.get("logo"), dict) else None
        if lf and os.path.exists(os.path.join(ROOT, lf)):
            lg = Image.open(os.path.join(ROOT, lf)).convert("RGBA")
            lg.thumbnail((720, 500))
            card.alpha_composite(lg, ((W - lg.width) // 2, (H - lg.height) // 2))
        else:
            f = load_font(DISPLAY, 200)
            ImageDraw.Draw(card).text((W / 2, H / 2), (it.get("text") or pack.get("label", "")).upper(), font=f,
                                      fill=c["pop"], anchor="mm")
    return card
