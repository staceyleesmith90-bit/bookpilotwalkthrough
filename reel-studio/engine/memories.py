"""Memories: the day's photos and clips → a keepsake video for your camera roll (posting optional).

For moms with 30 photos of the kids a day, and anyone who loves sharing without being "an influencer".

    python -m engine memories <project> [<google drive link | folder>] --name "Sandbox day" --story "line; line; line"

1. Brings the photos/videos in (Drive link or folder → projects/<p>/source/, or what's already there).
2. Picks the keepers: puts them in the order they were taken (photo date / video date), drops near-identical
   burst shots (keeps the sharpest), skips blurry or very dark ones, and keeps at most ~16.
3. Writes a gentle plan: an opener (date + title), each photo with a slow zoom or pan, short moments from the
   videos (sound off by default — it's usually mom talking), the story lines as handwritten labels, a scrapbook
   page in the middle, a soft ending, calm music and a cover. Then: storyboard → render → save to camera roll.
The story lines come from what the person said or voice-noted ("she pulled the cat's tail, then fell asleep"):
Claude turns that into 3–8 short, warm lines and passes them with --story.
"""
import datetime as _dt
import json, os, subprocess

import numpy as np
from PIL import Image, ImageOps

from . import project

ROOT = project.ROOT
PHOTO = (".jpg", ".jpeg", ".png", ".heic", ".webp")
VIDEO = (".mp4", ".mov", ".m4v")
MAX_ITEMS = 16


def _taken(path):
    """When it was taken (datetime) — photo EXIF, video creation time, else the file time."""
    low = path.lower()
    try:
        if low.endswith(PHOTO):
            ex = Image.open(path).getexif()
            v = ex.get(36867) or ex.get_ifd(0x8769).get(36867) or ex.get(306)
            if v:
                return _dt.datetime.strptime(str(v)[:19], "%Y:%m:%d %H:%M:%S")
        else:
            tags = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", path],
                                             capture_output=True, text=True).stdout or "{}").get("format", {}).get("tags", {})
            local = tags.get("com.apple.quicktime.creationdate")        # iPhone: the phone's own local time
            if local:
                return _dt.datetime.fromisoformat(local[:19])
            utc = tags.get("creation_time")                              # others: UTC → this computer's time zone
            if utc:
                return _dt.datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except Exception:
        pass
    return _dt.datetime.fromtimestamp(os.path.getmtime(path))


