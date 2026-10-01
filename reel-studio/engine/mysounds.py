"""The user's OWN sounds — taught once, used in every reel after that.

Three ways in (all stay on the user's computer; nothing is uploaded or shared):
  1. Their CapCut favourites: they make one CapCut project (e.g. "my favorites"), drop in the sounds
     they love (optionally with a text clip + animation over a sound to say "this text gets this sound"),
     close CapCut, and say "learn my sounds from my CapCut project called my favorites".
     We read that draft on THEIR computer and copy the sound files CapCut already downloaded for them.
  2. A folder of sounds they downloaded themselves (Pixabay, Epidemic Sound, their own recordings):
     inbox/sound-effects/ → "use the sound effects in my inbox".
  3. Single files with a role: learn(path, as_event="typing").

Learned sounds live in brand/sounds/<event>/*.wav and take priority over the built-in CC0 library
for that kind of moment. brand/sounds/pairs.json keeps text-animation → sound pairings.
The sounds remain the user's licence: they are only used inside their own reels on their own computer.
"""
import glob, json, os, re, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = os.path.join(ROOT, "brand", "sounds")
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".aif", ".aiff", ".opus", ".webm")

# words in a sound's name → which moments it is for (first match wins; order matters)
ROLES = [
    (r"typ|keyboard|keys?\b|kacha", ["typing"]),
    (r"glitter|sparkle|shine|twinkle|magic|shimmer|chime|appearance", ["reveal", "sparkle"]),
    (r"coin|cash|ka-?ching|register|earn|money", ["money"]),
    (r"shutter|camera|kasha", ["shutter"]),
    (r"pencil|writ|scribble|marker|chalk|pen\b", ["highlight", "writing"]),
    (r"wrong|error|fail|incorrect|buzz|record|scratch|needle", ["wrong"]),
    (r"riser|rise|build", ["riser"]),
    (r"glitch", ["glitch"]),
    (r"ding|bell|prompt|notif|alert", ["cta", "type_end"]),
    (r"whoosh|swoosh|swish|swipe|wind|fuwa|air|slide", ["whoosh", "swish", "slide", "transition"]),
    (r"pop|bubble|bloop", ["word_pop", "text_in", "sticker_in"]),
    (r"click|tap|mouse|button|select|decision|stationery|snap", ["select", "text_in"]),
    (r"hit|impact|boom|thud|punch|drum|kick", ["impact"]),
    (r"page|paper|flip", ["page", "slide"]),
]


def role_for(name):
    n = name.lower()
    for pat, events in ROLES:
        if re.search(pat, n):
            return events
    return None


def _guess_by_sound(path):
    """No helpful name: guess from length (short = click, medium = pop/whoosh, long = typing)."""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        d = float(out)
    except Exception:
        return ["text_in"]
    if d < 0.25:
        return ["select", "text_in"]
    if d < 0.8:
        return ["word_pop", "text_in", "sticker_in"]
    if d < 2.0:
        return ["whoosh", "swish", "transition"]
    return ["typing"]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "sound"


def _to_wav(src, dst, max_sec=6):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-t", str(max_sec), "-ac", "1", "-ar", "44100",
                        "-af", "silenceremove=start_periods=1:start_threshold=-50dB", dst],
                       capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(dst)


def learn(path, name=None, as_event=None):
    """Copy one sound into brand/sounds for the moments it suits. -> list of events."""
    name = name or os.path.splitext(os.path.basename(path))[0]
    events = [as_event] if as_event else (role_for(name) or _guess_by_sound(path))
    for ev in events:
        _to_wav(path, os.path.join(MINE, ev, _slug(name) + ".wav"))
    _index_add(name, events, path)
    return events


def _index_add(name, events, src):
    idx = index()
    idx["sounds"] = [s for s in idx["sounds"] if s["name"] != name] + [
        {"name": name, "events": events, "from": os.path.basename(src)}]
    _save(idx)


def index():
    try:
        return json.load(open(os.path.join(MINE, "index.json"), encoding="utf-8"))
    except Exception:
        return {"sounds": [], "pairs": []}


def _save(idx):
    os.makedirs(MINE, exist_ok=True)
    json.dump(idx, open(os.path.join(MINE, "index.json"), "w", encoding="utf-8"), indent=1)


def files_for(event):
    """The user's own sound files for one kind of moment (empty when they haven't taught any)."""
    return sorted(glob.glob(os.path.join(MINE, event, "*.wav")))


def pair_for(animation):
    """The sound the user paired with a text animation in CapCut (e.g. 'Typewriter'), or None."""
    a = (animation or "").lower()
    for p in index().get("pairs", []):
        if p["animation"].lower() == a:
            return p
    return None


