"""The user's own corners of the Studio: Favourites, Uploads (the inbox), Trash and Notifications.

Favourites  brand/favourites.json — per brand (each brand has its own favourite looks, sounds, templates)
Uploads     inbox/ — everything they dropped in (videos, photos, sounds, filters, fonts)
Trash       trash/ — deleted reels and uploads, restorable for 30 days, then removed for good
Notifications — built from what's actually on disk: finished reels, cuts ready to review, update notes
"""
import json, os, shutil, time, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAV = os.path.join(ROOT, "brand", "favourites.json")
INBOX = os.path.join(ROOT, "inbox")
TRASH = os.path.join(ROOT, "trash")
KEEP_DAYS = 30

KINDS = {".mp4": "video", ".mov": "video", ".m4v": "video", ".webm": "video",
         ".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".webp": "photo", ".gif": "photo", ".heic": "photo",
         ".mp3": "sound", ".wav": "sound", ".m4a": "sound", ".aac": "sound", ".ogg": "sound", ".flac": "sound",
         ".cube": "filter", ".ttf": "font", ".otf": "font"}


# ---------------------------------------------------------------- favourites
def favourites():
    try:
        return json.load(open(FAV, encoding="utf-8"))
    except Exception:
        return []


def toggle_favourite(kind, ident, title, extra=None):
    """Star / unstar. -> True when it is now a favourite."""
    favs = favourites()
    hit = [f for f in favs if f["kind"] == kind and f["id"] == ident]
    if hit:
        favs = [f for f in favs if f not in hit]
        on = False
    else:
        favs.append({"kind": kind, "id": ident, "title": title, "extra": extra or {}, "added": time.time()})
        on = True
    os.makedirs(os.path.dirname(FAV), exist_ok=True)
    json.dump(favs, open(FAV, "w", encoding="utf-8"), indent=1)
    return on


# ---------------------------------------------------------------- uploads
def _safe_name(name):
    n = os.path.basename(name or "")
    if not n or n.startswith(".") or n in ("..",):
        raise ValueError("Bad file name.")
    return n


def uploads():
    if not os.path.isdir(INBOX):
        return []
    out = []
    for f in os.listdir(INBOX):
        p = os.path.join(INBOX, f)
        if f.startswith(".") or not os.path.isfile(p):
            continue
        kind = KINDS.get(os.path.splitext(f)[1].lower(), "other")
        out.append({"name": f, "kind": kind, "size": os.path.getsize(p), "when": os.path.getmtime(p)})
    return sorted(out, key=lambda x: -x["when"])


def upload_path(name):
    p = os.path.join(INBOX, _safe_name(name))
    if not os.path.isfile(p):
        raise FileNotFoundError(name)
    return p


def video_thumb(name):
    import subprocess
    src = upload_path(name)
    out = os.path.join(ROOT, "out", "thumbs", "%s-%d.jpg" % (_safe_name(name), int(os.path.getmtime(src))))
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", src, "-frames:v", "1",
                        "-vf", "scale=320:-2", out], capture_output=True)
        if not os.path.exists(out):      # very short clip: take the first frame
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-frames:v", "1", "-vf", "scale=320:-2", out],
                           capture_output=True)
    return out


# ---------------------------------------------------------------- trash
def _index():
    try:
        return json.load(open(os.path.join(TRASH, "index.json"), encoding="utf-8"))
    except Exception:
        return []


def _save(idx):
    os.makedirs(TRASH, exist_ok=True)
    json.dump(idx, open(os.path.join(TRASH, "index.json"), "w", encoding="utf-8"), indent=1)


def to_trash(kind, ident, title=None):
    """kind = 'reel' (a project folder) or 'upload' (a file in the inbox)."""
    if kind == "reel":
        from . import project
        src = project.path(ident)
        if not os.path.isfile(os.path.join(src, "project.json")):
            raise ValueError("No reel like that.")
    elif kind == "upload":
        src = upload_path(ident)
    else:
        raise ValueError("Can't delete that.")
    tid = uuid.uuid4().hex[:10]
    dst = os.path.join(TRASH, "items", tid)
    os.makedirs(dst, exist_ok=True)
    shutil.move(src, os.path.join(dst, os.path.basename(src)))
    idx = _index()
    idx.append({"id": tid, "kind": kind, "name": os.path.basename(src), "title": title or os.path.basename(src),
                "when": time.time()})
    _save(idx)
    return tid


