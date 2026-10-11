from engine import handback


def tl():
    return {"cuts": [[10, 14], [20, 26]], "duration": 10.0,
            "items": [{"id": "a", "type": "text", "start": 1, "end": 3}, {"id": "b", "type": "sticker", "start": 5, "end": 7}],
            "captions": {"words": [{"w": "hi", "start": 0.5, "end": 0.8}, {"w": "there", "start": 6.0, "end": 6.4}]},
            "zooms": [{"start": 4.5, "end": 6.5, "type": "punch"}], "transitions": [{"t": 4.0, "type": "whip"}],
            "audio": {"cues": [[5.1, "pop", 0.5], [3.0, "click", 0.3]]}}


def test_cut_out_middle_and_move_everything():
    new = handback.remap(tl(), [(0, 2), (6, 10)])           # they cut 2s-6s out in CapCut
    assert new["duration"] == 6.0
    assert new["cuts"] == [[10, 12], [22, 26]]
    ids = {i["id"]: (i["start"], i["end"]) for i in new["items"]}
    assert ids["a"] == (1, 2)                                # clipped to what's left
    assert ids["b"] == (2.0, 3.0)                            # 6-7 -> 2-3
    assert [w["w"] for w in new["captions"]["words"]] == ["hi", "there"]
    assert new["captions"]["words"][1]["start"] == 2.0
    assert new["transitions"] == []                          # it sat in the removed part
    assert new["audio"]["cues"] == []


def test_reordered_pieces():
    new = handback.remap(tl(), [(6, 10), (0, 4)])            # moved the end to the front
    assert new["cuts"] == [[22, 26], [10, 14]]
    assert {i["id"]: i["start"] for i in new["items"]}["b"] == 0.0


def test_reads_capcut_project(tmp_path):
    d = {"materials": {"videos": [{"id": "m1", "path": "/x/reel-studio-media/footage.mp4"}, {"id": "m2", "path": "/x/end-screen.mp4"}]},
         "tracks": [{"type": "video", "segments": [
             {"material_id": "m1", "source_timerange": {"start": 6_000_000, "duration": 4_000_000}, "target_timerange": {"start": 2_000_000}},
             {"material_id": "m1", "source_timerange": {"start": 0, "duration": 2_000_000}, "target_timerange": {"start": 0}},
             {"material_id": "m2", "source_timerange": {"start": 0, "duration": 2_600_000}, "target_timerange": {"start": 6_000_000}}]}]}
    assert handback.kept_ranges(d) == [(0.0, 2.0), (6.0, 10.0)]
