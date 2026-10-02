"""Colour grades ("filters") as ffmpeg recipes. Our own looks — inspired by common
styles, not copied from any app. Users can also drop a .cube LUT in brand/ or inbox/
and use it by file name.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRADES = {
    "none": "",
    "clean-bright": "eq=brightness=0.03:contrast=1.06:saturation=1.08,unsharp=5:5:0.4",
    "warm-film": ("colorbalance=rs=0.06:gs=0.01:bs=-0.06:rm=0.04:bm=-0.04,"
                  "curves=all='0/0.06 0.5/0.52 1/0.95',eq=saturation=0.92,noise=alls=6:allf=t"),
    "soft-matte": "curves=all='0/0.1 0.5/0.5 1/0.92',eq=contrast=0.94:saturation=0.9",
    "vivid": "eq=contrast=1.12:saturation=1.35:brightness=0.02",
    "moody": ("curves=all='0/0 0.35/0.28 0.75/0.72 1/0.94',colorbalance=bs=0.05:bm=0.02:rh=0.04,"
              "eq=saturation=0.85,vignette=PI/5"),
    "cool-crisp": "colorbalance=bs=0.06:bm=0.03:rs=-0.03,eq=contrast=1.08:saturation=1.05,unsharp=5:5:0.5",
    "vintage-fade": ("curves=r='0/0.1 1/0.95':g='0/0.06 1/0.92':b='0/0.14 1/0.85',"
                     "eq=saturation=0.75,noise=alls=10:allf=t,vignette=PI/4"),
    "bw-classic": "hue=s=0,eq=contrast=1.15,noise=alls=5:allf=t",
    "golden-hour": "colorbalance=rs=0.08:gs=0.03:bs=-0.08:rh=0.05,eq=saturation=1.12:brightness=0.02",
    # --- lifestyle / social looks
    "clean-girl": ("eq=brightness=0.05:contrast=0.96:saturation=0.9,colorbalance=rs=0.03:bs=-0.01:rh=0.02,"
                   "curves=all='0/0.04 0.5/0.55 1/1'"),
    "latte": ("colorbalance=rs=0.07:gs=0.03:bs=-0.07:rm=0.05:gm=0.02:bm=-0.05,"
              "curves=all='0/0.08 0.5/0.52 1/0.93',eq=saturation=0.8"),
    "creamy-pastel": "curves=all='0/0.12 0.5/0.58 1/0.97',eq=saturation=0.78:contrast=0.9,colorbalance=rh=0.03:bh=0.03",
    "peachy": "colorbalance=rs=0.05:gs=-0.01:bs=0.01:rh=0.06:gh=0.02,eq=saturation=1.05:brightness=0.03",
    "soft-glow": "split[a][b];[b]gblur=sigma=18[g];[a][g]blend=all_mode=screen:all_opacity=0.28,eq=contrast=0.95",
    "dreamy-haze": ("split[a][b];[b]gblur=sigma=26,eq=brightness=0.06[g];[a][g]blend=all_mode=softlight:all_opacity=0.5,"
                    "curves=all='0/0.1 1/0.96',eq=saturation=0.85"),
    # --- film-inspired (our own recipes, not emulations of any branded stock)
    "portrait-film": ("colorbalance=rs=0.03:bs=-0.02:rm=0.02:gm=0.01:rh=0.02:bh=-0.03,"
                      "curves=all='0/0.05 0.25/0.24 0.75/0.78 1/0.96',eq=saturation=0.9,noise=alls=5:allf=t"),
    "green-film": ("colorbalance=gs=0.04:bs=0.02:gm=0.02:rh=0.02,curves=all='0/0.06 0.5/0.5 1/0.95',"
                   "eq=saturation=0.88,noise=alls=6:allf=t"),
    "disposable": ("colorbalance=rs=0.05:gs=0.02:bs=-0.03:rh=0.04,eq=contrast=1.12:saturation=1.15,"
                   "vignette=PI/4.5,noise=alls=12:allf=t"),
    "teal-orange": "colorbalance=rs=-0.05:bs=0.08:rm=0.02:rh=0.08:bh=-0.08,eq=contrast=1.08:saturation=1.1",
    "cinematic": ("colorbalance=bs=0.06:rh=0.06:bh=-0.05,curves=all='0/0.02 0.3/0.24 0.7/0.74 1/0.93',"
                  "eq=saturation=0.9,vignette=PI/5"),
    # --- seasonal / mood
    "summer": "colorbalance=rs=0.04:gs=0.02:bs=-0.04,eq=saturation=1.25:brightness=0.04:contrast=1.05",
    "winter": "colorbalance=rs=-0.04:bs=0.06:bh=0.04,eq=saturation=0.8:brightness=0.03,curves=all='0/0.05 1/1'",
    "noir": "hue=s=0,curves=all='0/0 0.3/0.18 0.7/0.82 1/1',vignette=PI/4,noise=alls=7:allf=t",
    "sepia-memory": ("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,"
                     "curves=all='0/0.08 1/0.92',noise=alls=8:allf=t,vignette=PI/4.5"),
    "retro-80s": "colorbalance=rs=0.06:bs=0.08:gm=-0.03,eq=saturation=1.3:contrast=1.1,noise=alls=10:allf=t",
    "vhs": ("rgbashift=rh=3:bh=-3,eq=saturation=1.2:contrast=1.05,noise=alls=14:allf=t,"
            "curves=all='0/0.06 1/0.94',vignette=PI/5"),
    "night-neon": "colorbalance=bs=0.1:rh=0.06:bm=0.05,eq=saturation=1.35:contrast=1.15",
}

GROUPS = {
    "Everyday": ["clean-bright", "clean-girl", "peachy", "vivid", "cool-crisp"],
    "Warm & soft": ["warm-film", "latte", "golden-hour", "creamy-pastel", "soft-matte"],
    "Dreamy": ["soft-glow", "dreamy-haze"],
    "Film": ["portrait-film", "green-film", "disposable", "vintage-fade", "sepia-memory"],
    "Cinematic": ["cinematic", "teal-orange", "moody", "noir", "bw-classic"],
    "Seasonal & retro": ["summer", "winter", "retro-80s", "vhs", "night-neon"],
}

DESCRIPTIONS = {
    "clean-bright": "true colours, a touch brighter and crisper",
    "warm-film": "warm, soft blacks, light film grain",
    "soft-matte": "faded blacks, gentle and calm",
    "vivid": "punchy colour and contrast",
    "moody": "deep shadows, cool tint, dark edges",
    "cool-crisp": "cool, clean, sharp",
    "vintage-fade": "faded retro colour with grain",
    "bw-classic": "black and white with grain",
    "golden-hour": "warm sunset glow",
    "clean-girl": "bright, soft and fresh with a hint of warmth",
    "latte": "creamy brown-beige, cosy café tones",
    "creamy-pastel": "lifted, milky pastel colours",
    "peachy": "warm peach highlights, glowing skin",
    "soft-glow": "gentle bloom on highlights",
    "dreamy-haze": "soft hazy glow, faded",
    "portrait-film": "flattering film-like skin tones and fine grain",
    "green-film": "cool-green film tint with grain",
    "disposable": "punchy, grainy, disposable-camera feel",
    "teal-orange": "movie-style teal shadows and warm skin",
    "cinematic": "deep, graded, filmic contrast",
    "summer": "bright, saturated, sunny",
    "winter": "cool, clean, airy",
    "noir": "high-contrast black and white",
    "sepia-memory": "old-photo sepia memory",
    "retro-80s": "saturated magenta/blue retro",
    "vhs": "home-video colour bleed and noise",
    "night-neon": "vibrant night-time neon",
}


def graph(grade, inp, out):
    """Full filtergraph fragment from label [inp] to [out] (handles bloom/glow grades)."""
    g = filter_for(grade)
    if not g:
        return f"[{inp}]format=yuv420p[{out}]"
    if g.startswith("split[a][b];"):
        body = g[len("split[a][b];"):]
        # "[b]<blur...>[g];[a][g]blend=...,<post>"
        blur, rest = body.split("[g];", 1)
        blur = blur.replace("[b]", "", 1)
        rest = rest.replace("[a][g]", "", 1)
        return (f"[{inp}]split[{out}_a][{out}_b];[{out}_b]{blur}[{out}_g];"
                f"[{out}_a][{out}_g]{rest},format=yuv420p[{out}]")
    return f"[{inp}]{g},format=yuv420p[{out}]"


def filter_for(grade):
    """ffmpeg -vf fragment for a preset name or a .cube file."""
    if not grade or grade == "none":
        return ""
    if grade.endswith(".cube"):
        for d in ("brand/luts", "brand", "inbox", "library/luts"):
            p = os.path.join(ROOT, d, grade)
            if os.path.exists(p):
                # ffmpeg filter paths: forward slashes, escaped drive colon (Windows-safe)
                safe = p.replace("\\", "/").replace(":", "\\:")
                return f"lut3d='{safe}'"
        raise FileNotFoundError(grade)
    return GRADES[grade]


def my_luts():
    """Filters the user uploaded (.cube files in brand/luts) — shown as "Yours" next to the built-in ones."""
    d = os.path.join(ROOT, "brand", "luts")
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".cube")) if os.path.isdir(d) else []


def add_lut(src, name):
    """Save an uploaded .cube filter for this brand. Checks it really is a LUT."""
    import re, shutil
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(name))
    if not name.lower().endswith(".cube"):
        raise ValueError("Filters need to be .cube files (the standard LUT format; most free packs include them).")
    head = open(src, encoding="utf-8", errors="ignore").read(4000)
    if "LUT_3D_SIZE" not in head and "LUT_1D_SIZE" not in head:
        raise ValueError("That file isn't a LUT filter (.cube). Look for the .cube files inside the pack.")
    d = os.path.join(ROOT, "brand", "luts")
    os.makedirs(d, exist_ok=True)
    shutil.copy(src, os.path.join(d, name))
    return name
