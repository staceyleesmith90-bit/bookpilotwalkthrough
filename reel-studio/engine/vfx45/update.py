"""Pull the latest effects from github.com/Vibha-Ramprakash/claude-video-effects (she adds new ones often).

    python -m engine effects-update            fetch, re-apply our fixes, report what's new
    python -m engine effects-update check      only say whether there is anything new

Our changes to her fx.py live in PATCHES below and are applied to every new version. If one no longer
fits (she changed that code), the update stops and keeps the working version, so nothing breaks.
New effects need nothing else: engine/scenefx.py reads their names from fx.py and puts them in plans,
the Studio's Scene effects page and the sound design automatically.
"""
import json, os, re, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "https://github.com/Vibha-Ramprakash/claude-video-effects"
STATE = os.path.join(HERE, "upstream.json")

# (what her code says, what ours says) — applied in order to a fresh fx.py
PATCHES = [
    ("ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
     "ROOT = os.path.dirname(os.path.abspath(__file__))       # Reel Studio: fonts/ and models/ sit next to this file"),
    ("    left = c.fx > c.W / 2\n",
     "    left = e.o['side'] == 'left' if e.o.get('side') else c.fx > c.W / 2   # Reel Studio: 'side' locks it (no flipping)\n"),
    ("    place(c, shadowed(im, 14, 8, 90), x, max(im.height / 2 + c.H * 0.06, c.fy - c.fw * 1.4), 0.8 + 0.2 * pop, 0, "
     "clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2), behind=True)",
     "    y = float(e.o['y']) * c.H if e.o.get('y') else max(im.height / 2 + c.H * 0.06, c.fy - c.fw * 1.4)\n"
     "    place(c, shadowed(im, 14, 8, 90), x, y, 0.8 + 0.2 * pop, 0, clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2), "
     "behind=not e.o.get('front'))"),
    ("('@vibha.in.progress  ·  ' + meta) if meta else '@vibha.in.progress'",
     "(e.o.get('handle', '@vibha.in.progress') + '  ·  ' + meta) if meta else e.o.get('handle', '@vibha.in.progress')"),
    ("# Optional private effects (not part of the public pack). If fx_private.py sits next to this file, its effects load too.\n"
     "_PRIV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fx_private.py')\n"
     "if os.path.exists(_PRIV): exec(open(_PRIV).read(), globals())\n",
     "# (Reel Studio: the original's optional \"fx_private.py\" loader is left out — only this public pack runs.)\n"),
    ("model_asset_path=os.path.join(ROOT, 'models', 'selfie_segmenter.tflite')",
     "model_asset_path=os.path.join(os.path.dirname(os.path.dirname(ROOT)), 'library', 'models', 'selfie_segmenter.tflite')"),
]


def effect_names(path=None):
    """[(name, description)] from fx.py's @effect(...) lines — read as text, no imports needed."""
    src = open(path or os.path.join(HERE, "fx.py"), encoding="utf-8").read()
    return re.findall(r"""@effect\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]""", src)


def state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"commit": "99c9a3393ee14d39bea155a05c73dc069f02f16f"}


def latest_commit():
    out = subprocess.run(["git", "ls-remote", REPO, "HEAD"], capture_output=True, text=True, timeout=60).stdout
    return out.split()[0] if out.strip() else None


def update(check_only=False):
    """Returns a plain-words report (dict)."""
    have = state().get("commit")
    head = latest_commit()
    if not head:
        return {"ok": False, "message": "Couldn't reach GitHub — try again later."}
    if head == have:
        return {"ok": True, "new": [], "message": f"Up to date ({len(effect_names())} effects, commit {have[:7]})."}
    if check_only:
        return {"ok": True, "new": None, "message": f"New version available ({head[:7]}, you have {have[:7]})."}
    tmp = tempfile.mkdtemp(prefix="vfx45-")
    try:
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
        subprocess.run(["git", "clone", "-q", "--depth", "1", REPO, tmp], check=True, env=env, timeout=600)
        src = open(os.path.join(tmp, "scripts", "fx.py"), encoding="utf-8").read()
        missing = [old[:60] for old, _ in PATCHES if old not in src]
        if missing:
            return {"ok": False, "message": "Her code changed where our fixes go — kept the working version. "
                                            "Needs a hand merge: " + "; ".join(missing)}
        for old, new in PATCHES:
            src = src.replace(old, new)
        before = {n for n, _ in effect_names()}
        cand = os.path.join(tmp, "fx_patched.py")
        open(cand, "w", encoding="utf-8").write(src)
        compile(src, cand, "exec")                       # never install code that doesn't even parse
        new = [(n, d) for n, d in effect_names(cand) if n not in before]
        shutil.copy(cand, os.path.join(HERE, "fx.py"))
        for folder in ("fonts", "models"):              # new fonts / models she added (selfie model: ours)
            for f in os.listdir(os.path.join(tmp, folder)):
                if f == "selfie_segmenter.tflite":
                    continue
                dst = os.path.join(HERE, folder, f)
                if not os.path.exists(dst):
                    shutil.copy(os.path.join(tmp, folder, f), dst)
        shutil.copy(os.path.join(tmp, "LICENSE"), os.path.join(HERE, "LICENSE"))
        json.dump({"commit": head, "effects": len(effect_names())}, open(STATE, "w"), indent=1)
        return {"ok": True, "new": new, "commit": head,
                "message": (f"Updated to {head[:7]}: {len(new)} new effect(s) — " + ", ".join(n for n, _ in new))
                if new else f"Updated to {head[:7]} (improvements to existing effects, no new names)."}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
