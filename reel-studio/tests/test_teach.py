import json, os, shutil, subprocess

import pytest

from engine import library_page, mysounds, rules, sounddesign, stylesheet

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_design_file_roles(tmp_path):
    f = tmp_path / "DESIGN.md"
    f.write_text("## Colors\n- Background: #F7F1E8\n- Text: #1F1A17\n- Accent: #C2185B\n"
                 "## Type\n- Headline font: Playfair Display\n- Body: font-family: \"Inter\", sans-serif\n"
                 "- Accent (handwritten): font name: Caveat\n")
    s = stylesheet.read(str(f))
    assert s["colors"] == {"background": "#F7F1E8", "text": "#1F1A17", "accent": "#C2185B"}
    assert s["fonts"] == {"main": "Playfair Display", "caption": "Inter", "accent": "Caveat"}


def test_css_and_fallback_palette():
    s = stylesheet.read(":root{--brand-primary:#e11d48;--surface:#ffffff;--ink:#111}")
    assert s["colors"]["accent"] == "#E11D48" and s["colors"]["background"] == "#FFFFFF"
    s2 = stylesheet.read("palette #FAFAFA #222222 #1E88E5")       # no labels: guessed by lightness/colour
    assert set(s2["colors"]) == {"background", "text", "accent"}


def test_style_overview(tmp_path):
    spec = {"colors": {"background": "#FFFFFF", "text": "#111111", "accent": "#E4572E"}, "fonts": {}}
    pack, _ = stylesheet.make_pack(spec, "T", save=False)
    out = stylesheet.overview(pack, str(tmp_path / "o.jpg"))
    assert os.path.getsize(out) > 10000


def test_sound_roles():
    assert mysounds.role_for("PC typing keyboard Kacha") == ["typing"]
    assert "reveal" in mysounds.role_for("Killarn glitter sparkle item appearance")
    assert mysounds.role_for("Ka-ching (shopping / cash register sound)") == ["money"]
    assert "whoosh" in mysounds.role_for("Fuwa: short wind noise: swipe etc")
    assert mysounds.role_for("Camera shutter sound") == ["shutter"]


@pytest.fixture
def mine(tmp_path, monkeypatch):
    monkeypatch.setattr(mysounds, "MINE", str(tmp_path / "sounds"))
    return tmp_path


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_learn_capcut_project_and_use_first(mine):
    src = os.path.join(ROOT, "library", "sfx", "uisfx", "soft", "typing.wav")
    drafts = mine / "drafts" / "my favorites"
    drafts.mkdir(parents=True)
    d = {"materials": {"audios": [{"id": "a1", "name": "PC typing keyboard", "path": src},
                                  {"id": "a2", "name": "Fast Swoosh", "path": "/not/downloaded.mp3"}],
                       "texts": [{"id": "t1"}],
                       "material_animations": [{"id": "m1", "animations": [{"name": "Typewriter", "type": "in"}]}]},
         "tracks": [{"segments": [{"material_id": "t1", "target_timerange": {"start": 0, "duration": 2_000_000},
                                   "extra_material_refs": ["m1"]}]},
                    {"segments": [{"material_id": "a1", "target_timerange": {"start": 100_000, "duration": 900_000}}]}]}
    (drafts / "draft_content.json").write_text(json.dumps(d))
    r = mysounds.learn_capcut("My Favorites", drafts_root=str(mine / "drafts"))
    assert r["ok"] and r["learned"][0][1] == ["typing"] and r["not_downloaded"] == ["Fast Swoosh"]
    assert mysounds.pair_for("typewriter")["sound"] == "PC typing keyboard"
    f, _, _ = sounddesign.source_file(sounddesign.cue("typing", 1.0, 3, "soft", 0.3, 0.8)[1])
    assert f.startswith(mysounds.MINE)                       # their sound wins over the library
    cues = sounddesign.typewriter(1.0, "Hi", 0.3, "soft")
    assert cues[0][1].split(":")[2] == "typing"              # one burst of their sound, not per-key clicks
    mysounds.forget(None)
    assert not mysounds.files_for("typing")


def test_locked_capcut_project_explains(mine):
    p = mine / "drafts" / "fav"
    p.mkdir(parents=True)
    (p / "draft_content.json").write_bytes(b"\x00\x13encrypted")
    r = mysounds.learn_capcut("fav", drafts_root=str(mine / "drafts"))
    assert not r["ok"] and "inbox/sound-effects" in r["why"]


def test_spoken_sparkle_and_money():
    tl = {"items": [], "captions": {"style": "line", "words": [{"w": "watch", "start": 1.0}, {"w": "it", "start": 1.2},
                                                               {"w": "shine!", "start": 1.5}, {"w": "R500", "start": 4.0}]}}
    evs = [n.split(":")[2] for _, n, _ in sounddesign.design(tl, [], "soft")]
    assert "sparkle" in evs and "money" in evs


def test_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "PATH", str(tmp_path / "rules.json"))
    assert "Nothing taught" in rules.listing()
    rules.remember("Never use emojis in captions")
    rules.remember("Highlight key words in butter yellow italic", name="my highlight captions")
    assert rules.load()[0]["area"] == "never"
    assert "my highlight captions" in rules.listing()
    assert rules.forget("butter")["name"] == "my highlight captions"
    assert rules.forget(1)["rule"].startswith("Never")
    assert rules.load() == []


def test_library_page(tmp_path, monkeypatch):
    monkeypatch.setattr(library_page, "OUT", str(tmp_path / "out" / "lib.html"))
    d = library_page.data()
    assert len(d["premium"]) > 300 and d["sounds"] and d["captions"]
    out = library_page.build(open_it=False)
    html = open(out, encoding="utf-8").read()
    assert "Effects Library" in html and "</script>" in html


def test_resources_and_lut_upload(tmp_path, monkeypatch):
    from engine import resources, grades
    rs = resources.all_resources()
    assert {g["group"] for g in rs} >= {"Sound effects", "B-roll video", "Filters (LUTs)", "GIFs"}
    assert all(i["url"].startswith("https://") for g in rs for i in g["items"])
    monkeypatch.setattr(grades, "ROOT", str(tmp_path))
    bad = tmp_path / "x.cube"; bad.write_text("hello")
    with pytest.raises(ValueError):
        grades.add_lut(str(bad), "x.cube")
    good = tmp_path / "w.cube"; good.write_text("LUT_3D_SIZE 2\n" + "0 0 0\n" * 8)
    assert grades.add_lut(str(good), "My Warm.cube") == "My-Warm.cube"
    assert grades.my_luts() == ["My-Warm.cube"]