def learn_folder(folder):
    out = []
    for f in sorted(os.listdir(folder)):
        p = os.path.join(folder, f)
        if f.lower().endswith(AUDIO_EXT):
            out.append((f, learn(p)))
        elif os.path.isdir(p):                       # a sub-folder name is the role: sound-effects/typing/*.mp3
            ev = role_for(f)
            for g in sorted(os.listdir(p)):
                if g.lower().endswith(AUDIO_EXT):
                    out.append((g, learn(os.path.join(p, g), as_event=ev[0] if ev else None)))
    return out


# ---------- CapCut favourites ----------
def _drafts():
    from .capcut import capcut_projects_folder
    root = capcut_projects_folder()
    return root, (sorted(os.listdir(root)) if root and os.path.isdir(root) else [])


def _read_draft(folder):
    for fn in ("draft_content.json", "draft_info.json"):
        p = os.path.join(folder, fn)
        if os.path.exists(p):
            raw = open(p, "rb").read()
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                continue
    return None


def learn_capcut(project_name, drafts_root=None):
    """Read a CapCut project the user made of their favourite sounds. -> report dict."""
    if drafts_root:
        root, names = drafts_root, sorted(os.listdir(drafts_root))
    else:
        root, names = _drafts()
    if not root:
        return {"ok": False, "why": "CapCut isn't installed on this computer (or has never saved a project)."}
    match = [n for n in names if n.lower().strip() == project_name.lower().strip()] or \
            [n for n in names if project_name.lower() in n.lower()]
    if not match:
        return {"ok": False, "why": f"No CapCut project called '{project_name}'.", "projects": names[:30]}
    folder = os.path.join(root, match[0])
    d = _read_draft(folder)
    if d is None:
        return {"ok": False, "project": match[0],
                "why": "Your CapCut version locks its project files, so I can't read the sound list from it. "
                       "Easiest instead: download the sounds you like (free at pixabay.com/sound-effects, or your "
                       "own Epidemic Sound account) into inbox/sound-effects and say 'use the sound effects in my inbox'."}
    mats = d.get("materials", {})
    audios = {a.get("id"): a for a in mats.get("audios", [])}
    texts = {t.get("id"): t for t in mats.get("texts", [])}
    anims = {a.get("id"): a for a in mats.get("material_animations", [])}
    learned, missing = [], []
    for a in audios.values():
        name = a.get("name") or os.path.basename(a.get("path", "")) or "sound"
        path = a.get("path", "")
        if path and os.path.exists(path):
            learned.append((name, learn(path, name=name)))
        else:
            missing.append(name)
    # text clip + animation laid over a sound → "this animation gets this sound"
    seg_audio, seg_text = [], []
    for tr in d.get("tracks", []):
        for s in tr.get("segments", []):
            tgt = s.get("target_timerange") or {}
            st, du = tgt.get("start", 0), tgt.get("duration", 0)
            mid = s.get("material_id")
            if mid in audios:
                seg_audio.append((st, du, audios[mid]))
            elif mid in texts:
                names = []
                for ref in s.get("extra_material_refs", []):
                    for an in anims.get(ref, {}).get("animations", []):
                        if an.get("name"):
                            names.append((an.get("type", "in"), an["name"]))
                seg_text.append((st, du, names))
    idx = index()
    pairs = {p["animation"]: p for p in idx.get("pairs", [])}
    for st, du, names in seg_text:
        for kind, an in names:
            for ast, adu, a in seg_audio:
                if st - 300_000 <= ast <= st + du:             # sound starts while the text is on (µs)
                    nm = a.get("name") or "sound"
                    pairs[an] = {"animation": an, "kind": kind, "sound": nm,
                                 "events": (role_for(nm) or ["text_in"]), "file": _slug(nm) + ".wav"}
    idx["pairs"] = list(pairs.values())
    _save(idx)
    return {"ok": True, "project": match[0], "learned": learned, "not_downloaded": missing,
            "pairs": idx["pairs"]}


def summary():
    idx = index()
    if not idx["sounds"]:
        return "No sounds of your own yet — using the built-in library."
    lines = [f"{len(idx['sounds'])} of your own sounds:"]
    for s in idx["sounds"]:
        lines.append(f"  - {s['name']} → {', '.join(s['events'])}")
    for p in idx.get("pairs", []):
        lines.append(f"  - text '{p['animation']}' ({p['kind']}) gets '{p['sound']}'")
    return "\n".join(lines)


def forget(name=None):
    """Forget one sound by name, or all of them (name=None)."""
    if name is None:
        shutil.rmtree(MINE, ignore_errors=True)
        return "Forgot all your sounds — back to the built-in library."
    idx = index()
    keep = [s for s in idx["sounds"] if s["name"].lower() != name.lower()]
    for ev in os.listdir(MINE) if os.path.isdir(MINE) else []:
        f = os.path.join(MINE, ev, _slug(name) + ".wav")
        if os.path.exists(f):
            os.remove(f)
    idx["sounds"] = keep
    idx["pairs"] = [p for p in idx.get("pairs", []) if p["sound"].lower() != name.lower()]
    _save(idx)
    return f"Forgot '{name}'."
