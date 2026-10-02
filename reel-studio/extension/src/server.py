"""Reel Studio extension: the local MCP server Claude Desktop (one-click .mcpb) or Codex talks to.

Everything runs on the customer's own computer:
  - their videos, brand and finished reels live in their Reel Studio folder (default
    Documents/Reel Studio) — nothing is uploaded or stored anywhere else;
  - the thinking happens in THEIR Claude / Codex plan; this server only runs the editing engine;
  - a monthly licence key (from their Systems Pilot account) unlocks the tools.

The engine is the same `python -m engine …` used everywhere else; it is copied from the extension
into the Reel Studio folder on first run and after every update (their own files are kept).
"""
import glob, json, os, platform, shutil, subprocess, sys, threading, time, uuid, webbrowser

from mcp.server.fastmcp import FastMCP

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import licence  # noqa: E402

# the engine shipped inside the extension (built by scripts/build_extension.py); repo checkout for dev
APP = next(p for p in (os.path.join(os.path.dirname(HERE), "app"), os.path.dirname(os.path.dirname(HERE)))
           if os.path.isdir(os.path.join(p, "engine")))


def _home():
    h = os.environ.get("REEL_HOME", "").strip()
    if not h or "${" in h:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        h = os.path.join(docs if os.path.isdir(docs) else os.path.expanduser("~"), "Reel Studio")
    return os.path.abspath(os.path.expanduser(h))


HOME = _home()
KEEP = {"brand", "brands", "projects", "inbox", "out", "trash", ".licence.json"}
KEEP_LIB = {"emoji-cache", "models", "cache"}
COPY = ["engine", "library", ".claude", "docs", "VERSION", "AGENTS.md", "CLAUDE.md", "requirements.txt", "scripts"]
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")


def _version(root):
    try:
        return open(os.path.join(root, "VERSION"), encoding="utf-8").read().strip()
    except Exception:
        return ""


def ensure_home():
    """Create the Reel Studio folder and install/update the engine in it (never touching their files)."""
    os.makedirs(HOME, exist_ok=True)
    for d in ("inbox", "projects", "brand", "brands", "out"):
        os.makedirs(os.path.join(HOME, d), exist_ok=True)
    if os.path.abspath(APP) == HOME or _version(HOME) == _version(APP) and os.path.isdir(os.path.join(HOME, "engine")):
        return
    for name in COPY:
        src = os.path.join(APP, name)
        dst = os.path.join(HOME, name)
        if not os.path.exists(src):
            continue
        if os.path.isdir(src):
            if name == "library":
                os.makedirs(dst, exist_ok=True)
                for sub in os.listdir(src):
                    if sub in KEEP_LIB:
                        continue
                    s, d = os.path.join(src, sub), os.path.join(dst, sub)
                    if os.path.isdir(d):
                        shutil.rmtree(d)
                    (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)
            else:
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)


