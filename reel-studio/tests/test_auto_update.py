import hashlib, http.server, io, json, os, threading, zipfile

from engine import update


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
    return buf.getvalue()


def test_auto_update_installs_and_keeps_user_files(tmp_path, monkeypatch):
    app = tmp_path / "app"
    (app / "engine").mkdir(parents=True)
    (app / "brand").mkdir()
    (app / "VERSION").write_text("1.0.0")
    (app / "engine" / "x.py").write_text("old")
    (app / "brand" / "brand.json").write_text("MINE")
    monkeypatch.setattr(update, "ROOT", str(app))
    monkeypatch.setattr(update, "WHATSNEW", str(app / "out" / "whatsnew.json"))
    monkeypatch.setattr(update, "STAMP", str(app / "out" / ".stamp"))
    rel = _zip({"VERSION": "1.1.0", "engine/x.py": "new", "brand/brand.json": "SELLER'S", "../evil.txt": "no"})
    meta = {"version": "1.1.0", "sha256": hashlib.sha256(rel).hexdigest(), "notes": "New effects"}
    seen = {}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            body = json.dumps(meta).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(body)

        def do_POST(self):
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            ok = seen["body"]["key"] == "RS-GOOD"
            self.send_response(200 if ok else 403); self.end_headers()
            if ok:
                self.wfile.write(rel)

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    feed = f"http://127.0.0.1:{srv.server_port}"
    assert update.auto_update(key="RS-BAD", force=True, feed=feed) is None          # no active subscription
    assert (app / "VERSION").read_text() == "1.0.0"
    msg = update.auto_update(key="RS-GOOD", force=True, feed=feed)
    assert "1.1.0" in msg and (app / "VERSION").read_text() == "1.1.0"
    assert (app / "engine" / "x.py").read_text() == "new"
    assert (app / "brand" / "brand.json").read_text() == "MINE"                   # user's files untouched
    assert not (tmp_path / "evil.txt").exists()
    assert update.whats_new()["notes"] == "New effects"
    assert update.auto_update(key="RS-GOOD", force=True, feed=feed) is None         # already current
    assert update.auto_update(key="RS-GOOD", force=False, feed=feed) is None        # once a day
    srv.shutdown()
