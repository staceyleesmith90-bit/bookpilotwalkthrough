"""Post Kit — turn a reel into a carousel post and story frames, in the brand.

    python -m engine posts <project>          -> projects/<p>/posts/ (carousel-01.png…, story-01.png…, caption.txt, posts.zip)

The words: projects/<p>/posts.json if Claude (or the person) wrote it —
    {"carousel": [{"title": "...", "body": "..."}, ...],   first = cover, last = call to action
     "stories":  [{"title": "...", "body": "...", "kind": "teaser|question|cta"}, ...],
     "caption": "post caption + hashtags", "handle": "@name"}
For personal posts (babies, family, milestones, trips) add "style": "memory": big real photos, polaroids with
washi tape and script writing, no logos / page numbers / call-to-action buttons. Each slide or story can name its
own "photo" (an image, or a video moment "clip.mp4@2.5") and a "layout":
    carousel: "photo" (full-bleed, title or a small handwritten note) | "polaroid" (one print on paper)
              | "collage" (2-4 prints on paper, give "photos": [...])
    stories:  "polaroid" | "collage" | "photo"
otherwise a first draft is made from the reel's own script (hook = first line, points = the clearest lines).
The pictures: real frames from the reel. Fonts and colours: the brand the reel was made for.
"""
import json, os, re, subprocess, zipfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import packs, project

CW, CH = 1080, 1350          # carousel (Instagram portrait)
SW, SH = 1080, 1920          # story


# ------------------------------------------------------------------ helpers
def _font(spec, size):
    try:
        f = ImageFont.truetype(spec["file"], size)
        try:
            f.set_variation_by_axes([spec.get("weight", 700)])
        except Exception:
            pass
        return f
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, spec, max_w, max_h, start, min_size=26, spacing=1.12):
    """Biggest font size where the text fits the box. -> (font, lines, line_height)"""
    size = start
    while size >= min_size:
        f = _font(spec, size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=f) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        lh = int(size * spacing)
        if lh * len(lines) <= max_h and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines, lh
        size -= 4
    f = _font(spec, min_size)
    return f, [text], int(min_size * spacing)


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(h):
    r, g, b = _rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _on(h):
    return "#111111" if _lum(h) > 0.6 else "#FFFFFF"


def _frames(video, n, out_dir):
    """n real frames spread through the reel (skipping the first and last seconds)."""
    os.makedirs(out_dir, exist_ok=True)
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                   capture_output=True, text=True).stdout.strip() or 10)
    except ValueError:
        dur = 10
    out = []
    for i in range(n):
        t = 1.2 + (dur - 2.4) * (i + 0.5) / n
        p = os.path.join(out_dir, f"frame-{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", p], capture_output=True)
        if os.path.exists(p):
            out.append(p)
    return out


def _cover(img_path, w, h):
    from PIL import ImageOps
    if img_path and os.path.exists(img_path):
        return ImageOps.fit(Image.open(img_path).convert("RGB"), (w, h), centering=(0.5, 0.35))
    return Image.new("RGB", (w, h), "#333333")


def _shade(im, top=0.0, bottom=0.82):
    """Dark gradient from the middle down so text on a photo always reads."""
    w, h = im.size
    g = Image.new("L", (1, h))
    for y in range(h):
        k = max(0.0, (y / h - 0.35) / 0.65)
        g.putpixel((0, y), int(255 * (top + (bottom - top) * k)))
    g = g.resize((w, h))
    black = Image.new("RGB", (w, h), "#000000")
    return Image.composite(black, im, g)


def _logo(pack):
    lg = (pack.get("logo") or {}).get("file")
    if lg:
        p = lg if os.path.isabs(lg) else os.path.join(project.ROOT, lg)
        if os.path.exists(p):
            return Image.open(p).convert("RGBA")
    return None