def trash_list():
    """Trash contents (and quietly empties anything older than 30 days)."""
    idx, keep = _index(), []
    for t in idx:
        if time.time() - t["when"] > KEEP_DAYS * 86400:
            shutil.rmtree(os.path.join(TRASH, "items", t["id"]), ignore_errors=True)
        else:
            keep.append(t)
    if len(keep) != len(idx):
        _save(keep)
    for t in keep:
        t["days_left"] = max(1, KEEP_DAYS - int((time.time() - t["when"]) / 86400))
    return sorted(keep, key=lambda t: -t["when"])


def restore(tid):
    idx = _index()
    t = next((x for x in idx if x["id"] == tid), None)
    if not t:
        raise ValueError("Not in the trash any more.")
    from . import project
    base = project.PROJECTS if t["kind"] == "reel" else INBOX
    os.makedirs(base, exist_ok=True)
    dst = os.path.join(base, t["name"])
    if os.path.exists(dst):                       # something new took the name: keep both
        stem, ext = os.path.splitext(t["name"])
        dst = os.path.join(base, f"{stem}-restored{ext}")
    shutil.move(os.path.join(TRASH, "items", tid, t["name"]), dst)
    shutil.rmtree(os.path.join(TRASH, "items", tid), ignore_errors=True)
    _save([x for x in idx if x["id"] != tid])
    return os.path.basename(dst)


def empty_trash():
    n = len(_index())
    shutil.rmtree(TRASH, ignore_errors=True)
    return n


# ---------------------------------------------------------------- notifications
_update_note = {"t": 0, "note": None}


def notifications(jobs=None):
    """What's new, from what's really on disk. -> [{id, text, when, action}] newest first."""
    from . import project
    out = []
    for slug in project.list_projects():
        meta = project.load(slug, "project.json") or {}
        title = (project.load(slug, "brief.json") or {}).get("topic") or slug
        final = project.path(slug, "renders", "final.mp4")
        rc = project.path(slug, "roughcut.json")
        if os.path.exists(final):
            out.append({"id": f"done-{slug}-{int(os.path.getmtime(final))}", "text": f"“{title}” is finished and ready to post.",
                        "when": os.path.getmtime(final), "action": f"/editor?p={slug}"})
        elif os.path.exists(rc) and meta.get("source"):
            out.append({"id": f"cut-{slug}-{int(os.path.getmtime(rc))}", "text": f"The rough cut of “{title}” is ready to review.",
                        "when": os.path.getmtime(rc), "action": f"/review?p={slug}"})
    for slug, j in (jobs or {}).items():
        if slug.startswith("_"):
            continue
        if j.get("state") == "error":
            out.append({"id": f"err-{slug}", "text": f"Something went wrong with “{slug}”. Tell Claude: “my reel {slug} failed”.",
                        "when": time.time(), "action": None})
        elif j.get("state") in ("roughcut", "rendering", "music"):
            out.append({"id": f"busy-{slug}-{j['state']}", "text": f"Working on “{slug}”…", "when": time.time(), "action": None})
    try:
        from .update import whats_new
        w = whats_new()
        if w:
            out.append({"id": f"new-{w['version']}", "text": f"✨ Updated to {w['version']}. {w.get('notes', '')}".strip(),
                        "when": w["when"], "action": None})
    except Exception:
        pass
    if time.time() - _update_note["t"] > 6 * 3600:
        _update_note["t"] = time.time()
        try:
            from .update import check
            _update_note["note"] = check()
        except Exception:
            _update_note["note"] = None
    if _update_note["note"]:
        out.append({"id": "update-" + str(abs(hash(_update_note["note"])) % 10 ** 8), "text": _update_note["note"],
                    "when": _update_note["t"], "action": None})
    return sorted(out, key=lambda n: -n["when"])[:12]
