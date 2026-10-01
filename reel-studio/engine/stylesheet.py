"""Brand style from a design file — the user's look, read from wherever they already keep it.

Accepts:
  * a DESIGN.md / brand.md / any markdown or text with colours (#hex) and font names
    (e.g. a design-system file exported from HyperFrames, Google Stitch, Figma notes, a brand guide)
  * CSS (custom properties like --accent: #e11d48; font-family: "Playfair Display")
  * JSON (any nesting: keys containing text/accent/background/heading/body …)
  * values Claude read from a Canva design through the Canva connector, passed as a small .md
Then: fonts are fetched from Google Fonts (free) when they're not already on the computer,
the pack is saved to brand/brand.json, and an overview sheet shows every piece in the new look.
"""
import json, os, re

from . import brand, packs

ROOT = packs.ROOT
HEX = r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
ROLE_WORDS = {
    "background": ("background", "bg", "surface", "canvas", "paper", "base", "backdrop"),
    "text": ("text", "ink", "foreground", "fg", "body colour", "body color", "on-surface", "neutral-900", "dark"),
    "accent": ("accent", "primary", "brand", "highlight", "pop", "cta", "action", "secondary"),
}
FONT_WORDS = {
    "main": ("heading", "headline", "display", "title", "h1", "main", "hook"),
    "caption": ("body", "caption", "text", "paragraph", "ui", "sans"),
    "accent": ("accent", "script", "handwrit", "signature", "side comment", "hand"),
}
GENERIC = {"sans-serif", "serif", "monospace", "cursive", "system-ui", "inherit", "arial", "helvetica",
           "-apple-system", "blinkmacsystemfont", "segoe ui", "ui-sans-serif", "ui-serif"}


def _hex6(h):
    h = h.lstrip("#")
    return "#" + ("".join(c * 2 for c in h) if len(h) == 3 else h).upper()


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix} {k}")
    elif isinstance(obj, list):
        for v in obj:
            yield from _flatten(v, prefix)
    else:
        yield f"{prefix}: {obj}"


