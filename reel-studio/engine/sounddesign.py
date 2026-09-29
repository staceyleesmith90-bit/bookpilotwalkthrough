"""Sound design — the CapCut-level layer that makes edits feel alive.

What pro short-form editors do (see docs/knowledge/sound-design.md):
  1. MOTION  every movement gets a whoosh, sized to the move and with its loudest point on the
             moment of most motion (a slow push = long soft whoosh, a punch = short swish + thud).
  2. TEXTURE text/graphics get tactile sounds: pops, clicks, key-by-key typing, paper swipes for
             slides and highlights, glass taps for glass labels, digital blips for UI-style pops.
  3. LIFT/HIT build-ups get a riser that peaks on the reveal; big moments get a layered hit
             (sub thump + mid punch + high sparkle) — layering frequencies makes it feel expensive.
  4. STYLE   one coherent kit per video (clean · luxe · playful · digital) — mixing random
             sounds is what makes edits feel cheap.
  5. VARIETY never the same sample twice in a row: variants + tiny pitch/level changes.

Cue names: "sd:<kit>:<event>:<seed>[:<duration>]" (see cue()). Samples: Kenney CC0 packs in
library/sfx/kenney/ plus sounds synthesised here (whooshes, risers, shimmer, sub hits).
"""
import glob, hashlib, os, wave
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEN = os.path.join(ROOT, "library", "sfx", "kenney")

# event -> kit -> candidate sources ("k:<glob>" = Kenney sample glob, "s:<synth>" = synth)
KITS = {
    "text_in":   {"clean": ["k:interface-click_*", "k:ui-click*"], "luxe": ["k:interface-glass_*", "s:shimmer"],
                  "playful": ["k:interface-drop_*", "k:interface-pluck_*"], "digital": ["k:interface-select_*", "k:digital-pepSound*"]},
    "word_pop":  {"clean": ["k:interface-tick_*"], "luxe": ["k:interface-tick_*"],
                  "playful": ["k:interface-toggle_*", "k:interface-drop_*"], "digital": ["k:ui-rollover*"]},
    "type_key":  {"*": ["k:ui-switch*"]},
    "type_end":  {"clean": ["k:interface-confirmation_*"], "luxe": ["s:shimmer"],
                  "playful": ["k:interface-bong_*", "k:interface-confirmation_*"], "digital": ["k:digital-twoTone*"]},
    "slide":     {"*": ["k:casino-card-slide-*"]},
    "highlight": {"*": ["k:casino-card-slide-*"]},
    "glass":     {"*": ["k:interface-glass_*", "k:impact-impactGlass_light_*"]},
    "select":    {"clean": ["k:interface-select_*"], "luxe": ["k:interface-glass_*"],
                  "playful": ["k:interface-pluck_*"], "digital": ["k:interface-select_*"]},
    "sticker_in": {"clean": ["k:interface-drop_*"], "luxe": ["k:interface-glass_*"],
                   "playful": ["k:interface-drop_*", "k:interface-pluck_*", "s:boing"], "digital": ["k:digital-pepSound*"]},
    "whoosh":    {"*": ["s:whoosh"]},
    "swish":     {"*": ["s:swish"]},
    "zoom_in":   {"*": ["s:zoom"]},
    "impact":    {"clean": ["s:hit_soft"], "luxe": ["s:hit_lux"], "playful": ["k:impact-impactSoft_heavy_*"],
                  "digital": ["s:hit_soft", "k:interface-glitch_*"]},
    "riser":     {"*": ["s:riser"]},
    "reveal":    {"clean": ["k:interface-confirmation_*"], "luxe": ["s:shimmer"],
                  "playful": ["k:digital-powerUp*"], "digital": ["k:digital-powerUp*", "k:digital-phaserUp*"]},
    "cta":       {"clean": ["k:interface-confirmation_*"], "luxe": ["k:impact-impactBell_heavy_*"],
                  "playful": ["k:interface-bong_*"], "digital": ["k:digital-threeTone*"]},
    "transition": {"*": ["s:whoosh"]},
    "glitch":    {"*": ["k:interface-glitch_*"]},
}
KIT_FOR_LOOK = {"premium": "luxe", "playful": "playful", "bold": "digital"}
KIT_GAIN = {"luxe": 0.8, "clean": 0.85, "playful": 1.0, "digital": 0.9}


