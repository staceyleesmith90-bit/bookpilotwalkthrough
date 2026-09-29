"""Built-in music composer — free, offline, royalty-free by construction.

Makes an original background track from the same brief the questionnaire collects
(mood, style, speed, energy). Everything is synthesised here: chords, bass, drums, pads,
arpeggios, vinyl texture. No samples, no model downloads, no licences to worry about.
It's designed to sit *under* a voice, not to compete with a hit song.

    python -m engine music <project> --free
"""
import math
import numpy as np

SR = 44100
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# chord = (root offset from key, quality)
PROGRESSIONS = {
    "warm":      [(0, "maj7"), (9, "m7"), (5, "maj7"), (7, "7")],       # I vi IV V
    "dreamy":    [(0, "maj9"), (4, "m7"), (9, "m9"), (5, "maj7")],
    "uplifting": [(0, "maj"), (7, "maj"), (9, "m"), (5, "maj")],        # I V vi IV
    "calm":      [(0, "maj7"), (5, "maj7"), (0, "maj7"), (5, "maj7")],
    "emotional": [(9, "m7"), (5, "maj7"), (0, "maj"), (7, "maj")],      # vi IV I V
    "chic":      [(2, "m9"), (7, "13"), (0, "maj9"), (9, "m7")],        # ii V I vi (jazzy)
    "mysterious": [(0, "m9"), (8, "maj7"), (3, "maj7"), (10, "7")],
    "playful":   [(0, "maj"), (5, "maj"), (7, "maj"), (5, "maj")],
    "nostalgic": [(0, "maj7"), (4, "m7"), (5, "maj7"), (5, "m6")],
}
QUAL = {"maj": [0, 4, 7], "m": [0, 3, 7], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "7": [0, 4, 7, 10],
        "maj9": [0, 4, 7, 11, 14], "m9": [0, 3, 7, 10, 14], "13": [0, 4, 10, 14, 21], "m6": [0, 3, 7, 9]}

# style -> instrument recipe
STYLES = {
    "lo-fi":       dict(drums="lofi", keys="epiano", bass="round", pad=True, vinyl=True, swing=0.12, bpm=78),
    "soft piano":  dict(drums=None, keys="piano", bass=None, pad=True, vinyl=False, swing=0, bpm=72),
    "acoustic":    dict(drums="brush", keys="pluck", bass="round", pad=False, vinyl=False, swing=0.05, bpm=92),
    "indie pop":   dict(drums="pop", keys="pluck", bass="round", pad=True, vinyl=False, swing=0, bpm=108),
    "jazz café":   dict(drums="brush", keys="epiano", bass="walk", pad=False, vinyl=True, swing=0.18, bpm=96),
    "bossa nova":  dict(drums="bossa", keys="pluck", bass="round", pad=False, vinyl=False, swing=0.05, bpm=100),
    "house":       dict(drums="house", keys="stab", bass="pump", pad=True, vinyl=False, swing=0, bpm=122),
    "cinematic":   dict(drums=None, keys="piano", bass="sub", pad=True, vinyl=False, swing=0, bpm=70),
    "ambient":     dict(drums=None, keys=None, bass="sub", pad=True, vinyl=False, swing=0, bpm=66),
    "synth-pop":   dict(drums="pop", keys="arp", bass="pump", pad=True, vinyl=False, swing=0, bpm=112),
    "r&b":         dict(drums="rnb", keys="epiano", bass="round", pad=True, vinyl=False, swing=0.1, bpm=84),
    "funk":        dict(drums="pop", keys="stab", bass="walk", pad=False, vinyl=False, swing=0.08, bpm=104),
    "afrobeats":   dict(drums="afro", keys="pluck", bass="round", pad=True, vinyl=False, swing=0.06, bpm=104),
    "amapiano":    dict(drums="piano-log", keys="epiano", bass="log", pad=True, vinyl=False, swing=0.08, bpm=112),
}
MOOD_TO_PROG = {"cosy": "warm", "sunny": "uplifting", "confident": "uplifting", "motivational": "uplifting",
                "energetic": "uplifting", "romantic": "dreamy", "dreamy": "dreamy", "calm": "calm",
                "emotional": "emotional", "chic": "chic", "mysterious": "mysterious", "playful": "playful",
                "nostalgic": "nostalgic", "uplifting": "uplifting"}


# ---------------------------------------------------------------- instruments
def _env(n, a, d, s=0.0, r=None):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * (s + (1 - s) * np.exp(-t / max(d, 1e-4)))
    if r:
        tail = int(r * SR)
        if tail < n:
            e[-tail:] *= np.linspace(1, 0, tail)
    return e


