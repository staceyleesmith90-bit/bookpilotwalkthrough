"""Brand setup helpers for the onboarding interview.

Three routes, all ending in brand/brand.json:
  1. from_website(url)   — pull colours, fonts and the logo from their site
  2. from_image(path)    — pull a palette from a logo, photo, mood board or screenshot
  3. starter_directions(vibe) — no brand yet: suggest 3 complete looks to pick from
Then build_pack(...) turns the answers into a pack and preview() renders a sample.
"""
import colorsys, io, json, os, re, urllib.parse, urllib.request
from collections import Counter
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND_DIR = os.path.join(ROOT, "brand")
GF = "https://raw.githubusercontent.com/google/fonts/main/"
UA = {"User-Agent": "Mozilla/5.0 (reel-studio brand setup)"}


# ---------------------------------------------------------------- colour helpers
def hex_(rgb):
    return "#%02X%02X%02X" % tuple(int(c) for c in rgb[:3])


def rgb_(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hsv(h):
    r, g, b = [c / 255 for c in rgb_(h)]
    return colorsys.rgb_to_hsv(r, g, b)


def is_neutral(h, sat=0.12):
    s, v = _hsv(h)[1], _hsv(h)[2]
    return s < sat or v < 0.12


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(rgb_(a), rgb_(b))) ** 0.5


def dedupe(colors, min_dist=40):
    out = []
    for c in colors:
        if all(_dist(c, o) > min_dist for o in out):
            out.append(c)
    return out


def assign_roles(palette, prefer="light"):
    """Turn a list of brand colours into pack roles with readable contrast."""
    from .packs import contrast
    cols = dedupe([c.upper() for c in palette])
    brights = sorted([c for c in cols if not is_neutral(c)], key=lambda c: -_hsv(c)[1] * _hsv(c)[2])
    neutrals = [c for c in cols if is_neutral(c)]
    light = max(neutrals + cols, key=lambda c: _hsv(c)[2]) if cols else "#FFFFFF"
    dark = min(neutrals + cols, key=lambda c: _hsv(c)[2]) if cols else "#111111"
    if _hsv(light)[2] < 0.85:
        light = "#FAF7F2"
    if _hsv(dark)[2] > 0.3:
        dark = "#1A1A1A"
    bg, ink = (light, dark) if prefer == "light" else (dark, light)
    pop = brights[0] if brights else ("#F2B705" if prefer == "light" else "#E8A0A8")
    accent = brights[1] if len(brights) > 1 else pop
    roles = {"bg": bg, "ink": ink, "pop": pop, "accent": accent,
             "paper": "#FFFFFF" if prefer == "light" else light}
    roles["bubble_text"] = dark if contrast(dark, roles["paper"]) > contrast(light, roles["paper"]) else light
    return roles


# ---------------------------------------------------------------- route 2: image
def from_image(path, n=8):
    """Palette from any image (logo, photo, mood board). Ignores the flat background."""
    img = Image.open(path).convert("RGBA")
    img.thumbnail((300, 300))
    px = [p[:3] for p in img.getdata() if p[3] > 200]
    if not px:
        return []
    q = Image.new("RGB", (len(px), 1))
    q.putdata(px)
    q = q.quantize(colors=n * 2, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = Counter(q.getdata())
    cols = [hex_(pal[i * 3:i * 3 + 3]) for i, _ in counts.most_common()]
    # the most common light/dark neutral is usually the background — keep it last
    return dedupe(cols, 45)[:n]


# ---------------------------------------------------------------- route 1: website
def _get(url, binary=False, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "ignore")


def from_website(url):
    """Read a site's HTML + CSS for brand colours, fonts and the logo.
    Returns {"colors": [...most used first], "fonts": [...], "logo_urls": [...]}."""
    if not url.startswith("http"):
        url = "https://" + url
    html = _get(url)
    css = [html]
    for href in re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)', html)[:6]:
        try:
            css.append(_get(urllib.parse.urljoin(url, href)))
        except Exception:
            pass
    text = "\n".join(css)
    hexes = [h.upper() for h in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text)]
    hexes = ["#" + (h if len(h) == 6 else "".join(c * 2 for c in h)) for h in hexes]
    for r, g, b in re.findall(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)", text):
        hexes.append(hex_((int(r), int(g), int(b))))
    ranked = [c for c, _ in Counter(hexes).most_common(40)]
    brand = [c for c in ranked if not is_neutral(c)][:6]
    neutrals = [c for c in ranked if is_neutral(c)][:3]
    fonts = []
    for fam in re.findall(r"font-family\s*:\s*([^;}{]+)", text):
        for f in fam.split(","):
            f = f.strip().strip("'\"")
            if f and not f.startswith(("var(", "ui-")) and not re.search(r"emoji|symbol", f, re.I) and f.lower() not in (
                    "inherit", "sans-serif", "serif", "monospace", "system-ui", "-apple-system", "cursive",
                    "blinkmacsystemfont", "segoe ui", "arial", "helvetica", "helvetica neue", "roboto",
                    "apple color emoji", "segoe ui emoji", "noto color emoji", "initial"):
                fonts.append(f)
    for fam in re.findall(r"fonts\.googleapis\.com/css2?\?family=([^\"'&]+)", html):
        fonts += [urllib.parse.unquote_plus(x.split(":")[0]) for x in fam.split("|")]
    fonts = [f for f, _ in Counter(fonts).most_common(6)]
    logos = []
    for tag in re.findall(r"<img[^>]+>", html):
        if re.search(r"logo", tag, re.I):
            m = re.search(r'src=["\']([^"\']+)', tag)
            if m:
                logos.append(urllib.parse.urljoin(url, m.group(1)))
    for pat in (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                r'<link[^>]+rel=["\'](?:apple-touch-icon|icon)["\'][^>]+href=["\']([^"\']+)'):
        logos += [urllib.parse.urljoin(url, m) for m in re.findall(pat, html)]
    return {"colors": brand + neutrals, "fonts": fonts, "logo_urls": list(dict.fromkeys(logos))[:5]}


