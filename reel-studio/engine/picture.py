"""Premium picture finish — every video gets it, before the colour grade.

Phone footage looks "cheap" mostly for technical reasons: a colour cast (yellow indoor light,
blue shade), too dark or blown out, flat contrast, soft focus. So first we CORRECT (measured per
video), then we FINISH (the same subtle polish pro editors put on everything):

  correct   white balance (grey-world, gentle), exposure, contrast for flat footage
  finish    fine luma sharpening, a whisper of film grain (hides compression, feels filmic),
            a soft vignette that pulls the eye to the centre
The grade/filter the user picked goes on top of this.
"""
import subprocess
import numpy as np

SW, SH = 108, 192


def analyse(source, ranges=None, samples=14):
    """Average colour/brightness of the kept footage (tiny frames, fast)."""
    ranges = ranges or [[0, 30]]
    total = sum(b - a for a, b in ranges)
    times, acc = [], 0.0
    for k in range(samples):
        target = total * (k + 0.5) / samples
        acc = 0.0
        for a, b in ranges:
            if acc + (b - a) >= target:
                times.append(a + target - acc)
                break
            acc += b - a
    px = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", source, "-frames:v", "1",
                              "-vf", f"scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        if len(raw) == SW * SH * 3:
            px.append(np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.float32) / 255)
    if not px:
        return None
    p = np.concatenate(px)
    luma = p @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mid = p[(luma > 0.15) & (luma < 0.9)]                 # ignore black and blown areas
    mean = mid.mean(0) if len(mid) else p.mean(0)
    return {"rgb": [round(float(x), 4) for x in mean], "luma": round(float(luma.mean()), 4),
            "contrast": round(float(luma.std()), 4), "clipped": round(float((luma > 0.98).mean()), 4)}


def plan(stats):
    """Correction settings + plain-words notes from the measured stats."""
    if not stats:
        return {"gains": [1, 1, 1], "gamma": 1.0, "contrast": 1.0, "notes": []}
    r, g, b = stats["rgb"]
    grey = (r + g + b) / 3
    strength = 0.55                                        # keep some of the scene's mood
    gains = [min(1.15, max(0.87, 1 + strength * (grey / max(c, 1e-3) - 1))) for c in (r, g, b)]
    notes = []
    if max(gains) - min(gains) > 0.04:
        cast = "warm/yellow" if b < r else "cool/blue" if b > r else "green"
        notes.append(f"{cast} colour cast balanced")
    gamma = 1.0
    if stats["luma"] < 0.36:
        gamma = min(1.35, 0.46 / max(stats["luma"], 0.1))
        notes.append("brightened (footage was dark)")
    elif stats["luma"] > 0.64:
        gamma = max(0.8, 0.56 / stats["luma"])
        notes.append("toned down (footage was bright)")
    contrast = 1.08 if stats["contrast"] < 0.17 else 1.0
    if contrast > 1:
        notes.append("contrast lifted (flat footage)")
    return {"gains": [round(x, 3) for x in gains], "gamma": round(gamma, 3), "contrast": contrast, "notes": notes}


def filters(pic, finish=True):
    """ffmpeg filter chain for the correction + premium finish."""
    parts = []
    if pic:
        rr, gg, bb = pic.get("gains", [1, 1, 1])
        if max(abs(rr - 1), abs(gg - 1), abs(bb - 1)) > 0.01:
            parts.append(f"colorchannelmixer=rr={rr}:gg={gg}:bb={bb}")
        if abs(pic.get("gamma", 1) - 1) > 0.01 or pic.get("contrast", 1) != 1:
            parts.append(f"eq=gamma={pic.get('gamma', 1)}:contrast={pic.get('contrast', 1)}")
    if finish:
        parts += ["unsharp=5:5:0.45:5:5:0", "noise=c0s=3:c0f=t", "vignette=angle=PI/7"]
    return ",".join(parts)
