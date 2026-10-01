"""Review page for a finished reel: Systems Pilot branded player + timestamped feedback.

  python -m engine share <project>   -> projects/<p>/renders/review/ (index.html + media)

Claude publishes that folder as a private web page (Artifact, `db` capability for the notes)
and gives the user the link. Why a page: some players (e.g. the Claude desktop app) show the
picture but can't decode AAC audio, so the page ships an Opus-audio copy first and the normal
AAC copy as fallback; the file for posting to TikTok/Instagram stays AAC.
Notes live in the page's `feedback` collection: {t, note, status: open|done, version, created}.
Claude reads them (ArtifactData list), makes the changes, and marks them done.
"""
import json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def _dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def review_device():
    """Where the user watches their edits (asked once at setup): phone · computer · both."""
    try:
        b = json.load(open(os.path.join(HERE, "..", "brand", "brand.json"), encoding="utf-8"))
        return b.get("review_device", "both")
    except Exception:
        return "both"


def script_lines(project_dir):
    """The kept lines with where they start in the finished reel (for the line-by-line review)."""
    try:
        rc = json.load(open(os.path.join(project_dir, "roughcut.json")))
        tl = json.load(open(os.path.join(project_dir, "timeline.json")))
    except Exception:
        return []
    words = (tl.get("captions") or {}).get("words") or []
    out, wi = [], 0
    for n, l in enumerate([l for l in rc.get("lines", []) if l.get("keep", True)], 1):
        k = len(l.get("words") or l["text"].split())
        t = words[wi]["start"] if wi < len(words) else None
        wi += k
        out.append({"n": n, "text": l["text"], "t": t,
                    "secs": round(l.get("duration", l.get("end", 0) - l.get("start", 0)), 1)})
    return out


def build(project_dir, title=None, version="v1", did=None):
    final = os.path.join(project_dir, "renders", "final.mp4")
    out = os.path.join(project_dir, "renders", "review")
    os.makedirs(out, exist_ok=True)
    v = ["-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "slow", "-b:v", "1250k", "-maxrate", "1500k",
         "-bufsize", "3000k", "-movflags", "+faststart"]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final] + v +
                   ["-c:a", "libopus", "-b:a", "128k", "-ac", "2", "-ar", "48000", os.path.join(out, "reel-opus.mp4")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final] + v +
                   ["-c:a", "aac", "-b:a", "128k", "-ac", "2", os.path.join(out, "reel.mp4")], check=True)
    # a WebM copy (VP9 + Opus): plays in players that can't decode H.264 at all
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-vf", "scale=720:1280", "-c:v", "libvpx-vp9",
                    "-b:v", "1300k", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                    "-c:a", "libopus", "-b:a", "128k", os.path.join(out, "reel.webm")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "1.2", "-i", final, "-frames:v", "1", "-vf", "scale=720:1280",
                    "-q:v", "4", os.path.join(out, "poster.jpg")], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-vn", "-b:a", "128k",
                    os.path.join(out, "soundtrack.mp3")], check=True)
    d = _dur(final)
    title = title or os.path.basename(project_dir.rstrip("/")).replace("-", " ").title()
    html = open(os.path.join(HERE, "review_page.html")).read()
    data = json.dumps({"title": title, "version": version, "did": did or [], "lines": script_lines(project_dir),
                       "device": review_device()}).replace("</", "<\\/")
    html = (html.replace("__TITLE__", title).replace("__VERSION__", version)
            .replace("__DURATION__", f"{int(d // 60)}:{int(d % 60):02d}").replace("__DATA__", data))
    open(os.path.join(out, "index.html"), "w").write(html)
    return out
