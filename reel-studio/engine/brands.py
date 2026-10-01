"""Many brands, one studio — for creators who make content for several brands or clients.

brand/            the brand in use right now (everything in the engine reads from here)
brands/<slug>/    every other brand, kept whole: brand.json, logo, fonts, sounds, rules, voice, effects
brands/active.txt the name of the brand in brand/

Switching saves the current brand back to brands/<its slug>/ and copies the chosen one into brand/,
so each brand keeps its own colours, fonts, logo, sounds, rules ("remember that") and voice.
Projects remember which brand they were made for (project.json "brand").
"""
import json, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(ROOT, "brand")
ALL = os.path.join(ROOT, "brands")
ACTIVE = os.path.join(ALL, "active.txt")
SHARED = {"trending-sounds.json", ".env"}      # personal to the user, not to a brand: stays in brand/


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "brand"


def active():
    try:
        return open(ACTIVE, encoding="utf-8").read().strip() or None
    except Exception:
        return None


def _label(folder):
    try:
        return json.load(open(os.path.join(folder, "brand.json"), encoding="utf-8")).get("label")
    except Exception:
        return None


def listing():
    """-> [(slug, label, is_active)]"""
    os.makedirs(ALL, exist_ok=True)
    act = active()
    out = []
    if os.path.exists(os.path.join(CUR, "brand.json")) or act:
        out.append((act or slug(_label(CUR) or "my brand"), _label(CUR) or act or "My brand", True))
    for d in sorted(os.listdir(ALL)):
        p = os.path.join(ALL, d)
        if os.path.isdir(p) and d != (act or ""):
            out.append((d, _label(p) or d, False))
    return out


def _move_out():
    """Save brand/ into brands/<active slug>/ (keeps the shared personal files in brand/)."""
    if not os.path.isdir(CUR) or not os.listdir(CUR):
        return None
    name = active() or slug(_label(CUR) or "my brand")
    dst = os.path.join(ALL, name)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for f in os.listdir(CUR):
        if f in SHARED:
            continue
        shutil.move(os.path.join(CUR, f), os.path.join(dst, f))
    return name


def _set_active(name):
    os.makedirs(ALL, exist_ok=True)
    open(ACTIVE, "w", encoding="utf-8").write(name)


def new(name):
    """Start a fresh brand (the current one is kept safe). -> slug"""
    s = slug(name)
    if s in [b[0] for b in listing()]:
        raise ValueError(f"There's already a brand called '{name}' — say 'switch to {name}'.")
    _move_out()
    os.makedirs(CUR, exist_ok=True)
    _set_active(s)
    json.dump({"label": name, "_pending": True}, open(os.path.join(CUR, "brand-name.json"), "w", encoding="utf-8"))
    return s


def use(name):
    """Switch to another brand by name or slug. -> slug"""
    want = slug(name)
    hits = [b for b in listing() if b[0] == want or slug(b[1]) == want] or \
           [b for b in listing() if want in b[0] or want in slug(b[1])]
    if not hits:
        raise ValueError(f"No brand called '{name}'. Brands: " + ", ".join(b[1] for b in listing()))
    s, _, is_active = hits[0]
    if is_active:
        return s
    _move_out()
    src = os.path.join(ALL, s)
    os.makedirs(CUR, exist_ok=True)
    for f in os.listdir(src):
        shutil.move(os.path.join(src, f), os.path.join(CUR, f))
    os.rmdir(src)
    _set_active(s)
    return s


def delete(name):
    s = slug(name)
    if s == active():
        raise ValueError("That's the brand in use — switch to another one first.")
    p = os.path.join(ALL, s)
    if not os.path.isdir(p):
        raise ValueError(f"No brand called '{name}'.")
    shutil.rmtree(p)
    return s


def pack_for(brand_slug):
    """The style pack of any brand (active or not) — so old projects re-render in their own brand."""
    from . import packs
    if not brand_slug or brand_slug == active():
        return packs.load("brand")
    p = os.path.join(ALL, brand_slug, "brand.json")
    if not os.path.exists(p):
        return packs.load("brand")
    pack = json.load(open(p, encoding="utf-8"))
    rel_old, rel_new = "brand/", f"brands/{brand_slug}/"
    for group in (pack.get("fonts", {}), pack.get("title_fonts", {})):
        for f in group.values():
            if isinstance(f, dict) and str(f.get("file", "")).replace("\\", "/").startswith(rel_old):
                f["file"] = rel_new + f["file"].replace("\\", "/")[len(rel_old):]
    if pack.get("logo", {}).get("file", "").replace("\\", "/").startswith(rel_old):
        pack["logo"]["file"] = rel_new + pack["logo"]["file"].replace("\\", "/")[len(rel_old):]
    return packs._resolve(pack)
