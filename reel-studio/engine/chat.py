"""The Studio chat box: type a change ("make NEVER bigger and put it behind me") and Claude does it.

The Studio runs on the person's computer next to Claude Code, so a message is handed to Claude Code
(`claude -p`) working inside Reel Studio, on that one reel: it follows the same skills and rules,
changes the plan / timeline, renders a preview and answers in a sentence or two. One conversation per
reel (it remembers earlier requests). No Claude Code on this machine -> the request is saved in
projects/<p>/chat-inbox.json and done the next time Claude opens Reel Studio (`python -m engine chat-inbox`).
"""
import json, os, shutil, subprocess, threading, time

from . import project

ROOT = project.ROOT
JOBS = {}                                      # slug -> {"state", "steps": [...], "reply"}
PROMPT = """You are Reel Studio's editor, working ONLY on the reel in projects/{slug}/ (read CLAUDE.md and the
reel-engine skill if you need them). The person typed this in the Studio chat box:

"{message}"

Make exactly that change, the Reel Studio way: edit projects/{slug}/plan.json (or timeline.json for small
tweaks), rebuild with `python -m engine timeline {slug}` only if you changed the plan, then render a quick
preview with `python -m engine render {slug} --preview`. Never touch other projects or their original
files. Then answer in one or two short, friendly sentences (no code, no file names) saying what you
changed. If the request is unclear, make the most sensible choice and say what you chose."""

TOOL_WORDS = {"Read": "Looking at the reel", "Edit": "Changing the edit", "Write": "Changing the edit",
              "Bash": "Working on it", "Grep": "Looking at the reel", "Glob": "Looking at the reel"}


def _path(slug, name):
    return project.path(slug, name)


def history(slug):
    try:
        return json.load(open(_path(slug, "chat.json"), encoding="utf-8"))
    except Exception:
        return {"messages": [], "session": None}


def _save(slug, h):
    json.dump(h, open(_path(slug, "chat.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def available():
    return shutil.which("claude") is not None


def _step_for(block):
    """A friendly progress line for one tool call from the stream."""
    name = block.get("name", "")
    cmd = (block.get("input") or {}).get("command", "")
    if "render" in cmd and "--preview" in cmd:
        return "Rendering a preview"
    if "engine timeline" in cmd:
        return "Rebuilding the edit"
    return TOOL_WORDS.get(name)


def send(slug, message):
    """Start working on a message (returns at once; poll status())."""
    h = history(slug)
    h["messages"].append({"role": "you", "text": message, "t": time.time()})
    _save(slug, h)
    if not available():
        inbox = _path(slug, "chat-inbox.json")
        q = json.load(open(inbox)) if os.path.exists(inbox) else []
        q.append({"message": message, "t": time.time()})
        json.dump(q, open(inbox, "w"), indent=1, ensure_ascii=False)
        reply = "Saved. Claude will make this change the next time you open Reel Studio in Claude Code."
        h["messages"].append({"role": "claude", "text": reply, "t": time.time()})
        _save(slug, h)
        JOBS[slug] = {"state": "done", "steps": [], "reply": reply}
        return JOBS[slug]
    JOBS[slug] = {"state": "working", "steps": ["Reading your message"], "reply": ""}
    threading.Thread(target=_run, args=(slug, message), daemon=True).start()
    return JOBS[slug]


def _run(slug, message):
    job = JOBS[slug]
    h = history(slug)
    cmd = ["claude", "-p", PROMPT.format(slug=slug, message=message.replace('"', "'")),
           "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
           "--allowedTools", "Read", "Edit", "Write", "Grep", "Glob",
           "Bash(python -m engine:*)", "Bash(python3 -m engine:*)"]
    if h.get("session"):
        cmd += ["--resume", h["session"]]
    reply, session = "", h.get("session")
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            session = ev.get("session_id") or session
            if ev.get("type") == "assistant":
                for b in (ev.get("message") or {}).get("content", []):
                    if b.get("type") == "tool_use":
                        step = _step_for(b)
                        if step and (not job["steps"] or job["steps"][-1] != step):
                            job["steps"].append(step)
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        reply = b["text"].strip()
            elif ev.get("type") == "result":
                reply = (ev.get("result") or reply or "").strip()
        proc.wait(timeout=60)
        if proc.returncode and not reply:
            reply = "I couldn't finish that one — try saying it another way, or ask me in Claude."
        job["state"] = "done"
    except Exception as e:                     # never leave the box spinning
        reply = f"Something went wrong: {str(e)[:200]}"
        job["state"] = "error"
    job["reply"] = reply
    h = history(slug)
    h["session"] = session
    h["messages"].append({"role": "claude", "text": reply, "t": time.time(),
                          "preview": os.path.exists(_path(slug, "renders/preview.mp4"))})
    _save(slug, h)


def status(slug):
    return JOBS.get(slug) or {"state": "idle", "steps": [], "reply": ""}


def inbox(slug=None):
    """Requests saved while Claude Code wasn't available: [(slug, message)]."""
    out = []
    for s in ([slug] if slug else project.list_projects()):
        p = _path(s, "chat-inbox.json")
        if os.path.exists(p):
            out += [(s, q["message"]) for q in json.load(open(p))]
    return out


def clear_inbox(slug):
    p = _path(slug, "chat-inbox.json")
    if os.path.exists(p):
        os.remove(p)
