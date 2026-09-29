"""Quality check — so users say "wow", not "why isn't it…?".

Runs automatically:
  • after the style plan (fix_timeline): finds and FIXES the things people complain about
      - nothing moving for too long        -> adds a slow push-in / emphasis bump
      - no visual in the first 1.5 s (hook) -> adds a punch-in at the start
      - too many stickers at once           -> drops the extra automatic ones
      - things covering a face              -> moves them
      - no captions on a talking video      -> turns captions on
  • after rendering (check_render): loudness, peaks, and a contact sheet of the finished reel
    (renders/check.jpg) that Claude looks at before showing the user.
Every finding comes back as a plain-words line for the "what I did" summary.
"""
import json, os, subprocess

W, H = 1080, 1920
MAX_STILL = 5.0          # seconds without any camera move/new graphic before it feels static
HOOK = 1.5               # something must happen in the first 1.5 s


def _motion_spans(tl):
    spans = [(z["start"], z["end"]) for z in tl.get("zooms", [])]
    spans += [(i["start"], min(i["end"], i["start"] + 1.2)) for i in tl.get("items", []) if i.get("role") != "logo"]
    spans += [(t["t"] - 0.2, t["t"] + 0.2) for t in tl.get("transitions", [])]
    return sorted(spans)


def _gaps(tl):
    """Stretches with no camera move and no new graphic."""
    dur, out, t = tl["duration"], [], 0.0
    for a, b in _motion_spans(tl):
        if a - t > MAX_STILL:
            out.append((t, a))
        t = max(t, b)
    if dur - t > MAX_STILL:
        out.append((t, dur))
    return out


def _overlap(r1, r2):
    return max(0, min(r1[2], r2[2]) - max(r1[0], r2[0])) * max(0, min(r1[3], r2[3]) - max(r1[1], r2[1]))


def fix_timeline(tl, faces_at=None, pack=None):
    """Check + auto-fix a timeline in place. Returns plain-words notes."""
    notes = []
    talking = tl.get("format") == "talking-head" or bool(tl.get("source"))
    # 1. static stretches -> slow push-in (or a gentle bump for short ones)
    added = 0
    for a, b in _gaps(tl):
        t = a
        while b - t > MAX_STILL:
            end = min(b, t + 4.5)
            tl.setdefault("zooms", []).append({"start": round(t + 0.3, 3), "end": round(end, 3), "type": "push",
                                               "scale": 1.1, "auto": True, "qa": True})
            added += 1
            t = end
    if added:
        notes.append(f"added {added} slow push-in{'s' if added > 1 else ''} so the video never sits still")
    # 2. hook: movement or a graphic in the first 1.5 s
    if not any(s < HOOK for s, _ in _motion_spans(tl)):
        tl.setdefault("zooms", []).append({"start": 0.0, "end": 1.2, "type": "whip", "scale": 1.12, "auto": True, "qa": True})
        notes.append("added a zoom in the first second to hook viewers")
    # 3. clutter: no more than 2 automatic stickers on screen at once, max ~1 per 4 s
    stickers = sorted([i for i in tl.get("items", []) if i["type"] in ("sticker", "badge", "callout")
                       and i.get("role") not in ("logo", "cta")], key=lambda i: i["start"])
    dropped = 0
    for i in stickers:
        live = [j for j in tl["items"] if j is not i and j["type"] in ("sticker", "badge", "callout")
                and j["start"] < i["end"] and i["start"] < j["end"]]
        if len(live) >= 2 and i.get("auto_pick"):
            tl["items"].remove(i)
            dropped += 1
    if dropped:
        notes.append(f"removed {dropped} extra sticker{'s' if dropped > 1 else ''} to keep it clean")
    # 4. faces: nothing may cover a face
    moved = 0
    if faces_at:
        from .render import item_image
        for i in tl.get("items", []):
            if i["type"] not in ("sticker", "badge") or "x" not in i:   # callouts point AT things on purpose
                continue
            faces = faces_at(i["start"] + 0.3) or []
            try:
                im = item_image(i, pack) if pack else None
            except Exception:
                im = None
            w, h = ((im.width, im.height) if im else (300, 300))
            w, h = w * i.get("scale", 1.0) * 0.8, h * i.get("scale", 1.0) * 0.8     # ignore the shadow margin
            box = (i["x"] - w / 2, i["y"] - h / 2, i["x"] + w / 2, i["y"] + h / 2)
            if any(_overlap(box, f) > 0.15 * w * h for f in faces):
                top = min(f[1] for f in faces)
                if top - 220 > h:                       # room above the faces: the calm top band
                    i["y"] = max(240 + h / 2, top - h / 2 - 30)
                else:                                   # else just below the lowest face, above captions
                    i["y"] = min(1120 - h / 2, max(f[3] for f in faces) + h / 2 + 30)
                moved += 1
        if moved:
            notes.append(f"moved {moved} sticker{'s' if moved > 1 else ''} off a face")
    # 5. graphics never sit on top of each other (sticker vs text vs badge at the same moment)
    if pack:
        from .render import item_image
        placed, nudged = [], 0
        for i in sorted([x for x in tl.get("items", []) if x["type"] in ("sticker", "badge", "callout", "text")
                         and x.get("role") != "logo" and "x" in x], key=lambda x: x["start"]):
            try:
                im = item_image(i, pack)
            except Exception:
                im = None
            if im is None:
                continue
            k = i.get("scale", 1.0) * 0.85
            w, h = im.width * k, im.height * k
            def box():
                return (i["x"] - w / 2, i["y"] - h / 2, i["x"] + w / 2, i["y"] + h / 2)
            for _ in range(12):
                hit = next((b for s0, e0, b in placed if s0 < i["end"] and i["start"] < e0 and _overlap(box(), b) > 0), None)
                if not hit:
                    break
                # move the newcomer below (or above) the thing it hits, inside the safe zone
                below = hit[3] + h / 2 + 20
                i["y"] = below if below + h / 2 < 1450 else max(240 + h / 2, hit[1] - h / 2 - 20)
                nudged += 1
            placed.append((i["start"], i["end"], box()))
        if nudged:
            notes.append("separated graphics that were overlapping")
    # 6. captions on talking videos
    if talking and tl.get("captions", {}).get("style", "off") == "off" and tl.get("captions", {}).get("words"):
        tl["captions"]["style"] = "pop"
        notes.append("turned captions on (most people watch muted)")
    tl.setdefault("qa", {})["plan_notes"] = notes
    return notes


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    lufs = peak = None
    for line in r.splitlines()[::-1]:
        s = line.strip()
        if s.startswith("I:") and lufs is None:
            lufs = float(s.split()[1])
        if s.startswith("Peak:") and peak is None:
            peak = float(s.split()[1])
    return lufs, peak


