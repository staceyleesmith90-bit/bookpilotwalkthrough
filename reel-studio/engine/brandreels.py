"""Brand reels: ready-made reels for brands where nobody has to talk — products and services — from the
brand's catalogue (brand/catalog.json, travels with the brand when you switch brands).

brand/catalog.json
{
  "business": {"what": "LED e-scooters for city commuters", "cta": "Shop now · link in bio", "website": "..."},
  "products": [{"name": "Volt X1", "tagline": "Glide to work", "price": "R8 999", "was": "R10 999",
                "photos": ["brand/products/volt.png"], "benefits": ["25 km range", "Folds in 3 s", "LED deck"],
                "badge": "NEW", "link": "..."}],
  "services": [{"name": "Gel nails", "price": "R350", "steps": ["Book online", "Pick your colour", "Leave glowing"],
                "details": ["2 min", "", ""], "photos": [...], "before": "...", "after": "..."}],
  "reviews":  [{"text": "Best buy this year!", "name": "Lerato", "stars": 5, "about": "Volt X1"}],
  "faqs":     [{"q": "How long does the battery last?", "a": "Up to 25 km on one charge."}]
}

    python -m engine brand-reel <recipe> --name "<product or service>" [--clips <folder>] [--options <project>]
    python -m engine brand-reels                     the recipes, and what's in this brand's catalogue

Every recipe writes a normal faceless plan.json (so the storyboard, the editor and the chat box all work on it),
in the brand's colours and fonts, with music, sounds, a cover and the brand's end card.
"""
import json, os, re

from . import project

ROOT = project.ROOT
CATALOG = os.path.join(ROOT, "brand", "catalog.json")

RECIPES = {
    # products
    "showcase":   ("product", "Product showcase", "The product floats in on your colour, its benefits pop in, then the price and your call to action."),
    "reasons":    ("product", "3 reasons to love it", "\"3 reasons you'll love ___\": each reason pops in around the product."),
    "offer":      ("product", "Sale / offer", "SALE badge, old price crossed out, the new price, and a nudge to buy now."),
    "new-drop":   ("product", "New arrival", "\"Just dropped\": a NEW seal, the product, its best feature and the price."),
    "reviews":    ("either",  "Customer reviews", "Real reviews with stars popping in, your product or service underneath."),
    # services
    "how-it-works": ("service", "How it works", "Numbered steps slide in, then your work and how to book."),
    "results":    ("service", "Before → after", "The before, the after, and the price of getting there."),
    "faq":        ("either",  "Questions answered", "A question your customers ask, answered in three quick cards."),
}


def catalog():
    try:
        return json.load(open(CATALOG, encoding="utf-8"))
    except Exception:
        return {"business": {}, "products": [], "services": [], "reviews": [], "faqs": []}


