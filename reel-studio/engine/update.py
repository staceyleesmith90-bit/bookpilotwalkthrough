"""'Update me' — get the latest Reel Studio without touching the user's own stuff.

Keeps: brand/ (brand, logo, fonts, voice hub), projects/, inbox/, out/, downloaded models and
emoji cache. Replaces everything else (engine, skills, library, docs).
Source: a git checkout pulls; otherwise the zip at library/update.json -> "zip"
(the seller sets this to the buyer download / release URL).
"""
import io, json, os, shutil, subprocess, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = {"brand", "brands", "projects", "inbox", "out", "trash", ".git", ".venv", "venv"}
KEEP_LIB = {"emoji-cache", "models"}


def _config():
    p = os.path.join(ROOT, "library", "update.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def local_version():
    p = os.path.join(ROOT, "VERSION")
    return open(p).read().strip() if os.path.exists(p) else "0"


def check():
    """Returns a one-line notice if a newer version exists (quiet if offline)."""
    url = _config().get("version_url")
    try:
        if _config().get("feed") or not url:
            latest = json.loads(urllib.request.urlopen(((_config().get("feed") or FEED).rstrip("/")) + "/latest",
                                                       timeout=4).read().decode() or "{}").get("version") or "0"
        else:
            latest = urllib.request.urlopen(url, timeout=4).read().decode().strip()
    except Exception:
        return None
    key = lambda v: [int(x) for x in v.split(".") if x.isdigit()]
    if key(latest) > key(local_version()):
        return f"✨ Reel Studio {latest} is available (you have {local_version()}). Say \"update me\"."
    return None


FEED = "https://reelstudio.systemspilot.co.za/api/update"
WHATSNEW = os.path.join(ROOT, "out", "whatsnew.json")
STAMP = os.path.join(ROOT, "out", ".last-update-check")


def _vkey(v):
    return [int(x) for x in str(v).split(".") if x.isdigit()]


def _apply_zip(data):
    """Install an update zip over the app, keeping everything that belongs to the user."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    top = names[0].split("/")[0] if all(n.split("/")[0] == names[0].split("/")[0] for n in names) and "/" in names[0] else ""
    for name in names:
        rel = name[len(top) + 1:] if top else name
        if not rel or rel.endswith("/") or ".." in rel.split("/"):
            continue
        first = rel.split("/")[0]
        if first in KEEP or (first == "library" and rel.split("/")[1:2] and rel.split("/")[1] in KEEP_LIB):
            continue
        dst = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with z.open(name) as src, open(dst, "wb") as out:
            shutil.copyfileobj(src, out)


def auto_update(key=None, machine=None, force=False, feed=None):
    """The automatic update (runs quietly when Reel Studio starts, at most once a day).
    Asks the update feed for the newest version; with an active subscription downloads and installs it.
    -> a one-line message, or None when there's nothing to do. Never raises."""
    import hashlib, time
    feed = (feed or _config().get("feed") or FEED).rstrip("/")
    try:
        if not force and os.path.exists(STAMP) and time.time() - os.path.getmtime(STAMP) < 86400:
            return None
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        open(STAMP, "w").write(str(time.time()))
        rel = json.loads(urllib.request.urlopen(feed + "/latest", timeout=6).read().decode() or "{}")
        if not rel.get("version") or _vkey(rel["version"]) <= _vkey(local_version()):
            return None
        if _vkey(rel.get("min_extension", "0")) > _vkey(os.environ.get("REEL_EXTENSION_VERSION", "999")):
            return (f"Reel Studio {rel['version']} needs the new installer: download it from your account page "
                    "and double-click it (your brands and reels stay as they are).")
        key = key or os.environ.get("REEL_LICENSE_KEY", "")
        if not machine:                                   # same id the licence check registers (extension/src/licence.py)
            import platform, uuid
            machine = hashlib.sha256(f"{platform.node()}|{uuid.getnode()}|{platform.system()}".encode()).hexdigest()[:24]
        req = urllib.request.Request(feed + "/download", data=json.dumps({"key": key, "machine": machine}).encode(),
                                     headers={"Content-Type": "application/json"})
        data = urllib.request.urlopen(req, timeout=300).read()
        if hashlib.sha256(data).hexdigest() != rel.get("sha256"):
            return None                                   # damaged download: try again tomorrow
        old = local_version()
        _apply_zip(data)
        note = {"version": rel["version"], "from": old, "notes": rel.get("notes", ""), "when": time.time()}
        json.dump(note, open(WHATSNEW, "w", encoding="utf-8"), indent=1)
        return f"Updated Reel Studio {old} → {rel['version']}. {rel.get('notes', '')}".strip()
    except Exception:
        return None


def whats_new():
    try:
        return json.load(open(WHATSNEW, encoding="utf-8"))
    except Exception:
        return None


def update():
    """'Update me' — right now, on request."""
    if os.path.isdir(os.path.join(ROOT, ".git")):
        r = subprocess.run(["git", "-C", ROOT, "pull", "--ff-only"], capture_output=True, text=True)
        msg = (r.stdout + r.stderr).strip()
    elif _config().get("feed") or not _config().get("zip"):
        msg = auto_update(force=True) or f"You're on the newest version ({local_version()})."
        return msg + "\nYour brands, reels and uploads were not touched."
    else:
        _apply_zip(urllib.request.urlopen(_config()["zip"], timeout=120).read())
        msg = "Downloaded and installed the latest version."
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(ROOT, "requirements.txt")])
    return msg + "\nYour brand, projects and inbox were not touched. Run: python -m engine setup-check"
