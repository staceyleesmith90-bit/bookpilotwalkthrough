from engine import sounddesign
from engine.plan import to_timeline


def _plan(**kw):
    return dict({"format": "faceless", "captions": "off", "auto_stickers": False,
                 "beats": [{"text": "", "dur": 2, "do": ["broll:library/samples/hero-photo.jpg", "scene:checklist_pop"],
                            "scene": {"items": ["a", "b"]}},
                           {"text": "", "dur": 2, "do": ["broll:library/samples/hero-photo.jpg"]}]}, **kw)


def test_quiet_means_no_sound_effects():
    tl = to_timeline(_plan(sound="quiet"), None, None)
    assert tl["audio"]["sfx"] == [] and tl["end_card"]["sound"] is False


def test_default_is_modern_recorded_sounds_only():
    tl = to_timeline(_plan(), None, None)
    names = [c["name"] for c in tl["audio"]["sfx"]]
    assert tl["end_card"]["sound"] is False
    for n in names:                       # never a synth or a Kenney game sound
        if n.startswith("sd:"):
            src = sounddesign.source_file(n)[0]
            assert not str(src).startswith("s:") and not str(src).startswith(sounddesign.KEN), n
    times = [c["t"] for c in tl["audio"]["sfx"]]
    assert all(b - a >= 0.7 for a, b in zip(times, times[1:]))


def test_modern_swaps_game_sounds_for_recorded_ones():
    cues = [(0.0, "sd:clean:zoom_in:1", 0.6), (1.0, "sd:clean:riser:2", 0.6), (2.0, "sd:clean:boom:3", 0.6),
            (3.0, "sd:clean:text_in:4", 0.6), (3.2, "sd:clean:page:5", 0.6)]
    kept = sounddesign.modern(cues)
    events = [n.split(":")[2] for _, n, _ in kept]
    assert "riser" not in events and "zoom_in" not in events and "boom" not in events
    assert "air" in events and len([t for t, _, _ in kept if 3.0 <= t < 3.5]) == 1


def test_sound_list_edits_turn_off_and_swap():
    cues = [(1.0, "sd:soft:text_in:1", 0.5), (2.5, "sd:soft:page:2", 0.5)]
    swap = sounddesign.choice_files("Pop")[0]
    out = sounddesign.apply_edits(cues, {"1.00": {"off": True}, "2.50": {"file": swap}})
    assert out == [(2.5, "file:" + swap, 0.5)]
    from engine import sfx
    assert len(sfx.load("file:" + swap)) > 100
    assert sounddesign.label_of("file:" + swap) == "Pop"
    assert all(sounddesign.choice_files(k) for k in sounddesign.CHOICES)


def test_sound_list_survives_rebuild():
    edits = {"sfx_edits": {}}
    tl = to_timeline(_plan(**edits), None, None)
    auto = tl["audio"]["sfx_auto"]
    if auto:
        k = sounddesign.key_of(auto[0]["t"])
        tl2 = to_timeline(_plan(sfx_edits={k: {"off": True}}), None, None)
        assert len(tl2["audio"]["sfx"]) == len(tl["audio"]["sfx"]) - 1 and len(tl2["audio"]["sfx_auto"]) == len(auto)


def test_soft_keeps_only_gentle_recorded_sounds():
    cues = [(0.0, "sd:clean:whoosh:1", 0.6), (0.5, "sd:clean:text_in:2", 0.6), (0.9, "sd:clean:pill_in:3", 0.6),
            (2.0, "sd:clean:zoom_in:4", 0.6), (2.5, "sd:clean:riser:5", 0.6), (3.0, "sd:clean:page:6", 0.6)]
    kept = sounddesign.soften(cues)
    events = [n.split(":")[2] for _, n, _ in kept]
    assert "whoosh" not in events and "zoom_in" not in events and "riser" not in events
    assert all(b[0] - a[0] >= 1.2 for a, b in zip(kept, kept[1:]))
