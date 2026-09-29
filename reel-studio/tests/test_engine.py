"""Fast checks for the parts most likely to break. Run: python -m pytest tests -q"""
import json, os
import pytest
from engine import layout, packs, plan, roughcut, stickers, textfit, sfx, brand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_text_always_fits_its_box():
    font = os.path.join(ROOT, "library/fonts/Poppins-ExtraBold.ttf")
    for text in ["hi", "a much longer sentence that has to wrap onto several lines to fit"]:
        fit = textfit.fit_text(text, font, 600, 300, max_px=200, min_px=12)
        w, h, _ = textfit.measure(fit["lines"], fit["font"], 1.08)
        assert fit["fits"] and w <= 600 and h <= 300


def test_bubble_grows_instead_of_overflowing():
    pack = packs.load("bold")
    small = layout.bubble_with_text("ok", pack, width=400)
    big = layout.bubble_with_text("wait, it even draws my stickers for me without asking, really?! " * 2, pack, width=400)
    assert big.width > small.width


@pytest.mark.parametrize("name", list(packs.presets()))
def test_every_preset_loads_and_renders_every_sticker(name):
    pack = packs.load(name)
    for s in stickers.GENERATORS:
        img = stickers.render(s, pack, 120)
        assert img.getbbox() is not None, (name, s)
    assert stickers.badge("TIP #1", pack).getbbox()


def test_library_svg_sticker_recolours():
    a = stickers.render("laptop", packs.load("bold"), 100)
    b = stickers.render("laptop", packs.load("editorial"), 100)
    assert a.tobytes() != b.tobytes()


def test_sticker_search_uses_tags():
    assert stickers.find("hours") == "clock"
    assert stickers.find("editing") == "laptop"


def test_roughcut_drops_retakes_and_stutters():
    def words(text, t0):
        out, t = [], t0
        for w in text.split():
            out.append({"w": w, "start": t, "end": t + 0.3})
            t += 0.35
        return out
    tr = {"duration": 20, "words": words("This is my first try.", 0) + words("This is my first try again.", 5)
          + words("how much to how much to charge?", 10)}
    rc = roughcut.rough_cut(tr)
    assert [l["keep"] for l in rc["lines"]][:2] == [False, True]
    assert rc["lines"][2]["text"] == "how much to charge?"
    tmap, dur = roughcut.time_map(roughcut.kept_ranges(rc))
    assert tmap(0.1) is None and dur < 20


def test_faceless_plan_has_no_collisions():
    tl = plan.to_timeline({"format": "faceless", "pack": "playful", "beats": [
        {"text": "Stop editing for hours", "do": ["takeover", "sticker:clock"]},
        {"text": "Tip one: batch your filming", "do": ["takeover", "badge:TIP #1"]}]})
    from engine.render import item_image
    pk = packs.load("playful")
    for t in (0.8, 2.5):
        boxes = []
        for it in tl["items"]:
            if it["start"] <= t < it["end"]:
                im = item_image(it, pk)
                k = it.get("scale", 1)
                boxes.append((it["x"] - im.width * k / 2, it["y"] - im.height * k / 2,
                              it["x"] + im.width * k / 2, it["y"] + im.height * k / 2))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                assert not layout.overlaps(boxes[i], boxes[j], pad=-10), (t, boxes)


def test_sfx_all_generate():
    for name, fn in sfx.SFX.items():
        x = fn()
        assert len(x) > 100 and abs(x).max() > 0, name


def test_contrast_check_and_role_assignment():
    roles = brand.assign_roles(["#1E63FF", "#EC4899", "#FFFFFF", "#111111"])
    assert packs.contrast(roles["ink"], roles["bg"]) >= 4.5


