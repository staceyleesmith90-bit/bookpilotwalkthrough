"""Face-aware placement — text that follows the person, graphics that never cover them.

Chin follow: captions sit a set distance under the speaker's chin, measured through the reel (camera
moves included), smoothed so they glide instead of jumping, and always kept clear of the app's buttons.
Guards: after everything is placed, every graphic is checked against the face and the caption band at
the moment it's on screen; anything that would land on them is moved to the nearest clear spot.
"""
from . import fx

W, H = 1080, 1920
TOP_SAFE, BOTTOM_SAFE = 270, 1620
GAP = 70                     # caption centre this far under the chin box
CAP_HALF = 70                # roughly half a caption's height


def _zoomed(box, t, zooms):
    """Where the face box ends up on screen with the camera move at t."""
    for z in zooms:
        st = fx.zoom_state(z, t, W, H)
        if st:
            k, cx, cy = st
            return tuple((v - c) * k + c for v, c in zip(box, (cx, cy, cx, cy)))
    return box


def chin_follow(tl, head_at, source_time, groups, default_y=1245):
    """-> y per caption group (or None when no face is seen). head_at(src_t) -> padded face box or None."""
    ys, last = [], None
    zooms = tl.get("zooms", [])
    for g in groups:
        t = (g[0]["start"] + g[-1]["end"]) / 2
        box = head_at(source_time(t))
        if box is None:
            ys.append(last if last is not None else default_y)
            continue
        x0, y0, x1, y1 = _zoomed(box, t, zooms)
        y = min(max(y1 + GAP, H * 0.52), BOTTOM_SAFE - CAP_HALF - 20)
        if last is not None and abs(y - last) < 45:            # small moves: hold still (no jitter)
            y = last
        elif last is not None:                                  # big moves: go only part of the way
            y = last + (y - last) * 0.6
        last = round(y)
        ys.append(last)
    return ys


def _overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def guard(tl, head_at, source_time, size_of):
    """Move graphics off the face and the caption band. size_of(item) -> (w, h) or None. -> moved ids."""
    cap = tl.get("captions") or {}
    cap_on = cap.get("style", "off") != "off" and cap.get("words")
    zooms = tl.get("zooms", [])
    moved = []
    for it in tl.get("items", []):
        if it.get("hide_captions") or it.get("type") in ("title", "takeover", "card", "hf", "window", "story", "overlay") \
                or it.get("x") is None or it.get("y") is None or it.get("pinned"):
            continue
        wh = size_of(it)
        if not wh:
            continue
        w, h = wh[0] * it.get("scale", 1.0), wh[1] * it.get("scale", 1.0)
        mid = (it["start"] + it["end"]) / 2
        face = head_at(source_time(mid)) if source_time else None
        if face is not None:
            face = _zoomed(face, mid, zooms)
        cy = cap.get("y", 1245)
        band = (90, cy - 85, W - 90, cy + 85) if cap_on else None
        avoid = [b for b in (face, band) if b]

        def hits(x, y):
            b = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            return sum(_overlap(b, a) for a in avoid)

        x, y = it["x"], it["y"]
        if not avoid or hits(x, y) <= 0.04 * w * h:
            continue
        spots = []
        for yy in range(int(TOP_SAFE + h / 2), int(BOTTOM_SAFE - h / 2), 40):
            for xx in (x, W / 2, 90 + w / 2, W - 90 - w / 2):
                if 60 + w / 2 <= xx <= W - 60 - w / 2:
                    spots.append((hits(xx, yy), abs(yy - y) + abs(xx - x) * 0.5, xx, yy))
        if not spots:
            continue
        best = min(spots)
        if best[0] < hits(x, y):
            it["x"], it["y"] = round(best[2]), round(best[3])
            moved.append(it.get("id"))
    return moved
