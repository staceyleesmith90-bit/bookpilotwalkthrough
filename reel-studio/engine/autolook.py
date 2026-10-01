"""A look made from the video itself — for people who haven't set up a brand (or a new client brand).

    python -m engine look-from-video <project|video>   -> 3 looks drawn on a frame of THEIR video
    python -m engine look-use <1|2|3>                  -> save the chosen one as the brand in use

Colours come from what's in the footage (the product, the outfit, the room) — skin and plain
greys are skipped — so the text always belongs with the picture. Each look pairs those colours
with a font pairing that suits a different feel (modern, soft editorial, bold).
"""
import colorsys, json, os, subprocess, tempfile

from . import brand, packs, stylesheet

ROOT = packs.ROOT
LOOKS = os.path.join(ROOT, "brand", "looks.json")
FEELS = [  # name, main font, accent font, caption font, background for full-screen moments
    ("Modern", "Poppins-ExtraBold", "Caveat-Variable", "Poppins-SemiBold", "light"),
    ("Soft editorial", "PlayfairDisplay-Variable", "Parisienne-Regular", "Inter-Variable", "cream"),
    ("Bold", "BebasNeue-Regular", "KaushanScript-Regular", "Montserrat-Variable", "dark"),
]


def _frames(video, n=8):
    tmp = tempfile.mkdtemp(prefix="look-")
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    video], capture_output=True, text=True).stdout.strip() or 10)
    except ValueError:
        dur = 10
    out = []
    for i in range(n):
        f = os.path.join(tmp, f"f{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(dur * (i + 0.5) / n), "-i", video, "-frames:v", "1",
                        "-vf", "scale=540:-2", f], capture_output=True)
        if os.path.exists(f):
            out.append(f)
    return out


def _is_skin(h):
    r, g, b = [x / 255 for x in brand.rgb_(h)]
    hh, s, v = colorsys.rgb_to_hsv(r, g, b)
    return hh * 360 < 50 and 0.15 < s < 0.65 and v > 0.3


def palette_from_video(video):
    """-> (colourful candidates, best frame path)"""
    frames = _frames(video)
    if not frames:
        return [], None
    import numpy as np
    from PIL import Image
    px = np.concatenate([np.asarray(Image.open(f).convert("RGB").resize((90, 160)), dtype=np.float32).reshape(-1, 3) / 255
                         for f in frames])
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    keep = (sat > 0.28) & (mx > 0.35)
    skin_or_wood = (hue > 5) & (hue < 50) & ((sat < 0.7) | (mx < 0.6))      # faces, hair, tables, floors
    keep &= ~skin_or_wood
    vivid = []
    if keep.sum() > 50:
        bins = (hue[keep] // 20).astype(int)
        cols = px[keep]
        counts = np.bincount(bins, minlength=18)
        score = np.bincount(bins, weights=sat[keep] ** 2 * mx[keep], minlength=18)   # colourful beats common
        for bi in np.argsort(-score)[:4]:
            if counts[bi] < max(40, keep.sum() * 0.04):
                continue
            c = (cols[bins == bi].mean(0) * 255).astype(int)
            vivid.append(brand.hex_(list(c)))
    return vivid, frames[len(frames) // 2]


def _shift(h, light=None, sat=None):
    r, g, b = [x / 255 for x in brand.rgb_(h)]
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(hh, ll if light is None else light, ss if sat is None else sat)
    return brand.hex_([int(r * 255), int(g * 255), int(b * 255)])


def _complement(h):
    r, g, b = [x / 255 for x in brand.rgb_(h)]
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb((hh + 0.5) % 1, 0.5, max(ss, 0.55))
    return brand.hex_([int(r * 255), int(g * 255), int(b * 255)])


def make_looks(video, name="My brand"):
    vivid, frame = palette_from_video(video)
    pick = (vivid + [_complement(vivid[0]) if vivid else "#E4572E", "#2F6BFF", "#E4572E"])[:3]
    # three feels, each led by a different colour from the video (soft editorial gets the gentlest)
    accents = [_shift(pick[0], light=0.5, sat=0.75), _shift(pick[1], light=0.45, sat=0.45),
               _shift(pick[2], light=0.55, sat=0.85)]
    looks = []
    for (feel, main, acc, cap, bgkind), pop in zip(FEELS, accents):
        bg = {"light": _shift(pop, light=0.95, sat=0.5), "cream": "#F6F1E9", "dark": "#141414"}[bgkind]
        ink = "#141414" if bgkind != "dark" else "#F6F1E9"
        roles = {"bg": bg, "ink": ink, "pop": pop, "accent": pop, "paper": "#FFFFFF" if bgkind != "dark" else "#F6F1E9",
                 "bubble_text": "#141414"}
        pack = brand.build_pack(name, roles, brand._font(main), brand._font(acc), brand._font(cap),
                                prefer="dark" if bgkind == "dark" else "light")
        looks.append({"feel": feel, "pack": pack})
    os.makedirs(os.path.dirname(LOOKS), exist_ok=True)
    json.dump({"video": video, "frame": frame, "looks": looks}, open(LOOKS, "w", encoding="utf-8"), indent=1)
    sheets = []
    for i, lk in enumerate(looks, 1):
        sheets.append(stylesheet.overview(lk["pack"], os.path.join(ROOT, "brand", "previews", f"look-{i}.jpg"),
                                          photo=frame, only=["hook headline", "captions", "takeover"],
                                          heading=f"{i}. {lk['feel']}"))
    return _stack(sheets, os.path.join(ROOT, "brand", "previews", "looks.jpg")), looks


def _stack(paths, out):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    sheet = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims)), "#F4F1EA")
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height
    sheet.thumbnail((1200, 3000))
    sheet.save(out, quality=88)
    return out


def use(n, name=None):
    data = json.load(open(LOOKS, encoding="utf-8"))
    pack = data["looks"][int(n) - 1]["pack"]
    pending = os.path.join(ROOT, "brand", "brand-name.json")
    if os.path.exists(pending):                  # a brand started with "new brand: …" gets its name
        pack["label"] = json.load(open(pending, encoding="utf-8")).get("label") or pack["label"]
        os.remove(pending)
    if name:
        pack["label"] = name
    old = packs.load("brand") if packs.has_brand() else {}
    if old.get("logo"):
        pack["logo"] = json.load(open(packs.BRAND, encoding="utf-8")).get("logo")
    packs.save_brand(pack)
    return pack