@pytest.mark.parametrize("pack_name", list(packs.presets()))
def test_every_title_template_builds_in_every_pack(pack_name):
    from engine import titles
    pk = packs.load(pack_name)
    for name in titles.TEMPLATES:
        layers = titles.build({"template": name, "title": "A Day With Me", "kicker": "mini vlog",
                               "sub": "January 2026", "tag": "Eps #1", "location": "Cape Town"}, pk)
        comp, _ = titles.composite(layers)
        assert comp.width <= 960 and comp.getbbox(), (pack_name, name)


def test_typed_title_gets_a_click_per_character_and_faceless_titles_use_ink():
    tl = plan.to_timeline({"format": "faceless", "pack": "bold", "beats": [
        {"text": "hello", "do": ["title:typed:POV: it types itself"]}]})
    clicks = [c for c in tl["audio"]["sfx"] if ":type_key:" in c["name"]]
    assert len(clicks) >= len("POV: it types itself") - 6          # one key per letter (spaces skipped)
    assert len({c["name"] for c in clicks}) > len(clicks) * 0.8     # every key sounds slightly different
    t = next(i for i in tl["items"] if i["type"] == "title")
    assert t["spec"]["ink"] == packs.load("bold")["colors"]["ink"]


def test_music_prompt_mentions_what_they_asked_for():
    from engine import music
    p = music.build_prompt({"mood": ["cosy"], "genre": ["lo-fi"], "tempo": "slow",
                            "describe": "rainy Sunday"}, 30)
    assert "cosy" in p and "lo-fi" in p and "rainy Sunday" in p and "instrumental" in p


@pytest.mark.parametrize("style", ["cutout", "chip", "puffy", "holo", "circle", "duotone", "retro", "neon", "line", "fill"])
def test_icon_sticker_styles_render(style):
    img = stickers.render("icon:rocket", packs.load("systems-pilot"), 160, "pop", style=style)
    assert img is not None and img.getbbox()


def test_icon_library_covers_everyday_words():
    for w in ["rocket", "toddler", "gym", "suitcase", "pizza", "camera"]:
        assert stickers.find(w), w


def test_every_caption_style_renders_and_fits():
    from engine import captions
    pk = packs.load("bold")
    g = [{"w": w, "start": i * .3, "end": i * .3 + .25} for i, w in enumerate("a really quite long line of words here".split())]
    for st in captions.STYLES:
        im = captions.render(g, 2, pk, {"style": st})
        assert 0 < im.width <= 1080, st


def test_zooms_and_transitions_keep_frame_size():
    from PIL import Image
    from engine import fx
    f = Image.new("RGBA", (540, 960), (120, 90, 60, 255))
    for z in fx.ZOOMS:
        st = fx.zoom_state({"start": 0, "end": 1, "type": z, "scale": 1.2, "cx": 540, "cy": 800}, 0.5, 540, 960)
        assert fx.apply_zoom(f, *st).size == f.size
    for t in fx.TRANSITIONS:
        assert fx.transition(f, {"t": 0.5, "type": t}, 0.5, "#FF0000").size == f.size


def test_every_grade_builds_a_filter_graph():
    from engine import grades
    for g in grades.GRADES:
        s = grades.graph(g, "in", "out")
        assert s.startswith("[in]") and s.endswith("[out]")


def test_free_music_is_generated_offline():
    from engine import musicgen
    stereo, desc = musicgen.compose({"mood": ["cosy"], "genre": ["jazz café"]}, 4)
    assert stereo.shape[1] == 2 and abs(stereo).max() > 0.1 and "jazz" in desc


def test_templates_make_valid_plans():
    from engine import templates
    for tid, t in templates.all_templates().items():
        p = templates.to_plan(tid, {"topic": "my week", "time": ["7:00"], "lesson": ["x"]}, [])
        if t["format"] != "talking-head":
            tl = plan.to_timeline(p)
            assert tl["duration"] > 0, tid


def test_unknown_sticker_is_created_not_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(stickers, "REQUESTS", str(tmp_path / "requests.json"))
    img = stickers.render("zxqv gadget", packs.load("sunny"), 300)
    assert img is not None and img.getbbox() is not None
    assert "zxqv gadget" in json.load(open(tmp_path / "requests.json"))


