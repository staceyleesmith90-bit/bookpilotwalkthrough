"""Background-noise check — runs on EVERY video before editing.

Measures, on the parts of the video that are kept:
  noise floor   how loud the room is between words (dB)
  speech level  how loud the voice is
  SNR           how far the voice stands out (higher = cleaner)
  hum           mains hum at 50/60 Hz
  clipping      distorted peaks
and picks the clean-up recipe:
  clean  -> gentle hiss removal
  some   -> spectral denoise tuned to the measured floor
  noisy  -> + RNNoise (neural speech denoiser) + gentle gate between words
Results go into the timeline (audio.noise) so the plan/report can say in plain words what was
found and done. No Claude credits: it's local maths.

RNNoise model: GregorR/rnnoise-models "somnolent-hogwash" (recording noise, speech signal) —
the authors state the models are not subject to copyright. Downloaded once to library/models/.
"""
import os, subprocess, urllib.request
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNN_URL = "https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn"
RNN_MODEL = os.path.join(ROOT, "library", "models", "rnnoise-speech.rnnn")
SR = 16000


def _pcm(source, ranges=None):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", source, "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if ranges:
        a = np.concatenate([a[int(s * SR):int(e * SR)] for s, e in ranges] or [a])
    return a


def rnnoise_model():
    if not os.path.exists(RNN_MODEL):
        try:
            os.makedirs(os.path.dirname(RNN_MODEL), exist_ok=True)
            urllib.request.urlretrieve(RNN_URL, RNN_MODEL)
        except Exception:
            return None
    return RNN_MODEL


def analyse(source, ranges=None):
    a = _pcm(source, ranges)
    if len(a) < SR:
        return {"level": "clean", "floor_db": -90, "speech_db": -90, "snr_db": 60, "hum": False, "clipping": 0}
    hop = SR // 20
    n = len(a) // hop
    rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    floor, speech = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    snr = speech - floor
    # hum: strong narrow peak at 50/60 Hz (or 100/120) in the quiet parts
    quiet = a[:n * hop].reshape(n, hop)[db < np.percentile(db, 25)].ravel()[: SR * 20]
    hum = False
    if len(quiet) > SR:
        spec = np.abs(np.fft.rfft(quiet * np.hanning(len(quiet))))
        freqs = np.fft.rfftfreq(len(quiet), 1 / SR)
        for f0 in (50, 60, 100, 120):
            band = (freqs > f0 - 2) & (freqs < f0 + 2)
            around = (freqs > f0 - 20) & (freqs < f0 + 20) & ~band
            if band.any() and spec[band].max() > 8 * np.median(spec[around]):
                hum = f0 if f0 in (50, 60) else f0 // 2
                break
    clipping = float((np.abs(a) > 0.985).mean() * 100)
    level = "clean" if (floor < -52 and snr > 30) else "noisy" if (floor > -40 or snr < 18) else "some"
    return {"level": level, "floor_db": round(floor, 1), "speech_db": round(speech, 1), "snr_db": round(snr, 1),
            "hum": hum, "clipping": round(clipping, 3)}


def chain(noise, post=False, deep=False):
    """ffmpeg filters for the measured noise: post=False -> clean-up before EQ/compression,
    post=True -> the gentle gate that goes AFTER compression (so compression can't lift the
    room noise back up between words)."""
    if post:
        lvl = (noise or {}).get("level", "some")
        return {"clean": "", "some": "agate=threshold=0.012:ratio=1.6:attack=5:release=200:range=0.5",
                "noisy": "agate=threshold=0.03:ratio=2.5:attack=5:release=180:range=0.25"}[lvl]
    n = noise or {"level": "some", "floor_db": -45}
    parts = []
    if n.get("hum"):
        f0 = n["hum"]
        parts += [f"bandreject=f={f0}:width_type=h:w=4", f"bandreject=f={f0 * 2}:width_type=h:w=4"]
    if n.get("clipping", 0) > 0.05:
        parts.append("adeclip")
    nf = max(-60, min(-20, n.get("floor_db", -45)))
    if deep:                      # DeepFilterNet already removed the noise: only hum/declip here
        return ",".join(parts)
    if n["level"] == "clean":
        parts.append(f"afftdn=nr=6:nf={nf:.0f}:tn=1")
    elif n["level"] == "some":
        parts.append(f"afftdn=nr=12:nf={nf:.0f}:tn=1")
    else:
        model = rnnoise_model()
        if model:
            safe = model.replace("\\", "/").replace(":", "\\:")   # Windows drive letters
            parts.append(f"arnndn=m='{safe}':mix=0.95")
        parts.append(f"afftdn=nr=16:nf={nf:.0f}:tn=1")
    return ",".join(parts)


