"""Local editor server: the review page and the manual timeline editor.

    python -m engine editor [--port 8765]     -> http://localhost:8765

Runs entirely on the user's computer. Nothing is uploaded anywhere.
"""
import glob, time, io, json, os, re, threading, traceback, urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from .. import brand, layout, music, packs, project, render, roughcut, stickers, titles

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
JOBS = {}  # slug -> {"state", "file", "error"}


def _slug_ok(s):
    return bool(re.fullmatch(r"[a-z0-9-]+", s or "")) and os.path.isdir(project.path(s))


# built-in music Reelmate composes itself (royalty-free: it's ours) — the Finish page's music choices
BEDS = {"upbeat": {"mood": ["sunny"], "genre": ["indie pop"], "tempo": "116", "energy": "steady"},
        "groove": {"mood": ["playful"], "genre": ["afrobeats"], "tempo": "108", "energy": "steady"},
        "calm": {"mood": ["calm"], "genre": ["soft piano"], "tempo": "80", "energy": "steady"}}

_WHISPER = {}


def voice_note_text(data):
    """Voice note -> text with faster-whisper on the user's own computer (free, private, no Claude usage)."""
    import subprocess, tempfile
    from .. import transcribe as tr
    d = tempfile.mkdtemp()
    src, wav = os.path.join(d, "note.bin"), os.path.join(d, "note.wav")
    open(src, "wb").write(data)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
    if "m" not in _WHISPER:
        from faster_whisper import WhisperModel
        _WHISPER["m"] = WhisperModel(tr.MODEL_SIZE, device="auto", compute_type="int8")
    segs, _ = _WHISPER["m"].transcribe(wav, vad_filter=True)
    return " ".join(s.text.strip() for s in segs).strip()