def test_trending_sounds_suggest_by_mood(tmp_path, monkeypatch):
    from engine import trends
    monkeypatch.setattr(trends, "FILE", str(tmp_path / "t.json"))
    trends.add("Song A — Artist", ["playful"])
    trends.add("Song B - Library", ["calm", "cosy"], business=True)
    assert trends.suggest({"mood": ["cosy"]})[0]["title"] == "Song B"
    assert [i["title"] for i in trends.suggest({"mood": ["playful"]}, business=True)] == ["Song B"]
    assert trends.load()[0]["artist"] == "Library"


def test_sticker_fonts_auto_choice_and_upload(tmp_path, monkeypatch):
    from engine import titles
    monkeypatch.setattr(stickers, "REQUESTS", str(tmp_path / "requests.json"))
    p = packs.load("sunny")
    assert stickers.sticker_font(p)["file"] == titles.fonts_for(p)["script"]["file"]  # automatic = brand script
    assert stickers.sticker_font(p, "label")["file"] == p["fonts"]["main"]["file"]
    assert "Pacifico" in stickers.sticker_font(p, font="Pacifico")["file"]  # per-sticker choice
    p2 = dict(p, sticker=dict(p["sticker"], font="serif"))
    assert stickers.sticker_font(p2)["file"] == titles.fonts_for(p)["serif"]["file"]  # brand-wide choice
    own = tmp_path / "MyOwnFont.ttf"
    own.write_bytes(open(os.path.join(ROOT, "library/fonts/Satisfy-Regular.ttf"), "rb").read())
    assert packs.resolve_font(p, str(own))["file"] == str(own)
    assert stickers.render("custom:hello", p, 300, font=str(own)).getbbox()
    with pytest.raises(ValueError):
        brand.add_font(str(tmp_path / "x.woff"))


def test_roughcut_drops_soft_fillers_and_stretched_words():
    w = lambda t, a, b: {"w": t, "start": a, "end": b}
    words = [w("so", 0, .2), w("let's", .25, .5), w("take", .5, .7), w("a", .7, .8), w("look", .8, 1.0),
             w("and", 1.0, 1.2), w("yeah", 1.6, 1.9), w("okay", 1.9, 5.3), w("we", 5.35, 5.5),
             w("have", 5.5, 5.8), w("three", 5.8, 6.1), w("sizes.", 6.1, 6.5)]
    rc = roughcut.rough_cut({"words": words, "duration": 7})
    text = " ".join(l["text"] for l in rc["lines"] if l["keep"])
    assert "yeah" not in text and "okay" not in text and not text.startswith("so ")
    assert sum(l["duration"] for l in rc["lines"] if l["keep"]) < 4.5   # the 3.4s "okay" is gone


def test_pop_captions_highlight_keywords():
    from engine import captions
    ws = [{"w": x} for x in "davey has the best quality in china".split()]
    keys = captions.auto_keywords(ws)
    assert 3 in keys and len(keys) < len(ws)            # "best" highlighted, not every word
    im = captions.render(ws[:3], 1, packs.load("bold"), {"style": "pop", "_keys_in_group": [0]})
    assert im.width <= 1000 and im.getbbox()


def test_director_frames_face_and_pushes_product_shots():
    from engine import director
    tl = {"cuts": [[0, 3], [5, 8], [10, 13], [20, 24]]}
    face = (300, 400, 700, 800)
    heads = {1.5: face, 6.5: face, 11.5: face, 22.0: None}
    z, tr = director.plan_camera(tl, [], lambda t: heads[t])
    kinds = [(x["type"], x["start"]) for x in z]
    assert ("push", 9.0) in kinds                        # no face -> slow push-in
    assert any(k == "punch" and x.get("cx") == 500 for x in z for k in [x["type"]])  # centred on the face


