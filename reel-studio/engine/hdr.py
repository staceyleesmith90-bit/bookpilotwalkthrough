"""HDR phone footage → normal (SDR) video, before anything else touches it.

iPhones (and many Androids) film HDR by default: BT.2020 colours with an HLG or PQ curve, 10-bit.
Edited as if it were normal video it comes out grey and washed out, and white text on top looks dull.
We detect it from the video's own colour tags and convert it once to standard BT.709, keeping a
cached copy so it's only done one time per clip. The user's original file is never changed.
"""
import hashlib, json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "out", "sdr-cache")
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}          # PQ (HDR10 / Dolby Vision) and HLG (iPhone)

TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
FALLBACK = "colorspace=all=bt709:iall=bt2020:itrc=bt2020-10:fast=1,format=yuv420p"


def info(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=color_transfer,color_primaries,color_space,pix_fmt", "-of", "json", path],
                             capture_output=True, text=True, timeout=30).stdout
        return (json.loads(out).get("streams") or [{}])[0]
    except Exception:
        return {}


def is_hdr(path):
    s = info(path)
    return s.get("color_transfer") in HDR_TRANSFERS or (
        s.get("color_primaries") == "bt2020" and "10" in (s.get("pix_fmt") or ""))


def to_sdr(src, dst):
    """Convert one HDR clip to SDR. Tries proper tone-mapping first, then a simpler colour conversion."""
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    for vf in (TONEMAP, FALLBACK):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "fast",
                            "-crf", "17", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", dst], capture_output=True)
        if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 1000:
            return dst
    raise RuntimeError("Couldn't convert this HDR video.")


def ensure_sdr(path):
    """Path to an SDR version of a video (the same path when it's already SDR)."""
    if not path or not os.path.exists(path) or not path.lower().endswith((".mp4", ".mov", ".m4v", ".hevc", ".mkv")):
        return path
    if not is_hdr(path):
        return path
    key = hashlib.md5(f"{os.path.abspath(path)}|{os.path.getsize(path)}|{os.path.getmtime(path)}".encode()).hexdigest()[:12]
    dst = os.path.join(CACHE, f"{os.path.splitext(os.path.basename(path))[0]}-{key}-sdr.mp4")
    if os.path.exists(dst):
        return dst
    try:
        return to_sdr(path, dst)
    except Exception:
        return path                                 # never block the edit: fall back to the original