def _lp(x, cutoff):
    a = 1 - math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def _lp_fast(x, cutoff):
    """Cheap low-pass via FFT (for long buffers)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def epiano(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3))
    x += 0.3 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6)
    return x * _env(n, 0.005, 0.9, 0.15, 0.2) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))


def piano(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * (0.6 ** (k - 1)) * np.exp(-t * (1.5 + k)) for k in range(1, 6))
    return x * _env(n, 0.003, 1.4, 0.0, 0.15)


def pluck(f, dur):
    """Karplus-Strong string (guitar-ish)."""
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = np.random.default_rng(int(f)).uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out * _env(n, 0.002, 2.0, 0.0, 0.05)


def stab(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 12))
    return _lp_fast(saw, 1800) * _env(n, 0.003, 0.18, 0.0, 0.05)


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.25, 0.0, 0.3):
            ff = f * 2 ** (det / 12 / 4)
            x += sum(np.sin(2 * np.pi * ff * k * t + k) / k for k in (1, 2, 3)) / 3
    x = _lp_fast(x, 1400)
    return x / (len(freqs) * 3) * _env(n, dur * 0.35, 99, 1.0, dur * 0.3)


def bass_note(f, dur, kind):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "sub":
        return np.sin(2 * np.pi * f * t) * _env(n, 0.02, 99, 1.0, 0.1)
    if kind == "log":  # amapiano 'log drum' style: pitched thud with glide
        ff = f * (1 + 0.6 * np.exp(-t * 25))
        return np.sin(2 * np.pi * np.cumsum(ff) / SR) * _env(n, 0.002, 0.35, 0.0, 0.05) * 1.3
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return x * _env(n, 0.005, 0.5 if kind != "pump" else 0.18, 0.3, 0.05)


def kick(level=1.0):
    t = _t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * level


def snare(level=1.0, soft=False):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(7).standard_normal(n) * np.exp(-t * (18 if not soft else 30))
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    return (noise * (0.4 if soft else 0.7) + body * 0.5) * level


def hat(level=1.0, open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(3).standard_normal(n)
    x = x - _lp_fast(x, 6000)
    return x * np.exp(-t * (12 if open_ else 70)) * 0.35 * level


def shaker(level=1.0):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(5).standard_normal(n)
    x = x - _lp_fast(x, 4000)
    return x * np.sin(np.pi * t / t[-1]) ** 2 * 0.25 * level


# drum patterns on a 16-step grid: (step, sound, level)
PATTERNS = {
    "lofi":  [(0, "k", 1), (6, "k", .6), (10, "k", .8), (4, "s", .7), (12, "s", .7)] + [(i, "h", .5) for i in range(0, 16, 2)],
    "pop":   [(0, "k", 1), (8, "k", 1), (4, "s", 1), (12, "s", 1)] + [(i, "h", .6) for i in range(0, 16, 2)],
    "house": [(i, "k", 1) for i in (0, 4, 8, 12)] + [(i, "o", .6) for i in (2, 6, 10, 14)] + [(4, "s", .7), (12, "s", .7)],
    "brush": [(0, "k", .5), (8, "k", .4), (4, "b", .6), (12, "b", .6)] + [(i, "sh", .6) for i in range(0, 16, 2)],
    "bossa": [(0, "k", .7), (6, "k", .5), (8, "k", .7), (14, "k", .5)] + [(i, "b", .45) for i in (3, 6, 10, 13)] + [(i, "sh", .5) for i in range(16)],
    "rnb":   [(0, "k", 1), (7, "k", .6), (10, "k", .8), (4, "s", .9), (12, "s", .9)] + [(i, "h", .45) for i in range(16)],
    "afro":  [(0, "k", 1), (7, "k", .7), (10, "k", .8), (3, "b", .6), (8, "s", .7), (13, "b", .6)] + [(i, "sh", .55) for i in range(0, 16, 2)],
    "piano-log": [(0, "k", 1), (4, "k", .9), (8, "k", 1), (12, "k", .9), (6, "s", .5), (14, "s", .5)] + [(i, "sh", .6) for i in range(16)],
}


def _place(buf, x, start):
    s = int(start * SR)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(x))
    buf[s:e] += x[: e - s]


def compose(brief, duration_s, seed=None):
    """Return (stereo float32 array [n, 2], description). brief like music.build_prompt's."""
    moods = brief.get("mood") or ["cosy"]
    styles = brief.get("genre") or ["lo-fi"]
    style = STYLES.get(styles[0], STYLES["lo-fi"])
    prog = PROGRESSIONS[MOOD_TO_PROG.get(moods[0], "warm")]
    tempo = brief.get("tempo", "medium")
    bpm = style["bpm"] * {"slow": 0.88, "medium": 1.0, "fast": 1.14}.get(str(tempo), 1.0)
    if str(tempo).isdigit():
        bpm = float(tempo)
    rng = np.random.default_rng(seed if seed is not None else hash(str(brief)) % 2 ** 31)
    key = int(rng.integers(0, 12))
    beat = 60 / bpm
    bar = beat * 4
    total = duration_s + 1.5
    n = int(total * SR)
    L = {k: np.zeros(n) for k in ("drums", "keys", "bass", "pad", "arp")}
    bars = int(math.ceil(total / bar))
    energy = brief.get("energy", "steady")
    for b in range(bars):
        t0 = b * bar
        root, q = prog[b % len(prog)]
        notes = [48 + key + root + i for i in QUAL[q]]
        # energy curve: build = sparse start, drop = drums from the middle
        section = b / max(bars - 1, 1)
        drums_on = style["drums"] and not (energy == "build" and section < 0.3) and not (energy == "drop" and section < 0.45)
        if style["pad"]:
            _place(L["pad"], pad([hz(m + 12) for m in notes[:4]], bar * 1.05), t0)
        if style["keys"] in ("epiano", "piano"):
            inst = epiano if style["keys"] == "epiano" else piano
            for hit, frac in ((0, 1.0), (2.5, 0.7)) if style["keys"] == "epiano" else ((0, 1.0),):
                for i, m in enumerate(notes[:4]):
                    _place(L["keys"], inst(hz(m + 12), bar * 0.9) * 0.22 * frac, t0 + hit * beat + i * 0.012)
        elif style["keys"] == "pluck":
            pattern = [0, 1, 2, 1, 3, 2, 1, 2]
            for i, p in enumerate(pattern):
                m = notes[p % len(notes)] + 12
                _place(L["keys"], pluck(hz(m), beat * 1.5) * 0.28, t0 + i * beat / 2 + (style["swing"] * beat / 2 if i % 2 else 0))
        elif style["keys"] == "stab":
            for i in (1, 3, 5.5, 7):
                for m in notes[:3]:
                    _place(L["keys"], stab(hz(m + 12), 0.25) * 0.12, t0 + i * beat / 2)
        elif style["keys"] == "arp":
            for i in range(16):
                m = notes[[0, 1, 2, 3, 2, 1, 0, 2][i % 8] % len(notes)] + 24
                _place(L["arp"], stab(hz(m), 0.18) * 0.08, t0 + i * beat / 4)
        if style["bass"]:
            kind = style["bass"]
            bn = 36 + key + root
            if kind == "walk":
                steps = [0, 4, 7, 9] if "m" not in q else [0, 3, 7, 10]
                for i, s in enumerate(steps):
                    _place(L["bass"], bass_note(hz(bn + s), beat * 0.95, "round") * 0.5, t0 + i * beat)
            elif kind == "pump":
                for i in range(8):
                    _place(L["bass"], bass_note(hz(bn), beat / 2 * 0.9, "pump") * 0.45, t0 + i * beat / 2)
            elif kind == "log":
                for i in (0, 3, 6, 10, 12):
                    _place(L["bass"], bass_note(hz(bn + (0 if i < 8 else 7)), beat, "log") * 0.5, t0 + i * beat / 4)
            else:
                _place(L["bass"], bass_note(hz(bn), bar * 0.5, kind) * 0.5, t0)
                _place(L["bass"], bass_note(hz(bn + 7), bar * 0.45, kind) * 0.4, t0 + bar / 2)
        if drums_on:
            for step, snd, lvl in PATTERNS[style["drums"]]:
                st = t0 + step * beat / 4 + (style["swing"] * beat / 4 if step % 2 else 0)
                x = {"k": kick(lvl), "s": snare(lvl), "b": snare(lvl * 0.7, soft=True), "h": hat(lvl),
                     "o": hat(lvl, open_=True), "sh": shaker(lvl)}[snd]
                _place(L["drums"], x * 0.6, st)
    mix = L["drums"] * 0.9 + L["keys"] + L["bass"] * 0.9 + L["pad"] * 0.55 + L["arp"]
    if style["vinyl"]:
        rng2 = np.random.default_rng(11)
        crackle = (rng2.random(n) > 0.9996) * rng2.uniform(-0.25, 0.25, n)
        mix = _lp_fast(mix, 5200) + crackle + rng2.standard_normal(n) * 0.004
    # soft compression, fades
    mix = np.tanh(mix * 1.4) / 1.4
    fade_in, fade_out = int(0.4 * SR), int(1.2 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    end = int(duration_s * SR)
    mix = mix[:end]
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    mix /= max(np.abs(mix).max(), 1e-6) / 0.8
    # gentle stereo: pad/keys slightly wide via tiny delay
    d = int(0.012 * SR)
    right = np.concatenate([np.zeros(d), mix[:-d]])
    stereo = np.stack([mix * 0.9 + right * 0.1, right * 0.9 + mix * 0.1], axis=1).astype(np.float32)
    desc = f"{moods[0]} {styles[0]} · {int(bpm)} BPM · key {list(NOTE)[key]} · {energy}"
    return stereo, desc


def write(path, stereo):
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(stereo, -1, 1) * 32767).astype(np.int16).tobytes())
    return path
