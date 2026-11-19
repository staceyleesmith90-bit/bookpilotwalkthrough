"""Brand effects: reels for brands where nobody talks — products and services. Drawn in the brand's own colours
and fonts (the active brand pack), registered as scene effects (engine/scenefx.py).

  product_hero   the product cut out of its photo (AI cut-out), floating on the brand colour with a soft floor
                 shadow and a slow push-in; name + tagline on top, price tag (with "was" price), a NEW / SALE
                 badge and benefit pills that pop in one by one.
                 spec: photo, name, tagline, price, was, badge, items [benefits], side ("right" = product right)
  review_card    a customer review: big quote, five stars popping in, the name; the product (or brand logo)
                 small underneath. spec: text, name, stars (1-5), photo (optional)
  steps_cards    "how it works" for services: numbered cards slide in one by one.
                 spec: title, items ["Book online", "We come to you", ...], details [...] (optional)
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = lambda n: os.path.join(ROOT, "library", "fonts", n)


def _rgb(h, a=255):
    h = str(h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _mix(a, b, k):
    a, b = _rgb(a), _rgb(b)
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (255,)


def _seg(lt, a, b):
    return min(max((lt - a) / max(b - a, 1e-6), 0.0), 1.0)


def _ease(x):
    return 1 - (1 - x) ** 3


def _back(x):
    if x <= 0:
        return 0.0
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _font(ctx, role, px, weight=None):
    """The brand's own font for this job (main = headline, caption = small bold), else a clean default."""
    f = ((ctx.pack or {}).get("fonts") or {}).get(role) or {}
    path = f.get("file")
    if path and not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    if not path or not os.path.exists(path):
        path = FONT("Poppins-Bold.ttf" if role != "caption" else "Poppins-SemiBold.ttf")
    try:
        return load_font(path, int(px), weight or f.get("weight"))
    except Exception:
        return load_font(path, int(px))


def _wrap(text, font, maxw):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


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


def _shadowed(im, blur, alpha=0.3, dy=8):
    pad = blur * 2 + abs(dy)
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sh.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    out.alpha_composite(sh, (pad, pad + dy))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def product_cutout(photo):
    """The product lifted out of its photo (rembg when installed, else the photo's plain background removed),
    trimmed to its edges. Cached next to the photo as <name>.cutout.png."""
    src = _abs(photo)
    out = os.path.splitext(src)[0] + ".cutout.png"
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return Image.open(out).convert("RGBA")
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((1400, 1400), Image.LANCZOS)
    from .aielements import _ai_alpha, _background_mask
    a = _ai_alpha(im)
    if a is None:
        a = ((~_background_mask(np.asarray(im))).astype(np.uint8) * 255)
    rgba = im.convert("RGBA")
    rgba.putalpha(Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.8)))
    box = rgba.split()[3].point(lambda v: 255 if v > 24 else 0).getbbox()
    if box:
        rgba = rgba.crop(box)
    try:
        rgba.save(out)
    except OSError:
        pass
    return rgba


def _backdrop(ctx, key):
    """Brand-colour studio backdrop: soft vertical gradient, a lighter spotlight behind the product, fine grain."""
    if key in ctx._store:
        return ctx._store[key]
    W, H = ctx.W, ctx.H
    top, bot = _mix(ctx.col["bg"], "#FFFFFF", 0.25), _mix(ctx.col["bg"], ctx.col["accent"], 0.35)
    y = np.linspace(0, 1, H)[:, None, None]
    grad = (np.array(top[:3]) * (1 - y) + np.array(bot[:3]) * y).astype(np.float32)
    img = np.repeat(grad, W, axis=1)
    yy, xx = np.mgrid[0:H, 0:W]
    spot = np.exp(-(((xx - W * 0.5) / (W * 0.42)) ** 2 + ((yy - H * 0.5) / (H * 0.26)) ** 2))[..., None]
    img = img * (1 - 0.45 * spot) + 255 * 0.45 * spot
    img += np.random.default_rng(3).normal(0, 2.2, img.shape[:2])[..., None]
    bg = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    ctx._store[key] = bg
    return bg