def test_noise_check_picks_stronger_cleanup_for_noisy_audio(tmp_path):
    import numpy as np, wave
    from engine import audiocheck
    sr = 16000
    t = np.arange(sr * 6) / sr
    speech = np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 0.5 * t) > 0) * 0.5
    for name, noise in (("clean", 0.0005), ("noisy", 0.06)):
        a = speech + np.random.default_rng(1).normal(0, noise, len(t))
        with wave.open(str(tmp_path / f"{name}.wav"), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    clean, noisy = audiocheck.analyse(str(tmp_path / "clean.wav")), audiocheck.analyse(str(tmp_path / "noisy.wav"))
    assert clean["level"] == "clean" and noisy["level"] == "noisy"
    assert "afftdn" in audiocheck.chain(noisy) and audiocheck.chain(noisy, post=True)


def test_picture_plan_balances_a_yellow_cast():
    from engine import picture
    pl = picture.plan({"rgb": [0.6, 0.5, 0.38], "luma": 0.5, "contrast": 0.22, "clipped": 0})
    r, g, b = pl["gains"]
    assert b > 1 > r and pl["notes"]
    assert "colorchannelmixer" in picture.filters(pl)


def test_quality_check_fills_static_stretches_and_hook():
    from engine import qa
    tl = {"duration": 20, "zooms": [], "items": [], "transitions": [], "captions": {"style": "pop", "words": []}}
    notes = qa.fix_timeline(tl)
    assert any(z["start"] < 1.5 for z in tl["zooms"])            # something happens at the start
    assert not qa._gaps(tl)                                      # never 5 s of nothing
    assert notes


def test_premium_glass_items_carry_a_blur_mask():
    from engine import premium
    p = packs.load("bold")
    chip = premium.glass_chip("Ultra thin", p, 320)
    assert chip.info.get("glass") is not None and chip.info["glass"].size == chip.size
    call = premium.callout("Strong waistband", p, sub="doesn't tear")
    assert "anchor" in call.info


def test_sound_design_uses_one_kit_with_variety():
    from engine import sounddesign, sfx
    tl = plan.to_timeline({"format": "faceless", "pack": "bold", "look": "premium", "beats": [
        {"text": "Stop editing for hours", "do": ["takeover", "badge:TIP #1"]},
        {"text": "Tip one", "do": ["takeover", "transition:whip"]}]})
    names = [c["name"] for c in tl["audio"]["sfx"]]
    kits = {n.split(":")[1] for n in names if n.startswith("sd:")}
    assert kits == {"luxe"}
    for n in names[:6]:
        assert len(sfx.load(n)) > 100


def test_kinetic_captions_never_jump():
    from engine import captions
    p = packs.load("bold")
    g = [{"w": w, "start": i * 0.3} for i, w in enumerate("the best quality in china".split())]
    for style in captions.KINETIC:
        sizes = {captions.render_kinetic(g, a, ph, p, {"style": style, "_keys_in_group": [1]}).size
                 for a in range(len(g)) for ph in range(captions.PHASES + 1)}
        assert len(sizes) == 1, (style, sizes)


def test_vlog_tag_title_and_vlog_inspiration():
    from engine import titles, packs
    from engine.inspire import plan_settings
    L = titles.build({"template": "tag", "title": "GRWM for School", "sub": "Tuesday, October 21"}, packs.load("brand"))
    assert len(L) == 2 and all(l["anim"] == "type" for l in L)
    comp, _ = titles.composite(L)
    assert comp.width < 700                      # a quiet label, not a headline
    s = plan_settings({"pacing": {"feel": "fast", "avg_shot_s": 0.7}, "speech": {"words_per_sec": 0.4},
                       "sound": {"events_per_sec": 1.2}, "look": {"suggested_grade": "soft-matte"}})
    assert s["format"] == "vlog" and s["captions"] == "off" and s["title_template"] == "tag"
    t = plan_settings({"pacing": {"feel": "fast"}, "speech": {"words_per_sec": 3.4}, "sound": {}, "look": {}})
    assert t["captions"] == "kinetic"
