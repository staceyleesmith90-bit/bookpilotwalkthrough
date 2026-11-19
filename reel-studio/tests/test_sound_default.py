from engine import sounddesign
from engine.plan import to_timeline


def _plan(**kw):
    return dict({"format": "faceless", "captions": "off", "auto_stickers": False,
                 "beats": [{"text": "", "dur": 2, "do": ["broll:library/samples/hero-photo.jpg", "scene:checklist_pop"],
                            "scene": {"items": ["a", "b"]}},
                           {"text": "", "dur": 2, "do": ["broll:library/samples/hero-photo.jpg"]}]}, **kw)


def test_no_sound_effects_unless_asked():
    tl = to_timeline(_plan(), None, None)
    assert tl["audio"]["sfx"] == [] and tl["end_card"]["sound"] is False


def test_soft_keeps_only_gentle_recorded_sounds():
    cues = [(0.0, "sd:clean:whoosh:1", 0.6), (0.5, "sd:clean:text_in:2", 0.6), (0.9, "sd:clean:pill_in:3", 0.6),
            (2.0, "sd:clean:zoom_in:4", 0.6), (2.5, "sd:clean:riser:5", 0.6), (3.0, "sd:clean:page:6", 0.6)]
    kept = sounddesign.soften(cues)
    events = [n.split(":")[2] for _, n, _ in kept]
    assert "whoosh" not in events and "zoom_in" not in events and "riser" not in events
    assert all(b[0] - a[0] >= 1.2 for a, b in zip(kept, kept[1:]))
