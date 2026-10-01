"""Guided brand setup — every route ends the same way: a few looks drawn out, the person taps one.

Routes (the Studio shows them as cards; Claude offers them as tap answers):
  design   pick a ready-made design (HyperFrames frame presets, open source) — optionally change its colours
  file     their own design file: a HyperFrames FRAME.md / DESIGN.md, CSS, a brand guide, Canva values
  website  colours, fonts and logo read from their website
  image    colours from their logo, a photo or a mood board
  video    colours from the video they're about to edit (no prep at all)
  vibe     three starter looks from a few feel words ("warm, calm, luxe")
After a route: brand/looks.json holds the candidates and brand/previews/looks.jpg shows them;
autolook.use(n) saves the chosen one as the brand in use (brands.py keeps every brand separately).
"""
import glob, json, os, re

from . import autolook, brand, packs, stylesheet

ROOT = packs.ROOT
DESIGNS = os.path.join(ROOT, "library", "hyperframes", "designs")
PREVIEW = "https://static.heygen.ai/hyperframes-oss/docs/images/design-templates/{name}.png"
GALLERY = "https://www.hyperframes.dev/design/{name}"

ROUTES = [
    {"id": "design", "title": "Pick a ready-made design", "time": "1 minute",
     "about": "13 professional looks (from HyperFrames, open source). Pick one, change the colours if you like."},
    {"id": "inspire", "title": "From a reel I love", "time": "2 minutes",
     "about": "Paste a TikTok, Reel or YouTube Short link (or a few). We take its colours, filter, pace and energy."},
    {"id": "video", "title": "From my video", "time": "no prep",
     "about": "Colours taken from the product, outfit or place in your video."},
    {"id": "website", "title": "From my website", "time": "1 minute",
     "about": "Your colours, fonts and logo read from your site."},
    {"id": "image", "title": "From my logo or a photo", "time": "1 minute",
     "about": "Upload your logo, a product photo or a mood board."},
    {"id": "file", "title": "From a design file", "time": "2 minutes",
     "about": "A HyperFrames design, a DESIGN.md, Canva or Figma export, or a brand guide."},
    {"id": "vibe", "title": "I don't have a brand yet", "time": "1 minute",
     "about": "Tell us how it should feel, get three looks to choose from."},
]

GUIDES = {
    "design": ["Tap the design that feels most like you.",
               "Press Show me my looks to see it in your reels before anything is saved.",
               "Optional: change the accent colour to your own.",
               "Press Use this look. You can change it any time."],
    "file": ["HyperFrames: open hyperframes.dev → Design, pick a design, change its colours, and download its "
             "FRAME.md (or DESIGN.md). Drop that file here.",
             "Canva: open your brand page, then File → Download → PDF or PNG, and drop it here. Or connect "
             "Canva to Claude (Settings → Connectors → Canva) and say \"I styled my Canva\".",
             "Figma or a brand guide: export the page with your colours and fonts as PNG or PDF and drop it here.",
             "We read your colours and fonts and show your look before anything is saved."],
    "inspire": ["Open the TikTok, Instagram Reel or YouTube Short you love and tap Share → Copy link.",
                "Paste it below. Got a few you love? Paste them all, one per line: we take what they share.",
                "We study its colours, filter, pace and sound energy (never its words, footage or music).",
                "Tap the look you like. Every reel for this brand then follows that style."],
    "website": ["Paste your website address.", "We read its colours, fonts and logo.",
                "Check the three looks and tap the one you like."],
    "image": ["Upload your logo (PNG is best), a product photo or a mood board.",
              "We take the colours from it.", "Tap the look you like."],
    "video": ["Choose a video from your inbox (or drop one in).", "We take the colours from what's in it.",
              "Tap the look you like."],
    "vibe": ["Tap two or three words for how your brand should feel.", "Tap the look you like."],
}

VIBE_WORDS = ["warm", "calm", "bold", "playful", "luxe", "clean", "natural", "retro", "modern", "friendly", "premium",
              "fun", "minimal", "earthy", "bright"]


def designs():
    """The ready-made designs: name, title, about, colours, fonts, preview image."""
    out = []
    for f in sorted(glob.glob(os.path.join(DESIGNS, "*", "FRAME.md"))):
        name = os.path.basename(os.path.dirname(f))
        txt = open(f, encoding="utf-8").read()
        title = re.search(r"^name:\s*(.+?)\s+—", txt, re.M)
        spec = stylesheet.read_frame(txt) or {"colors": {}, "fonts": {}}
        f_ = spec["fonts"]
        about_txt = (f"{f_.get('main', 'Clean')} headlines" + (f" · {f_['caption']} text" if f_.get("caption") and
                     f_.get("caption") != f_.get("main") else ""))
        out.append({"name": name, "title": title.group(1) if title else name.replace("-", " ").title(),
                    "about": about_txt[:180], "colors": spec["colors"], "fonts": spec["fonts"],
                    "preview": PREVIEW.format(name=name), "page": GALLERY.format(name=name)})
    return out


def _sample_frame():
    from .editor.server import _sample_frame as f
    return f()


