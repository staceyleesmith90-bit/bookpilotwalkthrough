"""Cut on the beat: photo, brand and memory reels change picture exactly on a beat of the music.

The beat grid comes from librosa (ISC licence) and is cached per music file. Talking reels are never touched —
their cuts follow the voice.
"""
import hashlib, json, os

from . import project

MIN_DUR = 1.0          # never make a moment shorter than this
MAX_MOVE = 0.45        # never move a cut further than this (keeps the plan's pacing)


def beats(music_path):
    """Beat times in seconds (cached next to the app in out/beats/)."""
    st = os.stat(music_path)
    key = hashlib.md5(f"{os.path.abspath(music_path)}|{st.st_size}|{st.st_mtime}".encode()).hexdigest()[:12]
    cache = os.path.join(project.ROOT, "out", "beats", key + ".json")
    if os.path.exists(cache):
        return json.load(open(cache))
    import librosa
    y, sr = librosa.load(music_path, sr=22050, mono=True, duration=240)
    _, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    times = [round(float(t), 3) for t in librosa.frames_to_time(frames, sr=sr)]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(times, open(cache, "w"))
    return times


def snap(plan, grid):
    """A copy of the plan whose moment lengths put every cut on the nearest beat (within MAX_MOVE)."""
    bts = plan.get("beats") or []
    if len(bts) < 2 or len(grid) < 4:
        return plan
    out, t, cut_prev = [], 0.0, 0.0
    for i, b in enumerate(bts):
        dur = float(b.get("dur", 3) or 3)
        t += dur
        if i < len(bts) - 1:
            near = min(grid, key=lambda g: abs(g - t))
            if abs(near - t) <= MAX_MOVE and near - cut_prev >= MIN_DUR:
                t = near
        out.append(dict(b, dur=round(t - cut_prev, 3)))
        cut_prev = t
    return dict(plan, beats=out, beat_synced=True)


def apply(plan):
    """Snap a faceless plan to its music's beat, if it has a music file and beat sync isn't switched off."""
    if plan.get("beat_sync") is False or plan.get("format") not in (None, "faceless", "memories", "brand", "photos"):
        return plan
    mu = plan.get("music") or {}
    f = mu.get("file")
    if not f or mu.get("none"):
        return plan
    path = f if os.path.isabs(f) else os.path.join(project.ROOT, f)
    if not os.path.exists(path):
        return plan
    try:
        return snap(plan, beats(path))
    except Exception:
        return plan
