import os, subprocess
from PIL import Image
from engine import packs, scrapbook


def _photos(tmp_path, n=3):
    out = []
    for i in range(n):
        p = tmp_path / f"p{i}.jpg"
        Image.new("RGB", (300, 400), (60 * i, 160, 90)).save(p)
        out.append(str(p))
    return out


def test_defaults_come_from_pack_and_are_clamped():
    pack = packs.load("blush")
    s = scrapbook.settings({"speed": 99, "tilt": -5, "size": 5, "direction": -3}, pack)
    assert s["speed"] == 5.0 and s["tilt"] == 0 and s["size"] == 160 and s["direction"] == -1
    assert pack["colors"]["pop"] in s["tape"] and "#FFFFFF" not in s["tape"]
    assert s["center"] == [540, 700]
    assert scrapbook.settings({"style": "page"}, pack)["center"] == [540, 900]
    assert scrapbook.settings({"style": "nope", "tape": "none"}, pack)["style"] == "orbit"
    assert scrapbook.settings({"tape": "#111111,#222222"}, pack)["tape"] == ["#111111", "#222222"]


def test_every_option_is_documented():
    text = scrapbook.options_help()
    for k in scrapbook.OPTIONS:
        assert k in text


def test_renders_each_style_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(scrapbook, "CACHE", str(tmp_path / "cache"))
    pack = packs.load("blush")
    photos = _photos(tmp_path)
    for style in scrapbook.STYLES:
        out = scrapbook.render({"style": style, "photos": photos, "duration": 1.0, "captions": ["hi"]}, pack=pack)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                                   capture_output=True, text=True).stdout)
        assert 0.9 <= dur <= 1.1
        assert scrapbook.render({"style": style, "photos": photos, "duration": 1.0, "captions": ["hi"]}, pack=pack) == out


def test_print_has_tape_frame_and_caption():
    pack = packs.load("blush")
    s = scrapbook.settings({"tilt": 0, "shadow": 0}, pack)
    card = scrapbook.make_print(Image.new("RGB", (300, 400), "green"), s, 0, pack, "liefie")
    plain = scrapbook.make_print(Image.new("RGB", (300, 400), "green"), dict(s, frame="none", tape=[]), 0, pack)
    assert card.height > plain.height and card.width > plain.width


def test_plan_beat_uses_scrapbook(tmp_path, monkeypatch):
    monkeypatch.setattr(scrapbook, "CACHE", str(tmp_path / "cache"))
    from engine.plan import to_timeline
    plan = {"format": "faceless", "pack": "blush", "beats": [
        {"text": "", "dur": 1.0, "do": ["scrapbook:stack"], "scrapbook": {"photos": _photos(tmp_path, 2)}}]}
    tl = to_timeline(plan)
    assert tl["broll"] and tl["broll"][0]["scrapbook"] == "stack"
    assert not any(i.get("role") == "takeover" for i in tl["items"])
