"""Sound effects synthesised from code — royalty-free by construction, no downloads.

Each function returns a mono float array at SR. Users can also drop their own .wav/.mp3
into library/sfx/ (or inbox/) and refer to them by file name; see `load`.
Pairing guide (see docs/knowledge/sound-design.md): pop = text/sticker in, whoosh =
transitions, hit = hook/takeover slam, riser -> hit = reveal, ding = CTA / result, tick =
count-up / list items, click = typewriter / UI, boing = playful punchline.
"""
import math, os, wave
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-5), 1) * np.exp(-t / decay)


def _lowpass(x, a):
    """One-pole low-pass; `a` may be a scalar or per-sample array (0..1)."""
    out, y = np.empty_like(x), 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        y += a[i] * (x[i] - y)
        out[i] = y
    return out


def pop():
    t = _t(0.12)
    f = 900 * np.exp(-t * 25) + 180
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.035)


def whoosh(dur=0.45):
    n = int(dur * SR)
    noise = np.random.default_rng(0).standard_normal(n)
    a = 0.02 + 0.25 * np.sin(np.pi * np.arange(n) / n)
    return _lowpass(noise, a) * np.sin(np.pi * np.arange(n) / n) ** 2 * 3


def swish():
    return whoosh(0.22)


def click():
    n = int(0.03 * SR)
    return np.random.default_rng(1).standard_normal(n) * env(n, 0.0005, 0.004)


def ding():
    t = _t(0.8)
    tone = sum(np.sin(2 * np.pi * f * t) / k for k, f in enumerate([1320, 2640, 3960], 1))
    return tone * env(len(t), 0.003, 0.18) * 0.6


def hit():
    t = _t(0.5)
    f = 110 * np.exp(-t * 8) + 45
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.001, 0.16)
    crack = np.random.default_rng(2).standard_normal(len(t)) * env(len(t), 0.0005, 0.02) * 0.5
    return body + crack


def riser(dur=1.2):
    t = _t(dur)
    noise = np.random.default_rng(3).standard_normal(len(t))
    a = 0.01 + 0.4 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / dur) ** 2) / SR) * 0.3
    return (_lowpass(noise, a) * 2 + tone) * (t / dur) ** 1.5


def tick():
    t = _t(0.05)
    return np.sin(2 * np.pi * 2400 * t) * env(len(t), 0.0005, 0.008)


def boing():
    t = _t(0.5)
    f = 300 + 180 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.003, 0.18)


def shutter():
    n = int(0.12 * SR)
    x = np.random.default_rng(4).standard_normal(n)
    e = env(n, 0.0005, 0.01)
    e2 = np.roll(env(n, 0.0005, 0.015), int(0.06 * SR))
    return x * (e + e2 * 0.8)


def notify():
    a, b = _t(0.12), _t(0.3)
    n1 = np.sin(2 * np.pi * 988 * a) * env(len(a), 0.002, 0.05)
    n2 = np.sin(2 * np.pi * 1319 * b) * env(len(b), 0.002, 0.1)
    return np.concatenate([n1, n2])


SFX = dict(pop=pop, whoosh=whoosh, swish=swish, click=click, ding=ding, hit=hit,
           riser=riser, tick=tick, boing=boing, shutter=shutter, notify=notify)


def load(name):
    """Built-in name, a sound-design cue (sd:kit:event:seed[:dur]), or a user .wav file."""
    if name.startswith("sd:"):
        from .sounddesign import render
        return render(name)
    if name in SFX:
        return SFX[name]()
    for d in ("library/sfx", "inbox"):
        p = os.path.join(ROOT, d, name)
        if os.path.exists(p) and p.endswith(".wav"):
            with wave.open(p) as w:
                x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32767
                if w.getnchannels() == 2:
                    x = x.reshape(-1, 2).mean(1)
                return x
    raise KeyError(f"Unknown sound '{name}'")


def write_wav(path, x, peak=0.8):
    """peak=None writes levels as-is (clipped); otherwise normalises to `peak`."""
    m = np.abs(x).max() if len(x) else 0
    if peak is not None and m > 0:
        x = x / m * peak
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def mix_cues(cues, duration):
    """cues: list of (time_s, name, gain). Returns a mono track `duration` long."""
    out = np.zeros(int((duration + 2) * SR))
    for t0, name, gain in cues:
        x = load(name)
        x = x / (np.abs(x).max() + 1e-9) * gain
        s0 = max(int(t0 * SR), 0)
        e = min(s0 + len(x), len(out))
        out[s0:e] += x[: e - s0]
    return out[: int(duration * SR)]
