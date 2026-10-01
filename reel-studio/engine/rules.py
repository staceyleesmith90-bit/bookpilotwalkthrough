"""The user's taste, taught once: "remember that" rules kept in brand/rules.json.

Claude reads these before every style plan (they override defaults), and the builders apply the
ones they understand (e.g. sound rules). Updates never touch brand/, so what they taught stays.
"""
import json, os, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "brand", "rules.json")
AREAS = ("text", "captions", "sound", "cuts", "graphics", "music", "never", "other")


def load():
    try:
        return json.load(open(PATH, encoding="utf-8"))
    except Exception:
        return []


def _save(rules):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(rules, open(PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def guess_area(text):
    t = text.lower()
    for area, words in (("never", ("never", "don't", "do not", "no more", "stop ")),
                        ("sound", ("sound", "whoosh", "pop", "ding", "click", "typing", "music bed")),
                        ("captions", ("caption", "subtitle")),
                        ("cuts", ("cut", "pause", "pace", "breath", "zoom")),
                        ("music", ("music", "song", "track")),
                        ("graphics", ("sticker", "card", "emoji", "label", "effect", "gif")),
                        ("text", ("font", "headline", "hook", "text", "title", "colour", "color"))):
        if any(w in t for w in words):
            return area
    return "other"


def remember(text, area=None, name=None):
    """Add a rule. name = an optional phrase that calls it back ("my highlight captions")."""
    rules = load()
    rules.append({"rule": text.strip(), "area": area if area in AREAS else guess_area(text),
                  "name": name, "added": time.strftime("%Y-%m-%d")})
    _save(rules)
    return len(rules)


def forget(which):
    """Forget by number (1-based) or by words in the rule/name."""
    rules = load()
    if str(which).isdigit() and 1 <= int(which) <= len(rules):
        gone = rules.pop(int(which) - 1)
    else:
        w = str(which).lower()
        hit = [r for r in rules if w in r["rule"].lower() or w in (r.get("name") or "").lower()]
        if not hit:
            return None
        gone = hit[0]
        rules.remove(gone)
    _save(rules)
    return gone


def listing():
    rules = load()
    if not rules:
        return "Nothing taught yet. Say \"remember that\" after any change you want every time."
    out = []
    for i, r in enumerate(rules, 1):
        nm = f'  (say "{r["name"]}")' if r.get("name") else ""
        out.append(f"{i}. [{r['area']}] {r['rule']}{nm}")
    return "\n".join(out)
