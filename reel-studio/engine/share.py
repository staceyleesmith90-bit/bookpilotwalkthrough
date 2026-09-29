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
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-vn", "-b:a", "128k",
                    os.path.join(out, "soundtrack.mp3")], check=True)
    d = _dur(final)
    title = title or os.path.basename(project_dir.rstrip("/")).replace("-", " ").title()
    html = open(os.path.join(HERE, "review_page.html")).read()
    data = json.dumps({"title": title, "version": version, "did": did or []}).replace("</", "<\\/")
    html = (html.replace("__TITLE__", title).replace("__VERSION__", version)
            .replace("__DURATION__", f"{int(d // 60)}:{int(d % 60):02d}").replace("__DATA__", data))
    open(os.path.join(out, "index.html"), "w").write(html)
    return out