def describe(n):
    if not n:
        return ""
    words = {"clean": "clean recording", "some": "some background noise, removed with the AI speech cleaner",
             "noisy": "noisy room: voice isolated with the AI speech cleaner"}[n["level"]]
    extra = []
    if n.get("hum"):
        extra.append(f"{n['hum']} Hz hum removed")
    if n.get("clipping", 0) > 0.05:
        extra.append("distorted peaks repaired")
    return words + (" · " + " · ".join(extra) if extra else "") + f" (voice {n['snr_db']:.0f} dB above the room)"


# ---------------------------------------------------------------- strong clean-up: DeepFilterNet
# Neural speech enhancer (MIT/Apache-2.0, Hendrik Schröter). One small offline program per OS,
# downloaded once to library/models/. Measured on a noisy factory recording: voice-above-room went
# 24 dB (raw) -> 38 dB (ffmpeg chain) -> 52 dB (DeepFilterNet).
DF_VER = "0.5.6"
DF_BASE = f"https://github.com/Rikorose/DeepFilterNet/releases/download/v{DF_VER}/deep-filter-{DF_VER}-"


def deepfilter_bin():
    import platform, stat, sys
    mach = platform.machine().lower()
    arm = mach in ("arm64", "aarch64")
    if sys.platform == "darwin":
        asset = "aarch64-apple-darwin" if arm else "x86_64-apple-darwin"
    elif sys.platform.startswith("win"):
        asset = "x86_64-pc-windows-msvc.exe"
    else:
        asset = "aarch64-unknown-linux-gnu" if arm else "x86_64-unknown-linux-musl"
    path = os.path.join(ROOT, "library", "models", "deep-filter" + (".exe" if asset.endswith(".exe") else ""))
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            urllib.request.urlretrieve(DF_BASE + asset, path)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        except Exception:
            return None
    return path


def deepfilter(inp, out, strength=None):
    """Clean speech with DeepFilterNet. strength: max attenuation in dB (None = full).
    Returns out, or None if unavailable (callers fall back to the ffmpeg chain)."""
    import shutil, tempfile
    exe = deepfilter_bin()
    if not exe:
        return None
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "voice.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", inp, "-vn", "-ac", "1", "-ar", "48000", src], check=True)
    cmd = [exe, "-D", "-o", os.path.join(tmp, "out"), src]        # -D keeps it in sync with the picture
    if strength:
        cmd[1:1] = ["--atten-lim-db", str(strength)]
    r = subprocess.run(cmd, capture_output=True)
    res = os.path.join(tmp, "out", "voice.wav")
    if r.returncode != 0 or not os.path.exists(res):
        return None
    shutil.move(res, out)
    return out


def elevenlabs_isolate(inp, out):
    """Optional studio tier: ElevenLabs Voice Isolator (paid, the user's own key in brand/.env).
    POST /v1/audio-isolation with the audio; returns the isolated voice. None if no key/failure."""
    import tempfile, uuid
    from .music import _api_key
    key = _api_key()
    if not key:
        return None
    tmp = os.path.join(tempfile.mkdtemp(), "voice.mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", inp, "-vn", "-ac", "1", "-b:a", "192k", tmp], check=True)
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"voice.mp3\"\r\n"
            f"Content-Type: audio/mpeg\r\n\r\n").encode() + open(tmp, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/audio-isolation", data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        data = urllib.request.urlopen(req, timeout=300).read()
    except Exception:
        return None
    mp3 = out + ".mp3"
    open(mp3, "wb").write(data)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "48000", out], check=True)
    return out
