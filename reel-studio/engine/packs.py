"""Style packs: preset looks (library/packs.json) and the user's own brand (brand/brand.json).

A pack is only tokens (fonts by role, colours, sticker style, sounds, grade, captions),
so any reel can be restyled by swapping the pack.
"""
import re, copy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS = os.path.join(ROOT, "library", "packs.json")
BRAND = os.path.join(ROOT, "brand", "brand.json")

DEFAULTS = {
    "sticker": {"style": "doodle", "stroke": 8, "wobble": 3, "fill": "paper", "die_cut": False},
    "sfx": {"text_in": "pop", "sticker_in": "pop", "transition": "whoosh", "reveal": "ding",
            "hook": "hit", "cta": "ding"},
    "captions": {"style": "karaoke", "words_per_line": 3},
    "grade": "clean-bright",
}


def _resolve(pack):
    if pack.get("_resolved"):
        return pack
    out = copy.deepcopy(DEFAULTS)
    for k, v in pack.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    for group in (out["fonts"], out.get("title_fonts", {})):
        for f in group.values():
            if not os.path.isabs(f["file"]):
                f["file"] = os.path.join(ROOT, f["file"])
    c = out["colors"]
    c.setdefault("paper", "#FFFFFF")
    c.setdefault("bubble_text", c["ink"] if _lum(c["paper"]) > 0.5 else "#FFFFFF")
    c.setdefault("caption", "#FFFFFF")
    c.setdefault("caption_active", c["pop"])
    c.setdefault("title_ink", "#FFFFFF")
    out["_resolved"] = True
    return out


FONT_DIRS = [os.path.join(ROOT, "brand", "fonts"), os.path.join(ROOT, "library", "fonts")]
FONT_EXT = (".ttf", ".otf")


def all_fonts():
    """Every usable font: the user's own uploads (brand/fonts) first, then the bundled library."""
    out = []
    for d in FONT_DIRS:
        if os.path.isdir(d):
            out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(FONT_EXT)]
    return out


def resolve_font(pack, choice):
    """Turn a font choice into a font spec {"file": ...}. A choice can be a role from the pack
    ("script", "serif", "sans", "main", "accent"…), a font file name (with or without extension,
    from brand/fonts or library/fonts), a path, or already a spec. None/"auto" -> None."""
    if not choice or choice == "auto":
        return None
    if isinstance(choice, dict):
        return choice
    from .titles import fonts_for
    roles = dict(fonts_for(pack))
    roles.update(pack.get("fonts", {}))
    if choice in roles:
        return roles[choice]
    for cand in (choice, os.path.join(ROOT, choice)):
        if os.path.isfile(cand):
            return {"file": os.path.abspath(cand)}
    key = re.sub(r"[^a-z0-9]", "", os.path.splitext(os.path.basename(choice))[0].lower())
    for f in all_fonts():
        if re.sub(r"[^a-z0-9]", "", os.path.splitext(os.path.basename(f))[0].lower()).startswith(key):
            return {"file": f}
    return None


def presets():
    return json.load(open(PRESETS))


def has_brand():
    return os.path.exists(BRAND)


def load(name=None):
    """name=None -> the user's brand if set up, else the 'bold' preset."""
    if name in (None, "brand") and has_brand():
        return _resolve(json.load(open(BRAND)))
    return _resolve(presets()[name or "bold"])


def save_brand(pack):
    os.makedirs(os.path.dirname(BRAND), exist_ok=True)
    json.dump(pack, open(BRAND, "w"), indent=2)
    return BRAND


def _lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """WCAG contrast ratio between two hex colours (1-21). Text needs >= 4.5."""
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check(pack):
    """Human-readable warnings about a pack (contrast problems, missing fonts)."""
    p = _resolve(pack)
    c, warn = p["colors"], []
    for fg, bg, what in [("ink", "bg", "main text on background"),
                         ("bubble_text", "paper", "bubble text on bubble"),
                         ("pop", "bg", "highlight colour on background")]:
        r = contrast(c[fg], c[bg])
        if r < (4.5 if fg != "pop" else 3.0):
            warn.append(f"Low contrast for {what} ({r:.1f}:1) — hard to read.")
    for role, f in p["fonts"].items():
        if not os.path.exists(f["file"]):
            warn.append(f"Font for '{role}' not found: {f['file']}")
    return warn