def _thumb(path):
    if path.lower().endswith(PHOTO):
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    else:
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                 capture_output=True, text=True).stdout.strip() or 0)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{d / 2:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=320:-2",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        import io
        im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((320, 320))
    return im


def _dhash(im):
    g = np.asarray(im.convert("L").resize((9, 8), Image.BILINEAR), np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def _quality(im):
    import cv2
    g = np.asarray(im.convert("L"), np.float32)
    sharp = min(cv2.Laplacian(g, cv2.CV_32F).var() / 300.0, 1.0)
    light = min(g.mean() / 70.0, 1.0)
    return float(sharp * light)


def pick(paths, max_items=MAX_ITEMS):
    """[(path, taken, quality)] — in time order, bursts collapsed to their sharpest shot, the weakest dropped."""
    items = []
    for p in paths:
        try:
            th = _thumb(p)
        except Exception:
            continue
        items.append({"path": p, "taken": _taken(p), "q": _quality(th), "h": _dhash(th),
                      "video": p.lower().endswith(VIDEO)})
    items.sort(key=lambda x: x["taken"])
    kept = []
    for it in items:                                   # near-identical to the last keeper → keep the better one
        if kept and not it["video"] and not kept[-1]["video"] and int((it["h"] != kept[-1]["h"]).sum()) <= 10:
            if it["q"] > kept[-1]["q"]:
                kept[-1] = it
            continue
        kept.append(it)
    kept = [k for k in kept if k["video"] or k["q"] > 0.04] or kept
    if len(kept) > max_items:                          # too many: keep the best, still in time order
        best = sorted(kept, key=lambda k: -k["q"] - (0.2 if k["video"] else 0))[:max_items]
        kept = [k for k in kept if k in best]
    return [(k["path"], k["taken"], round(k["q"], 3)) for k in kept]


def _nice_date(d):
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


def build(slug, name, story=None, keep_sound=False, max_items=MAX_ITEMS):
    src = project.path(slug, "source")
    files = [os.path.join(src, f) for f in sorted(os.listdir(src))
             if f.lower().endswith(PHOTO + VIDEO) and ".cutout." not in f] if os.path.isdir(src) else []
    chosen = pick(files, max_items)
    if not chosen:
        raise ValueError("No photos or videos found — add them first (a folder or a Google Drive link).")
    lines = [s.strip() for s in (story or []) if s.strip()]
    rel = lambda p: os.path.relpath(p, ROOT)
    first = chosen[0][1]
    best = max(chosen, key=lambda c: c[2] if not c[0].lower().endswith(VIDEO) else -1)
    moves = ["in", "left", "out", "right"]
    beats = [{"text": "", "dur": 3.0, "move": "in", "do": [f"broll:{rel(best[0])}", "scene:collage"],
              "scene": {"overlay": True, "kicker": _nice_date(first), "title": name, "title_y": 0.8, "title_px": 120,
                        "ink": "#FFFDF8"}}]
    li = 0
    body = [c for c in chosen if c[0] != best[0]] or chosen
    mid = len(body) // 2
    for i, (p, taken, q) in enumerate(body):
        if i == mid and len([c for c in body if not c[0].lower().endswith(VIDEO)]) >= 4:
            photos = [rel(c[0]) for c in body if not c[0].lower().endswith(VIDEO)][:5]
            beats.append({"text": "", "dur": 3.2, "do": [f"broll:{photos[0]}", "scrapbook:page"],
                          "scrapbook": {"photos": photos}})
        if p.lower().endswith(VIDEO):
            beat = {"text": "", "dur": 2.6, "do": [f"broll:{rel(p)}"]}
        else:
            beat = {"text": "", "dur": 2.0, "move": moves[i % 4], "do": [f"broll:{rel(p)}"]}
        if li < len(lines) and (i % max(1, len(body) // max(len(lines), 1)) == 0):
            beat["do"].append("scene:collage")
            beat["scene"] = {"overlay": True, "labels": [{"text": lines[li], "x": 0.5, "y": 0.86 if i % 2 else 0.13,
                                                          "rot": -2 if i % 2 else 2, "at": 0.2, "px": 46}]}
            li += 1
        beats.append(beat)
    ending = lines[li] if li < len(lines) else "a day to remember"
    beats.append({"text": "", "dur": 3.0, "move": "out", "transition": "dip-white",
                  "do": [f"broll:{rel(best[0])}", "scene:collage"],
                  "scene": {"overlay": True, "kicker": name, "title": ending, "title_y": 0.8, "title_px": 96, "ink": "#FFFDF8"}})
    plan = {"format": "faceless", "pack": "brand", "look": "playful", "captions": "off", "auto_stickers": False,
            "auto_transitions": False, "logo": False, "sound": "modern", "broll_sound": 0.9 if keep_sound else 0,
            "music": {"gain": 0.6}, "end_card": {"enabled": False}, "transition": "dip-white",
            "cover": {"kicker": _nice_date(first), "title": name, "photo": rel(best[0]), "y": 0.78},
            "beats": beats, "memories": {"count": len(chosen), "from": len(files)}}
    from . import musicgen
    dur = sum(b["dur"] for b in beats) + 2
    st, _ = musicgen.compose({"mood": ["dreamy"], "genre": ["soft piano"], "tempo": "76", "energy": "steady"}, dur, seed=len(slug))
    mp = project.path(slug, "music", "bed.wav")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    musicgen.write(mp, st)
    plan["music"]["file"] = rel(mp)
    project.save(slug, "plan.json", plan)
    return plan, chosen, len(files)
