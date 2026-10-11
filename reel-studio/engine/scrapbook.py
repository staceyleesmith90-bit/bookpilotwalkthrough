"""Scrapbook effects: polaroid prints with washi tape on a paper page, as a ready-to-use 1080x1920 clip.

Three styles, every setting optional (defaults come from the reel's style pack):
  orbit  prints circle on a tilted ring; the one at the front is big and sharp, the back ones fade
  page   prints drop onto the page one by one into a loose collage
  stack  prints land on top of each other in the middle, like a pile of photos being dealt

In a plan, on any beat:   "do": ["scrapbook"],  "scrapbook": {"style": "orbit", "photos": [...], ...}
or the short form "scrapbook:page" (photos then come from the beat's "scrapbook" options or plan["broll_pool"]).
CLI: python -m engine scrapbook out.mp4 --style orbit --photos a.jpg b.mp4@2.5 --set speed=1.4 tape=#F4B6C6,#CFE3D2
     python -m engine scrapbook-options      (every setting, with its default)

A photo can be an image, a video ("clip.mp4" = its middle frame, "clip.mp4@2.5" = the frame at 2.5 s),
or {"file": ..., "at": 2.5, "caption": "eerste tree"} for a handwritten line under that print.
"""
import hashlib, json, math, os, random, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "library", "cache", "scrapbook")
W, H, FPS = 1080, 1920, 30
STYLES = ("orbit", "page", "stack")

# every setting, its default and what it does (shown by `scrapbook-options` and the reel-engine skill)
OPTIONS = {
    "style": ("orbit", "orbit | page | stack"),
    "photos": ([], "images or videos (clip.mp4@2.5 = that moment); 4-8 works best"),
    "captions": ([], "a short handwritten line under each print, in order ('' = none)"),
    "duration": (6.0, "seconds"),
    "speed": (1.0, "orbit: how fast the ring turns · page/stack: how quickly prints arrive (1 = designed pace)"),
    "direction": (1, "orbit: 1 = clockwise, -1 = anticlockwise"),
    "size": (400, "print width in px at the front (page/stack scale it to fit)"),
    "tilt": (7, "how crooked the prints sit, in degrees (0 = perfectly straight)"),
    "frame": ("polaroid", "polaroid (thick bottom edge) | border (even white edge) | none"),
    "frame_color": ("#FFFDFA", "colour of the print border"),
    "tape": ("pack", "washi tape colours: 'pack' (from the style pack), 'none', or a list of hex colours"),
    "background": ("paper", "paper (pack colour with grain) | a hex colour | an image or video file (softly blurred)"),
    "center": (None, "middle of the ring / layout [x, y] (default: orbit [540, 700], page/stack [540, 900])"),
    "radius": ([300, 210], "orbit: ring width and depth [rx, ry]"),
    "shadow": (0.3, "drop shadow strength, 0-1"),
    "ink": ("pack", "caption colour: 'pack' or a hex colour"),
    "seed": (7, "change for a different random tilt / layout"),
}


def options_help():
    return "\n".join(f"  {k:12} default {json.dumps(v[0], ensure_ascii=False):22} {v[1]}" for k, v in OPTIONS.items())


def settings(spec, pack):
    """Spec + defaults, with pack-driven values filled in and numbers kept in sane ranges."""
    s = {k: v[0] for k, v in OPTIONS.items()}
    s.update({k: v for k, v in (spec or {}).items() if v is not None})
    c = pack["colors"] if pack else {}
    if s["style"] not in STYLES:
        s["style"] = "orbit"
    if not s["center"]:
        s["center"] = [540, 700] if s["style"] == "orbit" else [540, 900]
    if s["tape"] == "pack":
        base = [c.get("pop", "#F4B6C6"), c.get("accent", "#E9C7A6")]
        s["tape"] = [x for x in base if x.upper() not in ("#FFFFFF", "#FFF")] + ["#E9C7A6", "#CFE3D2", "#D9CDEB"]
    elif s["tape"] in ("none", None, False):
        s["tape"] = []
    elif isinstance(s["tape"], str):
        s["tape"] = [t.strip() for t in s["tape"].split(",") if t.strip()]
    if s["ink"] == "pack":
        s["ink"] = c.get("bubble_text") or c.get("ink", "#4A3A3F")
    s["duration"] = min(max(float(s["duration"]), 1.0), 30.0)
    s["speed"] = min(max(float(s["speed"]), 0.1), 5.0)
    s["direction"] = -1 if float(s["direction"]) < 0 else 1
    s["size"] = int(min(max(int(s["size"]), 160), 900))
    s["tilt"] = min(max(float(s["tilt"]), 0.0), 25.0)
    s["shadow"] = min(max(float(s["shadow"]), 0.0), 1.0)
    return s


