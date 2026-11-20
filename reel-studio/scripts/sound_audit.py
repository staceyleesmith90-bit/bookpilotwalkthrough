"""Listen to every sound in library/sfx once with earshot (github.com/Leonxlnx/earshot, MIT) and save what we learn
to library/sfx/audit.json, so Reelmate can use it on any computer WITHOUT the 1.1 GB listening models:
  real     p_real: 1 = a real recording / pro-produced, 0 = sounds made by code (game-like)
  hit      seconds from the start of the file to its loudest point (the sound is shifted so this lands on the cut)
  sounds   what it sounds like, in words (earshot's top reading)
Run again after adding sounds:  python scripts/sound_audit.py
"""
import glob, json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "library", "sfx")
OUT = os.path.join(SFX, "audit.json")


def hit_time(path):
    import soundfile as sf
    x, sr = sf.read(path, always_2d=True)
    x = np.abs(x).mean(1)
    if not len(x):
        return 0.0
    w = max(int(sr * 0.005), 1)                       # 5 ms envelope
    env = np.convolve(x, np.ones(w) / w, mode="same")
    peak = env.max() or 1
    onset = int(np.argmax(env > peak * 0.5))          # where it gets loud (the attack), not the very top
    return round(onset / sr, 3)


def main():
    from earshot import api
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    files = sorted(f for f in glob.glob(os.path.join(SFX, "**", "*.wav"), recursive=True))
    out = {}
    for i, f in enumerate(files):
        rel = os.path.relpath(f, SFX).replace(os.sep, "/")
        if rel in old and "--fresh" not in sys.argv:
            out[rel] = old[rel]
            continue
        r = api.realness(f)
        d = api.describe(f, top=3)
        top = d.get("top_tags") or []
        words = top[0].get("term", "") if top else ""
        out[rel] = {"real": round(float(r.get("p_real") if r.get("p_real") is not None else 0.5), 3), "hit": hit_time(f), "sounds": words[:80],
                    "designed": rel.startswith("earshot/")}
        if i % 25 == 0:
            print(i, len(files), rel, out[rel], flush=True)
    # rank every kind of sound for "Another sound" (best match first)
    import glob as _g
    sys.path.insert(0, ROOT)
    from engine.sounddesign import CHOICES, KIND_QUERY
    order = {}
    for label, pats in CHOICES.items():
        paths = sorted(f for p in pats for f in _g.glob(os.path.join(SFX, p)))
        if not paths:
            continue
        r = api.rank(paths, KIND_QUERY.get(label, label.lower()))
        items = r.get("ranked") or r.get("results") or r.get("items") or []
        ranked = [os.path.relpath(it.get("path") if isinstance(it, dict) else it, SFX).replace(os.sep, "/") for it in items]
        order[label] = ranked or [os.path.relpath(p, SFX).replace(os.sep, "/") for p in paths]
    out["_order"] = order
    json.dump(out, open(OUT, "w"), indent=0, sort_keys=True)
    print("saved", len(out), "sounds ->", OUT)


if __name__ == "__main__":
    main()