def cue(event, t, seed=0, kit="clean", gain=0.6, dur=None):
    """A mix cue (t, name, gain) for event at time t."""
    name = f"sd:{kit}:{event}:{int(seed)}" + (f":{dur:.2f}" if dur else "")
    return (max(float(t), 0.0), name, gain * KIT_GAIN.get(kit, 1.0))


# ---------------------------------------------------------------- samples
_cache = {}


def _wav(path):
    if path not in _cache:
        with wave.open(path) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32767
            if w.getnchannels() == 2:
                x = x.reshape(-1, 2).mean(1)
        _cache[path] = x
    return _cache[path]


def _pick(lst, seed, salt):
    h = int(hashlib.md5(f"{salt}:{seed}".encode()).hexdigest(), 16)
    return lst[h % len(lst)], h


def _pitch(x, semitones):
    if abs(semitones) < 0.05:
        return x
    k = 2 ** (semitones / 12)
    idx = np.arange(0, len(x) - 1, k)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


# ---------------------------------------------------------------- synths
def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _noise(n, rng):
    return rng.standard_normal(n).astype(np.float32)


def _bandsweep(x, f0, f1, q=1.2):
    """Cheap swept band-pass via FFT blocks (fast, no scipy)."""
    out = np.zeros_like(x)
    blk = 2048
    hop = blk // 2
    win = np.hanning(blk).astype(np.float32)
    n_blocks = max(1, (len(x) - blk) // hop + 1)
    freqs = np.fft.rfftfreq(blk, 1 / SR)
    for b in range(n_blocks):
        s = b * hop
        seg = x[s:s + blk]
        if len(seg) < blk:
            seg = np.pad(seg, (0, blk - len(seg)))
        p = b / max(n_blocks - 1, 1)
        fc = f0 * (f1 / f0) ** p
        bw = fc / q
        resp = np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
        y = np.fft.irfft(np.fft.rfft(seg * win) * resp)
        out[s:s + blk] += y[: len(out[s:s + blk])]
    return out


def whoosh(dur=0.45, seed=0, peak=0.55, low=False):
    """Air whoosh whose loudest moment sits at `peak` (0..1) of its length."""
    rng = np.random.default_rng(seed)
    n = int(max(dur, 0.12) * SR)
    t = np.linspace(0, 1, n)
    envl = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / max(1 - peak, 0.05) * 3.2))
    f0, f1 = (180, 900) if low else (400, 3200)
    body = _bandsweep(_noise(n, rng), f0, f1 * (0.8 + 0.4 * rng.random()), q=1.1)
    air = _bandsweep(_noise(n, rng), 3000, 9000, q=0.9) * 0.35
    x = (body + air) * envl
    return x / (np.abs(x).max() + 1e-9)


def swish(seed=0):
    return whoosh(0.22, seed, peak=0.45)


def zoom(dur=0.35, seed=0):
    """Punch-in: short swish that lands on a soft low thump (layered = feels 'expensive')."""
    w = whoosh(max(0.18, dur), seed, peak=0.8)
    th = _thump(0.18, seed) * 0.5
    out = np.zeros(len(w) + len(th) // 2, np.float32)
    out[: len(w)] += w
    s = int(len(w) * 0.8)
    out[s:s + len(th)] += th[: len(out) - s]
    return out


def _thump(dur=0.25, seed=0, f=58):
    t = _t(dur)
    sweep = f * (1 + 1.5 * np.exp(-t * 30))
    x = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t * 12)
    return x.astype(np.float32)


def hit_soft(seed=0):
    rng = np.random.default_rng(seed)
    t = _t(0.5)
    sub = _thump(0.5, seed, 52)
    click = _noise(len(t), rng) * np.exp(-t * 90) * 0.4
    return (sub + click) / 1.3


