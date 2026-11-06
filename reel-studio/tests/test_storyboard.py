from engine import storyboard


def test_moments_follow_faceless_beats():
    tl = {"duration": 6.0, "broll": [], "scenes": []}
    plan = {"format": "faceless", "beats": [{"dur": 2}, {"dur": 3}, {"dur": 1}]}
    assert storyboard._moments(tl, plan) == [(0.0, 2.0, 0), (2.0, 5.0, 1), (5.0, 6.0, 2)]


def test_describe_lists_text_and_stickers():
    tl = {"scenes": [{"fx": "collage", "start": 0, "end": 3, "spec": {"overlay": True, "labels": [{"text": "hi"}],
                      "stickers": [{"emoji": "Sun"}, {"image": "x/blocks_stack.png"}]}}], "items": []}
    d = storyboard._describe(tl, 0, 3)
    assert '"hi"' in d and "stickers: Sun, blocks stack" in d and d[0] == "effect: text + stickers"
    assert storyboard._describe({"scenes": [], "items": []}, 0, 1) == ["footage only"]


def test_skip_graphics_keeps_only_footage():
    from engine.plan import to_timeline
    plan = {"format": "faceless", "captions": "off", "auto_stickers": False, "beats": [
        {"text": "", "dur": 2, "do": ["broll:library/samples/x.jpg", "scene:collage"], "scene": {"overlay": True},
         "skip_graphics": True}]}
    tl = to_timeline(plan, None, None)
    assert not tl.get("scenes") and len(tl["broll"]) == 1