def sound_list(slug):
    """Every sound effect in the reel with its second, a friendly name, and the user's choices."""
    from .. import sounddesign as sd
    pl = project.load(slug, "plan.json") or {}
    if not pl:
        return {"sounds": [], "choices": list(sd.CHOICES)}
    tl = project.build_timeline(slug)
    edits = pl.get("sfx_edits") or {}
    beats, t0, at = pl.get("beats") or [], 0.0, []
    from ..storyboard import texts_of
    for n, b in enumerate(beats):
        words = (b.get("text") or "").strip() or next((x["value"].split("\n")[0] for x in texts_of(b) if x["value"]), "")
        at.append((t0, f"Moment {n + 1}" + (f": {words}" if words else "")))
        t0 += float(b.get("dur", 3) or 3)
    rows, seen = [], set()
    for c in tl.get("audio", {}).get("sfx_auto", []):
        k = sd.key_of(c["t"])
        seen.add(k)
        e = edits.get(k, {})
        name = "file:" + e["file"] if e.get("file") else c["name"]
        moment = next((txt for s0, txt in reversed(at) if s0 <= c["t"]), "")
        rows.append({"t": c["t"], "key": k, "name": name, "label": sd.label_of(name), "off": bool(e.get("off")),
                     "swapped": bool(e.get("file")), "moment": moment[:60]})
    return {"sounds": rows, "choices": list(sd.CHOICES), "mode": pl.get("sound") or "modern"}

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # ------------------------------------------------------------ helpers
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, p, ctype):
        if not os.path.exists(p):
            return self.send_error(404)
        size = os.path.getsize(p)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:  # video seeking needs byte ranges
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                start = int(m.group(1) or 0)
                end = int(m.group(2)) if m.group(2) else size - 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(1 << 16, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except BrokenPipeError:
                    return
                remaining -= len(chunk)

    def _png(self, img):
        buf = io.BytesIO()
        img.save(buf, "PNG")
        body = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=60")
        self.end_headers()
        self.wfile.write(body)

    def _png(self, im, fmt="PNG"):
        import io
        buf = io.BytesIO()
        im.convert("RGB").save(buf, fmt, quality=88) if fmt == "JPEG" else im.save(buf, fmt)
        body = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg" if fmt == "JPEG" else "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    # ------------------------------------------------------------ routes
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        parts = [p for p in u.path.split("/") if p]
        try:
            if u.path in ("/", "/studio"):
                return self._file(os.path.join(STATIC, "studio.html"), "text/html")
            if u.path == "/editor":
                return self._file(os.path.join(STATIC, "editor.html"), "text/html")
            if u.path.startswith("/brand-sp/"):          # Systems Pilot logo files
                name = os.path.basename(u.path)
                return self._file(os.path.join(project.ROOT, "library", "brand-sp", name),
                                  "image/svg+xml" if name.endswith(".svg") else "image/png")
            if u.path == "/theme.css":                   # the Studio's look (one file for every page)
                return self._file(os.path.join(STATIC, "theme.css"), "text/css")
            if u.path == "/theme.js":
                return self._file(os.path.join(STATIC, "theme.js"), "application/javascript")
            if u.path == "/chat.js":                     # the chat box, shared by the Studio pages
                return self._file(os.path.join(STATIC, "chat.js"), "application/javascript")
            if u.path.startswith("/fonts/"):
                name = os.path.basename(u.path)
                return self._file(os.path.join(project.ROOT, "library", "fonts", name), "font/ttf")
            if u.path == "/api/overview":
                return self._json(overview())
            if u.path == "/api/title-preview":
                return self._png(title_preview({k: v[0] for k, v in q.items()}))
            if u.path == "/api/grade-preview":
                return self._file(grade_preview(q.get("grade", ["none"])[0], q.get("file", [None])[0]), "image/jpeg")
            if u.path == "/api/caption-preview":
                return self._png(caption_preview(q.get("style", ["karaoke"])[0], q.get("pack", [None])[0]))
            if u.path == "/api/fonts":
                from ..stickers import sticker_font
                pk = packs.load()
                st = pk.get("sticker", {})
                return self._json({"fonts": [{"name": os.path.splitext(os.path.basename(f))[0], "mine": os.sep + "brand" + os.sep in f}
                                             for f in packs.all_fonts()],
                                   "sticker": os.path.splitext(os.path.basename(sticker_font(pk, "lettering")["file"]))[0],
                                   "sticker_label": os.path.splitext(os.path.basename(sticker_font(pk, "label")["file"]))[0],
                                   "sticker_auto": not st.get("font"), "label_auto": not st.get("label_font")})
            if u.path == "/api/font-file":  # serve a font so the browser can preview it
                name = os.path.basename(q.get("name", [""])[0])
                hit = next((f for f in packs.all_fonts() if os.path.splitext(os.path.basename(f))[0] == name), None)
                return self._file(hit, "font/ttf") if hit else self.send_error(404)
            if u.path == "/api/sounds":
                from .. import trends
                return self._json({"sounds": trends.fresh(trends.load()), "how_to": trends.HOW_TO,
                                   "creative_center": trends.CREATIVE_CENTER, "commercial": trends.COMMERCIAL_LIBRARY})
            if u.path == "/api/templates":
                from .. import templates as tpl
                return self._json(tpl.all_templates())
            if u.path == "/api/sfx-play":                 # ▶ on the sound list: one cue, as it will sound
                from .. import sfx as sfxmod
                name = q.get("name", [""])[0]
                if not (name.startswith("sd:") or name.startswith("file:")) or ".." in name:
                    return self.send_error(404)
                if name.startswith("file:") and not os.path.exists(os.path.join(project.ROOT, "library", "sfx", name[5:])):
                    return self.send_error(404)
                out = os.path.join(project.ROOT, "out", "sfx-preview", re.sub(r"[^a-zA-Z0-9]+", "-", name) + ".wav")
                if not os.path.exists(out):
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    x = sfxmod.load(name)
                    sfxmod.write_wav(out, x, peak=0.7)
                return self._file(out, "audio/wav")
            if u.path == "/api/music-preview":
                from .. import music as mus
                brief = {"mood": q.get("mood", ["cosy"])[0].split(","), "genre": q.get("genre", ["lo-fi"])[0].split(","),
                         "tempo": q.get("tempo", ["medium"])[0], "energy": q.get("energy", ["steady"])[0]}
                out = os.path.join(project.ROOT, "out", "music-preview", re.sub(r"[^a-z0-9]+", "-", json.dumps(brief).lower()) + ".wav")
                if not os.path.exists(out):
                    mus.generate_free(brief, 12, out, seed=int(q.get("seed", ["1"])[0]))
                return self._file(out, "audio/wav")
            if u.path == "/api/brand-preview":
                out = os.path.join(project.ROOT, "brand", "previews", "brand.jpg")
                if not os.path.exists(out) or q.get("rebuild"):
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    brand.preview(packs.load(), out)
                return self._file(out, "image/jpeg")
            if u.path == "/api/brands":
                from .. import brands as brs, brandsetup
                rows = []
                for sl, label, on in brs.listing():
                    pk = brs.pack_for(sl) if (on and packs.has_brand()) or not on else None
                    rows.append({"slug": sl, "label": label, "active": on,
                                 "ready": bool(pk) and (not on or packs.has_brand()),
                                 "colors": (pk or {}).get("colors", {})})
                return self._json({"brands": rows, "routes": brandsetup.ROUTES, "guides": brandsetup.GUIDES,
                                   "vibes": brandsetup.VIBE_WORDS, "job": JOBS.get("_brand")})
            if u.path == "/api/resources":
                from .. import resources, mysounds, grades
                return self._json({"groups": resources.all_resources(), "luts": grades.my_luts(),
                                   "sounds": mysounds.index().get("sounds", [])})
            if u.path == "/api/hero-photo":           # the home banner phone: a mock-up photo (Pexels)
                return self._file(os.path.join(project.ROOT, "library", "samples", "hero-phone.jpg"), "image/jpeg")
            if u.path == "/api/hero-card":
                return self._file(os.path.join(project.ROOT, "library", "samples", "hero-photo.jpg"), "image/jpeg")
            if u.path == "/api/plan":                 # Reelmate is theirs: version + updates (no licence, no key)
                from .. import update as upd
                latest = None
                try:
                    latest = upd.check()
                except Exception:
                    pass
                return self._json({"version": upd.local_version(), "link_saved": bool(upd.download_link()),
                                   "latest": latest})
            if u.path == "/api/favourites":
                from .. import library_user as lu
                return self._json(lu.favourites())
            if u.path == "/api/uploads":
                from .. import library_user as lu
                return self._json(lu.uploads())
            if u.path in ("/api/upload-file", "/api/upload-thumb"):
                from .. import library_user as lu
                name = q.get("name", [""])[0]
                try:
                    if u.path == "/api/upload-thumb":
                        return self._file(lu.video_thumb(name), "image/jpeg")
                    import mimetypes
                    pth = lu.upload_path(name)
                    return self._file(pth, mimetypes.guess_type(pth)[0] or "application/octet-stream")
                except (ValueError, FileNotFoundError):
                    return self.send_error(404)
            if u.path == "/api/catalog":                 # this brand's products, services, reviews + the brand reel recipes
                from .. import brandreels
                return self._json({"catalog": brandreels.catalog(),
                                   "recipes": [{"id": k, "kind": v[0], "label": v[1], "about": v[2]} for k, v in brandreels.RECIPES.items()]})
            if u.path == "/api/make-job":
                return self._json(JOBS.get("make", {"state": "idle"}))
            if u.path.startswith("/style-examples/"):     # an example picture of each sticker style
                fn = os.path.basename(urllib.parse.unquote(u.path))
                full = os.path.join(project.ROOT, "library", "style-examples", fn)
                if not fn.endswith(".jpg") or not os.path.exists(full):
                    return self.send_error(404)
                return self._file(full, "image/jpeg")
            if u.path == "/api/ai-status":               # AI stickers: which generator, is Cloudflare connected
                from .. import aielements
                return self._json(aielements.status())
            if u.path == "/api/drive-job":
                return self._json(JOBS.get("drive", {"state": "idle"}))
            if u.path == "/api/trash":
                from .. import library_user as lu
                return self._json(lu.trash_list())
            if u.path == "/api/notifications":
                from .. import library_user as lu
                return self._json(lu.notifications(JOBS))
            if u.path == "/api/sample-photo":
                return self._file(os.path.join(project.ROOT, "library", "samples", "filter-sample.jpg"), "image/jpeg")
            if u.path == "/api/designs":
                from .. import brandsetup
                return self._json(brandsetup.designs())
            if u.path == "/api/look":
                n = int(q.get("i", ["1"])[0])
                return self._file(os.path.join(project.ROOT, "brand", "previews", f"look-{n}.jpg"), "image/jpeg")
            if u.path == "/api/prompts":
                from .. import prompts
                return self._json(prompts.all_prompts())
            if u.path == "/library":                     # the effects library page, fresh every time
                from ..library_page import build
                return self._file(build(open_it=False), "text/html")
            if u.path.startswith(("/library/sfx/", "/brand/sounds/")):   # sounds the library page plays
                rel = os.path.normpath(urllib.parse.unquote(u.path.lstrip("/")))
                full = os.path.join(project.ROOT, rel)
                if not rel.startswith(("library", "brand")) or ".." in rel or not full.endswith(".wav"):
                    return self.send_error(404)
                return self._file(full, "audio/wav")
            if u.path == "/finish":                      # Sound & Finish: sound, music, build, watch, download
                return self._file(os.path.join(STATIC, "finish.html"), "text/html")
            if u.path == "/storyboard":                  # Storyboard: every moment as a still — tick before the build
                return self._file(os.path.join(STATIC, "storyboard.html"), "text/html")
            if u.path == "/scenes":                      # Scene effects: 20 full-frame effects, previewed on their footage
                return self._file(os.path.join(STATIC, "scenes.html"), "text/html")
            if u.path == "/scrapbook":                   # Scrapbook maker: every setting, live preview
                return self._file(os.path.join(STATIC, "scrapbook.html"), "text/html")
            if u.path == "/review":
                return self._file(os.path.join(STATIC, "review.html"), "text/html")
            if u.path == "/api/projects":
                return self._json(project.list_projects())
            if u.path == "/api/library":
                return self._json({"stickers": sorted(stickers.all_stickers()),
                                   "inbox": [os.path.relpath(p, project.ROOT) for p in layout.inbox_files(project.ROOT)],
                                   "packs": list(packs.presets()) + (["brand"] if packs.has_brand() else [])})
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "p":
                slug = parts[2]
                if not _slug_ok(slug):
                    return self.send_error(404)
                what = parts[3] if len(parts) > 3 else ""
                if what == "chat":                      # the chat box: history + what Claude is doing now
                    from .. import chat
                    return self._json({"history": chat.history(slug)["messages"], "status": chat.status(slug),
                                       "available": chat.available()})
                if what == "scrapbooks":
                    return self._json(scrapbooks(slug))
                if what == "sound":                     # Sound & Finish page: what this reel has now
                    pl = project.load(slug, "plan.json") or {}
                    mu = pl.get("music") or {}
                    kind = "trending" if mu.get("none") or not mu else ("mine" if "/music/mine" in str(mu.get("file", "")) else
                                                                        next((k for k in BEDS if f"bed-{k}." in str(mu.get("file", ""))), "builtin"))
                    rd = project.path(slug, "renders")
                    files = [f for f in ("final.mp4", "final-for-trending-sound.mp4", "cover.jpg") if os.path.exists(os.path.join(rd, f))]
                    return self._json({"sound": pl.get("sound") or "modern", "music": kind, "gain": mu.get("gain", 0.6),
                                       "has_source": bool((project.load(slug, "project.json") or {}).get("source")),
                                       "files": files, "job": JOBS.get(slug, {"state": "idle"})})
                if what == "sounds":                    # the sound list: every sound, at which second, on/off/swapped
                    return self._json(sound_list(slug))
                if what == "elements":                  # this reel's sticker set (+ one sticker image)
                    from .. import aielements
                    if len(parts) > 4:
                        fn = os.path.basename(parts[4])
                        return self._file(project.path(slug, "elements", fn), "image/png")
                    return self._json({"stickers": [os.path.basename(f) for f in aielements.stickers_of(slug)],
                                       "about": aielements.about_of(slug), "connected": aielements.status(),
                                       "reference": next((os.path.basename(f) for f in glob.glob(project.path(slug, "elements", "reference.*"))), None),
                                       "examples": sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(project.ROOT, "library", "style-examples"))),
                                       "styles": list(aielements.STYLES), "job": JOBS.get(slug + ":elements")})
                if what == "storyboard":                # the moments, what each shows, ticks + notes
                    if len(parts) > 4:
                        fn = os.path.basename(parts[4])
                        return self._file(project.path(slug, "renders", "storyboard", fn), "image/jpeg")
                    sb = project.load(slug, "storyboard.json") or {}
                    return self._json(dict(sb, job=JOBS.get(slug + ":storyboard")))
                if what == "scenes":                    # the reel's lines + which scene effect each one has
                    return self._json(scene_lines(slug))
                if what == "scene-clip":                # one effect, played on this reel's own footage (cached)
                    path = scene_clip(slug, (q.get("fx") or [""])[0])
                    if not path:
                        return self.send_error(404)
                    return self._file(path, "image/webp")
                if what == "thumb":                     # small preview of a photo / video moment in this project
                    f = _media_ok(slug, (q.get("f") or [""])[0])
                    if not f:
                        return self.send_error(404)
                    at = (q.get("at") or [None])[0]
                    from ..scrapbook import _photo
                    im, _ = _photo(f + (f"@{at}" if at else ""))
                    im.thumbnail((240, 320))
                    return self._png(im, "JPEG")
                if what in ("timeline", "roughcut", "review", "plan"):
                    return self._json(project.load(slug, what + ".json") or {})
                if what == "proxy.mp4":
                    p = project.path(slug, "proxy.mp4")
                    if not os.path.exists(p) or q.get("rebuild"):
                        project.proxy(slug)
                    return self._file(p, "video/mp4")
                if what == "rough.mp4":
                    p = project.path(slug, "renders", "rough.mp4")
                    if not os.path.exists(p) or q.get("rebuild"):
                        project.rough_preview(slug)
                    return self._file(p, "video/mp4")
                if what == "render" and len(parts) > 4:
                    name = os.path.basename(parts[4])
                    ctype = "image/jpeg" if name.endswith(".jpg") else "video/mp4"
                    return self._file(project.path(slug, "renders", name), ctype)
                if what == "item" and len(parts) > 4:
                    tl = project.load(slug, "timeline.json")
                    item_id = parts[4].replace(".png", "")
                    it = next((i for i in tl["items"] if i["id"] == item_id), None)
                    if not it:
                        return self.send_error(404)
                    img = render.item_image(it, packs.load(tl.get("pack")))
                    buf = io.BytesIO()
                    img.save(buf, "PNG")
                    body = buf.getvalue()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return self.wfile.write(body)
                if what == "posts":
                    d = project.path(slug, "posts")
                    if len(parts) > 4:
                        fn = os.path.basename(parts[4])
                        ct = "application/zip" if fn.endswith(".zip") else "text/plain; charset=utf-8" if fn.endswith(".txt") else "image/png"
                        return self._file(os.path.join(d, fn), ct)
                    files = sorted(os.listdir(d)) if os.path.isdir(d) else []
                    cap = os.path.join(d, "caption.txt")
                    return self._json({"carousel": [f for f in files if f.startswith("carousel-")],
                                       "stories": [f for f in files if f.startswith("story-")],
                                       "caption": open(cap, encoding="utf-8").read() if os.path.exists(cap) else "",
                                       "job": JOBS.get(slug + ":posts")})
                if what == "job":
                    return self._json(JOBS.get(slug, {"state": "idle"}))
                if what == "cover.jpg":
                    return self._file(project.path(slug, "renders", "cover.jpg"), "image/jpeg")
                if what == "brief":
                    return self._json(project.load(slug, "brief.json") or {})
                if what == "music" and len(parts) > 4:
                    fn = os.path.basename(parts[4])
                    return self._file(project.path(slug, "music", fn), "audio/wav" if fn.endswith(".wav") else "audio/mpeg")
            return self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            return self._json({"error": str(e)}, 500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/update-link":   # their welcome-page link, saved once for free updates
                from .. import update as upd
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n) or b"{}")
                try:
                    upd.save_download_link(data.get("link", ""))
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)})
                return self._json({"ok": True, "message": upd.auto_update(force=True) or "Saved. You're on the newest version."})
            if u.path == "/api/transcribe":   # a voice note (raw audio from the mic button) -> the words, on this computer
                n = int(self.headers.get("Content-Length", 0))
                if not n or n > 40 * 1024 * 1024:
                    return self._json({"error": "That voice note is empty or too long."}, 400)
                return self._json({"text": voice_note_text(self.rfile.read(n))})
            if u.path == "/api/upload":  # raw file body; ?name=clip.mp4
                name = re.sub(r"[^A-Za-z0-9._-]+", "-", q.get("name", ["upload.mp4"])[0])[-80:]
                n = int(self.headers.get("Content-Length", 0))
                dst = os.path.join(project.ROOT, "inbox", name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    remaining = n
                    while remaining > 0:
                        chunk = self.rfile.read(min(1 << 20, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)
                return self._json({"ok": True, "file": os.path.relpath(dst, project.ROOT)})
            if u.path == "/api/catalog/add":             # add a product / service / review / question to this brand
                from .. import brandreels
                import shutil as _sh
                data = self._body()
                kind = data.get("kind")
                if kind not in ("products", "services", "reviews", "faqs"):
                    return self._json({"ok": False, "error": "unknown kind"}, 400)
                item = {k: v for k, v in (data.get("item") or {}).items() if isinstance(v, (str, int, list))}
                if kind in ("products", "services"):
                    photos = []
                    for ph in item.get("photos") or []:
                        src = os.path.join(project.ROOT, ph)
                        if os.path.isfile(src) and os.path.realpath(src).startswith(os.path.realpath(project.ROOT)):
                            dst_dir = os.path.join(project.ROOT, "brand", "products")
                            os.makedirs(dst_dir, exist_ok=True)
                            dst = os.path.join(dst_dir, os.path.basename(src))
                            _sh.copy2(src, dst)
                            photos.append(os.path.relpath(dst, project.ROOT))
                    item["photos"] = photos
                    for k in ("benefits", "steps"):
                        if isinstance(item.get(k), str):
                            item[k] = [x.strip() for x in re.split(r"[;\n]", item[k]) if x.strip()]
                cat = brandreels.catalog()
                cat.setdefault(kind, []).append(item)
                brandreels.save_catalog(cat)
                return self._json({"ok": True, "catalog": cat})
            if u.path in ("/api/brand-reel", "/api/memories"):   # make the plan + storyboard in the background
                data = self._body()
                def job(path=u.path, data=data):
                    JOBS["make"] = {"state": "working"}
                    try:
                        if path == "/api/brand-reel":
                            from .. import brandreels
                            slug = brandreels.make(data.get("recipe"), data.get("name"))
                        else:
                            from .. import memories, footage
                            slug = project.new(None, data.get("title") or "our-day")
                            if data.get("link"):
                                footage.fetch(slug, data["link"])
                            for f in data.get("files") or []:      # picked in the Studio → already in the Inbox
                                src = os.path.join(project.ROOT, f)
                                if os.path.isfile(src):
                                    import shutil as _sh
                                    _sh.copy2(src, project.path(slug, "source"))
                            story = [x for x in re.split(r"[\n.;!]+", data.get("story") or "") if x.strip()][:8]
                            memories.build(slug, data.get("title") or "Our day", story)
                        project.build_timeline(slug)
                        from .. import storyboard
                        storyboard.make(slug)
                        JOBS["make"] = {"state": "done", "slug": slug}
                    except Exception as e:
                        JOBS["make"] = {"state": "error", "error": str(e)[-300:]}
                threading.Thread(target=job, daemon=True).start()
                return self._json({"ok": True})
            if u.path == "/api/ai-connect":              # their own Cloudflare: checked, then saved on this computer
                from .. import aielements
                data = self._body()
                ok, msg = aielements.connect_cloudflare(data.get("account_id"), data.get("token"))
                return self._json({"ok": ok, "message": msg})
            if u.path == "/api/drive":                   # a Google Drive link → its videos/photos into the Inbox
                data = self._body()
                link = str(data.get("link", "")).strip()
                if "drive.google.com" not in link:
                    return self._json({"ok": False, "error": "Paste a Google Drive link (shared: anyone with the link)."})
                def job():
                    JOBS["drive"] = {"state": "downloading"}
                    try:
                        from .. import footage
                        got = footage.fetch(None, link, os.path.join(project.ROOT, "inbox"))
                        JOBS["drive"] = {"state": "done", "files": got}
                    except BaseException as e:            # fetch raises SystemExit with a plain message
                        JOBS["drive"] = {"state": "error", "error": str(e)[-300:]}
                threading.Thread(target=job, daemon=True).start()
                return self._json({"ok": True})
            if u.path in ("/api/lut-upload", "/api/sound-upload"):   # raw body; ?name=Warm.cube / pop.mp3
                import tempfile
                n = int(self.headers.get("Content-Length", 0))
                if n > 60 * 1024 * 1024:
                    return self._json({"ok": False, "error": "That file is too big."})
                name = os.path.basename(q.get("name", ["file"])[0])
                tmp = os.path.join(tempfile.mkdtemp(), name)
                open(tmp, "wb").write(self.rfile.read(n))
                try:
                    if u.path == "/api/lut-upload":
                        from .. import grades
                        return self._json({"ok": True, "name": grades.add_lut(tmp, name)})
                    from .. import mysounds
                    if not name.lower().endswith(mysounds.AUDIO_EXT):
                        return self._json({"ok": False, "error": "That isn't a sound file (mp3, wav, m4a…)."})
                    return self._json({"ok": True, "name": name, "events": mysounds.learn(tmp)})
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)})
            if u.path == "/api/font-upload":  # raw font body; ?name=MyFont.otf&role=sticker
                import tempfile
                n = int(self.headers.get("Content-Length", 0))
                if n > 30 * 1024 * 1024:
                    return self._json({"ok": False, "error": "That file is too big for a font."})
                tmp = os.path.join(tempfile.mkdtemp(), "upload")
                open(tmp, "wb").write(self.rfile.read(n))
                try:
                    out = brand.add_font(tmp, q.get("role", [None])[0] or None, q.get("name", ["font.ttf"])[0])
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)})
                return self._json({"ok": True, "font": os.path.splitext(os.path.basename(out))[0]})
            if u.path == "/api/font-role":
                d = self._body()
                try:
                    brand.set_font_role(d["role"], d.get("font") or "auto")
                except ValueError as e:
                    return self._json({"ok": False, "error": str(e)})
                return self._json({"ok": True})
            if u.path == "/api/sounds":
                from .. import trends
                d = self._body()
                if d.get("remove"):
                    trends.save([i for i in trends.load() if i["title"] != d["remove"]])
                    return self._json({"ok": True})
                moods = [m.strip().lower() for m in str(d.get("mood", "")).split(",") if m.strip()]
                return self._json({"ok": True, "sound": trends.add(d["text"], moods, d.get("tempo"),
                                                                   bool(d.get("business")), d.get("link"))})
            if u.path in ("/api/favourite", "/api/trash/add", "/api/trash/restore", "/api/trash/empty"):
                from .. import library_user as lu
                d = self._body()
                try:
                    if u.path == "/api/favourite":
                        return self._json({"ok": True, "on": lu.toggle_favourite(d["kind"], d["id"], d.get("title") or d["id"], d.get("extra"))})
                    if u.path == "/api/trash/add":
                        return self._json({"ok": True, "id": lu.to_trash(d["kind"], d["id"], d.get("title"))})
                    if u.path == "/api/trash/restore":
                        return self._json({"ok": True, "name": lu.restore(d["id"])})
                    return self._json({"ok": True, "removed": lu.empty_trash()})
                except (ValueError, FileNotFoundError, KeyError) as e:
                    return self._json({"ok": False, "error": str(e)})
            if u.path == "/api/brands/new":
                from .. import brands as brs
                d = self._body()
                return self._json({"ok": True, "slug": brs.new(d.get("name") or "My brand")})
            if u.path == "/api/brands/use":
                from .. import brands as brs
                d = self._body()
                return self._json({"ok": True, "slug": brs.use(d.get("slug"))})
            if u.path == "/api/brand-setup":
                from .. import brandsetup
                d = self._body()
                value = d.get("value")
                if d.get("route") in ("image", "file", "video") and value and not os.path.isabs(value):
                    value = os.path.join(project.ROOT, value)
                pending = os.path.join(project.ROOT, "brand", "brand-name.json")
                name = d.get("name") or (json.load(open(pending, encoding="utf-8")).get("label")
                                         if os.path.exists(pending) else None) or \
                    (packs.load().get("label") if packs.has_brand() else "My brand")

                def bjob():
                    JOBS["_brand"] = {"state": "working", "route": d.get("route")}
                    try:
                        _, looks = brandsetup.run(d.get("route"), value, name, overrides=d.get("overrides"))
                        JOBS["_brand"] = {"state": "looks", "looks": [
                            {"i": i, "feel": lk["feel"], "colors": lk["pack"]["colors"],
                             "notes": lk.get("notes", [])} for i, lk in enumerate(looks, 1)], "t": time.time()}
                    except Exception as e:
                        JOBS["_brand"] = {"state": "error", "error": str(e)[-400:]}
                threading.Thread(target=bjob, daemon=True).start()
                return self._json({"ok": True})
            if u.path == "/api/brand-pick":
                from .. import autolook
                d = self._body()
                pack = autolook.use(int(d.get("i", 1)), d.get("name"))
                out = os.path.join(project.ROOT, "brand", "previews", "brand.jpg")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                try:
                    brand.preview(packs.load(), out)
                except Exception:
                    pass
                JOBS.pop("_brand", None)
                return self._json({"ok": True, "label": pack.get("label")})
            if u.path == "/api/new":
                data = self._body()
                src = data.get("file")
                src_abs = os.path.join(project.ROOT, src) if src else None
                slug = project.new(src_abs, data.get("name") or (data.get("brief", {}).get("topic") or None))
                project.save(slug, "brief.json", data.get("brief", {}))
                if src_abs:
                    def job():
                        JOBS[slug] = {"state": "roughcut"}
                        try:
                            project.do_roughcut(slug)
                            JOBS[slug] = {"state": "ready-for-review"}
                        except Exception as e:
                            JOBS[slug] = {"state": "error", "error": str(e)[-500:]}
                    threading.Thread(target=job, daemon=True).start()
                return self._json({"ok": True, "slug": slug})
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "p" and parts[3] == "music-upload":
                slug = parts[2]                          # their own song (mp3 / m4a / wav) for this reel
                if not _slug_ok(slug):
                    return self.send_error(404)
                ext = os.path.splitext((q.get("name") or ["song.mp3"])[0])[1].lower()
                if ext not in (".mp3", ".m4a", ".wav", ".aac", ".ogg"):
                    return self._json({"ok": False, "error": "Pick an mp3, m4a or wav song."})
                n = int(self.headers.get("Content-Length", 0))
                if n > 60 * 1024 * 1024:
                    return self._json({"ok": False, "error": "That song file is too big."})
                d = project.path(slug, "music")
                os.makedirs(d, exist_ok=True)
                dst = os.path.join(d, "mine" + ext)
                with open(dst, "wb") as f:
                    f.write(self.rfile.read(n))
                pl = project.load(slug, "plan.json") or {}
                pl["music"] = {"file": os.path.relpath(dst, project.ROOT), "gain": 0.7}
                project.save(slug, "plan.json", pl)
                return self._json({"ok": True})
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "p" and parts[3] == "reference-upload":
                slug = parts[2]                          # a picture of what they mean: they attach it in ChatGPT too
                if not _slug_ok(slug):
                    return self.send_error(404)
                n = int(self.headers.get("Content-Length", 0))
                if n > 25 * 1024 * 1024:
                    return self._json({"ok": False, "error": "That picture is too big."})
                raw = self.rfile.read(n)
                d = project.path(slug, "elements")
                os.makedirs(d, exist_ok=True)
                for old in glob.glob(os.path.join(d, "reference.*")):
                    os.remove(old)
                from PIL import Image as _Im
                import io as _io
                im = _Im.open(_io.BytesIO(raw)).convert("RGB")
                im.thumbnail((1600, 1600))
                im.save(os.path.join(d, "reference.jpg"), quality=90)
                return self._json({"ok": True})
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "p" and parts[3] == "elements-upload":
                slug = parts[2]                          # the picture they made in ChatGPT / Canva → stickers
                if not _slug_ok(slug):
                    return self.send_error(404)
                n = int(self.headers.get("Content-Length", 0))
                if n > 40 * 1024 * 1024:
                    return self._json({"ok": False, "error": "That picture is too big."})
                raw = self.rfile.read(n)
                d = project.path(slug, "elements", "sheets")
                os.makedirs(d, exist_ok=True)
                sheet = os.path.join(d, f"upload-{int(time.time())}.png")
                try:
                    from PIL import Image as _Im
                    _Im.open(io.BytesIO(raw)).convert("RGB").save(sheet)
                except Exception:
                    return self._json({"ok": False, "error": "That doesn't look like a picture (PNG or JPG)."})
                from .. import aielements
                names = [x.strip() for x in (q.get("items") or [""])[0].split(";") if x.strip()] or None
                paths = aielements.cut(sheet, project.path(slug, "elements"), names)
                return self._json({"ok": bool(paths), "stickers": [os.path.basename(p_) for p_ in paths],
                                   "error": "" if paths else "No stickers found in that picture: it needs a plain white background."})
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "p":
                slug, what = parts[2], parts[3]
                if not _slug_ok(slug):
                    return self.send_error(404)
                data = self._body()
                if what in ("elements-prompt", "elements-make", "elements-place"):
                    from .. import aielements, storyboard
                    items = [x.strip() for x in re.split(r"[;,\n]", data.get("items") or "") if x.strip()]
                    style = data.get("style") or aielements.DEFAULT_STYLE
                    if what == "elements-prompt":
                        about = data.get("about")
                        if about is not None:            # remember their line about the reel
                            pl = project.load(slug, "plan.json") or {}
                            if pl and pl.get("about") != about:
                                pl["about"] = about
                                project.save(slug, "plan.json", pl)
                        else:
                            about = aielements.about_of(slug)
                        ref = bool(glob.glob(project.path(slug, "elements", "reference.*")))
                        return self._json({"prompt": aielements.chatgpt_prompt(about, items,
                                                                               style, aielements.colors_of(slug), ref)})
                    def job(what=what, items=items, style=style, data=data):
                        JOBS[slug + ":elements"] = {"state": "working"}
                        try:
                            if what == "elements-make":
                                aielements.make(slug, items, style)
                            elif data.get("none"):
                                aielements.clear(slug)
                            else:
                                files = [project.path(slug, "elements", os.path.basename(f)) for f in data.get("files") or []]
                                aielements.place(slug, [f for f in files if os.path.exists(f)] or aielements.stickers_of(slug))
                            if what == "elements-place":
                                project.build_timeline(slug)
                                storyboard.make(slug)
                            JOBS[slug + ":elements"] = {"state": "done", "what": what}
                        except Exception as e:
                            JOBS[slug + ":elements"] = {"state": "error", "error": str(e)[-300:]}
                    threading.Thread(target=job, daemon=True).start()
                    return self._json({"ok": True})
                if what == "timeline":
                    project.save(slug, "timeline.json", data)
                    return self._json({"ok": True})
                if what == "review":
                    project.save(slug, "review.json", data)
                    rc = project.apply_review(slug)
                    return self._json({"ok": True, "summary": roughcut.summary(rc)})
                if what == "music":
                    tl = project.load(slug, "timeline.json") or {}
                    dur = tl.get("duration") or data.get("duration") or 30

                    def mjob():
                        JOBS[slug] = {"state": "music"}
                        try:
                            files, prompt = music.generate(project.path(slug), data.get("brief", {}), dur,
                                                           int(data.get("options", 2)), data.get("provider"))
                            JOBS[slug] = {"state": "music-done", "files": [os.path.basename(f) for f in files],
                                          "prompt": prompt}
                        except Exception as e:
                            JOBS[slug] = {"state": "error", "error": str(e)[-500:]}
                    threading.Thread(target=mjob, daemon=True).start()
                    return self._json({"ok": True})
                if what == "posts":
                    def pjob():
                        JOBS[slug + ":posts"] = {"state": "working"}
                        try:
                            from ..postkit import make
                            make(slug)
                            JOBS[slug + ":posts"] = {"state": "done"}
                        except Exception as e:
                            JOBS[slug + ":posts"] = {"state": "error", "error": str(e)[-300:]}
                    threading.Thread(target=pjob, daemon=True).start()
                    return self._json({"ok": True})
                if what == "chat":
                    from .. import chat
                    msg = str(data.get("message", "")).strip()[:2000]
                    if not msg:
                        return self._json({"error": "empty"}, 400)
                    if chat.status(slug).get("state") == "working":
                        return self._json({"error": "busy"}, 409)
                    return self._json(chat.send(slug, msg))
                if what == "scrapbook-preview":
                    from ..scrapbook import preview
                    spec = _clean_spec(slug, data.get("spec") or {})
                    plan = project.load(slug, "plan.json") or {}
                    im = preview(spec, packs.load(plan.get("pack")), data.get("t"))
                    im.thumbnail((540, 960))
                    return self._png(im, "JPEG")
                if what == "storyboard":                # save ticks + notes; "build": apply them and render
                    from .. import storyboard
                    if data.get("redraw"):
                        if data.get("moments"):         # "Update the words": save their typing into the plan first
                            storyboard.save_choices(slug, data["moments"])
                            storyboard.apply(slug)
                        def job():
                            JOBS[slug + ":storyboard"] = {"state": "drawing"}
                            try:
                                project.build_timeline(slug)
                                storyboard.make(slug)
                                JOBS[slug + ":storyboard"] = {"state": "done"}
                            except Exception as e:
                                JOBS[slug + ":storyboard"] = {"state": "error", "error": str(e)[-400:]}
                        threading.Thread(target=job, daemon=True).start()
                        return self._json({"ok": True, "state": "drawing"})
                    sb = storyboard.save_choices(slug, data.get("moments", []))
                    out = {"ok": True}
                    if data.get("build"):
                        r = storyboard.apply(slug)
                        out["notes"] = r["notes"]
                        if r["notes"]:                  # notes need Claude: hand them over through the chat box
                            from .. import chat
                            msg = ("Storyboard notes — please change these, redraw the storyboard, then build:\n"
                                   + "\n".join(r["notes"]))
                            if chat.status(slug).get("state") != "working":
                                out["chat"] = chat.send(slug, msg)
                        else:                           # nothing to rewrite: build straight away
                            def job():
                                JOBS[slug] = {"state": "rendering"}
                                try:
                                    project.build_timeline(slug)
                                    project.do_render(slug)
                                    JOBS[slug] = {"state": "done"}
                                except Exception as e:
                                    JOBS[slug] = {"state": "error", "error": str(e)[-400:]}
                            threading.Thread(target=job, daemon=True).start()
                            out["state"] = "rendering"
                    return self._json(out)
                if what == "scene-set":                 # put an effect on a line (fx "" = none), rebuild the edit
                    return self._json(scene_set(slug, int(data.get("line", 0)), str(data.get("fx", "")),
                                                data.get("series")))
                if what == "scrapbook-save":
                    return self._json(save_scrapbook(slug, int(data.get("beat", 0)), _clean_spec(slug, data.get("spec") or {})))
                if what == "brief":
                    project.save(slug, "brief.json", data)
                    return self._json({"ok": True})
                if what == "sound-edit":                # one row of the sound list: off / on / another sound
                    from .. import sounddesign as sd
                    pl = project.load(slug, "plan.json") or {}
                    ed = pl.setdefault("sfx_edits", {})
                    k = sd.key_of(data.get("t", 0))
                    e = ed.get(k, {})
                    if "off" in data:
                        e["off"] = bool(data["off"])
                    if data.get("label"):               # "another sound": the next one of that kind (or a chosen kind)
                        lab = sd.CHOICE_FOR.get(data["label"], data["label"])
                        files = sd.choice_files(lab if lab in sd.CHOICES else "Soft pop")
                        if files:
                            cur = e.get("file")
                            e["file"] = files[(files.index(cur) + 1) % len(files)] if cur in files else files[0]
                            e["off"] = False
                    if data.get("reset"):
                        e = {}
                    if e:
                        ed[k] = e
                    else:
                        ed.pop(k, None)
                    project.save(slug, "plan.json", pl)
                    return self._json(sound_list(slug))
                if what == "sound":                     # sound effects + music choice → plan.json
                    pl = project.load(slug, "plan.json") or {}
                    if data.get("sound") in ("modern", "quiet", "soft"):
                        pl["sound"] = data["sound"]
                    m = data.get("music")
                    if m == "trending":                 # no music in the file: they add a trending sound in the app
                        pl["music"] = {"none": True}
                    elif m == "builtin" or m in BEDS:
                        cur = pl.get("music") or {}
                        f = cur.get("file") if m == "builtin" and cur.get("file") and "/music/mine" not in cur.get("file", "") \
                            and "/bed-" not in cur.get("file", "") else None
                        if not f:
                            from .. import musicgen
                            dur = sum(b.get("dur", 3) for b in pl.get("beats", [])) + 3 if pl.get("beats") else 60
                            brief = BEDS.get(m, BEDS["calm"])
                            st, _ = musicgen.compose(brief, dur, seed=7)
                            mp = project.path(slug, "music", f"bed-{m if m in BEDS else 'calm'}.wav")
                            os.makedirs(os.path.dirname(mp), exist_ok=True)
                            musicgen.write(mp, st)
                            f = os.path.relpath(mp, project.ROOT)
                        pl["music"] = {"file": f, "gain": float(data.get("gain", cur.get("gain", 0.6)))}
                    elif m == "mine" and isinstance(pl.get("music"), dict):
                        pl["music"]["gain"] = float(data.get("gain", pl["music"].get("gain", 0.7)))
                    project.save(slug, "plan.json", pl)
                    return self._json({"ok": True})
                if what == "render":
                    preview = bool(data.get("preview"))

                    def job():
                        JOBS[slug] = {"state": "rendering", "preview": preview}
                        try:
                            if project.load(slug, "plan.json"):
                                project.build_timeline(slug)     # storyboard / sound changes always go in
                            out = project.do_render(slug, preview=preview)
                            JOBS[slug] = {"state": "done", "file": os.path.basename(out)}
                        except Exception as e:
                            JOBS[slug] = {"state": "error", "error": str(e)[-500:]}
                    threading.Thread(target=job, daemon=True).start()
                    return self._json({"ok": True})
            return self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            return self._json({"error": str(e)}, 500)


MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".mp4", ".mov", ".m4v")


def _media_ok(slug, rel):
    """A project media path (relative to the app root) if it really is inside this project, else None."""
    if not rel:
        return None
    full = os.path.realpath(os.path.join(project.ROOT, rel.partition("@")[0]))
    base = os.path.realpath(project.path(slug))
    if not full.startswith(base + os.sep) or not full.lower().endswith(MEDIA_EXT) or not os.path.exists(full):
        return None
    return full


def _clean_spec(slug, spec):
    """Only known settings; photos only from this project."""
    from ..scrapbook import OPTIONS
    out = {k: v for k, v in spec.items() if k in OPTIONS}
    photos = []
    for ph in out.get("photos", []):
        f = ph["file"] if isinstance(ph, dict) else str(ph)
        if _media_ok(slug, f):
            photos.append(ph)
    out["photos"] = photos
    return out


def scrapbooks(slug):
    """The reel's scrapbook moments (with every setting filled in) + the photos and clips it can use."""
    from ..scrapbook import OPTIONS, settings
    plan = project.load(slug, "plan.json") or {}
    pack = packs.load(plan.get("pack"))
    found = []
    for i, b in enumerate(plan.get("beats", [])):
        d = next((x for x in b.get("do", []) if x.split(":")[0] == "scrapbook"), None)
        if d is None:
            continue
        spec = dict(b.get("scrapbook") or {})
        if ":" in d and d.split(":", 1)[1]:
            spec["style"] = d.split(":", 1)[1]
        spec.setdefault("photos", plan.get("broll_pool", []))
        spec["duration"] = b.get("dur", spec.get("duration", 6))
        full = settings(spec, pack)
        found.append({"beat": i, "spec": dict(full, photos=spec["photos"]), "text": b.get("text", "")})
    media = []
    for root, _, files in os.walk(project.path(slug, "source")):
        for f in sorted(files):
            if f.lower().endswith(MEDIA_EXT) and not f.startswith("."):
                media.append(os.path.relpath(os.path.join(root, f), project.ROOT))
    return {"scrapbooks": found, "media": media, "pack": plan.get("pack"),
            "options": {k: {"default": v[0], "about": v[1]} for k, v in OPTIONS.items()}}


