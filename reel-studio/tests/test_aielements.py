from PIL import Image, ImageDraw

from engine import aielements


def _sheet(path):
    im = Image.new("RGB", (800, 800), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((60, 60, 340, 340), fill=(169, 139, 214))
    d.ellipse((150, 150, 250, 250), fill=(255, 255, 255))          # white INSIDE a sticker must stay
    d.rectangle((460, 80, 740, 320), fill=(46, 196, 201))
    d.polygon([(200, 460), (340, 740), (60, 740)], fill=(240, 120, 90))
    d.rounded_rectangle((470, 470, 730, 730), 40, fill=(75, 63, 92))
    d.ellipse((700, 700, 712, 712), fill=(75, 63, 92))              # a loose bit joins its neighbour
    im.save(path)


def test_cut_finds_each_sticker_in_reading_order(tmp_path, monkeypatch):
    monkeypatch.setenv("REEL_NO_REMBG", "1")                       # the plain colour cut, deterministic
    _sheet(tmp_path / "s.png")
    paths = aielements.cut(str(tmp_path / "s.png"), str(tmp_path / "out"), ["Bucket", "Splash!", "Cone", "Box"])
    assert [p.rsplit("/", 1)[1] for p in paths] == ["bucket.png", "splash.png", "cone.png", "box.png"]
    first = Image.open(paths[0])
    assert first.getpixel((first.width // 2, first.height // 2))[3] > 200      # the white middle is kept
    assert first.getpixel((2, 2))[3] < 30                                       # the sheet background is gone


def test_prompt_names_every_item_and_style():
    t = aielements.prompt(["a cat", "a hat"], "clay", ["#A98BD6"])
    assert "a cat, then a hat" in t and "no numbers" in t and "clay" in t and "#A98BD6" in t and "white background" in t


def test_animate_makes_a_looping_transparent_webp(tmp_path):
    from PIL import ImageSequence
    src = tmp_path / "s.png"
    Image.new("RGBA", (120, 120), (0, 0, 0, 0)).save(src)
    im = Image.open(src); d = ImageDraw.Draw(im); d.ellipse((10, 10, 110, 110), fill=(200, 80, 80, 255)); im.save(src)
    for mv in aielements.MOTIONS:
        out = aielements.animate(str(src), str(tmp_path / f"{mv}.webp"), mv, seconds=0.5, fps=10, px=100)
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(Image.open(out))]
        assert len(frames) >= 2 and frames[0].getpixel((1, 1))[3] == 0      # identical frames merge


def test_connect_cloudflare_rejects_bad_details_without_saving(tmp_path, monkeypatch):
    monkeypatch.setattr(aielements, "ENV", str(tmp_path / ".env"))
    ok, msg = aielements.connect_cloudflare("not-an-id", "x" * 40)
    assert not ok and "Account ID" in msg and not (tmp_path / ".env").exists()


def test_place_puts_one_sticker_per_moment_off_centre_and_clear_removes_them(tmp_path, monkeypatch):
    from engine import project
    monkeypatch.setattr(project, "PROJECTS", str(tmp_path))
    slug = "p"
    (tmp_path / slug / "elements").mkdir(parents=True)
    for n in ("a", "b"):
        Image.new("RGBA", (20, 20), (200, 0, 0, 255)).save(tmp_path / slug / "elements" / f"{n}.png")
    project.save(slug, "plan.json", {"beats": [{"do": ["broll:x.jpg"]}, {"do": ["broll:y.jpg", "scene:collage"], "scene": {"overlay": True}},
                                               {"do": ["broll:z.jpg", "scene:product_hero"], "scene": {}}]})
    assert aielements.place(slug, aielements.stickers_of(slug)) == 2          # the full-screen effect is left alone
    plan = project.load(slug, "plan.json")
    st = [b.get("scene", {}).get("stickers") for b in plan["beats"]]
    assert st[0][0]["x"] != 0.5 and st[1][0]["image"].endswith("b.png") and not st[2]
    aielements.clear(slug)
    assert all(not (b.get("scene") or {}).get("stickers") for b in project.load(slug, "plan.json")["beats"])


def test_chatgpt_prompt_is_explicit():
    from engine.aielements import chatgpt_prompt
    p = chatgpt_prompt("our garden day", ["sand bucket", "sun"], "clay", ["#E8541E"], reference=True)
    assert "our garden day" in p and "- sand bucket" in p and "- sun" in p and "clay" in p
    assert "reference picture" in p and "pure white background" in p and "no words" in p
    assert "Choose 5" in chatgpt_prompt("x", [], "paper")
