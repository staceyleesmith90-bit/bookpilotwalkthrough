"""'Update me' — get the latest Reel Studio without touching the user's own stuff.

Keeps: brand/ (brand, logo, fonts, voice hub), projects/, inbox/, out/, downloaded models and
emoji cache. Replaces everything else (engine, skills, library, docs).
Source: a git checkout pulls; otherwise the zip at library/update.json -> "zip"
(the seller sets this to the buyer download / release URL).
"""
import io, json, os, shutil, subprocess, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = {"brand", "projects", "inbox", "out", ".git", ".venv", "venv"}
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
    if not url:
        return None
    try:
        latest = urllib.request.urlopen(url, timeout=4).read().decode().strip()
    except Exception:
        return None
    key = lambda v: [int(x) for x in v.split(".") if x.isdigit()]
    if key(latest) > key(local_version()):
        return f"✨ Reel Studio {latest} is available (you have {local_version()}). Say \"update me\"."
    return None


def update():
    if os.path.isdir(os.path.join(ROOT, ".git")):
        r = subprocess.run(["git", "-C", ROOT, "pull", "--ff-only"], capture_output=True, text=True)
        msg = (r.stdout + r.stderr).strip()
    else:
        url = _config().get("zip")
        if not url:
            return "No update source set (library/update.json -> zip). Ask the seller for the download link."
        data = urllib.request.urlopen(url, timeout=120).read()
        z = zipfile.ZipFile(io.BytesIO(data))
        top = z.namelist()[0].split("/")[0]
        for name in z.namelist():
            rel = name[len(top) + 1:]
            if not rel or rel.endswith("/"):
                continue
            first = rel.split("/")[0]
            if first in KEEP or (first == "library" and rel.split("/")[1:2] and rel.split("/")[1] in KEEP_LIB):
                continue
            dst = os.path.join(ROOT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with z.open(name) as src, open(dst, "wb") as out:
                shutil.copyfileobj(src, out)
        msg = "Downloaded and installed the latest version."
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(ROOT, "requirements.txt")])
    return msg + "\nYour brand, projects and inbox were not touched. Run: python -m engine setup-check"