def _scene_source(slug):
    tl = project.load(slug, "timeline.json") or {}
    src = tl.get("source")
    if src and not os.path.isabs(src):
        src = os.path.join(project.ROOT, src)
    return src if src and os.path.exists(src) else None


def _example_clip():
    """A short sample clip (from a library photo) so photo-only reels still get a moving example of every effect."""
    import subprocess
    out = os.path.join(project.ROOT, "out", "effect-example.mp4")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        photo = os.path.join(project.ROOT, "library", "samples", "hero-photo.jpg")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", photo, "-t", "6", "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
                        "-r", "30", out + ".part.mp4"], check=True)
        os.replace(out + ".part.mp4", out)
    return out


def scene_lines(slug):
    """Spoken lines (from the rough cut) and the scene effect on each, for the Scene effects page."""
    from .. import scenefx
    plan = project.load(slug, "plan.json") or {}
    rc = project.load(slug, "roughcut.json") or {}
    on = {}
    for b in plan.get("beats", []):
        for d in b.get("do", []):
            if d.startswith("scene:") and "line" in b:
                on.setdefault(b["line"], []).append(d[6:])
    lines = [{"id": l["id"], "text": l.get("text", ""), "fx": on.get(l["id"], [])} for l in rc.get("lines", []) if l.get("keep")]
    return {"lines": lines, "has_video": True, "example": not _scene_source(slug), "series": plan.get("series"),
            "effects": [{"name": k, "label": v, "about": scenefx.ABOUT.get(k, ""), "pack": "vfx45" if k in scenefx.V45 else "studio"}
                        for k, v in scenefx.LABELS.items()]}