def _photo_backdrop(ctx, photo):
    """The brand's own photo, softly blurred and washed with the brand colour, so cards sit on THEIR world."""
    key = ("pbd", photo, ctx.col["bg"])
    if key in ctx._store:
        return ctx._store[key]
    try:
        im = ImageOps.exif_transpose(Image.open(_abs(photo))).convert("RGB")
    except Exception:
        return _backdrop(ctx, ("pbg", ctx.col["bg"], ctx.col["accent"]))
    im = ImageOps.fit(im, (ctx.W // 4, ctx.H // 4), Image.LANCZOS).filter(ImageFilter.GaussianBlur(6))
    im = im.resize((ctx.W, ctx.H), Image.BICUBIC).convert("RGBA")
    tint = Image.new("RGBA", (ctx.W, ctx.H), _rgb(ctx.col["bg"], 165))
    im.alpha_composite(tint)
    ctx._store[key] = im
    return im


def _bg(ctx, spec):
    if spec.get("backdrop") == "photo" and spec.get("photo"):
        return _photo_backdrop(ctx, spec["photo"]).copy()
    return _backdrop(ctx, ("pbg", ctx.col["bg"], ctx.col["accent"])).copy()


def _tag(ctx, price, was=None):
    u = ctx.u
    fb = _font(ctx, "caption", 58 * u, 800)
    fw = _font(ctx, "caption", 30 * u, 600)
    w = int(max(fb.getlength(price), fw.getlength(was or "")) + 70 * u)
    h = int((118 if was else 92) * u)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), int(26 * u), fill=_rgb(ctx.col["pop"]))
    tc = (255, 255, 255, 255)
    if was:
        d.text((w / 2, 30 * u), was, font=fw, fill=tc[:3] + (200,), anchor="mm")
        tw = fw.getlength(was)
        d.line((w / 2 - tw / 2 - 4, 31 * u, w / 2 + tw / 2 + 4, 31 * u), fill=tc[:3] + (220,), width=max(2, int(3 * u)))
        d.text((w / 2, 78 * u), price, font=fb, fill=tc, anchor="mm")
    else:
        d.text((w / 2, h / 2), price, font=fb, fill=tc, anchor="mm")
    return _shadowed(im, int(10 * u), 0.28, int(6 * u))


def _badge(ctx, text):
    u = ctx.u
    s = int(170 * u)
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(32):                                   # a scalloped seal
        a = i / 32 * 2 * math.pi
        r = s / 2 * (1 if i % 2 == 0 else 0.88)
        pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
    d.polygon(pts, fill=_rgb(ctx.col["ink"]))
    f = _font(ctx, "caption", (48 if len(text) <= 4 else 34) * u, 800)
    d.text((s / 2, s / 2), text.upper(), font=f, fill=_rgb(ctx.col["paper"]), anchor="mm")
    return im


def _pill(ctx, text):
    u = ctx.u
    f = _font(ctx, "caption", 36 * u, 700)
    w, h = int(f.getlength(text) + 64 * u), int(70 * u)
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=_rgb(ctx.col["paper"]))
    d.ellipse((18 * u, h / 2 - 9 * u, 36 * u, h / 2 + 9 * u), fill=_rgb(ctx.col["pop"]))
    d.text((46 * u, h / 2), text, font=f, fill=_rgb(ctx.col["ink"]), anchor="lm")
    return _shadowed(im, int(9 * u), 0.22, int(5 * u))