def download_logo(url, name="logo"):
    data = _get(url, binary=True)
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        ext = ".png"
    os.makedirs(BRAND_DIR, exist_ok=True)
    p = os.path.join(BRAND_DIR, name + ext)
    open(p, "wb").write(data)
    return p


# ---------------------------------------------------------------- fonts
LIBRARY_FONTS = {  # our bundled OFL fonts by category, for fallbacks
    "sans": "library/fonts/Poppins-ExtraBold.ttf", "serif": "library/fonts/PlayfairDisplay-Variable.ttf",
    "script": "library/fonts/Caveat-Variable.ttf", "display": "library/fonts/BebasNeue-Regular.ttf",
    "handwriting": "library/fonts/Caveat-Variable.ttf", "clean": "library/fonts/Inter-Variable.ttf",
}


def google_font(family):
    """Download a Google Font (OFL/Apache — free to use) into brand/fonts. Returns path or None."""
    slug = re.sub(r"[^a-z0-9]", "", family.lower())
    os.makedirs(os.path.join(BRAND_DIR, "fonts"), exist_ok=True)
    for lic in ("ofl", "apache", "ufl"):
        try:
            meta = _get(f"{GF}{lic}/{slug}/METADATA.pb")
        except Exception:
            continue
        files = re.findall(r'filename:\s*"([^"]+)"', meta)
        pick = next((f for f in files if "Italic" not in f and ("Bold" in f or "[" in f)), files[0] if files else None)
        if not pick:
            return None
        out = os.path.join(BRAND_DIR, "fonts", pick.replace("[", "-").replace("]", "").replace(",", "_"))
        if "[" in pick and "Variable" not in out:
            out = out.replace(".ttf", "-Variable.ttf")
        if not os.path.exists(out):
            open(out, "wb").write(_get(f"{GF}{lic}/{slug}/{urllib.parse.quote(pick)}", binary=True))
        return out
    return None


FONT_ROLES = {  # what a font can be used for -> where it lives in the brand pack
    "headline": ("fonts", "main"), "main": ("fonts", "main"), "accent": ("fonts", "accent"),
    "caption": ("fonts", "caption"),
    "script": ("title_fonts", "script"), "serif": ("title_fonts", "serif"), "serif_bold": ("title_fonts", "serif_bold"),
    "brush": ("title_fonts", "brush"), "sans": ("title_fonts", "sans"),
    "sticker": ("sticker", "font"), "sticker_label": ("sticker", "label_font"),
}