def _pill(d, xy, text, font, fill, ink, arrow=False):
    x, y = xy
    w = d.textlength(text, font=font) + (font.size * 1.3 if arrow else 0)
    h = font.size + 26
    d.rounded_rectangle((x, y, x + w + 44, y + h), radius=h // 2, fill=fill)
    d.text((x + 22, y + 11), text, font=font, fill=ink)
    if arrow:                                           # drawn, so it never depends on the font having the glyph
        ax = x + 22 + d.textlength(text, font=font) + font.size * 0.35
        ay = y + h / 2
        L = font.size * 0.8
        d.line((ax, ay, ax + L, ay), fill=ink, width=max(3, font.size // 9))
        d.line((ax + L * 0.6, ay - L * 0.35, ax + L, ay, ax + L * 0.6, ay + L * 0.35), fill=ink, width=max(3, font.size // 9), joint="curve")


# ------------------------------------------------------------------ the words
def draft(slug):
    """A first draft of the words from the reel's own script (Claude usually rewrites it)."""
    brief = project.load(slug, "brief.json") or {}
    rc = project.load(slug, "roughcut.json") or {}
    lines = [l["text"].strip() for l in rc.get("lines", []) if l.get("keep", True) and len(l["text"].split()) >= 4]
    hook = brief.get("topic") or (lines[0] if lines else "Watch this")
    pts = sorted(lines[1:], key=lambda t: -len(t))[:4]                  # the fullest thoughts
    pts = [p for p in lines if p in pts][:4]                              # in the order they were said
    carousel = [{"title": hook, "body": ""}]
    for i, p in enumerate(pts, 1):
        words = p.split()
        carousel.append({"title": " ".join(words[:6]).rstrip(",.") + ("…" if len(words) > 6 else ""), "body": p})
    carousel.append({"title": "Save this for later", "body": "Follow for more like this"})
    stories = [{"kind": "teaser", "title": hook, "body": "New reel is up"},
               {"kind": "question", "title": "Would you try this?", "body": "Yes, today|Maybe later"},
               {"kind": "cta", "title": "Watch the full reel", "body": "Tap the link on my profile"}]
    return {"carousel": carousel, "stories": stories, "caption": hook + "\n\n" + "\n".join("• " + p for p in pts[:3])}


# ------------------------------------------------------------------ slides
def carousel_slide(i, n, s, pack, photo, logo, handle):
    c, f = pack["colors"], pack["fonts"]
    first, last = i == 0, i == n - 1
    if first:
        im = _shade(_cover(photo, CW, CH))
        d = ImageDraw.Draw(im)
        font, lines, lh = _wrap(d, s["title"].upper() if len(s["title"]) < 40 else s["title"], f["main"], CW - 160, 520, 112)
        y = CH - 180 - lh * len(lines)
        for ln in lines:
            d.text((80, y), ln, font=font, fill="#FFFFFF")
            y += lh
        _pill(d, (80, CH - 150), "Swipe", _font(f["caption"], 34), c["pop"], _on(c["pop"]), arrow=True)
    elif last:
        im = Image.new("RGB", (CW, CH), c["pop"])
        d = ImageDraw.Draw(im)
        ink = _on(c["pop"])
        font, lines, lh = _wrap(d, s["title"], f["main"], CW - 200, 520, 104)
        y = CH // 2 - lh * len(lines) // 2 - 60
        for ln in lines:
            d.text(((CW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=ink)
            y += lh
        if s.get("body"):
            bf = _font(f["accent"], 64)
            d.text(((CW - d.textlength(s["body"], font=bf)) / 2, y + 30), s["body"], font=bf, fill=ink)
    else:
        bg = c.get("bg", "#FFFFFF")
        im = Image.new("RGB", (CW, CH), bg)
        d = ImageDraw.Draw(im)
        ink = c["ink"] if abs(_lum(c["ink"]) - _lum(bg)) > 0.4 else _on(bg)
        if photo:                                                          # a strip of the real reel at the top
            strip = _cover(photo, CW - 160, 470)
            m = Image.new("L", strip.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, strip.width - 1, strip.height - 1), 36, fill=255)
            im.paste(strip, (80, 80), m)
            top = 600
        else:
            top = 160
        nb = _font(f["main"], 46)
        d.ellipse((80, top, 160, top + 80), fill=c["pop"])
        num = str(i)
        d.text((120 - d.textlength(num, font=nb) / 2, top + 10), num, font=nb, fill=_on(c["pop"]))
        font, lines, lh = _wrap(d, s["title"], f["main"], CW - 160, 230, 72)
        y = top + 120
        for ln in lines:
            d.text((80, y), ln, font=font, fill=ink)
            y += lh
        if s.get("body") and s["body"] != s["title"]:
            bfont, blines, blh = _wrap(d, s["body"], f["caption"], CW - 160, CH - y - 160, 44, 26, 1.35)
            y += 24
            for ln in blines:
                d.text((80, y), ln, font=bfont, fill=ink)
                y += blh
    d = ImageDraw.Draw(im)
    small = _font(f["caption"], 30)
    foot_ink = "#FFFFFF" if first else (_on(c["pop"]) if last else c["ink"])
    d.text((CW - 80 - d.textlength(f"{i + 1}/{n}", font=small), 60), f"{i + 1}/{n}", font=small, fill=foot_ink)
    if handle:
        d.text((80 if not first else 80, 52 if not first else 60), handle, font=small, fill=foot_ink)
    if logo is not None and not first:
        lg = logo.copy()
        lg.thumbnail((150, 70))
        im.paste(lg, (CW - 80 - lg.width, CH - 60 - lg.height), lg)
    return im


def story_frame(s, pack, photo, handle):
    c, f = pack["colors"], pack["fonts"]
    kind = s.get("kind", "teaser")
    if kind == "teaser":
        im = _shade(_cover(photo, SW, SH), 0.05, 0.85)
        d = ImageDraw.Draw(im)
        _pill(d, (80, 300), s.get("body") or "New reel", _font(f["caption"], 40), c["pop"], _on(c["pop"]))
        font, lines, lh = _wrap(d, s["title"], f["main"], SW - 160, 700, 110)
        y = SH - 520 - lh * len(lines)
        for ln in lines:
            d.text((80, y), ln, font=font, fill="#FFFFFF")
            y += lh
        bf = _font(f["caption"], 44)
        d.rounded_rectangle((80, SH - 400, SW - 80, SH - 290), 55, fill="#FFFFFF")
        t = "Tap to watch"
        tw = d.textlength(t, font=bf)
        x0 = (SW - tw) / 2 + 30
        d.polygon([(x0 - 64, SH - 368), (x0 - 64, SH - 322), (x0 - 26, SH - 345)], fill="#111111")
        d.text((x0, SH - 375), t, font=bf, fill="#111111")
    elif kind == "question":
        bg = c.get("bg", "#FFFFFF")
        im = Image.new("RGB", (SW, SH), bg)
        if photo:
            ph = _cover(photo, SW, SH).filter(ImageFilter.GaussianBlur(28))
            im = Image.blend(ph, im, 0.55)
        d = ImageDraw.Draw(im)
        card = (100, 560, SW - 100, 1360)
        d.rounded_rectangle(card, 48, fill="#FFFFFF")
        font, lines, lh = _wrap(d, s["title"], f["main"], SW - 300, 300, 84)
        y = 640
        for ln in lines:
            d.text(((SW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill="#111111")
            y += lh
        opts = (s.get("body") or "Yes|No").split("|")[:2]
        of = _font(f["caption"], 46)
        for k, o in enumerate(opts):
            top = 1000 + k * 150
            d.rounded_rectangle((180, top, SW - 180, top + 120), 60, fill=c["pop"] if k == 0 else "#F1F1F1")
            d.text(((SW - d.textlength(o, font=of)) / 2, top + 32), o, font=of, fill=_on(c["pop"]) if k == 0 else "#111111")
    else:
        im = Image.new("RGB", (SW, SH), c["pop"])
        d = ImageDraw.Draw(im)
        ink = _on(c["pop"])
        font, lines, lh = _wrap(d, s["title"], f["main"], SW - 200, 600, 110)
        y = 700
        for ln in lines:
            d.text(((SW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=ink)
            y += lh
        bf = _font(f["accent"], 70)
        if s.get("body"):
            fb, bl, blh = _wrap(d, s["body"], f["accent"], SW - 200, 300, 70)
            y += 40
            for ln in bl:
                d.text(((SW - d.textlength(ln, font=fb)) / 2, y), ln, font=fb, fill=ink)
                y += blh
        d.rounded_rectangle((220, 1380, SW - 220, 1500), 60, fill="#FFFFFF")
        lt = "Open the link"
        lf = _font(f["caption"], 46)
        d.text(((SW - d.textlength(lt, font=lf)) / 2, 1410), lt, font=lf, fill="#111111")
    if handle:
        hf = _font(f["caption"], 36)
        ImageDraw.Draw(im).text((80, 160), handle, font=hf, fill="#FFFFFF" if kind == "teaser" else _on(c["pop"]) if kind == "cta" else "#111111")
    return im


# ------------------------------------------------------------------ memory style (personal posts)
def _photo_img(ref, slug):
    from .scrapbook import _photo
    f = ref["file"] if isinstance(ref, dict) else str(ref).partition("@")[0]
    if not os.path.isabs(f) and not os.path.exists(os.path.join(project.ROOT, f)):
        ref = project.path(slug, "source", f) + ("@" + str(ref).partition("@")[2] if "@" in str(ref) else "")
    return _photo(ref)[0]


def _paper(w, h, pack):
    import numpy as np
    rgb = np.array(_rgb(pack["colors"].get("bg", "#FBEFF1")))
    rng = np.random.default_rng(3)
    y = np.linspace(-1, 1, h)[:, None, None]; x = np.linspace(-1, 1, w)[None, :, None]
    arr = np.ones((h, w, 3)) * rgb * (1 - 0.05 * (x ** 2 + y ** 2)) + rng.normal(0, 3.0, (h, w, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).convert("RGBA")


def _print(img, pack, width, caption="", k=0, tilt=6):
    from .scrapbook import make_print, settings
    st = settings({"size": width, "tilt": tilt, "seed": 11 + k}, pack)
    return make_print(img, st, k, pack, caption)


def _script(d, text, pack, box_w, size, max_h=400):
    return _wrap(d, text, pack["fonts"].get("accent", pack["fonts"]["main"]), box_w, max_h, size, 40, 1.05)


def _soft_fade(im, colour, start=0.55, strength=0.85):
    """A soft fade into the pack colour at the bottom (gentler than the dark shade, for personal posts)."""
    w, h = im.size
    g = Image.new("L", (1, h))
    for y in range(h):
        g.putpixel((0, y), int(255 * strength * max(0.0, (y / h - start) / (1 - start)) ** 1.6))
    return Image.composite(Image.new("RGB", (w, h), colour), im.convert("RGB"), g.resize((w, h)))


def memory_slide(i, n, s, pack, slug, fallback):
    c = pack["colors"]
    ink = c.get("bubble_text") or c["ink"]
    lay = s.get("layout") or ("photo" if i == 0 else "collage" if i == n - 1 else "photo")
    photo = _photo_img(s["photo"], slug) if s.get("photo") else (Image.open(fallback).convert("RGB") if fallback else None)
    if lay == "photo" and photo is not None:
        from PIL import ImageOps
        im = ImageOps.fit(photo, (CW, CH), Image.LANCZOS, centering=(0.5, 0.4))
        if s.get("title"):
            im = _soft_fade(im, c.get("bg", "#FBEFF1"), 0.5, 0.92)
            d = ImageDraw.Draw(im)
            if s.get("kicker"):
                kf = _font(pack["fonts"]["main"], 40)
                d.text(((CW - d.textlength(s["kicker"].upper(), font=kf)) / 2, CH - 330), s["kicker"].upper(), font=kf, fill=ink)
            font, lines, lh = _script(d, s["title"], pack, CW - 160, 150, 260)
            y = CH - 270
            for ln in lines:
                d.text(((CW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=ink)
                y += lh
        elif s.get("body"):                                   # a small handwritten note on a white tag
            d = ImageDraw.Draw(im)
            f = _font(pack["fonts"].get("accent", pack["fonts"]["main"]), 78)
            tw = d.textlength(s["body"], font=f)
            d.rounded_rectangle((60, CH - 190, 60 + tw + 80, CH - 66), 36, fill="#FFFDFA")
            d.text((100, CH - 186), s["body"], font=f, fill=ink)
        return im.convert("RGB")
    im = _paper(CW, CH, pack)
    d = ImageDraw.Draw(im)
    if lay == "polaroid" and photo is not None:
        pr = _print(photo, pack, 640, s.get("body", ""), i, 4)
        im.alpha_composite(pr, ((CW - pr.width) // 2, (CH - pr.height) // 2 - (40 if s.get("title") else 0)))
    else:                                                     # collage of prints
        refs = s.get("photos") or ([s["photo"]] if s.get("photo") else [])
        imgs = [_photo_img(r, slug) for r in refs][:4] or ([photo] if photo else [])
        spots = [(300, 430), (780, 470), (330, 900), (770, 940)][:len(imgs)]
        for k, (img, (x, y)) in enumerate(zip(imgs, spots)):
            pr = _print(img, pack, 380, "", k, 7)
            im.alpha_composite(pr, (int(x - pr.width / 2), int(y - pr.height / 2) - (60 if s.get("title") else 0)))
    if s.get("title"):
        font, lines, lh = _script(d, s["title"], pack, CW - 160, 120, 240)
        y = CH - 60 - lh * len(lines)
        for ln in lines:
            d.text(((CW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=ink)
            y += lh
    return im.convert("RGB")


def memory_story(s, pack, slug, fallback):
    c = pack["colors"]
    ink = c.get("bubble_text") or c["ink"]
    lay = s.get("layout", "collage")
    photo = _photo_img(s["photo"], slug) if s.get("photo") else (Image.open(fallback).convert("RGB") if fallback else None)
    if lay == "photo" and photo is not None:
        from PIL import ImageOps
        im = _soft_fade(ImageOps.fit(photo, (SW, SH), Image.LANCZOS, centering=(0.5, 0.4)), c.get("bg", "#FBEFF1"), 0.55, 0.95)
    else:
        im = _paper(SW, SH, pack)
        if lay == "polaroid" and photo is not None:
            pr = _print(photo, pack, 620, s.get("body", ""), 0, 4)
            im.alpha_composite(pr, ((SW - pr.width) // 2, 250))
        else:
            refs = s.get("photos") or ([s["photo"]] if s.get("photo") else [])
            imgs = [_photo_img(r, slug) for r in refs][:3] or ([photo] if photo else [])
            spots = [(330, 560), (750, 680), (520, 980)][:len(imgs)]
            for k, (img, (x, y)) in enumerate(zip(imgs, spots)):
                pr = _print(img, pack, 400, "", k, 8)
                im.alpha_composite(pr, (int(x - pr.width / 2), int(y - pr.height / 2)))
    d = ImageDraw.Draw(im)
    if s.get("kicker"):
        kf = _font(pack["fonts"]["main"], 44)
        d.text(((SW - d.textlength(s["kicker"].upper(), font=kf)) / 2, SH - 560), s["kicker"].upper(), font=kf, fill=ink)
    if s.get("title"):
        font, lines, lh = _script(d, s["title"], pack, SW - 100, 150, 330)
        y = SH - 490
        for ln in lines:
            d.text(((SW - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=ink)
            y += lh
    if s.get("tag"):                                          # a soft pill, e.g. "nuwe reel"
        tf = _font(pack["fonts"].get("caption", pack["fonts"]["main"]), 40)
        tw = d.textlength(s["tag"], font=tf)
        d.rounded_rectangle(((SW - tw) / 2 - 36, SH - 250, (SW + tw) / 2 + 36, SH - 170), 40, fill=c.get("pop", "#E58FA6"))
        d.text(((SW - tw) / 2, SH - 239), s["tag"], font=tf, fill="#FFFFFF")
    return im.convert("RGB")


# ------------------------------------------------------------------ the kit
def make(slug):
    meta = project.load(slug, "project.json") or {}
    words = project.load(slug, "posts.json") or draft(slug)
    plan = project.load(slug, "plan.json") or {}
    if plan.get("pack") and plan["pack"] != "brand":          # the reel's own look (e.g. a family reel in Blush)
        pack = packs.load(plan["pack"])
    else:
        pack = packs.load("brand:" + meta["brand"]) if meta.get("brand") else packs.load("brand")
    memory = words.get("style") == "memory"
    out = project.path(slug, "posts")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith((".png", ".zip", ".txt")):
            os.remove(os.path.join(out, f))
    final = project.path(slug, "renders", "final.mp4")
    src = project.source_of(slug)
    video = src if src and os.path.exists(src) else (final if os.path.exists(final) else None)   # clean footage, no overlays
    photos = _frames(video, max(3, len(words["carousel"])), os.path.join(out, "frames")) if video else []
    pick = lambda i: photos[i % len(photos)] if photos else None
    logo, handle = _logo(pack), words.get("handle") or ""
    files = []
    n = len(words["carousel"])
    for i, s in enumerate(words["carousel"]):
        p = os.path.join(out, f"carousel-{i + 1:02d}.png")
        (memory_slide(i, n, s, pack, slug, pick(i)) if memory else
         carousel_slide(i, n, s, pack, pick(i), logo, handle)).save(p, optimize=True)
        files.append(p)
    for i, s in enumerate(words.get("stories", [])):
        p = os.path.join(out, f"story-{i + 1:02d}.png")
        (memory_story(s, pack, slug, pick(i + 1)) if memory else
         story_frame(s, pack, pick(i + 1), handle)).save(p, optimize=True)
        files.append(p)
    cap = os.path.join(out, "caption.txt")
    open(cap, "w", encoding="utf-8").write(words.get("caption", ""))
    files.append(cap)
    zp = os.path.join(out, "posts.zip")
    with zipfile.ZipFile(zp, "w") as z:
        for f in files:
            z.write(f, os.path.basename(f))
    project.save(slug, "posts.json", words)
    return {"carousel": [os.path.basename(f) for f in files if "carousel-" in f],
            "stories": [os.path.basename(f) for f in files if "story-" in f], "zip": "posts.zip",
            "caption": words.get("caption", "")}