def hit_lux(seed=0):
    """Layered cinematic hit: sub + soft body + shimmer tail."""
    base = hit_soft(seed)
    sh = shimmer(seed, 1.0) * 0.35
    out = np.zeros(max(len(base), len(sh)), np.float32)
    out[: len(base)] += base
    out[: len(sh)] += sh
    return out


def shimmer(seed=0, dur=0.8):
    rng = np.random.default_rng(seed)
    t = _t(dur)
    base = 1318.5 * 2 ** (rng.integers(-2, 3) / 12)
    x = sum(np.sin(2 * np.pi * base * m * (1 + 0.002 * rng.standard_normal()) * t) / m ** 1.3
            for m in (1, 2, 3, 4.2, 5.4))
    x = x * np.exp(-t * 4.5) * np.minimum(t / 0.01, 1)
    return (x / np.abs(x).max()).astype(np.float32)


def riser(dur=1.2, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = _bandsweep(_noise(n, rng), 300, 6000, q=1.5) * t ** 2
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * t ** 2) / SR) * t ** 3 * 0.25
    x = x / (np.abs(x).max() + 1e-9) + tone
    return (x / np.abs(x).max()).astype(np.float32)


def boing(seed=0):
    t = _t(0.4)
    f = 180 + 260 * np.exp(-t * 9) * (1 + 0.3 * np.sin(2 * np.pi * 14 * t))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)).astype(np.float32)


SYNTH = {"whoosh": whoosh, "swish": swish, "zoom": zoom, "hit_soft": hit_soft, "hit_lux": hit_lux,
         "shimmer": shimmer, "riser": riser, "boing": boing}


# ---------------------------------------------------------------- render a cue
def render(name):
    """name = sd:<kit>:<event>:<seed>[:<dur>] -> mono float32 at SR."""
    _, kit, event, seed, *rest = name.split(":")
    seed = int(seed)
    dur = float(rest[0]) if rest else None
    table = KITS.get(event, KITS["text_in"])
    cands = table.get(kit) or table.get("*") or next(iter(table.values()))
    src, h = _pick(cands, seed, event)
    if src.startswith("s:"):
        fn = SYNTH[src[2:]]
        if src[2:] in ("whoosh", "riser", "zoom") and dur:
            x = fn(dur, seed)
        else:
            x = fn(seed=seed)
    else:
        files = sorted(glob.glob(os.path.join(KEN, src[2:] + ".wav")))
        if not files:
            x = SYNTH["swish"](seed)
        else:
            f, h2 = _pick(files, seed, src)
            x = _pitch(_wav(f), ((h2 >> 8) % 7 - 3) * 0.4)          # ±1.2 semitone variation
    level = 0.85 + ((h >> 16) % 30) / 100                             # ±15% level variation
    return (x / (np.abs(x).max() + 1e-9) * level).astype(np.float32)


def typewriter(t0, text, dur, kit="clean", seed=0, gain=0.35):
    """One key click per character across `dur` seconds (spaces quieter), a soft end sound."""
    chars = [c for c in text]
    n = max(len(chars), 1)
    cues = []
    for i, c in enumerate(chars):
        if c == " ":
            continue
        cues.append(cue("type_key", t0 + dur * i / n, seed * 97 + i, kit, gain * (0.8 + 0.4 * ((i * 7) % 5) / 5)))
    cues.append(cue("type_end", t0 + dur + 0.05, seed, kit, gain * 0.9))
    return cues


LEGACY = {"pop": "text_in", "click": "select", "tick": "word_pop", "ding": "cta", "notify": "cta",
          "hit": "impact", "boing": "sticker_in", "whoosh": "whoosh", "swish": "swish", "riser": "riser"}


TYPE_SPEED = 0.055          # seconds per character when text types itself on


def vary_entrances(items):
    """Text shouldn't all arrive the same way. Big text rotates type / pop / slide; glass labels
    and callouts type themselves on (with key sounds); serif words slide in."""
    cycle = ["type", "pop", "slide"]
    k = 0
    for it in sorted(items, key=lambda i: i["start"]):
        text = it.get("text") or ""
        if it.get("role") in ("takeover", "hook") and it.get("type") == "text":
            it["anim"] = cycle[k % len(cycle)]
            k += 1
        elif (it.get("type") == "badge" and it.get("shape") == "glass") or it.get("type") == "callout":
            it["anim"] = "type"
        elif it.get("type") == "sticker" and str(it.get("name", "")).startswith("custom:"):
            it["anim"] = "slide"
        if it.get("anim") == "type":
            it["type_dur"] = round(min(max(len(text) * TYPE_SPEED, 0.35), 1.6), 2)
    return items