def scene_clip(slug, fx):
    from .. import scenefx
    src = _scene_source(slug) or _example_clip()
    if fx not in scenefx.LABELS:
        return None
    folder = project.path(slug, "cache", "scenes")
    os.makedirs(folder, exist_ok=True)
    plan = project.load(slug, "plan.json") or {}
    import hashlib
    key = hashlib.md5(f"{plan.get('pack')}|{os.path.getsize(src)}|{os.path.getmtime(scenefx.__file__)}".encode()).hexdigest()[:10]
    out = os.path.join(folder, f"{fx}-{key}.webp")
    if not os.path.exists(out):
        tl = project.load(slug, "timeline.json") or {}
        cuts = tl.get("cuts") or [[0, 3]]
        at = float(cuts[len(cuts) // 3][0]) + 0.5      # a moment a third of the way in, where they're talking
        scenefx.preview_anim(fx, src, out + ".part.webp", packs.load(plan.get("pack")), at=at)
        os.replace(out + ".part.webp", out)
    return out


def scene_set(slug, line, fx, series=None):
    """Put one scene effect on a spoken line (replacing any other on that line), or none; rebuild the edit."""
    from .. import scenefx
    if fx and fx not in scenefx.LABELS:
        raise ValueError("unknown effect")
    plan = project.load(slug, "plan.json") or {}
    beats = plan.setdefault("beats", [])
    b = next((x for x in beats if x.get("line") == line), None)
    if b is None and fx:
        b = {"line": line, "do": []}
        beats.append(b)
        beats.sort(key=lambda x: x.get("line", 0))
    if b is not None:
        b["do"] = [d for d in b.get("do", []) if not d.startswith("scene:")] + ([f"scene:{fx}"] if fx else [])
        if not fx:
            b.pop("scene", None)
    if series is not None:
        if series:
            plan["series"] = {"title": series if isinstance(series, str) else f"{sum(1 for x in beats for d in x.get('do', []) if d.startswith('scene:'))} Video Effects"}
        else:
            plan.pop("series", None)
    if any(d.startswith("scene:") for x in beats for d in x.get("do", [])) and "sound" not in plan:
        plan["sound"] = "effects"             # each effect brings its own sounds (shatter, boom, lights…)
    project.save(slug, "plan.json", plan)
    project.build_timeline(slug)
    return {"ok": True, **scene_lines(slug)}


def save_scrapbook(slug, beat, spec):
    """Save the settings into the plan and swap just that clip in the timeline (other hand tweaks stay)."""
    from .. import scrapbook
    plan = project.load(slug, "plan.json") or {}
    beats = plan.get("beats", [])
    if not (0 <= beat < len(beats)):
        raise ValueError("no such moment in this reel")
    b = beats[beat]
    order = [i for i, x in enumerate(beats) if any(d.split(":")[0] == "scrapbook" for d in x.get("do", []))].index(beat)
    style = spec.get("style", "orbit")
    b["do"] = [f"scrapbook:{style}" if d.split(":")[0] == "scrapbook" else d for d in b.get("do", [])]
    b["scrapbook"] = {k: v for k, v in spec.items() if k not in ("duration", "style")}
    project.save(slug, "plan.json", plan)
    tl = project.load(slug, "timeline.json") or {}
    sb = [x for x in tl.get("broll", []) if x.get("scrapbook")]
    if order < len(sb):
        entry = sb[order]
        clip = scrapbook.render(dict(spec, duration=entry["dur"]), pack=packs.load(plan.get("pack")))
        entry["file"], entry["scrapbook"] = os.path.relpath(clip, project.ROOT), style
        project.save(slug, "timeline.json", tl)
    else:
        project.build_timeline(slug)
    return {"ok": True}


def overview():
    items = []
    for slug in reversed(project.list_projects()):
        meta = project.load(slug, "project.json") or {}
        tl = project.load(slug, "timeline.json")
        items.append({"slug": slug, "created": meta.get("created"), "faceless": not meta.get("source"),
                      "has_timeline": bool(tl), "duration": (tl or {}).get("duration"),
                      "has_cover": os.path.exists(project.path(slug, "renders", "cover.jpg")),
                      "has_scrapbook": any(b.get("scrapbook") for b in (tl or {}).get("broll", [])),
                      "has_final": os.path.exists(project.path(slug, "renders", "final.mp4")),
                      "has_nomusic": os.path.exists(project.path(slug, "renders", "final-for-trending-sound.mp4")),
                      "brief": project.load(slug, "brief.json") or {}, "job": JOBS.get(slug),
                      "brand": meta.get("brand")})
    b = packs.load() if packs.has_brand() else None
    return {"projects": items,
            "brand": ({"label": b.get("label"), "vibe": b.get("vibe"), "colors": b["colors"],
                       "fonts": {k: os.path.basename(v["file"]) for k, v in b["fonts"].items()},
                       "has_logo": bool(b.get("logo"))} if b else None),
            "packs": {k: {"label": v.get("label", k), "vibe": v.get("vibe", ""), "colors": v["colors"]}
                      for k, v in packs.presets().items()},
            "titles": {k: v[1] for k, v in titles.TEMPLATES.items()},
            "music": {"providers": music.available(), "moods": music.MOODS, "genres": music.GENRES},
            "grades": dict(__import__("engine.grades", fromlist=["x"]).GROUPS,
                           **({"Yours": __import__("engine.grades", fromlist=["x"]).my_luts()}
                              if __import__("engine.grades", fromlist=["x"]).my_luts() else {})),
            "grade_desc": __import__("engine.grades", fromlist=["x"]).DESCRIPTIONS,
            "captions": __import__("engine.captions", fromlist=["x"]).STYLES,
            "transitions": {"whip": "fast swipe", "flash": "white flash", "zoom-blur": "zoom through", "glitch": "digital glitch",
                            "light-leak": "warm light leak", "film-burn": "film burn", "shape-wipe": "brand-colour circle",
                            "dip-white": "soft fade to white", "dip-black": "fade to black", "blur": "soft blur",
                            "pixelate": "pixel", "spin": "spin", "rgb-split": "colour split"},
            "inbox": inbox_all(), "sound_counts": _sound_counts()}


def _sound_counts():
    import glob as _g
    L = os.path.join(project.ROOT, "library", "sfx")
    return {"interface": len(_g.glob(os.path.join(L, "uisfx", "*", "*.wav"))),
            "recorded": len(_g.glob(os.path.join(L, "foley", "*.wav"))),
            "air": len(_g.glob(os.path.join(L, "cc0pack", "*.wav"))) + len(_g.glob(os.path.join(L, "kenney", "*.wav"))),
            "yours": len(_g.glob(os.path.join(project.ROOT, "brand", "sounds", "*", "*.wav")))}


def inbox_all():
    """Everything usable in inbox/: images, videos and music."""
    d = os.path.join(project.ROOT, "inbox")
    ok = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp4", ".mov", ".m4v", ".mp3", ".wav", ".m4a")
    return sorted(os.path.join("inbox", f) for f in os.listdir(d) if f.lower().endswith(ok)) if os.path.isdir(d) else []


_TP_CACHE = {}


def title_preview(qs):
    """A 9:16 card showing a title template in the user's brand (or a preset)."""
    from PIL import Image, ImageDraw
    key = json.dumps(qs, sort_keys=True)
    if key in _TP_CACHE:
        return _TP_CACHE[key]
    pack = packs.load(qs.get("pack") or None)
    spec = {k: v for k, v in qs.items() if k not in ("pack", "w")}
    spec.setdefault("template", "with-me")
    W, H = 540, 960
    bg = Image.new("RGBA", (W, H))
    top, bot = (58, 52, 48), (140, 118, 98)  # warm photo-like gradient so white titles read
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        d.line((0, y, W, y), fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)) + (255,))
    layers = titles.build(dict(spec, size=float(spec.get("size", 1.3)) * 0.62, max_width=490), pack)
    comp, (cx, cy) = titles.composite(layers)
    bg.alpha_composite(comp, (int(W / 2 + cx - comp.width / 2), int(H * 0.45 + cy - comp.height / 2)))
    img = bg.convert("RGB")
    if len(_TP_CACHE) > 200:
        _TP_CACHE.clear()
    _TP_CACHE[key] = img
    return img


