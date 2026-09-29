"""Inspiration reels: learn the style of reels the user loves.

    python -m engine inspire <url-or-file> [--name cozy-coffee]

Everything is measured locally (no Claude usage): cut pacing, colour palette, brightness/
contrast/saturation (-> suggested grade), speaking pace and the hook's words. It saves ONE
contact sheet of 6 frames — the only image Claude needs to look at — plus a profile JSON in
brand/inspiration/. Claude then fills in what only eyes can judge (caption style, text
treatment, sticker style) and the planner uses the profile when editing their reels.
"""
import json, os, re, subprocess, tempfile
from PIL import Image, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSP = os.path.join(ROOT, "brand", "inspiration")


def fetch(source, work):
    if os.path.exists(source):
        return source
    out = os.path.join(work, "ref.%(ext)s")
    subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "mp4/best", "-o", out, source], check=True)
    for f in os.listdir(work):
        if f.startswith("ref."):
            return os.path.join(work, f)
    raise RuntimeError("download failed")


def scene_cuts(path, threshold=0.22):
    r = subprocess.run(["ffmpeg", "-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def sample_frames(path, dur, n, work, width=270):
    frames = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        p = os.path.join(work, f"f{i}.jpg")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1",
                        "-vf", f"scale={width}:-2", p])
        if os.path.exists(p):
            frames.append((t, p))
    return frames


def look_stats(frames):
    bright, contrast, sat, warm = [], [], [], []
    for _, p in frames:
        im = Image.open(p).convert("RGB")
        hsv = im.convert("HSV")
        st = ImageStat.Stat(im.convert("L"))
        bright.append(st.mean[0] / 255)
        contrast.append(st.stddev[0] / 128)
        sat.append(ImageStat.Stat(hsv).mean[1] / 255)
        r, g, b = ImageStat.Stat(im).mean
        warm.append((r - b) / 255)
    avg = lambda xs: sum(xs) / max(len(xs), 1)
    return {"brightness": round(avg(bright), 2), "contrast": round(avg(contrast), 2),
            "saturation": round(avg(sat), 2), "warmth": round(avg(warm), 2)}


def suggest_grade(s):
    if s["saturation"] < 0.08:
        return "bw-classic"
    if s["warmth"] > 0.12 and s["contrast"] < 0.45:
        return "warm-film"
    if s["warmth"] > 0.12:
        return "golden-hour"
    if s["brightness"] < 0.35:
        return "moody"
    if s["saturation"] > 0.45:
        return "vivid"
    if s["contrast"] < 0.38:
        return "soft-matte"
    if s["warmth"] < -0.03:
        return "cool-crisp"
    return "clean-bright"


def sound_density(path):
    """Sound events per second (spectral-flux onsets): ~0.5 calm, 1.5 lively, 2.5+ edit-heavy."""
    import numpy as np, subprocess as sp
    raw = sp.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                 capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(a) < 16000:
        return 0.0
    hop, win = 256, 1024
    fr = np.lib.stride_tricks.sliding_window_view(a, win)[::hop] * np.hanning(win)
    spec = np.abs(np.fft.rfft(fr, axis=1))
    flux = np.maximum(np.diff(spec, axis=0), 0).sum(1)
    thr = np.median(flux) * 4
    on, last = 0, -1.0
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            t = i * hop / 16000
            if t - last > 0.08:
                on += 1
                last = t
    return round(on / (len(a) / 16000), 2)


def plan_settings(profile):
    """Edit settings that make a reel feel like the reference (Claude refines after one look)."""
    notes = profile.get("claude_notes") or {}
    feel = profile.get("pacing", {}).get("feel", "medium")
    dens = profile.get("sound", {}).get("events_per_sec", 1.0)
    wps = profile.get("speech", {}).get("words_per_sec", 2.5)
    fmt = (notes.get("format") or "").lower()
    if "vlog" in fmt or "photo dump" in fmt or (not fmt and wps < 1.5):
        # aesthetic vlog / GRWM: music + many short clips, a quiet held label, no word-by-word captions
        return {"format": "vlog", "speed": 1.0, "captions": notes.get("caption_style") or "off",
                "grade": profile.get("look", {}).get("suggested_grade"), "title_template": "tag",
                "sound_kit": "playful", "framed": "off",
                "beat_seconds": max(0.5, min(1.2, profile.get("pacing", {}).get("avg_shot_s", 0.8)))}
    return {
        "speed": 1.12 if (feel == "fast" or wps > 3.2) else 1.0,
        "captions": notes.get("caption_style") or ("kinetic" if feel != "slow" else "duo"),
        "grade": profile.get("look", {}).get("suggested_grade"),
        "sound_kit": "digital" if dens > 2.2 else "playful" if dens > 1.4 else "luxe",
        "framed": "auto" if feel != "slow" else "off",
    }


def analyse(source, name=None, transcribe_audio=True):
    from .brand import from_image
    from .transcribe import probe_duration, transcribe
    work = tempfile.mkdtemp()
    path = fetch(source, work)
    dur = probe_duration(path)
    cuts = scene_cuts(path)
    frames = sample_frames(path, dur, 12, work)
    fh = max(Image.open(p).height for _, p in frames)
    sheet = Image.new("RGB", (270 * 6, fh * 2))
    for i, (_, p) in enumerate(frames):
        sheet.paste(Image.open(p), ((i % 6) * 270, (i // 6) * fh))
    stats = look_stats(frames)
    name = name or re.sub(r"[^a-z0-9]+", "-", os.path.basename(source).lower())[:40].strip("-") or "reference"
    os.makedirs(INSP, exist_ok=True)
    sheet_path = os.path.join(INSP, f"{name}.jpg")
    sheet.save(sheet_path, quality=85)
    profile = {
        "name": name, "source": source, "duration": round(dur, 1),
        "pacing": {"cuts": len(cuts), "cuts_per_min": round(len(cuts) / dur * 60, 1) if dur else 0,
                   "avg_shot_s": round(dur / (len(cuts) + 1), 2),
                   "feel": "fast" if len(cuts) / max(dur, 1) > 0.5 else "medium" if len(cuts) / max(dur, 1) > 0.2 else "slow"},
        "look": dict(stats, suggested_grade=suggest_grade(stats)),
        "sound": {"events_per_sec": sound_density(path)},
        "palette": from_image(sheet_path, 6),
        "contact_sheet": os.path.relpath(sheet_path, ROOT),
        # filled in by Claude after one look at the contact sheet:
        "claude_notes": {"format": None, "caption_style": None, "text_treatments": None,
                         "sticker_style": None, "energy": None, "what_to_borrow": None},
    }
    if transcribe_audio:
        t = transcribe(path)
        words = t["words"]
        if words:
            speech = words[-1]["end"] - words[0]["start"]
            profile["speech"] = {"words_per_sec": round(len(words) / max(speech, 0.1), 2),
                                 "hook": " ".join(w["w"] for w in words if w["start"] < 3.0)}
    profile["plan_settings"] = plan_settings(profile)
    json.dump(profile, open(os.path.join(INSP, f"{name}.json"), "w"), indent=2)
    return profile


def load_all():
    if not os.path.isdir(INSP):
        return []
    return [json.load(open(os.path.join(INSP, f))) for f in sorted(os.listdir(INSP)) if f.endswith(".json")]
