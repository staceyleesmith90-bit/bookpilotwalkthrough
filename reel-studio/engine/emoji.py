"""Emoji stickers, fetched on demand and cached (library/emoji-cache/).

Sources (both allow commercial use):
  - Microsoft Fluent Emoji, flat style — MIT licence. Looked up by English name.
  - Twemoji (jdecked/twemoji) — CC-BY 4.0, attribution in docs/CREDITS.md.
    Looked up by the emoji character itself.
"""
import os, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "library", "emoji-cache")
FLUENT = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"
TWEMOJI = "https://raw.githubusercontent.com/jdecked/twemoji/main/assets/svg/"

# Common reel concepts -> Fluent emoji names. Claude can pass any other name or character.
NAMES = {
    "money": "Money bag", "coffee": "Hot beverage", "time": "Alarm clock", "idea": "Light bulb",
    "fire": "Fire", "love": "Red heart", "wow": "Star-struck", "sad": "Crying face",
    "laugh": "Face with tears of joy", "think": "Thinking face", "rocket": "Rocket",
    "growth": "Chart increasing", "phone": "Mobile phone", "camera": "Camera",
    "party": "Party popper", "check": "Check mark button", "warning": "Warning", "no": "Cross mark",
    "baby": "Baby", "family": "Family", "home": "House", "gift": "Wrapped gift",
    "target": "Direct hit", "sparkles": "Sparkles", "eyes": "Eyes", "clap": "Clapping hands",
    "muscle": "Flexed biceps", "brain": "Brain", "book": "Open book", "laptop": "Laptop",
    "shock": "Face screaming in fear", "cool": "Smiling face with sunglasses", "100": "Hundred points",
}


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "reel-studio"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def _fluent_candidates(name):
    folder = urllib.parse.quote(name)
    base = name.lower().replace(" ", "_").replace("-", "_")
    return [f"{FLUENT}{folder}/Flat/{base}_flat.svg",
            f"{FLUENT}{folder}/Default/Flat/{base}_flat_default.svg"]


def _twemoji_url(char):
    cps = [f"{ord(c):x}" for c in char if ord(c) != 0xFE0F]
    return f"{TWEMOJI}{'-'.join(cps)}.svg"


def get_svg(key):
    """key: a concept ('coffee'), a Fluent name ('Hot beverage') or an emoji ('☕')."""
    os.makedirs(CACHE, exist_ok=True)
    name = NAMES.get(key.lower(), key)
    is_char = any(ord(c) > 0x2000 for c in key)
    cache = os.path.join(CACHE, ("tw_" + "-".join(f"{ord(c):x}" for c in key)) if is_char
                         else "fl_" + name.lower().replace(" ", "_")) + ".svg"
    if os.path.exists(cache):
        return open(cache).read()
    urls = [_twemoji_url(key)] if is_char else _fluent_candidates(name)
    for url in urls:
        try:
            svg = _fetch(url)
            open(cache, "w").write(svg)
            return svg
        except Exception:
            continue
    return None


def known(concept):
    return concept.lower() in NAMES