def _frame_or_sample(frame=None):
    return frame if frame and os.path.exists(frame) else _sample_frame()


def from_spec(spec, name, frame=None, source=None, overrides=None):
    """One exact look from a design (their fonts and colours), plus the same design in two other
    accent colours from it — so there's still a choice."""
    spec = json.loads(json.dumps(spec))
    for k, v in (overrides or {}).items():
        if v:
            spec["colors"][k] = v
    looks = []
    pack, notes = stylesheet.make_pack(spec, name, save=False)
    looks.append({"feel": "Exactly this design", "pack": pack, "notes": notes})
    others = [c for c in spec.get("found", []) if c not in spec["colors"].values()
              and not brand.is_neutral(c, 0.25)][:2]
    for c in others:
        alt = json.loads(json.dumps(spec))
        alt["colors"]["accent"] = c
        p2, _ = stylesheet.make_pack(alt, name, save=False)
        looks.append({"feel": f"Same design, another accent", "pack": p2})
    return autolook.save_looks(looks, _frame_or_sample(frame), source)


def run(route, value=None, name="My brand", frame=None, overrides=None):
    """Run one route. value = design name / file path / url / image path / video path / vibe words.
    -> (sheet, looks)"""
    if route == "design":
        f = os.path.join(DESIGNS, re.sub(r"[^a-z0-9-]", "", (value or "").lower()), "FRAME.md")
        if not os.path.exists(f):
            raise ValueError(f"No design called '{value}'.")
        return from_spec(stylesheet.read(f), name, frame, {"design": value}, overrides)
    if route == "file":
        if value.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return run("image", value, name, frame)
        if value.lower().endswith(".pdf"):
            txt = _pdf_text(value)
            spec = stylesheet.read(txt) if txt else None
            if not spec or not spec["colors"]:
                raise ValueError("I couldn't read colours from that PDF — export the page as PNG instead.")
            return from_spec(spec, name, frame, {"file": os.path.basename(value)}, overrides)
        return from_spec(stylesheet.read(value), name, frame, {"file": os.path.basename(value)}, overrides)
    if route == "inspire":
        return from_reels(value, name, frame)
    if route == "website":
        site = brand.from_website(value)
        cols = [c for c in site["colors"] if not brand.is_neutral(c)]
        if site.get("fonts"):                       # their own fonts: show the site exactly, plus two feels
            spec = {"colors": {"accent": cols[0] if cols else "#E4572E"},
                    "fonts": {"main": site["fonts"][0], "caption": site["fonts"][-1]}, "found": site["colors"]}
            return from_spec(spec, name, frame, {"website": value}, overrides)
        return autolook.looks_from_colours(cols, name, _frame_or_sample(frame), {"website": value})
    if route == "image":
        cols = [c for c in brand.from_image(value, n=10) if not brand.is_neutral(c)]
        return autolook.looks_from_colours(cols, name, _frame_or_sample(frame), {"image": os.path.basename(value)})
    if route == "video":
        vivid, fr = autolook.palette_from_video(value)
        return autolook.looks_from_colours(vivid, name, fr, {"video": value})
    if route == "vibe":
        dirs = brand.starter_directions(value or "warm")
        looks = [{"feel": d["name"], "pack": dict(brand.direction_pack(d), label=name)} for d in dirs]
        return autolook.save_looks(looks, _frame_or_sample(frame), {"vibe": value})
    raise ValueError(f"Unknown route '{route}'.")


def from_reels(links, name, frame=None):
    """Brand looks from reels they love: the shared colours + the reel's style (filter, pace, sound
    energy, caption feel) saved into the brand so every reel for it follows that style."""
    from . import inspire
    urls = [u.strip() for u in re.split(r"[\s,]+", links or "") if u.strip()]
    if not urls:
        raise ValueError("Paste at least one link.")
    profs, errs = [], []
    for u in urls[:4]:
        try:
            profs.append(inspire.analyse(u, transcribe_audio=False))
        except Exception:
            errs.append(u)
    if not profs:
        raise ValueError("I couldn't open that link. Check it's public, or download the video and use "
                         "'From my video' instead.")
    cols = []
    for p in profs:
        cols += [c for c in p.get("palette", []) if not brand.is_neutral(c, 0.22) and not autolook._is_skin(c)]
    style = inspire.plan_settings(profs[0])
    style = {k: v for k, v in style.items() if v and k not in ("captions",)}   # captions: their brand's own style
    sheet, looks = autolook.looks_from_colours(cols, name, _frame_or_sample(frame),
                                               {"inspire": urls, "names": [p["name"] for p in profs]})
    for lk in looks:
        lk["pack"]["reel_style"] = dict(style, from_reels=[p["name"] for p in profs])
        if style.get("grade"):
            lk["pack"]["grade"] = style["grade"]
        if errs:
            lk["notes"] = [f"Couldn't open: {', '.join(errs)}"]
    autolook.save_looks(looks, _frame_or_sample(frame), {"inspire": urls})
    return sheet, looks


def _pdf_text(path):
    try:
        import pypdf
        return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages[:20])
    except Exception:
        return ""
