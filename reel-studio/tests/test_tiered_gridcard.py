import json, subprocess
from engine import captions, gridcard, packs
from engine.plan import to_timeline


def W(s):
    return [{"w": x} for x in s.split()]


def test_tiered_splits_lead_and_big_and_animates():
    assert captions.tiered_split(W("feels like to China"), {2}) == (W("feels like"), W("to China"))
    assert captions.tiered_split(W("doing business"), set())[1] == []
    pack = packs.load("minimal")
    done = captions.render_tiered(W("feels like to China"), 3, captions.PHASES, pack, {"_keys_in_group": [2]})
    mid = captions.render_tiered(W("feels like to China"), 3, 1, pack, {"_keys_in_group": [2]})
    assert done.size == mid.size and done.getbbox()
    assert done.tobytes() != mid.tobytes()          # the newest word is still blurring in
    assert captions._spoken_case("China") == "China" and captions._spoken_case("WOW") == "wow"


def test_gridcard_frames_settle_and_plan_item():
    f = gridcard.frames({"lead": "here's your", "big": "driver"}, packs.load("minimal"))
    assert f[-1][1] > 100 and f[-1][0].size == (1080, 1920)
    tl = to_timeline({"format": "faceless", "pack": "minimal",
                      "beats": [{"text": "here's your driver", "dur": 1.5, "do": ["gridcard"]}]})
    it = [i for i in tl["items"] if i["type"] == "gridcard"][0]
    assert it["lead"] == "here's your" and it["big"] == "driver" and it["hide_captions"]
    assert not any(i.get("role") == "takeover" for i in tl["items"])


def test_renders_with_tiered_captions_and_gridcard(tmp_path):
    from engine import render
    tl = to_timeline({"format": "faceless", "pack": "minimal",
                      "beats": [{"text": "hello there", "dur": 1.0, "do": ["keep-footage"]},
                                {"text": "here's your driver", "dur": 1.0, "do": ["gridcard"]}]})
    tl["captions"] = {"style": "tiered", "words_per_line": 4, "y": 1080,
                      "words": [{"w": "hello", "start": 0.1, "end": 0.4}, {"w": "there", "start": 0.4, "end": 0.9}]}
    tl["end_card"] = {"enabled": False}
    out = tmp_path / "t.mp4"
    render.render(tl, str(out), preview=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout)
    assert 1.8 < dur < 2.6
