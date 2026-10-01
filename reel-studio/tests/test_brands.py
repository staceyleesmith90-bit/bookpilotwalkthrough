import json, os, shutil, subprocess

import pytest

from engine import autolook, brands, packs, plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def studio(tmp_path, monkeypatch):
    cur, allb = tmp_path / "brand", tmp_path / "brands"
    cur.mkdir()
    (cur / "brand.json").write_text(json.dumps({"label": "Glow Skin", "fonts": {}, "colors": {}}))
    (cur / "rules.json").write_text("[]")
    (cur / "trending-sounds.json").write_text("[]")
    monkeypatch.setattr(brands, "CUR", str(cur))
    monkeypatch.setattr(brands, "ALL", str(allb))
    monkeypatch.setattr(brands, "ACTIVE", str(allb / "active.txt"))
    return tmp_path


def test_new_switch_keep_everything(studio):
    assert brands.listing()[0][1] == "Glow Skin"
    s = brands.new("Sunny Bakery")
    assert s == "sunny-bakery" and brands.active() == "sunny-bakery"
    assert (studio / "brands" / "glow-skin" / "rules.json").exists()         # old brand kept whole
    assert (studio / "brand" / "trending-sounds.json").exists()              # personal files stay
    (studio / "brand" / "brand.json").write_text(json.dumps({"label": "Sunny Bakery"}))
    names = {b[1]: b[2] for b in brands.listing()}
    assert names == {"Sunny Bakery": True, "Glow Skin": False}
    brands.use("glow skin")
    assert json.load(open(studio / "brand" / "brand.json"))["label"] == "Glow Skin"
    assert (studio / "brands" / "sunny-bakery" / "brand.json").exists()
    with pytest.raises(ValueError):
        brands.new("Sunny Bakery")
    with pytest.raises(ValueError):
        brands.delete("Glow Skin")                                          # in use
    brands.delete("Sunny Bakery")
    assert [b[1] for b in brands.listing()] == ["Glow Skin"]


def test_pack_for_inactive_brand_fixes_paths(studio, monkeypatch):
    other = studio / "brands" / "client-a"
    other.mkdir(parents=True)
    pk = json.loads(json.dumps(packs.presets()["bold"]))
    pk["label"] = "Client A"
    pk["fonts"]["main"]["file"] = "brand/fonts/Their-Font.ttf"
    (other / "brand.json").write_text(json.dumps(pk))
    p = brands.pack_for("client-a")
    assert p["label"] == "Client A" and p["fonts"]["main"]["file"].replace("\\", "/").endswith("brands/client-a/fonts/Their-Font.ttf")


def test_broll_look_words():
    assert plan.BROLL_LOOKS["black and white"] == "bw-classic"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_look_from_video_picks_the_colourful_thing(tmp_path, monkeypatch):
    v = str(tmp_path / "v.mp4")
    # grey room with a bright pink product in it
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x8a8a8a:s=360x640:d=2",
                    "-vf", "drawbox=x=100:y=250:w=160:h=160:color=0xE8308C:t=fill", v], check=True)
    vivid, frame = autolook.palette_from_video(v)
    r, g, b = [int(vivid[0][i:i + 2], 16) for i in (1, 3, 5)]
    assert r > 180 and b > 90 and g < 120                                    # pink, not the grey room
    monkeypatch.setattr(autolook, "LOOKS", str(tmp_path / "looks.json"))
    monkeypatch.setattr(autolook, "ROOT", str(tmp_path))
    sheet, looks = autolook.make_looks(v, "Pink Co")
    assert len(looks) == 3 and os.path.exists(sheet)