def _sample_frame():
    """A real picture to preview looks on: a frame from their newest video if they have one,
    otherwise a real photo that ships with Reelmate (library/samples)."""
    import glob, subprocess
    vids = [p for p in glob.glob(os.path.join(project.ROOT, "projects", "*", "source", "*"))
            + glob.glob(os.path.join(project.ROOT, "inbox", "*"))
            if p.lower().endswith((".mp4", ".mov", ".m4v"))]
    if vids:
        newest = max(vids, key=os.path.getmtime)
        out = os.path.join(project.ROOT, "out", "preview-frame-%d.jpg" % int(os.path.getmtime(newest)))
        if not os.path.exists(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
            try:
                dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                            newest], capture_output=True, text=True).stdout.strip() or 4)
            except ValueError:
                dur = 4
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(dur * 0.3), "-i", newest, "-frames:v", "1",
                            "-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", out])
        if os.path.exists(out):
            return out
    return os.path.join(project.ROOT, "library", "samples", "filter-sample.jpg")


def grade_preview(grade, file=None):
    """Their own frame (or a sample) with a filter applied."""
    from .. import grades
    import subprocess, hashlib
    src = os.path.join(project.ROOT, file) if file and os.path.exists(os.path.join(project.ROOT, file)) else _sample_frame()
    key = hashlib.md5(f"{src}|{grade}".encode()).hexdigest()[:12]
    out = os.path.join(project.ROOT, "out", "grade-previews", f"{key}.jpg")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        g = grades.graph(grade, "0:v", "o").replace(",format=yuv420p", "")
        pre = ["-ss", "1"] if src.lower().endswith((".mp4", ".mov", ".m4v")) else []
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + pre + ["-i", src, "-frames:v", "1", "-filter_complex",
                        f"[0:v]scale=360:640:force_original_aspect_ratio=increase,crop=360:640[s];" + g.replace("[0:v]", "[s]", 1),
                        "-map", "[o]", out])
    return out


def caption_preview(style, pack_name=None):
    from PIL import Image
    from .. import captions
    pack = packs.load(pack_name or None)
    words = [{"w": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(["this", "changed", "everything"])]
    if style in captions.KINETIC:
        im = captions.render_kinetic(words, 2, captions.PHASES, pack, {"style": style, "_keys_in_group": [1]})
    else:
        im = captions.render(words, 1, pack, {"style": style, "_keys_in_group": [1]})
    card = Image.new("RGBA", (420, 150), (70, 62, 56, 255))
    im.thumbnail((400, 130))
    card.alpha_composite(im, ((420 - im.width) // 2, (150 - im.height) // 2))
    return card.convert("RGB")


def serve(port=8765, open_browser=True, slug=None):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}/" + (f"editor?p={slug}" if slug else "")
    print(f"Reelmate editor running at {url}  (Ctrl+C to stop)")
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    srv.serve_forever()