def design(tl, cues, kit="clean"):
    """Turn the planner's rough cues into a designed soundtrack for this timeline:
    legacy names -> kit events (with variety), plus texture sounds for everything that appears.
    Whooshes only where something really moves (transitions, explicit zooms) — never on the
    automatic reframing zooms, or the edit sounds like wind. Explicit user sounds are kept."""
    out, n = [], 0
    items = tl.get("items", [])
    typed = [(it["start"], it) for it in items if it.get("anim") == "type"]
    clicks = {round(t, 2) for t, name, _ in cues if name == "click"}
    for t, name, g in cues:
        n += 1
        ev = LEGACY.get(name)
        if name == "click" and sum(1 for x in clicks if abs(x - t) < 0.4) > 2:
            ev = "type_key"                               # a run of clicks = typewriter title
        if ev is None:
            out.append((t, name, g))
            continue
        if ev in ("text_in", "sticker_in", "select") and any(abs(t - s) < 0.3 for s, _ in typed):
            continue                                      # typed items get key sounds instead
        dur = 1.2 if ev == "riser" else (0.5 if ev == "whoosh" else None)
        out.append(cue(ev, t, n, kit, g, dur))
    # typing: one key per letter while the text types on, then a soft end sound
    for i, (s, it) in enumerate(typed):
        text = it.get("text") or ""
        out += typewriter(s, text, it.get("type_dur", 0.6), kit, seed=400 + i, gain=0.32)
    # motion: only real moves get a whoosh
    for i, z in enumerate(tl.get("zooms", [])):
        if z.get("auto"):
            continue                                      # quiet reframing — felt, not heard
        if z.get("type") in ("punch", "whip"):
            out.append(cue("zoom_in", z["start"] - 0.22, i, kit, 0.3, 0.28))
        elif z.get("type") == "push" and z["end"] - z["start"] > 1.5:
            out.append(cue("whoosh", z["start"], i, kit, 0.12, min(z["end"] - z["start"], 2.8)))
    for i, tr in enumerate(tl.get("transitions", [])):     # whoosh peak lands on the cut
        d = max(tr.get("dur", 0.36) * 1.6, 0.45)
        out.append(cue("whoosh", tr["t"] - d * 0.55, 100 + i, kit, 0.45, d))
    # texture: glass icons tap, callouts get a swipe for the line
    for i, it in enumerate(items):
        if it.get("type") == "callout":
            out.append(cue("slide", it["start"], 200 + i, kit, 0.25))
        elif it.get("style") == "glass" and it.get("type") == "sticker" and it.get("anim") != "type":
            out.append(cue("glass", it["start"], 200 + i, kit, 0.4))
        elif it.get("type") == "sticker" and it.get("anim") == "slide":
            out.append(cue("slide", it["start"], 200 + i, kit, 0.3))
    # captions: highlighted keywords tick as they appear (max one per 1.5 s, never under a big sound)
    cap = tl.get("captions") or {}
    if cap.get("style") in ("pop", "duo", "boxed", "rainbow", "stack", "popin", "kinetic") and cap.get("words"):
        from .captions import auto_keywords
        kws = cap.get("keywords")
        idx = auto_keywords(cap["words"]) if kws is None else [
            i for i, w in enumerate(cap["words"]) if i in kws or w["w"].lower().strip(".,!?") in {str(k).lower() for k in kws}]
        busy = sorted(t for t, _, g in out if g >= 0.3)
        last = -9.0
        for i in idx:
            t = cap["words"][i]["start"]
            if t - last >= 1.5 and not any(abs(t - b) < 0.4 for b in busy):
                out.append(cue("word_pop", t, 300 + i, kit, 0.2))
                last = t
    return sorted(out)