# ---------------------------------------------------------------- pieces
def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


_PHOTOS = {}


def _photo(entry):
    """(PIL image, caption) for an image, a video moment or a {file, at, caption} dict. Remembered, so the
    Studio's live preview doesn't re-read every photo / video frame on each change."""
    if isinstance(entry, dict):
        f, at, cap = entry["file"], entry.get("at"), entry.get("caption", "")
    else:
        f, _, a = str(entry).partition("@")
        at, cap = (float(a) if a else None), ""
    try:
        key = (_abs(f), at, os.path.getmtime(_abs(f)))
    except OSError:
        key = None
    if key in _PHOTOS:
        return _PHOTOS[key].copy(), cap
    img, _ = _load_photo(f, at)
    if key:
        if len(_PHOTOS) > 64:
            _PHOTOS.clear()
        _PHOTOS[key] = img
    return img.copy(), cap


def _load_photo(f, at):
    f, cap = _abs(f), ""
    if f.lower().endswith((".mp4", ".mov", ".m4v", ".mkv", ".webm")):
        if at is None:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                 capture_output=True, text=True).stdout.strip()
            at = float(out or 2) / 2
        png = os.path.join(tempfile.mkdtemp(), "f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", f, "-frames:v", "1", png], check=True)
        return Image.open(png).convert("RGB"), cap
    return ImageOps.exif_transpose(Image.open(f)).convert("RGB"), cap


def _font(pack, px):
    from .textfit import load_font
    fonts = (pack or {}).get("fonts", {})
    f = fonts.get("accent") or fonts.get("main") or {"file": "library/fonts/Caveat-Variable.ttf"}
    try:
        return load_font(f["file"], px, f.get("weight"))
    except Exception:
        return load_font("library/fonts/Caveat-Variable.ttf", px)