def _tools_on_path():
    """ffmpeg/ffprobe without any install step (downloaded once, per OS, by static-ffmpeg)."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as e:  # noqa: BLE001
        print(f"[reel] ffmpeg setup: {e}", file=sys.stderr)


def _browser_ready():
    """The hidden browser that draws animation windows (installed once, quietly, in the background)."""
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, timeout=900)
    except Exception:
        pass


ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
JOBS = {}
SERVERS = {}
LONG = {"roughcut", "render", "capcut", "share", "layers", "music", "inspire", "learn-me", "chop", "trial", "batch",
        "brand-site", "timeline"}
APPS = {"studio", "editor", "review"}         # local web apps (stay running)
ALLOWED = {"setup-check", "new", "roughcut", "review", "timeline", "render", "studio", "editor", "music", "titles",
           "templates", "template", "inspire", "layers", "share", "capcut", "styleplan", "effects", "effect-save",
           "fonts", "font-add", "font-use", "sounds", "sounds-add", "sounds-suggest", "sticker-requests", "chop",
           "trial", "batch", "learn-me", "brand-image", "brand-preview", "brand-site", "brand-starters", "update"}


def _gate():
    ok, msg = licence.status(HOME)
    return None if ok else msg


def _tail(text, n=4000):
    text = text or ""
    return text if len(text) <= n else "…" + text[-n:]


mcp = FastMCP("Reel Studio", instructions=(
    "You are the user's reel editor (Reel Studio by Systems Pilot). Call reel_guide first in every new chat "
    "and follow it exactly. Run engine steps with reel_command (the playbooks write them as "
    "`python -m engine <command> …` — pass the command and its arguments). Long steps return a job id: "
    "check with reel_job. The user is not technical: one friendly question at a time, no jargon. Their files "
    "stay on their computer in their Reel Studio folder; videos to edit go in its Inbox (reel_inbox opens it)."))


@mcp.tool()
def reel_guide(topic: str = "") -> str:
    """The Reel Studio playbook. No topic: the overview + the editing flow. A topic (e.g. 'brand-onboarding',
    'reel-engine', 'inspiration-reels', 'finish-check', 'title-designer', 'trending-sounds', 'help-me') returns
    that playbook. Read it before doing that kind of task."""
    ensure_home()
    sk = os.path.join(HOME, ".claude", "skills")
    if topic:
        p = os.path.join(sk, topic.strip().lower(), "SKILL.md")
        if not os.path.exists(p):
            return "No playbook called that. Available: " + ", ".join(sorted(os.listdir(sk)))
        body = open(p, encoding="utf-8").read()
    else:
        body = open(os.path.join(HOME, "CLAUDE.md"), encoding="utf-8").read()
        rp = os.path.join(sk, "reel-engine", "SKILL.md")
        body += "\n\n---\n" + open(rp, encoding="utf-8").read()
        body += "\n\nPlaybooks: " + ", ".join(sorted(os.listdir(sk)))
    note = ("\n\n[Running in the Reel Studio extension: wherever this says `python -m engine X …`, call "
            "reel_command with command='X' and the rest as args. Files: reel_read / reel_write (paths relative "
            f"to the Reel Studio folder: {HOME}). New videos: reel_inbox.]")
    return body + note


@mcp.tool()
def reel_command(command: str, args: list[str] | None = None) -> str:
    """Run a Reel Studio engine step, e.g. command='roughcut', args=['my-reel'];
    command='new', args=['inbox/video.mp4', '--name', 'my-reel']; command='render', args=['my-reel'].
    Long steps (rough cut, render, CapCut export…) return a job id — check it with reel_job."""
    blocked = _gate()
    if blocked:
        return blocked
    command = command.strip().lower()
    if command not in ALLOWED:
        return f"Unknown step '{command}'. Steps: " + ", ".join(sorted(ALLOWED))
    ensure_home()
    _tools_on_path()
    args = [str(a) for a in (args or [])]
    cmd = [sys.executable, "-X", "utf8", "-m", "engine", command] + args
    if command in APPS:
        key = command + ":" + " ".join(args)
        if key not in SERVERS or SERVERS[key].poll() is not None:
            SERVERS[key] = subprocess.Popen(cmd + ["--no-browser"], cwd=HOME, env=ENV,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
        path = {"studio": "", "editor": f"editor?p={args[0]}" if args else "editor",
                "review": f"review?p={args[0]}" if args else ""}[command]
        url = f"http://localhost:8765/{path}"
        webbrowser.open(url)
        return f"Opened in the browser: {url} (keep Claude open while you use it)."
    log = os.path.join(HOME, "out", f"job-{uuid.uuid4().hex[:8]}.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    f = open(log, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=HOME, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    wait = 50 if command in LONG else 120
    try:
        proc.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        jid = os.path.basename(log)[4:-4]
        JOBS[jid] = (proc, log, command)
        return (f"Working on it ({command}) — this can take a few minutes. Job id: {jid}. "
                "Check with reel_job (every 30–60 seconds is plenty).")
    f.close()
    out = open(log, encoding="utf-8", errors="replace").read()
    return _tail(_clean(out)) + ("" if proc.returncode == 0 else f"\n[step failed with code {proc.returncode}]")


def _clean(out):
    # drop library noise (TensorFlow / MediaPipe logging) so Claude reads only what matters
    keep = [l for l in out.splitlines() if not l.startswith(("W0000", "I0000", "INFO: Created", "WARNING: Logging"))]
    return "\n".join(keep)


@mcp.tool()
def reel_job(job_id: str) -> str:
    """Status of a long step started by reel_command: still working (with the latest progress) or finished (with its summary)."""
    j = JOBS.get(job_id.strip())
    if not j:
        return "No job with that id (it may have finished in an earlier chat — check the project folder)."
    proc, log, command = j
    out = _clean(open(log, encoding="utf-8", errors="replace").read())
    if proc.poll() is None:
        return f"Still working on {command}… latest:\n" + _tail(out, 800)
    JOBS.pop(job_id.strip(), None)
    return f"Finished {command}" + ("" if proc.returncode == 0 else f" with an error (code {proc.returncode})") + ":\n" + _tail(out)


def _inside(rel):
    p = os.path.abspath(os.path.join(HOME, rel))
    if not (p == HOME or p.startswith(HOME + os.sep)):
        raise ValueError("Only files inside the Reel Studio folder.")
    return p


@mcp.tool()
def reel_read(path: str) -> str:
    """Read a text file in the Reel Studio folder, e.g. 'projects/my-reel/roughcut.json' or 'brand/brand.json'."""
    blocked = _gate()
    if blocked:
        return blocked
    try:
        p = _inside(path)
        txt = open(p, encoding="utf-8", errors="replace").read()
        return txt if len(txt) < 60000 else txt[:60000] + "\n…(truncated)"
    except Exception as e:  # noqa: BLE001
        return f"Couldn't read {path}: {e}"


@mcp.tool()
def reel_write(path: str, content: str) -> str:
    """Write a text file (plan.json, brand settings, notes) inside projects/ or brand/ of the Reel Studio folder."""
    blocked = _gate()
    if blocked:
        return blocked
    try:
        p = _inside(path)
        rel = os.path.relpath(p, HOME).replace("\\", "/")
        if not rel.startswith(("projects/", "brand/")):
            return "Only files in projects/ or brand/ can be written."
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(content)
        return f"Saved {rel}."
    except Exception as e:  # noqa: BLE001
        return f"Couldn't write {path}: {e}"


def _open(path):
    if platform.system() == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


@mcp.tool()
def reel_inbox(open_folder: bool = False) -> str:
    """Videos ready to edit: the Reel Studio Inbox plus videos from the last 3 days in Downloads and Desktop.
    open_folder=True opens the Inbox so the user can drop videos in."""
    blocked = _gate()
    if blocked:
        return blocked
    ensure_home()
    inbox = os.path.join(HOME, "inbox")
    if open_folder:
        _open(inbox)
    found = []
    for f in sorted(glob.glob(os.path.join(inbox, "*"))):
        if f.lower().endswith(VIDEO_EXT):
            found.append(("inbox/" + os.path.basename(f), os.path.getsize(f)))
    cutoff = time.time() - 3 * 86400
    for d in ("Downloads", "Desktop"):
        for f in glob.glob(os.path.join(os.path.expanduser("~"), d, "*")):
            if f.lower().endswith(VIDEO_EXT) and os.path.getmtime(f) > cutoff:
                found.append((f, os.path.getsize(f)))
    if not found:
        return f"No videos yet. Drop them into the Inbox folder: {inbox}" + (" (opened it for you)." if open_folder else "")
    return "\n".join(f"- {p}  ({s / 1e6:.0f} MB)" for p, s in found) + \
        "\nUse the path with reel_command new, e.g. args=['<path>', '--name', 'short-name']."


@mcp.tool()
def reel_open(what: str) -> str:
    """Open something for the user: 'studio' (the Reel Studio app), 'folder' (their Reel Studio folder),
    or a file/folder path inside it (e.g. 'projects/my-reel/renders/final.mp4' plays the reel with sound)."""
    blocked = _gate()
    if blocked and what != "folder":
        return blocked
    ensure_home()
    if what.strip().lower() == "studio":
        return reel_command("studio", [])
    try:
        p = HOME if what.strip().lower() == "folder" else _inside(what)
        if not os.path.exists(p):
            return f"Not found: {what}"
        _open(p)
        return f"Opened {p}."
    except Exception as e:  # noqa: BLE001
        return f"Couldn't open it: {e}"


@mcp.tool()
def reel_licence() -> str:
    """Check the Reel Studio subscription."""
    ok, msg = licence.status(HOME)
    return ("✓ " if ok else "✗ ") + msg


def main():
    ensure_home()
    threading.Thread(target=_tools_on_path, daemon=True).start()
    threading.Thread(target=_browser_ready, daemon=True).start()
    mcp.run()


if __name__ == "__main__":
    main()
