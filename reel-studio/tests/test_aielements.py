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