def make_print(img, s, k, pack, caption=""):
    """One print: photo in a frame, washi tape, rotation and shadow. RGBA."""
    rng = random.Random(s["seed"] * 31 + k)
    w = s["size"]
    ph = int(w * 1.18)
    im = ImageOps.fit(img, (w, ph), Image.LANCZOS, centering=(0.5, 0.42))
    pad = {"polaroid": 26, "border": 22, "none": 0}.get(s["frame"], 26)
    bottom = {"polaroid": 110 if not caption else 140, "border": 22, "none": 0}.get(s["frame"], 110)
    card = Image.new("RGBA", (w + 2 * pad, ph + pad + bottom), s["frame_color"])
    card.paste(im, (pad, pad))
    if caption and s["frame"] != "none":
        d = ImageDraw.Draw(card)
        f = _font(pack, max(34, int(w * 0.16)))
        d.text((card.width / 2, ph + pad + bottom / 2), caption, font=f, fill=s["ink"], anchor="mm")
    elif caption:                                   # no frame: caption under the photo on a little strip
        strip = Image.new("RGBA", (card.width, int(w * 0.2)), s["frame_color"])
        ImageDraw.Draw(strip).text((strip.width / 2, strip.height / 2), caption, font=_font(pack, int(w * 0.1)),
                                   fill=s["ink"], anchor="mm")
        c2 = Image.new("RGBA", (card.width, card.height + strip.height), (0, 0, 0, 0))
        c2.paste(card, (0, 0)); c2.paste(strip, (0, card.height)); card = c2
    full = Image.new("RGBA", (card.width + 40, card.height + 60), (0, 0, 0, 0))
    full.alpha_composite(card, (20, 40))
    if s["tape"]:
        col = s["tape"][k % len(s["tape"])]
        tw, th = int(w * 0.42), max(30, int(w * 0.14))
        t = Image.new("RGBA", (tw, th), col + "C8" if len(col) == 7 else col)
        d = ImageDraw.Draw(t)
        for i in range(0, tw, 22):
            d.line([(i, 0), (i + 10, th)], fill=(255, 255, 255, 60), width=6)
        t = t.rotate(rng.uniform(-6, 6), expand=True, resample=Image.BICUBIC)
        full.alpha_composite(t, ((full.width - t.width) // 2, 6))
    if s["tilt"]:
        full = full.rotate(rng.uniform(-s["tilt"], s["tilt"]), expand=True, resample=Image.BICUBIC)
    out = Image.new("RGBA", (full.width + 60, full.height + 60), (0, 0, 0, 0))
    if s["shadow"]:
        a = full.split()[3].point(lambda v: int(v * s["shadow"]))
        sh = Image.new("RGBA", full.size, (70, 45, 50, 0)); sh.putalpha(a)
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (38, 46))
    out.alpha_composite(full, (20, 20))
    return out


def background(s, pack):
    bg = s["background"]
    c = (pack or {}).get("colors", {})
    if isinstance(bg, str) and bg.startswith("#"):
        return Image.new("RGBA", (W, H), bg)
    if isinstance(bg, str) and bg != "paper" and os.path.exists(_abs(bg.split("@")[0])):
        im, _ = _photo(bg)
        im = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(36))
        tint = Image.new("RGB", (W, H), c.get("bg", "#FBEFF1"))
        return Image.blend(im, tint, 0.35).convert("RGBA")
    hexc = c.get("bg", "#FBEFF1").lstrip("#")
    rgb = np.array([int(hexc[i:i + 2], 16) for i in (0, 2, 4)])
    rng = np.random.default_rng(s["seed"])
    y = np.linspace(-1, 1, H)[:, None, None]; x = np.linspace(-1, 1, W)[None, :, None]
    arr = np.ones((H, W, 3)) * rgb * (1 - 0.05 * (x ** 2 + y ** 2)) + rng.normal(0, 3.2, (H, W, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).convert("RGBA")


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _paste(fr, card, scale, x, y, alpha=1.0):
    cc = card.resize((max(1, int(card.width * scale)), max(1, int(card.height * scale))), Image.BICUBIC)
    if alpha < 1:
        cc.putalpha(cc.split()[3].point(lambda v: int(v * alpha)))
    fr.alpha_composite(cc, (int(x - cc.width / 2), int(y - cc.height / 2)))


# ---------------------------------------------------------------- styles: one frame at time t
def _orbit(cards, s, bg):
    cx, cy = s["center"]; rx, ry = s["radius"]
    N = len(cards)

    def frame(t):
        ent = _ease(t / 1.0)                                       # the ring opens out from the middle
        base = s["direction"] * (0.62 * s["speed"] * t) + 1.2 * (1 - ent)
        placed = []
        for k, c in enumerate(cards):
            a = base + 2 * math.pi * k / N
            depth = (math.sin(a) + 1) / 2                          # 0 = back, 1 = front
            placed.append((depth, c, (0.55 + 0.55 * depth) * (0.4 + 0.6 * ent),
                           cx + math.cos(a) * rx * ent, cy + math.sin(a) * ry * ent))
        fr = bg.copy()
        for depth, c, sc, x, y in sorted(placed, key=lambda p: p[0]):
            _paste(fr, c, sc, x, y, 1.0 if depth >= 0.5 else 0.45 + 1.1 * depth)
        return fr
    return frame


def _layout(n, s):
    """Loose collage positions for n prints around the centre: 2 columns, rows as needed."""
    cx, cy = s["center"]
    rows = math.ceil(n / 2)
    rng = random.Random(s["seed"])
    step = min(560, 1300 / max(rows, 1))
    pos = []
    for k in range(n):
        r, col = divmod(k, 2)
        x = cx + (-225 if col == 0 else 225) + rng.uniform(-25, 25)
        if n % 2 and k == n - 1:
            x = cx
        y = cy + (r - (rows - 1) / 2) * step + (60 if col else 0) + rng.uniform(-20, 20)
        pos.append((x, y))
    fit = min(1.0, 440 / s["size"], step / (s["size"] * 1.5))
    return pos, fit


def _page(cards, s, bg):
    pos, fit = _layout(len(cards), s)
    gap = 0.7 / s["speed"]

    def frame(t):
        fr = bg.copy()
        for k, c in enumerate(cards):
            p = _ease((t - 0.15 - k * gap) / 0.55)
            if p > 0:
                x, y = pos[k]
                _paste(fr, c, fit * (1.18 - 0.18 * p), x, y - (1 - p) * 40, min(1, p * 1.6))
        return fr
    return frame


def _stack(cards, s, bg):
    cx, cy = s["center"]
    rng = random.Random(s["seed"] + 1)
    offs = [(rng.uniform(-70, 70), rng.uniform(-60, 60)) for _ in cards]
    fit = min(1.5, 640 / s["size"])
    gap = max(0.35, (s["duration"] - 1.2) / max(len(cards), 1)) / s["speed"]

    def frame(t):
        fr = bg.copy()
        for k, c in enumerate(cards):
            p = _ease((t - 0.1 - k * gap) / 0.45)
            if p > 0:                                              # each new print slides in from below and lands on top
                dx, dy = offs[k]
                _paste(fr, c, fit * (1.12 - 0.12 * p), cx + dx, cy + dy + (1 - p) * 700, min(1, p * 2))
        return fr
    return frame


def _framer(spec, pack):
    """(settings, frame(t) function) for a spec — shared by the clip render and the Studio preview."""
    s = settings(spec, pack)
    photos = list(s["photos"])
    if not photos:
        raise ValueError("scrapbook needs at least one photo or video")
    caps = list(s["captions"]) + [""] * len(photos)
    cards = []
    for k, p in enumerate(photos):
        img, cap = _photo(p)
        cards.append(make_print(img, s, k, pack, cap or caps[k]))
    return s, {"orbit": _orbit, "page": _page, "stack": _stack}[s["style"]](cards, s, background(s, pack))


def preview(spec, pack=None, t=None):
    """One frame (PIL RGB) — by default the moment everything has arrived. For the Studio's live preview."""
    from . import packs as _packs
    pack = pack or _packs.load(None)
    s, frame = _framer(spec, pack)
    return frame(s["duration"] * 0.8 if t is None else t).convert("RGB")


def render(spec, out=None, pack=None):
    """Render the scrapbook clip; cached by its settings and photo files. Returns the mp4 path."""
    from . import packs as _packs
    pack = pack or _packs.load(None)
    s = settings(spec, pack)
    photos = list(s["photos"])
    if not photos:
        raise ValueError("scrapbook needs at least one photo or video")
    sig = []
    for p in photos:
        f = (p["file"] if isinstance(p, dict) else str(p).partition("@")[0])
        try:
            st = os.stat(_abs(f)); sig.append(f"{f}|{st.st_size}|{int(st.st_mtime)}")
        except OSError:
            raise FileNotFoundError(f"scrapbook photo not found: {f}")
    key = hashlib.md5(json.dumps([s, sig, pack.get("colors"), pack.get("fonts")], sort_keys=True,
                                 default=str).encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    cached = os.path.join(CACHE, f"{s['style']}-{key}.mp4")
    if not os.path.exists(cached):
        s, frame = _framer(spec, pack)
        frames = (frame(i / FPS) for i in range(int(s["duration"] * FPS)))
        part = cached + ".part.mp4"
        enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16",
                                "-preset", "fast", "-pix_fmt", "yuv420p", part], stdin=subprocess.PIPE)
        for fr in frames:
            enc.stdin.write(fr.convert("RGB").tobytes())
        enc.stdin.close(); enc.wait()
        os.replace(part, cached)
    if out and os.path.abspath(out) != cached:
        import shutil
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        shutil.copyfile(cached, out)
        return out
    return cached
