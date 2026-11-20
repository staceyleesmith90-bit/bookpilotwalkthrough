from engine import beatsync


def test_cuts_snap_to_the_nearest_beat():
    plan = {"format": "faceless", "beats": [{"dur": 2.1}, {"dur": 2.8}, {"dur": 3.0}]}
    grid = [i * 0.5 for i in range(40)]                     # 120 bpm
    out = beatsync.snap(plan, grid)
    cuts, t = [], 0
    for b in out["beats"][:-1]:
        t += b["dur"]
        cuts.append(round(t, 3))
    assert all(abs(c * 2 - round(c * 2)) < 1e-6 for c in cuts)   # every cut on a beat
    assert out["beat_synced"] and all(b["dur"] >= beatsync.MIN_DUR for b in out["beats"])


def test_far_beats_and_talking_reels_are_left_alone():
    plan = {"format": "faceless", "beats": [{"dur": 2.0}, {"dur": 2.0}, {"dur": 2.0}]}
    assert [b["dur"] for b in beatsync.snap(plan, [10, 11, 12, 13, 14])["beats"]] == [2.0, 2.0, 2.0]
    talk = {"format": "talking", "beats": plan["beats"], "music": {"file": "x.wav"}}
    assert beatsync.apply(talk) is talk
