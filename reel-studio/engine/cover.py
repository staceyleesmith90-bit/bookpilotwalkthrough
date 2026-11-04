"""Cover frame: every reel opens on a designed cover that says what the video is about, so before
anyone presses play (phone gallery, WhatsApp, Drive, the IG grid) they see a picture + title, not black.

The cover is held for HOLD seconds as the first frames of the video, then cross-fades into the reel. It is
also saved as renders/cover.jpg and embedded as the file's thumbnail.

plan / timeline "cover" (all optional — on by default):
  enabled  true
  title    "while mom's on duty"           big serif line (default: the reel's first title / hook)
  kicker   "entertaining an 8-month-old"    handwritten line above it
  photo    "projects/x/source/pic.jpg"      picture behind it (default: a frame of the reel at `at`)
  at       1.0                              which moment of the reel to use as the picture
  y        0.72                             where the title sits (0-1 of the height; keep it off faces)
  hold     0.6                              seconds the cover stays before the reel starts
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .textfit import load_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = lambda n: os.path.join(ROOT, "library", "fonts", n)
HOLD, XFADE = 0.6, 0.25


def _rgb(h, alpha=255):
    h = str(h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def defaults(tl):
    """Title + kicker from the reel itself: its first collage/scene title, else its first hook text."""
    for sc in tl.get("scenes", []):
        sp = sc.get("spec") or {}
        if sp.get("title"):
            return sp.get("title"), sp.get("kicker", "")
    for it in tl.get("items", []):
        if it.get("role") in ("hook", "takeover", "title") and it.get("text"):
            return it["text"], ""
    return tl.get("end_card", {}).get("title") or "", ""


def _wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def design(pic, title, kicker, colors, W=1080, H=1920, y=0.72):
    """The cover image (RGB): picture, soft dark fade behind the text, kicker + big title, a 'play' hint."""
    im = ImageOps.fit(pic.convert("RGB"), (W, H), Image.LANCZOS).convert("RGBA")
    u = W / 1080
    # a gentle dark band where the text sits, so any photo stays readable
    band = np.zeros((H, 1), np.float32)
    yy = np.arange(H)[:, None] / H
    band = np.clip(1 - np.abs(yy - y) / 0.26, 0, 1) ** 1.4 * 0.62
    shade = np.zeros((H, W, 4), np.uint8)
    shade[..., 3] = (np.repeat(band, W, axis=1) * 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(shade, "RGBA"))
    paper = _rgb(colors.get("paper", "#FFFBF5"))
    pop = _rgb(colors.get("pop", "#F29BB2"))
    px = int(150 * u)
    fb = load_font(FONT("DMSerifDisplay-Regular.ttf"), px)
    while px > 70 * u and max(fb.getlength(w) for w in (title or " ").split()) > W * 0.84:
        px = int(px * 0.92); fb = load_font(FONT("DMSerifDisplay-Regular.ttf"), px)
    lines = _wrap(title or "", fb, W * 0.86)
    if len(lines) > 2:
        px = int(px * 0.8); fb = load_font(FONT("DMSerifDisplay-Regular.ttf"), px); lines = _wrap(title, fb, W * 0.88)
    fk = load_font(FONT("Caveat-Variable.ttf"), int(px * 0.46), 700)
    lh = px * 1.02
    block = len(lines) * lh + (px * 0.62 if kicker else 0)
    top = H * y - block / 2
    lay = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(lay)
    sh = Image.new("RGBA", (W, H)); ds = ImageDraw.Draw(sh)
    cy = top
    if kicker:
        for dd, fill in ((ds, (0, 0, 0, 150)), (d, pop)):
            dd.text((W / 2 + (3 * u if dd is ds else 0), cy + (4 * u if dd is ds else 0)), kicker, font=fk, fill=fill, anchor="mt")
        cy += px * 0.62
    for ln in lines:
        ds.text((W / 2 + 3 * u, cy + 5 * u), ln, font=fb, fill=(0, 0, 0, 160), anchor="mt")
        d.text((W / 2, cy), ln, font=fb, fill=paper, anchor="mt")
        cy += lh
    # small round play badge under the title: "this is a video, press play"
    r = int(46 * u); bx, by = W / 2, cy + r * 1.5
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=paper[:3] + (235,))
    d.polygon([(bx - r * 0.3, by - r * 0.45), (bx - r * 0.3, by + r * 0.45), (bx + r * 0.5, by)], fill=pop)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6 * u)))
    im.alpha_composite(lay)
    return im.convert("RGB")


def _frame(video, t, W, H):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{max(t, 0):.3f}", "-i", video, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if len(raw) < W * H * 3:
        return None
    return Image.frombuffer("RGB", (W, H), raw[:W * H * 3], "raw", "RGB", 0, 1).copy()


def spec_of(tl):
    sp = dict(tl.get("cover") or {})
    if sp.get("enabled", True) is False:
        return None
    t, k = defaults(tl)
    sp.setdefault("title", t)
    sp.setdefault("kicker", k)
    return sp if (sp.get("title") or sp.get("kicker")) else None


def add(video, tl, pack, base, out_jpg, tmp):
    """Put the cover in front of `video` (in place) and save it as out_jpg. Returns out_jpg, or None if off."""
    sp = spec_of(tl)
    if not sp:
        return None
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip().split(",")
    W, H = int(wh[0]), int(wh[1])
    if sp.get("photo"):
        p = sp["photo"] if os.path.isabs(sp["photo"]) else os.path.join(ROOT, sp["photo"])
        pic = ImageOps.exif_transpose(Image.open(p))
    else:
        pic = _frame(base, float(sp.get("at", 1.0)), W, H) or _frame(video, 0.5, W, H)
    img = design(pic, sp.get("title", ""), sp.get("kicker", ""), pack.get("colors", {}), W, H, float(sp.get("y", 0.72)))
    full = img if (W, H) == (1080, 1920) else design(pic, sp.get("title", ""), sp.get("kicker", ""),
                                                      pack.get("colors", {}), 1080, 1920, float(sp.get("y", 0.72)))
    os.makedirs(os.path.dirname(os.path.abspath(out_jpg)), exist_ok=True)
    full.save(out_jpg, quality=92)
    png = os.path.join(tmp, "cover.png"); img.save(png)
    hold = float(sp.get("hold", HOLD))
    fps = tl.get("fps", 30)
    joined = os.path.join(tmp, "with-cover.mp4")
    fc = (f"[0:v]fps={fps},format=yuv420p,setsar=1[c];[1:v]fps={fps},format=yuv420p,setsar=1[v];"
          f"[c][v]xfade=transition=fade:duration={XFADE}:offset={hold - XFADE:.3f}[vv];"
          f"[1:a]adelay={int((hold - XFADE) * 1000)}:all=1[aa]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(fps), "-t", f"{hold:.3f}",
                    "-i", png, "-i", video, "-i", out_jpg, "-filter_complex", fc,
                    "-map", "[vv]", "-map", "[aa]", "-map", "2:v",
                    "-c:v:0", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M",
                    "-pix_fmt:v:0", "yuv420p", "-c:v:1", "mjpeg", "-disposition:v:1", "attached_pic",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", joined], check=True)
    os.replace(joined, video)
    return out_jpg