def fx_product_hero(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    out = _backdrop(ctx, ("pbg", ctx.col["bg"], ctx.col["accent"])).copy()
    k_in = _ease(_seg(lt, 0.0, 0.45))
    push = 1 + 0.06 * (lt / max(dur, 0.1))
    bob = math.sin(lt * 2.1) * 8 * u
    if spec.get("photo"):
        key = ("cut", spec["photo"])
        if key not in ctx._store:
            ctx._store[key] = product_cutout(spec["photo"])
        prod = ctx._store[key]
        maxw, maxh = W * float(spec.get("size", 0.74)), H * 0.46
        s = min(maxw / prod.width, maxh / prod.height)
        pw, ph = prod.width * s, prod.height * s
        cy = H * 0.5
        # floor shadow
        sh = Image.new("RGBA", (W, H))
        ImageDraw.Draw(sh).ellipse((W / 2 - pw * 0.42, cy + ph / 2 - 18 * u, W / 2 + pw * 0.42, cy + ph / 2 + 26 * u),
                                   fill=(0, 0, 0, int(70 * k_in)))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18 * u)))
        _paste(out, prod, W / 2, cy + bob + (1 - k_in) * 60 * u, s * push * (0.9 + 0.1 * k_in), k_in)
    # name + tagline
    if spec.get("name"):
        fn = _font(ctx, "main", 92 * u)
        lines = _wrap(spec["name"], fn, W * 0.86)[:2]
        k = _ease(_seg(lt, 0.15, 0.55))
        lay = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(lay)
        y = H * 0.12
        for ln in lines:
            d.text((W / 2, y), ln, font=fn, fill=_rgb(ctx.col["ink"]), anchor="mt")
            y += 96 * u
        if spec.get("tagline"):
            ft = _font(ctx, "caption", 38 * u, 600)
            d.text((W / 2, y + 8 * u), spec["tagline"], font=ft, fill=_rgb(ctx.col["ink"], 200), anchor="mt")
        _paste(out, lay, W / 2, H / 2 - (1 - k) * 30 * u, 1.0, k)
    # benefit pills, one by one, alternating sides around the product
    for i, item in enumerate(spec.get("items") or []):
        st = 0.8 + i * 0.45
        k = _back(_seg(lt, st, st + 0.35))
        if k <= 0:
            continue
        pill = ctx._store.setdefault(("pill", item, ctx.col["pop"]), _pill(ctx, item))
        left = i % 2 == 0
        x = W * (0.3 if left else 0.7)
        x = min(max(x, pill.width / 2 + 24 * u), W - pill.width / 2 - 24 * u)
        _paste(out, pill, x, H * (0.33 + 0.1 * i), k, min(1, k * 2), -3 if left else 3)
    # price tag + badge
    if spec.get("price"):
        k = _back(_seg(lt, float(spec.get("price_at", max(0.9, dur * 0.55))), float(spec.get("price_at", max(0.9, dur * 0.55))) + 0.35))
        tag = ctx._store.setdefault(("tag", spec["price"], spec.get("was")), _tag(ctx, spec["price"], spec.get("was")))
        _paste(out, tag, W * 0.5, H * 0.8, k, min(1, k * 2), -4)
    if spec.get("badge"):
        k = _back(_seg(lt, 0.5, 0.85))
        b = ctx._store.setdefault(("badge", spec["badge"]), _badge(ctx, spec["badge"]))
        _paste(out, b, W * 0.8, H * 0.3, k, min(1, k * 2), 12 - 10 * k)
    return out


def fx_review_card(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    out = _bg(ctx, spec)
    k = _ease(_seg(lt, 0.0, 0.4))
    cw = int(W * 0.88)
    fq = _font(ctx, "main", 74 * u)
    lines = _wrap(spec.get("text", "Absolutely love it!"), fq, cw - 120 * u)[:6]
    ch = int(270 * u + len(lines) * 88 * u)
    card = Image.new("RGBA", (cw, ch))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, cw - 1, ch - 1), int(40 * u), fill=_rgb(ctx.col["paper"]))
    d.text((48 * u, 10 * u), "“", font=_font(ctx, "main", 190 * u), fill=_rgb(ctx.col["pop"]))
    y = 160 * u
    for ln in lines:
        d.text((cw / 2, y), ln, font=fq, fill=_rgb(ctx.col["ink"]), anchor="mt")
        y += 88 * u
    if spec.get("name"):
        d.text((cw / 2, y + 26 * u), "— " + spec["name"], font=_font(ctx, "caption", 40 * u, 700),
               fill=_rgb(ctx.col["ink"], 190), anchor="mt")
    card = _shadowed(card, int(16 * u), 0.25, int(10 * u))
    cy = H * 0.44
    _paste(out, card, W / 2, cy + (1 - k) * 80 * u, 0.94 + 0.06 * k, k)
    # stars pop in one by one above the card
    n = max(1, min(5, int(spec.get("stars", 5))))
    for i in range(n):
        ks = _back(_seg(lt, 0.45 + i * 0.12, 0.75 + i * 0.12))
        if ks <= 0:
            continue
        s = int(104 * u)
        st = Image.new("RGBA", (s, s))
        pts = []
        for j in range(10):
            a = -math.pi / 2 + j * math.pi / 5
            r = s / 2 * (1 if j % 2 == 0 else 0.45)
            pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
        ImageDraw.Draw(st).polygon(pts, fill=_rgb("#F2B705"))
        _paste(out, st, W / 2 + (i - (n - 1) / 2) * 116 * u, cy - ch / 2 - 90 * u, ks, min(1, ks * 2))
    if spec.get("photo") and spec.get("backdrop") != "photo":      # products: the product, small, underneath
        key = ("cut", spec["photo"])
        if key not in ctx._store:
            ctx._store[key] = product_cutout(spec["photo"])
        prod = ctx._store[key]
        s = min(W * 0.4 / prod.width, H * 0.2 / prod.height)
        kp = _ease(_seg(lt, 0.3, 0.8))
        _paste(out, prod, W / 2, H * 0.82 + (1 - kp) * 40 * u, s, kp)
    return out