def _lum(h):
    r, g, b = brand.rgb_(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _sat(h):
    r, g, b = [x / 255 for x in brand.rgb_(h)]
    return (max(r, g, b) - min(r, g, b)) / max(max(r, g, b), 1e-6)


def read_frame(txt):
    """A HyperFrames FRAME.md / design-system front matter: a `colors:` block and a `typography:` block
    of `role: { fontFamily: "X", cqw: N … }` lines. -> spec, or None when the text isn't one."""
    if not re.search(r"^colors:\s*$", txt, re.M) or "fontFamily" not in txt:
        return None
    cols, block = [], None
    fams = []                                                 # (role, family, size)
    for line in txt.splitlines():
        if re.match(r"^\S", line):
            block = line.split(":")[0].strip()
            continue
        if block == "colors":
            m = re.match(r"\s+([\w-]+):\s*[\"']?(#[0-9a-fA-F]{3,6})\b", line)
            if m:
                cols.append((m.group(1).lower(), _hex6(m.group(2))))
        elif block == "typography":
            m = re.match(r"\s+([\w-]+):\s*\{.*?fontFamily:\s*[\"']([^\"']+)[\"'](.*)", line)
            if m:
                size = re.search(r"(?:cqw|px):\s*([\d.]+)", m.group(3))
                fams.append((m.group(1).lower(), m.group(2), float(size.group(1)) if size else 0))
    if not cols:
        return None
    hexes = [h for _, h in cols]
    text = min(hexes, key=_lum)
    lights = [h for h in hexes if _lum(h) > 0.8]
    bg = next((h for h in lights if h != "#FFFFFF"), lights[0] if lights else "#FFFFFF")
    named = [h for n, h in cols if re.search(r"accent|primary|brand|pop|highlight", n)
             and h not in (text, bg) and _lum(h) < 0.85]
    vivid = [h for h in hexes if _sat(h) > 0.35 and 0.12 < _lum(h) < 0.9 and h not in (text, bg)]
    accent = (named + vivid + [h for h in hexes if h not in (text, bg)] + ["#E4572E"])[0]
    fonts = {}
    disp = [f for f in fams if re.search(r"hero|display|headline|title|jumbo|poster", f[0])]
    if disp:
        fonts["main"] = max(disp, key=lambda f: f[2])[1]
    body = [f for f in fams if f[0].startswith("body")]
    if body:
        fonts["caption"] = body[0][1]
    acc = [f for f in fams if re.search(r"script|hand|accent|quote|italic|signature", f[0])
           and f[1] not in fonts.values()]
    if acc:
        fonts["accent"] = acc[0][1]
    if fams:
        fonts.setdefault("main", fams[0][1])
        fonts.setdefault("caption", fonts["main"])
    return {"colors": {"background": bg, "text": text, "accent": accent}, "fonts": fonts, "found": hexes}


def read(path_or_text):
    """-> {"colors": {background,text,accent}, "fonts": {main,caption,accent}, "found": [...]}"""
    txt = path_or_text
    if os.path.exists(str(path_or_text)):
        txt = open(path_or_text, encoding="utf-8", errors="ignore").read()
    fr = read_frame(txt)
    if fr:
        return fr
    if True:
        if path_or_text.lower().endswith(".json"):
            try:
                txt = "\n".join(_flatten(json.loads(txt)))
            except Exception:
                pass
    lines = [l.strip() for l in re.split(r"[\n;{}]", txt) if l.strip()]
    colors, fonts, seen = {}, {}, []
    last_label = ""
    for l in lines:
        low = l.lower()
        hexes = re.findall(HEX, l)
        if not hexes and len(l) < 80 and not re.search(r"font|family", low):
            last_label = low                           # a heading like "### Accent" before "#E11D48"
        for h in hexes:
            ctx = low.split(h.lower())[0][-60:] or last_label
            seen.append(_hex6(h))
            for role, words in ROLE_WORDS.items():
                if role not in colors and any(w in ctx for w in words):
                    colors[role] = _hex6(h)
                    break
        m = re.search(r"(?:font[-\s]?family|font|typeface)\s*[:=]\s*[\"']?([A-Za-z][A-Za-z0-9 ]+?)[\"']?\s*(?:,|$|\(|\.|;)", l, re.I)
        m = m or re.search(r"font name:\s*([A-Za-z][A-Za-z0-9 ]+)", l, re.I)
        if m:
            fam = m.group(1).strip()
            if fam.lower() not in GENERIC:
                ctx = low[:low.find(fam.lower())] + " " + last_label
                for role, words in FONT_WORDS.items():
                    if role not in fonts and any(w in ctx for w in words):
                        fonts[role] = fam
                        break
                else:
                    fonts.setdefault("main" if "main" not in fonts else "caption", fam)
    # anything still missing: fill from the palette in order (light = background, dark = text, colourful = accent)
    rest = [h for h in dict.fromkeys(seen) if h not in colors.values()]
    for h in rest:
        r, g, b = brand.rgb_(h)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if "accent" not in colors and not brand.is_neutral(h):
            colors["accent"] = h
        elif "background" not in colors and lum > 0.8:
            colors["background"] = h
        elif "text" not in colors and lum < 0.3:
            colors["text"] = h
    return {"colors": colors, "fonts": fonts, "found": list(dict.fromkeys(seen))}


def _font_file(family):
    if not family:
        return None
    stem = re.sub(r"[^a-z0-9]", "", family.lower())
    for f in sorted(packs.all_fonts(), key=lambda x: "italic" in x.lower()):     # upright first
        if re.sub(r"[^a-z0-9]", "", os.path.basename(f).lower()).startswith(stem):
            return f
    try:
        return brand.google_font(family)
    except Exception:
        return None


def make_pack(spec, name="My style", save=True):
    """Spec from read() -> saved brand pack. -> (pack, notes)"""
    c = spec["colors"]
    bg = c.get("background", "#FFFFFF")
    ink = c.get("text", "#111111")
    pop = c.get("accent", "#E4572E")
    dark = sum(brand.rgb_(bg)) / 3 < 110
    roles = {"bg": bg, "ink": ink, "pop": pop, "accent": pop, "paper": "#FFFFFF" if not dark else ink,
             "bubble_text": ink if not dark else bg}
    notes, files = [], {}
    for role in ("main", "caption", "accent"):
        fam = spec["fonts"].get(role)
        files[role] = _font_file(fam)
        if fam and not files[role]:
            notes.append(f"'{fam}' isn't on Google Fonts — send me the font file (or install it) and I'll use it; "
                         f"using a close free font for now.")
    pack = brand.build_pack(name, roles, files["main"], files["accent"], files["caption"] or files["main"],
                            prefer="dark" if dark else "light")
    old = packs.load("brand") if packs.has_brand() else {}
    for k in ("logo", "endcard", "voice"):
        if old.get(k):
            pack[k] = old[k]
    if save:
        packs.save_brand(pack)
    return pack, notes


def overview(pack, out, name="your name", handle="what you do", photo=None, only=None, heading=None):
    """One sheet with every piece in the new look: hook, captions, side comment, takeover, name tag, end card.
    photo = a frame from their own video to draw on; only = which panels; heading = a title above the row."""
    from PIL import Image, ImageDraw, ImageFont
    p = packs._resolve(json.loads(json.dumps(pack)))
    col = p["colors"]
    W, H, pad = 360, 640, 24

    def f(role, size):
        try:
            fo = ImageFont.truetype(p["fonts"][role]["file"], size)
            try:                                          # variable fonts: use the pack's weight
                fo.set_variation_by_axes([p["fonts"][role].get("weight", 400)])
            except Exception:
                pass
            return fo
        except Exception:
            return ImageFont.load_default()

    still = None
    if photo and os.path.exists(photo):
        from PIL import ImageOps, ImageEnhance
        still = ImageEnhance.Brightness(ImageOps.fit(Image.open(photo).convert("RGB"), (W, H))).enhance(0.82)

    def panel(title, draw_fn, bg):
        if only and title not in only:
            return None
        im = still.copy() if (bg == "photo" and still is not None) else Image.new("RGB", (W, H), "#5E646C" if bg == "photo" else bg)
        d = ImageDraw.Draw(im)
        state["photo"] = bg == "photo"
        draw_fn(d)
        d.text((14, H - 30), title, fill="#888888", font=f("caption", 16))
        return im

    state = {"photo": False}

    def center(d, y, text, font, fill):
        w = d.textlength(text, font=font)
        if state["photo"]:                                # a soft shadow keeps text readable on footage
            d.text(((W - w) / 2 + 2, y + 3), text, fill="#00000099", font=font)
        d.text(((W - w) / 2, y), text, fill=fill, font=font)

    photo = "photo"                   # their own footage (or grey when there is none)
    panels = [
        panel("hook headline", lambda d: (center(d, 150, "STOP THE", f("main", 52), "#FFFFFF"),
                                          center(d, 210, "SCROLL", f("main", 52), col["pop"])), photo),
        panel("captions", lambda d: (center(d, 470, "how your", f("caption", 34), "#FFFFFF"),
                                     center(d, 512, "captions read", f("caption", 34), col["caption_active"])), photo),
        panel("side comment", lambda d: (d.text((40, 160), "wait for it...", fill="#FFFFFF", font=f("accent", 40)),
                                         center(d, 470, "this part is so me", f("accent", 38), col["pop"])), photo),
        panel("takeover", lambda d: [center(d, 180 + i * 80, w, f("main", 70), c)
                                     for i, (w, c) in enumerate([("THE", col["ink"]), ("BIG", col["pop"]),
                                                                 ("IDEA", col["ink"])])], col["bg"]),
        panel("name tag", lambda d: (d.rounded_rectangle((40, 440, 320, 540), 18, fill=col["paper"]),
                                     d.text((60, 452), name, fill=col["bubble_text"], font=f("main", 32)),
                                     d.text((60, 496), handle, fill=col["pop"], font=f("caption", 24))), photo),
        panel("end card", lambda d: (center(d, 200, "want this?", f("accent", 40), col["ink"]),
                                     center(d, 260, "COMMENT", f("main", 46), col["ink"]),
                                     center(d, 318, "REEL", f("main", 74), col["pop"]),
                                     center(d, 410, "and i'll send you the link", f("caption", 20), col["ink"])), col["bg"]),
    ]
    panels = [x for x in panels if x is not None]
    cols = min(3, len(panels))
    rows = (len(panels) + cols - 1) // cols
    top = 56 if heading else 0
    sheet = Image.new("RGB", (W * cols + pad * (cols + 1), top + H * rows + pad * (rows + 1)), "#F4F1EA")
    if heading:
        ImageDraw.Draw(sheet).text((pad, 18), heading, fill="#16181D", font=f("main", 30))
    for i, im in enumerate(panels):
        sheet.paste(im, (pad + (i % cols) * (W + pad), top + pad + (i // cols) * (H + pad)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out, quality=92)
    return out
