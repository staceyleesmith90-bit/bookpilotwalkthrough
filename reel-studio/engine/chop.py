"""B-roll chopper + trial-reel batcher.

  python -m engine chop <file-or-folder> [--seconds 6]
      Long clips -> the best short b-roll clips (sharp, steady, well exposed, no scene cut
      inside), saved to inbox/broll-cuts/ with a numbered contact sheet for choosing.
  python -m engine trial <trial.json>
      One hook-on-b-roll reel per entry + a captions map (file -> post caption), ready to
      post as trial reels. trial.json (Claude writes it, the user approves the hooks):
      [{"clip": "inbox/broll-cuts/x-03.mp4", "hook": "POV: ...", "caption": "...", "pack": "brand"}]
Scoring is local maths on tiny frames — no Claude credits.
"""
import json, os, subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "inbox", "broll-cuts")


def _scores(source):
    from .director import frames, AFPS
    t, f = frames(source)
    if len(f) < 3:
        return t, np.zeros(len(f)), np.zeros(len(f)), AFPS
    lap = np.abs(f[:, 1:-1, 1:-1] * 4 - f[:, :-2, 1:-1] - f[:, 2:, 1:-1] - f[:, 1:-1, :-2] - f[:, 1:-1, 2:])
    sharp = lap.mean(axis=(1, 2))
    diff = np.r_[0, np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))]
    luma = f.mean(axis=(1, 2)) / 255
    expo = 1 - np.clip(np.abs(luma - 0.5) * 2.2, 0, 1)
    shake = np.clip(diff / (np.median(diff) * 3 + 1e-6), 0, 3)
    score = (sharp / (np.percentile(sharp, 90) + 1e-6)) * 0.5 + expo * 0.3 + (1 - np.clip(shake / 3, 0, 1)) * 0.2
    cut = diff > max(25.0, np.median(diff) * 6)          # scene changes
    return t, score, cut, AFPS


def best_windows(source, seconds=6.0, max_n=None):
    t, score, cut, fps = _scores(source)
    n = int(seconds * fps)
    if len(score) < n:
        return [(0.0, len(score) / fps, float(score.mean()) if len(score) else 0)]
    cands = []
    for s in range(0, len(score) - n, max(1, fps // 2)):
        if cut[s + 1:s + n].any():
            continue
        cands.append((float(score[s:s + n].mean()), s))
    cands.sort(reverse=True)
    picked = []
    for sc, s in cands:
        if all(abs(s - p) >= n for _, p in picked) and sc > 0.35:
            picked.append((sc, s))
        if max_n and len(picked) >= max_n:
            break
    return sorted((s / fps, s / fps + seconds, sc) for sc, s in picked)


def chop(paths, seconds=6.0, max_per_clip=None):
    os.makedirs(OUT, exist_ok=True)
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith((".mp4", ".mov", ".m4v"))]
        else:
            files.append(p)
    made = []
    for src in files:
        base = os.path.splitext(os.path.basename(src))[0]
        for k, (a, b, sc) in enumerate(best_windows(src, seconds, max_per_clip), 1):
            out = os.path.join(OUT, f"{base}-{k:02d}.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", src,
                            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", out], check=True)
            made.append({"file": os.path.relpath(out, ROOT), "from": os.path.basename(src), "at": round(a, 1),
                         "score": round(sc, 2)})
    if made:
        sheet(made, os.path.join(OUT, "contact-sheet.jpg"))
    return made


def sheet(clips, out, w=180):
    """Numbered contact sheet (middle frame of each clip) so Claude/the user can pick."""
    from PIL import Image, ImageDraw
    tiles = []
    for i, c in enumerate(clips, 1):
        png = out + f".{i}.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "3", "-i", os.path.join(ROOT, c["file"]),
                        "-frames:v", "1", "-vf", f"scale={w}:-1", png])
        if os.path.exists(png):
            im = Image.open(png).convert("RGB")
            ImageDraw.Draw(im).rectangle((0, 0, 44, 30), fill="black")
            ImageDraw.Draw(im).text((8, 6), str(i), fill="white")
            tiles.append(im)
            os.remove(png)
    if not tiles:
        return None
    cols = min(6, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    th = tiles[0].height
    board = Image.new("RGB", (cols * (w + 6), rows * (th + 6)), "white")
    for i, im in enumerate(tiles):
        board.paste(im, ((i % cols) * (w + 6), (i // cols) * (th + 6)))
    board.save(out)
    return out


def trial(spec_path):
    """Render one hook-on-b-roll reel per entry and write the captions map."""
    from . import project
    spec = json.load(open(spec_path))
    out_dir = os.path.join(ROOT, "out", "trial-reels")
    os.makedirs(out_dir, exist_ok=True)
    lines = ["# Trial reels: file -> caption\n"]
    for i, e in enumerate(spec, 1):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    os.path.join(ROOT, e["clip"])], capture_output=True, text=True).stdout or 6)
        slug = project.new(None, f"trial-{i:02d}")
        plan = {"format": "faceless", "pack": e.get("pack", "brand"), "captions": "off",
                "beats": [{"text": e["hook"], "dur": round(dur, 2), "do": [f"broll:{e['clip']}", f"hook:{e['hook']}"]}]}
        if e.get("music"):
            plan["music"] = {"file": e["music"], "gain": 0.3}
        project.save(slug, "plan.json", plan)
        project.build_timeline(slug)
        final = project.do_render(slug)
        name = f"trial-{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-c", "copy", os.path.join(out_dir, name)])
        lines.append(f"## {name}\nHook: {e['hook']}\n\n{e.get('caption', '')}\n")
    open(os.path.join(out_dir, "captions.md"), "w").write("\n".join(lines))
    return out_dir