def fx_steps_cards(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    out = _bg(ctx, spec)
    items = spec.get("items") or ["Book online", "We come to you", "Enjoy the result"]
    details = spec.get("details") or []
    kt = _ease(_seg(lt, 0.0, 0.4))
    lay = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(lay)
    y = H * 0.1
    if spec.get("kicker"):
        d.text((W / 2, y), spec["kicker"], font=_font(ctx, "caption", 40 * u, 700), fill=_rgb(ctx.col["pop"]), anchor="mt")
        y += 60 * u
    if spec.get("title"):
        ft = _font(ctx, "main", 96 * u)
        for ln in _wrap(spec["title"], ft, W * 0.86)[:2]:
            d.text((W / 2, y), ln, font=ft, fill=_rgb(ctx.col["ink"]), anchor="mt")
            y += 104 * u
    _paste(out, lay, W / 2, H / 2, 1.0, kt)
    fb = _font(ctx, "caption", 50 * u, 800)
    fs = _font(ctx, "caption", 36 * u, 600)
    fn = _font(ctx, "main", 64 * u)
    cw = int(W * 0.88)
    r = 54 * u
    tx = 30 * u + 2 * r + 30 * u
    cards = []
    for i, it in enumerate(items):
        lines = _wrap(it, fb, cw - tx - 34 * u)[:3]
        sub = _wrap(details[i], fs, cw - tx - 34 * u)[:2] if i < len(details) and details[i] else []
        ch = int(max(2 * r + 48 * u, 44 * u + len(lines) * 60 * u + len(sub) * 46 * u))
        card = Image.new("RGBA", (cw, ch))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, cw - 1, ch - 1), int(34 * u), fill=_rgb(ctx.col["paper"]))
        cd.ellipse((30 * u, ch / 2 - r, 30 * u + 2 * r, ch / 2 + r), fill=_rgb(ctx.col["pop"]))
        cd.text((30 * u + r, ch / 2), str(i + 1), font=fn, fill=(255, 255, 255, 255), anchor="mm")
        ty = ch / 2 - (len(lines) * 60 * u + len(sub) * 46 * u) / 2
        for ln in lines:
            cd.text((tx, ty), ln, font=fb, fill=_rgb(ctx.col["ink"]), anchor="lt"); ty += 60 * u
        for ln in sub:
            cd.text((tx, ty + 4 * u), ln, font=fs, fill=_rgb(ctx.col["ink"], 170), anchor="lt"); ty += 46 * u
        cards.append(_shadowed(card, int(12 * u), 0.2, int(7 * u)))
    total = sum(c.height for c in cards) + 26 * u * (len(cards) - 1)
    yc = max(y + 40 * u, H * 0.58 - total / 2)
    step = float(spec.get("step", max(0.5, (dur - 0.8) / max(len(items), 1))))
    for i, card in enumerate(cards):
        st = 0.35 + i * step
        k = _ease(_seg(lt, st, st + 0.35))
        if k > 0:
            _paste(out, card, W / 2 + (1 - k) * W * 0.6, yc + card.height / 2, 1.0, k)
        yc += card.height + 26 * u - 14 * u
    return out


EFFECTS = {"product_hero": fx_product_hero, "review_card": fx_review_card, "steps_cards": fx_steps_cards}
LABELS = {"product_hero": "Product Hero", "review_card": "Review Card", "steps_cards": "Steps Cards"}
ABOUT = {"product_hero": "Your product cut out of its photo, floating on your brand colour with price tag, badge and benefits.",
         "review_card": "A customer review: big quote, five stars popping in, their name, your product underneath.",
         "steps_cards": "How it works: numbered cards slide in one by one (great for services)."}
DUR = {"product_hero": 4.0, "review_card": 4.0, "steps_cards": 4.5}


def sound_times(fx, spec, dur):
    spec = spec or {}
    if fx == "product_hero":
        out = [(0.0, "whoosh", 0.6)] + [(0.8 + i * 0.45, "pill_in", 0.8) for i in range(len(spec.get("items") or []))]
        if spec.get("badge"):
            out.append((0.5, "slam", 0.5))
        if spec.get("price"):
            out.append((float(spec.get("price_at", max(0.9, dur * 0.55))), "money", 0.9))
        return out
    if fx == "review_card":
        return [(0.0, "page", 0.6)] + [(0.45 + i * 0.12, "sparkle", 0.6) for i in range(int(spec.get("stars", 5)))]
    if fx == "steps_cards":
        n = len(spec.get("items") or [1, 2, 3])
        step = float(spec.get("step", max(0.5, (dur - 0.8) / max(n, 1))))
        return [(0.35 + i * step, "slide", 0.8) for i in range(n)]
    return []
