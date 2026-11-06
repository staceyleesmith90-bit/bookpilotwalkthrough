"""Footage from Google Drive (or any folder): big videos never have to be dropped into a chat.

    python -m engine footage <project> <drive folder link | drive file link | local folder | file>
    python -m engine footage <project>            just re-scan what's already in projects/<p>/source/

1. Fetch: a Drive link shared "anyone with the link" downloads straight into projects/<p>/source/ (no Google
   account needed here; folders up to 50 files). On a computer with the Google Drive app, a synced folder
   path works too (nothing is downloaded, it is copied). Files already there are skipped.
2. Scan: every clip gets its length, whether it's iPhone HDR, and 6 frames; ALL clips land on one picture
   (renders/footage-sheet.jpg, one row per clip, each frame labelled with its second) plus footage.json.
   Claude looks at that one image (cheap) and picks the moments: "broll:<file>@<second>" in the plan.
"""
import json, os, re, shutil, subprocess
from PIL import Image, ImageDraw

from . import project
from .textfit import load_font

VIDEO = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")
PHOTO = (".jpg", ".jpeg", ".png", ".heic", ".webp")
FRAMES = 6
_ID = re.compile(r"(?:/folders/|/file/d/|[?&]id=)([A-Za-z0-9_-]{20,})")


def _is_media(name):
    return name.lower().endswith(VIDEO + PHOTO)


def fetch(slug, source, dest=None):
    """Bring the media from `source` into projects/<slug>/source/ (or `dest`, e.g. the Inbox). Returns [new names]."""
    dest = dest or project.path(slug, "source")
    os.makedirs(dest, exist_ok=True)
    got = []
    if os.path.exists(source):                                      # a local / synced folder or one file
        files = ([os.path.join(source, f) for f in sorted(os.listdir(source))] if os.path.isdir(source) else [source])
        for f in files:
            if _is_media(f) and not os.path.exists(os.path.join(dest, os.path.basename(f))):
                shutil.copy2(f, dest)
                got.append(os.path.basename(f))
        return got
    m = _ID.search(source)
    if not m:
        raise SystemExit("That isn't a Google Drive link or a folder on this computer.")
    import gdown
    fid = m.group(1)
    if "/folders/" in source:
        listing = gdown.download_folder(id=fid, output=dest, quiet=True, skip_download=True) or []
        seen = set()
        for f in listing:
            name = os.path.basename(f.path)
            if not _is_media(name) or name in seen:                 # Drive keeps duplicates of the same name
                continue
            seen.add(name)
            out = os.path.join(dest, name)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                continue
            gdown.download(id=f.id, output=out, quiet=True)
            got.append(name)
    else:
        out = gdown.download(id=fid, output=dest + os.sep, quiet=True)
        if out:
            got.append(os.path.basename(out))
    if not got and "/folders/" in source and not os.listdir(dest):
        raise SystemExit("Couldn't open that Drive folder — set it to 'Anyone with the link can view' and try again.")
    return got


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,color_transfer:stream_side_data=rotation:format=duration", "-of", "json", path],
                         capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except Exception:
        return {}
    st = (d.get("streams") or [{}])[0]
    rot = next((abs(int(s.get("rotation", 0))) for s in st.get("side_data_list", []) if "rotation" in s), 0)
    w, h = st.get("width", 0), st.get("height", 0)
    if rot in (90, 270):
        w, h = h, w
    return {"duration": round(float((d.get("format") or {}).get("duration", 0) or 0), 2), "w": w, "h": h,
            "hdr": st.get("color_transfer") in ("arib-std-b67", "smpte2084")}


def _frame(path, t, hdr, w=180):
    vf = (f"zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,"
          f"format=yuv420p,scale={w}:-2" if hdr else f"scale={w}:-2")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", vf,
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    try:
        import io
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return None


def _sharp(im):
    """Rough 'is it in focus / not too dark' score (0-1) so blurry frames can be skipped."""
    import numpy as np, cv2
    g = np.asarray(im.convert("L"), np.float32)
    return round(float(min(cv2.Laplacian(g, cv2.CV_32F).var() / 400.0, 1.0) * min(g.mean() / 60.0, 1.0)), 2)


def scan(slug):
    src = project.path(slug, "source")
    files = sorted(f for f in os.listdir(src) if _is_media(f)) if os.path.isdir(src) else []
    clips, rows = [], []
    for n, f in enumerate(files, 1):
        p = os.path.join(src, f)
        rel = os.path.relpath(p, project.ROOT)
        if f.lower().endswith(PHOTO):
            try:
                from PIL import ImageOps
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                im.thumbnail((180, 320))
                clips.append({"n": n, "file": rel, "kind": "photo"})
                rows.append((n, f, "photo", [(None, im)]))
            except Exception:
                pass
            continue
        info = _probe(p)
        d = info.get("duration", 0)
        times = [round(d * (i + 0.5) / FRAMES, 1) for i in range(FRAMES)] if d else [0]
        shots = [(t, _frame(p, t, info.get("hdr"))) for t in times]
        shots = [(t, im) for t, im in shots if im]
        clips.append(dict(info, n=n, file=rel, kind="video", frames=[{"t": t, "sharp": _sharp(im)} for t, im in shots]))
        rows.append((n, f, f"{d:.1f}s" + (" HDR" if info.get("hdr") else ""), shots))
    project.save(slug, "footage.json", {"clips": clips})
    sheet = _sheet(slug, rows) if rows else None
    return clips, sheet


def _sheet(slug, rows):
    fw, fh = 150, 266
    lab = 26
    W = 16 + 200 + FRAMES * (fw + 6)
    H = 16 + len(rows) * (fh + lab + 14)
    out = Image.new("RGB", (W, H), (243, 245, 251))
    d = ImageDraw.Draw(out)
    root = project.ROOT
    fb = load_font(os.path.join(root, "library", "fonts", "Inter-Variable.ttf"), 15, 700)
    fs = load_font(os.path.join(root, "library", "fonts", "Inter-Variable.ttf"), 12, 500)
    y = 16
    for n, name, info, shots in rows:
        d.text((16, y + 4), f"#{n}", font=fb, fill=(14, 22, 56))
        d.text((16, y + 26), name[:22], font=fs, fill=(14, 22, 56))
        d.text((16, y + 44), info, font=fs, fill=(95, 104, 137))
        for i, (t, im) in enumerate(shots):
            x = 216 + i * (fw + 6)
            th = im.copy()
            th.thumbnail((fw, fh))
            out.paste(th, (x + (fw - th.width) // 2, y + (fh - th.height) // 2))
            if t is not None:
                d.rounded_rectangle([x + 4, y + fh - 22, x + 52, y + fh - 4], 6, fill=(14, 22, 56))
                d.text((x + 9, y + fh - 20), f"@{t}", font=fs, fill=(255, 255, 255))
        y += fh + lab + 14
    p = project.path(slug, "renders", "footage-sheet.jpg")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    out.save(p, quality=82)
    return p