def contact_sheet(video, out, n=12, width=180):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 0)
    if not dur:
        return None
    fps = n / dur
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vf",
                    f"fps={fps:.4f},scale={width}:-1,tile={n // 2}x2:padding=4:color=white", "-frames:v", "1", out])
    return out if os.path.exists(out) else None


def voice_check(video, start=None, length=8):
    """Listen to the finished file: is there an audio track, and can speech be heard in it?
    True / False, or None when there's nothing to check (e.g. a music-only reel)."""
    import tempfile
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    if not r.stdout.strip():
        return False
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout.strip() or 0)
    start = dur * 0.3 if start is None else start
    wav = os.path.join(tempfile.mkdtemp(), "v.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", str(length), "-i", video,
                    "-vn", "-ac", "1", "-ar", "16000", wav])
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("tiny", compute_type="int8").transcribe(wav)
        return len(" ".join(s.text for s in segs).split()) >= 3
    except Exception:
        return None


def check_render(video, tl=None):
    """After rendering: loudness/peaks + contact sheet. Returns (notes, problems)."""
    notes, problems = [], []
    lufs, peak = loudness(video)
    if lufs is not None:
        if abs(lufs + 14) <= 2:
            notes.append(f"loudness {lufs:.0f} LUFS (right for TikTok/Instagram)")
        else:
            problems.append(f"loudness {lufs:.0f} LUFS (should be about -14)")
    if peak is not None and peak > -0.5:
        problems.append(f"audio peaks at {peak:.1f} dBFS (may distort)")
    heard = voice_check(video)
    if heard is True:
        notes.append("voice audible (checked by listening to the finished file)")
    elif heard is False:
        problems.append("no voice heard in the finished video — audio is silent or missing")
    sheet = contact_sheet(video, os.path.join(os.path.dirname(video), "check.jpg"))
    if sheet:
        notes.append(f"contact sheet for a final look: {os.path.relpath(sheet)}")
    return notes, problems


def summary(tl):
    """Everything done to the video, in plain words — the 'what I did' list for the user."""
    lines = []
    if tl.get("stabilized"):
        lines.append("steadied the shaky footage")
    z = tl.get("zooms", [])
    face = sum(1 for x in z if x.get("cx"))
    push = sum(1 for x in z if x.get("type") == "push")
    bump = sum(1 for x in z if x.get("type") == "pulse")
    if face:
        lines.append(f"{face} punch-ins framed on your face at the cuts")
    if push:
        lines.append(f"{push} slow push-ins on product shots / quiet moments")
    if bump:
        lines.append(f"{bump} emphasis bumps on key words")
    if tl.get("transitions"):
        lines.append(f"{len(tl['transitions'])} transition{'s' if len(tl['transitions']) > 1 else ''} where the angle changes")
    if tl.get("picture", {}).get("notes"):
        lines.append("picture: " + ", ".join(tl["picture"]["notes"]))
    lines.append("premium finish: fine sharpening, film grain, soft vignette")
    if tl.get("audio", {}).get("noise"):
        from .audiocheck import describe
        lines.append("sound: " + describe(tl["audio"]["noise"]))
    lines += tl.get("qa", {}).get("plan_notes", [])
    return lines
