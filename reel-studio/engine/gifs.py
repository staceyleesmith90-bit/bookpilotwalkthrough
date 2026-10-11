"""GIF drop-ins — moving pictures on top of the reel, and GIFs made from your own footage.

Drop-in: a timeline item {"type": "gif", "file": "brand/gifs/wave.webp", "x", "y", "size", "start", "end"}
plays (and loops) in the finished reel, in the editor, and arrives in CapCut as a real moving clip.

Make your own:
    python -m engine gif-make <video> --start 3.2 --end 5.0 [--name wave] [--cutout]
  --cutout lifts you out of the background (a moving sticker of yourself, transparent .webp);
  without it you get a classic rounded GIF clip. Saved in brand/gifs/ so every reel of this brand can use it.
    python -m engine gifs        -> the brand's GIFs (and any GIFs in the inbox)
"""
import os, re, subprocess, tempfile

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIFS = os.path.join(ROOT, "brand", "gifs")
EXTS = (".gif", ".webp", ".apng", ".png")
_CACHE = {}


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def frames(path, px=360):
    """[(RGBA frame, seconds)] with the longest side = px. A still picture is one frame."""
    key = (path, px, os.path.getmtime(_abs(path)) if os.path.exists(_abs(path)) else 0)
    if key in _CACHE:
        return _CACHE[key]
    im = Image.open(_abs(path))
    out = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        f = im.convert("RGBA")
        k = px / max(f.size)
        f = f.resize((max(1, int(f.width * k)), max(1, int(f.height * k))), Image.LANCZOS)
        out.append((f, max(0.02, (im.info.get("duration") or 80) / 1000)))
    _CACHE.clear() if len(_CACHE) > 40 else None
    _CACHE[key] = out
    return out


def frame_at(frs, lt):
    """The frame showing lt seconds after the GIF started (it loops)."""
    total = sum(d for _, d in frs) or 1
    lt %= total
    for f, d in frs:
        if lt < d:
            return f
        lt -= d
    return frs[-1][0]


def clip_frames(it, fps=30):
    """Frames sampled at fps for the item's whole time on screen (for the CapCut clip)."""
    frs = frames(it["file"], it.get("size", 360))
    n = max(1, int((it["end"] - it["start"]) * fps))
    return [frame_at(frs, i / fps) for i in range(n)]


def _round(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=r, fill=255)
    im.putalpha(m)
    return im


def make(video, start, end, name=None, cutout=False, fps=12, width=480):
    """A GIF from part of a video -> path in brand/gifs/."""
    if end <= start:
        raise ValueError("The end has to be after the start.")
    if end - start > 8:
        end = start + 8                                 # GIFs are short by nature
    os.makedirs(GIFS, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "-", (name or os.path.splitext(os.path.basename(video))[0]).lower()).strip("-") or "my-gif"
    tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-to", str(end), "-i", _abs(video),
                    "-vf", f"fps={fps},scale={width}:-2", os.path.join(tmp, "%04d.png")], check=True)
    pngs = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
    if not pngs:
        raise ValueError("No picture in that part of the video.")
    ims = [Image.open(os.path.join(tmp, f)).convert("RGBA") for f in pngs]
    if cutout:
        from .segment import PersonMasker
        masker = PersonMasker()
        try:
            from PIL import ImageFilter
            for i, im in enumerate(ims):              # open: drop specks the cut-out leaves behind
                im.putalpha(masker.mask(im, i * 1000 / fps).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(7)))
        finally:
            try:
                masker.close()
            except Exception:
                pass
        box = None
        for im in ims:
            b = im.getbbox()
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        if box:
            ims = [im.crop(box) for im in ims]
    else:
        ims = [_round(im, int(width * 0.06)) for im in ims]
    out = os.path.join(GIFS, name + ".webp")
    n = 2
    while os.path.exists(out):                          # never overwrite one they already have
        out = os.path.join(GIFS, f"{name}-{n}.webp")
        n += 1
    ims[0].save(out, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0, lossless=False, quality=85)
    return out


def library():
    """The brand's GIFs plus GIFs dropped in the inbox. -> [{name, file, kind}]"""
    out = []
    for folder, kind in ((GIFS, "mine"), (os.path.join(ROOT, "inbox"), "upload")):
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith((".gif", ".webp")):
                p = os.path.join(folder, f)
                try:
                    if getattr(Image.open(p), "n_frames", 1) < 2:
                        continue
                except Exception:
                    continue
                out.append({"name": os.path.splitext(f)[0], "file": os.path.relpath(p, ROOT).replace(os.sep, "/"), "kind": kind})
    return out
