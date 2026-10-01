"""Local editor server: the review page and the manual timeline editor.

    python -m engine editor [--port 8765]     -> http://localhost:8765

Runs entirely on the user's computer. Nothing is uploaded anywhere.
"""
import time, io, json, os, re, threading, traceback, urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from .. import brand, layout, music, packs, project, render, roughcut, stickers, titles

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
JOBS = {}  # slug -> {"state", "file", "error"}


def _slug_ok(s):
    return bool(re.fullmatch(r"[a-z0-9-]+", s or "")) and os.path.isdir(project.path(s))


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
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "p":
                slug, what = parts[2], parts[3]
                if not _slug_ok(slug):
                    return self.send_error(404)
                data = self._body()
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
                if what == "brief":
                    project.save(slug, "brief.json", data)
                    return self._json({"ok": True})
                if what == "render":
                    preview = bool(data.get("preview"))

                    def job():
                        JOBS[slug] = {"state": "rendering", "preview": preview}
                        try:
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


def overview():
    items = []
    for slug in reversed(project.list_projects()):
        meta = project.load(slug, "project.json") or {}
        tl = project.load(slug, "timeline.json")
        items.append({"slug": slug, "created": meta.get("created"), "faceless": not meta.get("source"),
                      "has_timeline": bool(tl), "duration": (tl or {}).get("duration"),
                      "has_cover": os.path.exists(project.path(slug, "renders", "cover.jpg")),
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
            "grades": __import__("engine.grades", fromlist=["x"]).GROUPS,
            "grade_desc": __import__("engine.grades", fromlist=["x"]).DESCRIPTIONS,
            "captions": __import__("engine.captions", fromlist=["x"]).STYLES,
            "transitions": {"whip": "fast swipe", "flash": "white flash", "zoom-blur": "zoom through", "glitch": "digital glitch",
                            "light-leak": "warm light leak", "film-burn": "film burn", "shape-wipe": "brand-colour circle",
                            "dip-white": "soft fade to white", "dip-black": "fade to black", "blur": "soft blur",
                            "pixelate": "pixel", "spin": "spin", "rgb-split": "colour split"},
            "inbox": inbox_all()}


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
    """A neutral sample 'photo' (soft gradient scene) for filter previews without footage."""
    from PIL import Image, ImageDraw, ImageFilter
    p = os.path.join(project.ROOT, "out", "sample-frame.jpg")
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        im = Image.new("RGB", (540, 960))
        d = ImageDraw.Draw(im)
        for y in range(960):
            k = y / 960
            d.line((0, y, 540, y), fill=(int(120 + 110 * (1 - k)), int(150 + 60 * (1 - k)), int(190 - 60 * k)))
        d.ellipse((140, 160, 400, 420), fill=(250, 214, 160))
        d.rectangle((0, 640, 540, 960), fill=(92, 120, 84))
        d.ellipse((180, 520, 360, 900), fill=(205, 120, 110))
        d.ellipse((215, 400, 325, 520), fill=(232, 190, 160))
        im.filter(ImageFilter.GaussianBlur(2)).save(p, quality=92)
    return p


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
                        f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480[s];" + g.replace("[0:v]", "[s]", 1),
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
    print(f"Reel Studio editor running at {url}  (Ctrl+C to stop)")
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    srv.serve_forever()
