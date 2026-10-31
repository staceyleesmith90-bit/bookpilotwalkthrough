import os
from PIL import Image
from engine import packs, scenefx, sounddesign
from engine.plan import to_timeline


class _NoMask(scenefx.Ctx):
    """Tests run without the cut-out model: use the soft centre shape."""
    def _masker(self, which):
        return None


def test_every_effect_draws_a_full_frame_at_every_moment():
    pk = packs.load("minimal")
    W, H = 270, 480
    frame = Image.new("RGBA", (W, H), (120, 110, 100, 255))
    for name in scenefx.EFFECTS:
        sc = {"fx": name, "start": 0.0, "end": 1.5, "spec": {"steps": [[0.0, "One"]]} if name == "series" else {}}
        ctx = _NoMask(W, H, pk, scenes=[sc])
        ctx.frame_at = lambda t: frame
        for t in (0.0, 0.4, 0.8, 1.2, 1.49):
            out = scenefx.apply(frame.copy(), t, ctx)
            assert out.size == (W, H) and out.mode == "RGBA", name


def test_effect_sounds_resolve_and_sit_inside_the_effect():
    for name in scenefx.LABELS:
        sc = {"fx": name, "start": 5.0, "end": 7.0, "spec": {}}
        for t, ev, g in scenefx.sounds(sc):
            assert 5.0 <= t < 7.0 and ev in sounddesign.KITS, (name, ev)
    for ev in ("boom", "shatter", "slam", "crack", "lights", "camera"):
        x = sounddesign.render(f"sd:motion:{ev}:2")
        assert len(x) > 1000 and abs(x).max() > 0.2


def test_plan_scene_beats_series_and_effects_sound():
    plan = {"format": "faceless", "pack": "minimal", "sound": "effects", "series": {"title": "3 Effects"},
            "beats": [{"text": "one", "dur": 2.0, "do": ["scene:paper_cutout"]},
                      {"text": "two", "dur": 2.0, "do": ["scene:recap", "scene:zoom_through"],
                       "scene": {"recap": {"dur": 1.0}, "zoom_through": {"at_s": 1.0}}},
                      {"text": "three", "dur": 2.0, "do": ["scene:frame_break"]}]}
    tl = to_timeline(plan)
    fx = [c["fx"] for c in tl["scenes"]]
    assert fx[:4] == ["paper_cutout", "recap", "zoom_through", "frame_break"] and fx[-1] == "series"
    main = [c for c in tl["scenes"] if c["fx"] != "series"]
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(main, main[1:]))      # one at a time
    assert [s[1] for s in tl["scenes"][-1]["spec"]["steps"]] == ["Paper Cutout", "Checklist", "Zoom Through Cut", "Frame Break"]
    names = {s["name"].split(":")[2] for s in tl["audio"]["sfx"]}
    assert {"shatter", "boom"} <= names and "word_pop" not in names


def test_effects_pack_names_are_read_and_registered():
    from engine.vfx45.update import PATCHES, effect_names
    names = effect_names()
    assert len(names) >= 45
    theirs = {v[0] for v in scenefx.V45.values()}
    assert all(n in theirs for n, _ in names)            # every effect in fx.py is usable in plans
    src = open(os.path.join(os.path.dirname(scenefx.__file__), "vfx45", "fx.py"), encoding="utf-8").read()
    assert all(new in src for _, new in PATCHES)         # our fixes are in the installed copy
