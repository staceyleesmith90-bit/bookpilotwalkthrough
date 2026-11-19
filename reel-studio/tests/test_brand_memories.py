import os

import pytest
from PIL import Image, ImageDraw

from engine import brandreels, memories, scenefx, brandfx


def _photo(path, color=(200, 80, 60)):
    im = Image.new("RGB", (600, 800), (240, 240, 238))
    ImageDraw.Draw(im).rounded_rectangle((150, 200, 450, 650), 40, fill=color)
    im.save(path)
    return path


CAT = {"business": {"cta": "Shop now"},
       "products": [{"name": "Volt X1", "price": "R8 999", "was": "R10 999", "benefits": ["25 km range", "Folds fast"], "photos": []}],
       "services": [{"name": "Gel nails", "price": "R350", "steps": ["Book", "Pick a colour", "Glow"], "photos": []}],
       "reviews": [{"text": "Love it", "name": "Lerato", "stars": 5}], "faqs": [{"q": "How long?", "a": "Two weeks. Easy."}]}


def test_recipes_build_plans_and_check_what_fits(tmp_path):
    p = _photo(str(tmp_path / "volt.png"))
    cat = {k: (v if not isinstance(v, list) else [dict(i) for i in v]) for k, v in CAT.items()}
    cat["products"][0]["photos"] = [p]
    cat["services"][0]["photos"] = [p]
    plan, item = brandreels.build("showcase", "volt", cat=cat)
    fx = [d for b in plan["beats"] for d in b["do"] if d.startswith("scene:")]
    assert item["name"] == "Volt X1" and "scene:product_hero" in fx and plan["end_card"]["cta"] == "Shop now"
    assert any(b.get("scene", {}).get("price") == "R8 999" for b in plan["beats"])
    plan, _ = brandreels.build("how-it-works", "gel", cat=cat)
    assert plan["beats"][0]["scene"]["items"] == ["Book", "Pick a colour", "Glow"]
    with pytest.raises(ValueError):
        brandreels.build("how-it-works", "volt", cat=cat)          # a product can't use a service recipe
    with pytest.raises(ValueError):
        brandreels.build("showcase", "nothing-here", cat={"products": [], "services": []})


@pytest.mark.parametrize("fx", list(brandfx.EFFECTS))
def test_brand_effects_draw(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("REEL_NO_REMBG", "1")
    p = _photo(str(tmp_path / "x.png"))
    ctx = scenefx.Ctx(540, 960, {"colors": {"bg": "#E8EEF1", "ink": "#0F1A22", "pop": "#00B39B", "accent": "#FFC93C", "paper": "#FFFFFF"}}, scenes=[])
    spec = {"photo": p, "name": "Volt X1", "price": "R8 999", "was": "R10 999", "badge": "NEW", "items": ["25 km range", "LED deck"],
            "text": "Best buy this year", "title": "How it works", "stars": 5}
    out = brandfx.EFFECTS[fx](Image.new("RGBA", (540, 960), (0, 0, 0, 255)), None, 3.0, 4.0, spec, ctx, 1.0)
    assert out.size == (540, 960) and len(set(out.convert("RGB").resize((54, 96)).getdata())) > 20
    assert scenefx.sounds({"fx": fx, "start": 0, "end": 4.0, "spec": spec})


def test_memories_pick_orders_and_collapses_bursts(tmp_path):
    a = _photo(str(tmp_path / "a.jpg"), (200, 80, 60))
    b = _photo(str(tmp_path / "b.jpg"), (201, 81, 61))                 # a near-identical burst shot
    c = str(tmp_path / "c.jpg")
    im = Image.new("RGB", (600, 800), (20, 120, 200))
    ImageDraw.Draw(im).ellipse((100, 100, 500, 500), fill=(250, 250, 250))
    im.save(c)
    for i, f in enumerate((a, b, c)):
        os.utime(f, (1_700_000_000 + i * 60, 1_700_000_000 + i * 60))
    got = [os.path.basename(p) for p, _, _ in memories.pick([c, b, a])]
    assert got[-1] == "c.jpg" and len(got) == 2                        # time order, burst collapsed