def add_font(src, role=None, filename=None):
    """Use a font that isn't on Google Fonts: the user's own .ttf/.otf (a bought or custom font).
    Checks it opens, copies it to brand/fonts/ and, if a role is given, uses it there
    (e.g. role="sticker" for sticker lettering, "headline" for big text). Returns the saved path."""
    from PIL import ImageFont
    name = os.path.basename(filename or src)
    if not name.lower().endswith((".ttf", ".otf")):
        raise ValueError("Please upload a .ttf or .otf font file (.woff web fonts don't work for video).")
    try:
        ImageFont.truetype(src, 40)
    except Exception:
        raise ValueError("That font file couldn't be opened — it may be damaged or a web-only font.")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    dst = os.path.join(BRAND_DIR, "fonts", name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.abspath(src) != os.path.abspath(dst):
        with open(src, "rb") as a, open(dst, "wb") as b:
            b.write(a.read())
    if role:
        set_font_role(role, dst)
    return dst


def set_font_role(role, font):
    """Point a brand role at a font (a path, an uploaded/library font name, or "auto" to reset
    sticker fonts to the automatic brand match)."""
    from . import packs
    if role not in FONT_ROLES:
        raise ValueError(f"Unknown font role '{role}'. Choose from: {', '.join(FONT_ROLES)}")
    group, key = FONT_ROLES[role]
    pack = json.load(open(packs.BRAND)) if packs.has_brand() else json.loads(json.dumps(packs.presets()["bold"]))
    if group == "sticker":
        if font in (None, "", "auto"):
            pack.setdefault("sticker", {}).pop(key, None)
        else:
            spec = packs.resolve_font(packs.load(), font)
            if not spec:
                raise ValueError(f"Font '{font}' not found. Upload it first.")
            pack.setdefault("sticker", {})[key] = os.path.relpath(spec["file"], ROOT) if os.path.isabs(spec["file"]) else spec["file"]
    else:
        spec = packs.resolve_font(packs.load(), font) if not os.path.exists(font) else {"file": font}
        if not spec:
            raise ValueError(f"Font '{font}' not found. Upload it first.")
        f = os.path.relpath(os.path.abspath(spec["file"]), ROOT)
        old = pack.setdefault(group, {}).get(key, {})
        pack[group][key] = {"file": f, **({"case": old["case"]} if old.get("case") else {})}
    packs.save_brand(pack)
    return pack


# ---------------------------------------------------------------- route 3: new brand
DIRECTIONS = [
    {"name": "Warm & Honest", "tags": {"warm", "honest", "cosy", "family", "mom", "friendly", "soft"},
     "colors": ["#FFF4E6", "#3A2E2A", "#E07A5F", "#F2CC8F"], "fonts": ("Nunito-Variable", "ShadowsIntoLight"), "sticker": "flat"},
    {"name": "Bold Business", "tags": {"bold", "confident", "business", "money", "loud", "modern"},
     "colors": ["#F4EFE6", "#141414", "#F2B705", "#E4572E"], "fonts": ("Poppins-ExtraBold", "Caveat-Variable"), "sticker": "doodle"},
    {"name": "Calm Editorial", "tags": {"calm", "classic", "elegant", "wellness", "slow", "premium"},
     "colors": ["#1F3B2D", "#F4EFE6", "#E8A0A8", "#C9B79C"], "fonts": ("PlayfairDisplay-Variable", "PlayfairDisplay-Italic-Variable"), "sticker": "doodle"},
    {"name": "Playful Pop", "tags": {"fun", "playful", "kids", "colourful", "colorful", "silly", "bright"},
     "colors": ["#EDE7FF", "#23104F", "#FF5FA2", "#2EC4B6"], "fonts": ("Baloo2-Variable", "Pacifico-Regular"), "sticker": "retro"},
    {"name": "Clean Minimal", "tags": {"clean", "minimal", "tech", "simple", "coach", "b2b", "quiet"},
     "colors": ["#FFFFFF", "#111111", "#2F6BFF", "#9DB4FF"], "fonts": ("Inter-Variable", "Inter-Variable"), "sticker": "doodle"},
    {"name": "Dark Luxe", "tags": {"luxury", "luxe", "beauty", "fashion", "moody", "rich", "high-end"},
     "colors": ["#14110F", "#F3E9DC", "#C8A165", "#8C6A43"], "fonts": ("CormorantGaramond-Variable", "DMSerifDisplay-Regular"), "sticker": "neon"},
    {"name": "Retro Sunshine", "tags": {"retro", "vintage", "70s", "sunny", "nostalgic", "warm"},
     "colors": ["#FDF0D5", "#3D2C1E", "#E76F51", "#2A9D8F"], "fonts": ("BebasNeue-Regular", "Pacifico-Regular"), "sticker": "retro"},
    {"name": "Fresh Natural", "tags": {"natural", "green", "health", "organic", "fresh", "earthy"},
     "colors": ["#F1F5EC", "#1F2D1B", "#6A994E", "#F4A259"], "fonts": ("DMSerifDisplay-Regular", "Caveat-Variable"), "sticker": "doodle"},
]


def starter_directions(vibe_words, n=3):
    words = {w.strip().lower() for w in re.split(r"[,\s]+", vibe_words) if w.strip()}
    scored = sorted(DIRECTIONS, key=lambda d: -len(d["tags"] & words))
    return scored[:n]


def _font(stem):
    return f"library/fonts/{stem}.ttf"


VIBE_TO_PRESET = {  # which preset's title-font pairing suits a vibe word
    "bold": "bold", "confident": "bold", "business": "bold", "loud": "bold", "modern": "bold",
    "calm": "editorial", "classic": "editorial", "elegant": "editorial", "premium": "editorial", "wellness": "editorial",
    "warm": "sunny", "cosy": "sunny", "cozy": "sunny", "friendly": "sunny", "soft": "sunny", "family": "sunny", "honest": "sunny",
    "fun": "playful", "playful": "playful", "kids": "playful", "bright": "playful", "silly": "playful",
    "clean": "minimal", "minimal": "minimal", "tech": "minimal", "simple": "minimal", "quiet": "minimal",
    "luxe": "luxe", "luxury": "luxe", "beauty": "luxe", "fashion": "luxe", "moody": "luxe", "rich": "luxe",
}


def title_fonts_for_vibe(vibe):
    """Pick a title-font pairing (serif / script / brush / sans) that matches the vibe words."""
    from .packs import presets
    votes = Counter(VIBE_TO_PRESET[w] for w in re.split(r"[,\s]+", (vibe or "").lower()) if w in VIBE_TO_PRESET)
    name = votes.most_common(1)[0][0] if votes else "editorial"
    return json.loads(json.dumps(presets()[name]["title_fonts"]))


def build_pack(name, colors, main_font=None, accent_font=None, caption_font=None, prefer="light",
               sticker_style="doodle", vibe="", logo=None, captions="karaoke", grade=None, case=None,
               title_fonts=None):
    """Make a complete pack from brand answers. `colors` may be roles (dict) or a list."""
    roles = colors if isinstance(colors, dict) else assign_roles(colors, prefer)
    main_font = main_font or _font("Poppins-ExtraBold")
    heavy = {"main": 800, "caption": 700}
    pack = {
        "label": name, "vibe": vibe,
        "fonts": {
            "main": {"file": main_font, "weight": heavy["main"], **({"case": case} if case else {})},
            "accent": {"file": accent_font or _font("Caveat-Variable"), "weight": 600},
            "caption": {"file": caption_font or main_font, "weight": heavy["caption"]},
        },
        "colors": roles,
        "sticker": {"style": sticker_style, "stroke": 8 if sticker_style != "neon" else 5, "wobble": 2,
                    "fill": "paper", "die_cut": sticker_style in ("doodle", "flat")},
        "captions": {"style": captions, "words_per_line": 3 if captions != "single-word" else 1},
        "title_fonts": title_fonts or title_fonts_for_vibe(vibe),
        "grade": grade or ("warm-film" if prefer == "light" else "moody"),
    }
    if logo:
        pack["logo"] = {"file": os.path.relpath(logo, ROOT) if os.path.isabs(logo) else logo,
                        "position": "top-left", "width": 230, "knock_out_white": True}
    return pack


def direction_pack(d, logo=None):
    dark_bg = _hsv(d["colors"][0])[2] < 0.4
    roles = {"bg": d["colors"][0], "ink": d["colors"][1], "pop": d["colors"][2], "accent": d["colors"][3],
             "paper": "#FFFFFF" if not dark_bg else d["colors"][1]}
    roles["bubble_text"] = d["colors"][1] if not dark_bg else d["colors"][0]
    return build_pack(d["name"], roles, _font(d["fonts"][0]), _font(d["fonts"][1]), sticker_style=d["sticker"],
                      prefer="dark" if dark_bg else "light", logo=logo, vibe=" ".join(sorted(d["tags"])))


def preview(pack, out, text="This is how your reels will look", sticker="sparkle"):
    """One still in the pack: takeover + sticker + bubble + caption. Cheap (no video)."""
    from . import render
    tl = {"size": [1080, 1920], "items": []}
    p = json.loads(json.dumps(pack))
    from .packs import _resolve
    p = _resolve(p)
    frame = Image.new("RGBA", (1080, 1920), p["colors"]["bg"])
    items = [
        {"id": "a", "type": "text", "text": text, "x": 540, "y": 720, "w": 880, "h": 520, "start": 0, "end": 9, "anim": "none"},
        {"id": "b", "type": "sticker", "name": sticker, "x": 840, "y": 420, "size": 260, "colour": "pop", "start": 0, "end": 9, "anim": "none"},
        {"id": "c", "type": "bubble", "text": "and it's all on brand", "x": 400, "y": 1250, "width": 560, "start": 0, "end": 9, "anim": "none"},
    ]
    if p.get("logo"):
        items.append({"id": "logo", "type": "overlay", "file": p["logo"]["file"], "x": 220, "y": 290, "width": 230,
                      "knock_out_white": True, "start": 0, "end": 9, "anim": "none"})
    for it in items:
        img = render.item_image(it, p)
        if img is not None:
            render._place(frame, img, it, 5, 1.0)
    frame.convert("RGB").save(out, quality=90)
    return out