def save_catalog(cat):
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    json.dump(cat, open(CATALOG, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def find(cat, name):
    """(kind, item) for a product or service by (part of) its name; first one if no name."""
    n = (name or "").strip().lower()
    for kind in ("products", "services"):
        for it in cat.get(kind, []):
            if not n or n in it.get("name", "").lower():
                return kind[:-1], it
    return None, None


def _clips(folder):
    if not folder:
        return []
    exts = (".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".webp")
    if os.path.isdir(folder):
        return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(exts)]
    return [folder] if os.path.exists(folder) else []


def _photo(item):
    for p in item.get("photos") or []:
        if os.path.exists(p if os.path.isabs(p) else os.path.join(ROOT, p)):
            return os.path.relpath(p if os.path.isabs(p) else os.path.join(ROOT, p), ROOT)
    return None


def _beat(dur, media, fx=None, spec=None, cut=True):
    b = {"text": "", "dur": dur, "do": [f"broll:{media}"] + ([f"scene:{fx}"] if fx else [])}
    if spec is not None:
        b["scene"] = spec
    if cut:
        b["cut"] = True
    return b


def _label_beat(dur, media, text, y=0.14):
    return _beat(dur, media, "collage", {"overlay": True, "labels": [{"text": text, "x": 0.5, "y": y, "rot": -2, "at": 0.15, "px": 50}]})


def build(recipe, name=None, clips=None, cat=None):
    """-> (plan dict, the item used). Raises ValueError with a plain message if something's missing."""
    if recipe not in RECIPES:
        raise ValueError(f"Unknown recipe '{recipe}'. Choose: {', '.join(RECIPES)}")
    cat = cat or catalog()
    kind, item = find(cat, name)
    need = RECIPES[recipe][0]
    if item is None:
        raise ValueError("Add a product or service to this brand's catalogue first (name, photo, price…).")
    if need != "either" and kind != need:
        raise ValueError(f"'{RECIPES[recipe][1]}' is for a {need}; '{item.get('name')}' is a {kind}.")
    photo = _photo(item)
    extra = _clips(clips)
    media = photo or (os.path.relpath(extra[0], ROOT) if extra else None)
    if not media:
        raise ValueError(f"'{item.get('name')}' needs a photo (catalogue \"photos\") or some clips.")
    biz = cat.get("business") or {}
    beats = []
    hero = {"photo": photo} if photo else None
    nm, price, was = item.get("name", ""), item.get("price"), item.get("was")
    benefits = (item.get("benefits") or [])[:3]
    clip_beats = [_label_beat(2.4, os.path.relpath(c, ROOT), benefits[i % len(benefits)] if benefits else nm)
                  for i, c in enumerate(extra[:3])]

    if recipe == "showcase":
        beats.append(_beat(3.0, media, "product_hero", dict(hero or {}, name=nm, tagline=item.get("tagline", ""),
                                                             badge=item.get("badge")), cut=False))
        beats.append(_beat(3.6, media, "product_hero", dict(hero or {}, items=benefits)))
        beats += clip_beats
        if price:
            beats.append(_beat(2.8, media, "product_hero", dict(hero or {}, name=nm, price=price, was=was, price_at=0.5)))
    elif recipe == "reasons":
        beats.append(_beat(2.6, media, "product_hero", dict(hero or {}, name=f"{len(benefits) or 3} reasons you'll love {nm}")))
        beats.append(_beat(1.2 + 0.6 * max(len(benefits), 1), media, "product_hero", dict(hero or {}, items=benefits)))
        beats += clip_beats
        if price:
            beats.append(_beat(2.4, media, "product_hero", dict(hero or {}, price=price, was=was, price_at=0.4)))
    elif recipe == "offer":
        beats.append(_beat(3.0, media, "product_hero", dict(hero or {}, name=item.get("offer") or "Sale on now", tagline=nm, badge="SALE"), cut=False))
        beats += clip_beats[:1]
        beats.append(_beat(3.0, media, "product_hero", dict(hero or {}, name=nm, price=price or "", was=was, badge="SALE", price_at=0.6)))
    elif recipe == "new-drop":
        beats.append(_beat(2.8, media, "product_hero", dict(hero or {}, name="Just dropped", tagline=nm, badge="NEW"), cut=False))
        beats.append(_beat(3.0, media, "product_hero", dict(hero or {}, items=benefits[:2])))
        beats += clip_beats[:2]
        if price:
            beats.append(_beat(2.6, media, "product_hero", dict(hero or {}, name=nm, price=price, was=was, price_at=0.4)))
    elif recipe == "reviews":
        revs = [r for r in cat.get("reviews", []) if not r.get("about") or r["about"].lower() in nm.lower()][:3]
        if not revs:
            raise ValueError("Add a review or two to the catalogue first (text, name, stars).")
        beats.append(_beat(2.2, media, "product_hero" if photo and kind == "product" else "collage",
                           dict(hero or {}, name="What our customers say") if photo and kind == "product"
                           else {"overlay": True, "kicker": nm, "title": "What clients say", "title_y": 0.14, "title_px": 120}, cut=False))
        for r in revs:
            beats.append(_beat(3.4, media, "review_card", {"text": r.get("text", ""), "name": r.get("name", ""),
                                                           "stars": r.get("stars", 5),
                                                           **({"photo": photo} if photo and kind == "product" else {}),
                                                           **({"photo": photo, "backdrop": "photo"} if photo and kind == "service" else {})}))
    elif recipe == "how-it-works":
        steps = item.get("steps") or ["Book online", "We get to work", "Enjoy the result"]
        beats.append(_beat(1.2 + 0.8 * len(steps), media, "steps_cards", {"kicker": nm, "title": "How it works", "items": steps,
                                                                          "details": item.get("details") or [],
                                                                          **({"photo": photo, "backdrop": "photo"} if photo else {})}, cut=False))
        beats += clip_beats or ([_label_beat(2.4, media, item.get("result") or nm)] if photo else [])
        if price:
            beats.append(_label_beat(2.4, media, f"{nm} · {price}", y=0.82))
    elif recipe == "results":
        b, a = item.get("before"), item.get("after")
        if not (b and a):
            raise ValueError("Add a 'before' and an 'after' photo to this service in the catalogue.")
        beats.append(_beat(2.4, b, "collage", {"overlay": True, "labels": [{"text": "before", "x": 0.5, "y": 0.12, "px": 64, "at": 0.1}]}, cut=False))
        beats.append({"text": "", "dur": 3.0, "transition": "flash", "do": [f"broll:{a}", "scene:collage"],
                      "scene": {"overlay": True, "labels": [{"text": "after ✦", "x": 0.5, "y": 0.12, "px": 64, "at": 0.1},
                                                            *([{"text": f"{nm} · {price}", "x": 0.5, "y": 0.86, "px": 46, "at": 0.8}] if price else [])]}})
    elif recipe == "faq":
        faqs = cat.get("faqs") or []
        if not faqs:
            raise ValueError("Add a question and answer to the catalogue first (faqs: q, a).")
        f = faqs[0]
        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", f.get("a", "")) if s.strip()][:3] or [f.get("a", "")]
        beats.append(_beat(2.6, media, "collage", {"overlay": True, "kicker": "you asked", "title": f.get("q", ""),
                                                   "title_y": 0.16, "title_px": 84}, cut=False))
        beats.append(_beat(1.2 + 0.9 * len(parts), media, "steps_cards", {"kicker": "you asked", "title": "Here's the answer", "items": parts,
                                                                          **({"photo": photo, "backdrop": "photo"} if photo else {})}))

    cta = biz.get("cta") or "Shop now · link in bio"
    plan = {"format": "faceless", "pack": "brand", "look": "clean", "captions": "off", "auto_stickers": False,
            "auto_transitions": False, "logo": True, "sound": "effects", "broll_sound": 0,
            "music": {"generate": {"mood": ["confident"], "genre": ["indie pop"], "tempo": "112", "energy": "steady"}, "gain": 0.6},
            "end_card": {"enabled": True, "cta": cta},
            "cover": {"kicker": RECIPES[recipe][1], "title": nm, **({"photo": photo} if photo else {}), "y": 0.8},
            "beats": beats, "brand_reel": {"recipe": recipe, "item": nm, "kind": kind}}
    return plan, item


def make(recipe, name=None, clips=None, slug=None):
    """Write the project (plan.json + music) and return its slug."""
    plan, item = build(recipe, name, clips)
    slug = project.new(None, slug or f"{item.get('name', 'brand')}-{recipe}")
    gen = plan["music"].pop("generate")
    from . import musicgen
    dur = sum(b["dur"] for b in plan["beats"]) + 3
    st, _ = musicgen.compose(gen, dur, seed=len(slug))
    mp = project.path(slug, "music", "bed.wav")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    musicgen.write(mp, st)
    plan["music"]["file"] = os.path.relpath(mp, ROOT)
    project.save(slug, "plan.json", plan)
    return slug


def overview():
    cat = catalog()
    lines = ["Recipes:"]
    for k, (kind, label, about) in RECIPES.items():
        lines.append(f"  {k:13} {label:24} ({'product or service' if kind == 'either' else kind}) — {about}")
    lines.append("\nThis brand's catalogue:")
    for kind in ("products", "services"):
        for it in cat.get(kind, []):
            lines.append(f"  {kind[:-1]:8} {it.get('name')}  {it.get('price', '')}  photos: {len(it.get('photos') or [])}")
    lines.append(f"  reviews: {len(cat.get('reviews', []))} · faqs: {len(cat.get('faqs', []))}")
    if not (cat.get("products") or cat.get("services")):
        lines.append("  (empty — add products/services to brand/catalog.json, or ask Claude: \"add my products\")")
    return "\n".join(lines)
