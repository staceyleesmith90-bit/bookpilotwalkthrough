from engine import harvest


def w(text, t0, rate=0.35):
    out = []
    for k, x in enumerate(text.split()):
        out.append({"w": x, "start": round(t0 + k * rate, 2), "end": round(t0 + k * rate + 0.3, 2)})
    return out


def test_moments_pick_strong_openers(tmp_path, monkeypatch):
    words = (w("so um anyway we were talking about stuff and things for a while there today.", 0)
             + w("Why do most people never finish their first reel? " + "Because they edit for hours instead of minutes. " * 6, 6)
             + w("and yeah okay that was a lot of rambling about nothing in particular for now. " * 8, 60)
             + w("Here are 3 mistakes you should stop making today. " + "The first one costs you followers every single week. " * 5, 120))
    monkeypatch.setattr(harvest, "transcribe", lambda v, cache=None: {"words": words})
    monkeypatch.setattr(harvest, "CACHE", str(tmp_path))
    ms = harvest.moments("long.mp4", n=2)
    firsts = [m["first"] for m in ms]
    assert any(f.startswith("Why do most people") for f in firsts)
    assert any(f.startswith("Here are 3 mistakes") for f in firsts)
    assert all(15 <= m["seconds"] <= 61 for m in ms)
    assert ms[0]["end"] <= ms[1]["start"]                    # no overlap, in time order
