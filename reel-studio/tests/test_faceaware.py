from engine import faceaware


def _groups(n, step=2.0):
    return [[{"start": i * step, "end": i * step + 1.5}] for i in range(n)]


def test_chin_follow_sits_under_the_chin_and_holds_still():
    head = lambda t: (400, 600, 700, 1000)                    # chin at 1000
    ys = faceaware.chin_follow({"zooms": []}, head, lambda t: t, _groups(4))
    assert ys[0] == 1000 + faceaware.GAP
    assert len(set(ys)) == 1                                   # no jitter


def test_chin_follow_stays_clear_of_app_buttons_and_glides():
    boxes = [(400, 500, 700, 900), (400, 900, 700, 1600)]      # head drops very low
    head = lambda t: boxes[0] if t < 2 else boxes[1]
    ys = faceaware.chin_follow({"zooms": []}, head, lambda t: t, _groups(3))
    assert all(y <= faceaware.BOTTOM_SAFE - faceaware.CAP_HALF - 20 for y in ys)
    assert ys[0] < ys[1] < ys[2]                               # moves part of the way each time


def test_chin_follow_keeps_last_spot_when_no_face():
    head = lambda t: (400, 600, 700, 1000) if t < 2 else None
    ys = faceaware.chin_follow({"zooms": []}, head, lambda t: t, _groups(3), default_y=1245)
    assert ys == [1070, 1070, 1070]


def test_guard_moves_a_sticker_off_the_face_but_not_pinned_or_titles():
    tl = {"items": [
        {"id": "s1", "type": "sticker", "x": 540, "y": 700, "start": 0, "end": 2},
        {"id": "s2", "type": "sticker", "x": 540, "y": 700, "start": 0, "end": 2, "pinned": True},
        {"id": "t1", "type": "title", "x": 540, "y": 700, "start": 0, "end": 2},
        {"id": "s3", "type": "sticker", "x": 900, "y": 350, "start": 0, "end": 2}],
        "captions": {"style": "pop", "y": 1245, "words": [{"w": "hi", "start": 0, "end": 1}]}}
    head = lambda t: (380, 450, 700, 950)
    moved = faceaware.guard(tl, head, lambda t: t, lambda it: (200, 200))
    assert moved == ["s1"]
    s1 = tl["items"][0]
    box = (s1["x"] - 100, s1["y"] - 100, s1["x"] + 100, s1["y"] + 100)
    assert faceaware._overlap(box, (380, 450, 700, 950)) == 0
    assert faceaware._overlap(box, (90, 1160, 990, 1330)) == 0
