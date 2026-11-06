"""Turn the engine's transcript of old reels into plain words, one reel at a time.

Run it from the engine folder with the engine's own Python (same on Mac and PC):

    PY="$(bash scripts/ensure-python.sh)" && "$PY" .claude/skills/script-kit-library/tools/reel-transcripts.py script-desk/old-reels

It reads script-desk/old-reels/transcript/words.json (written by the engine's transcriber) and prints JSON:

    {"videos": [...], "missing": [...], "skipped": [...], "reels": [{"file", "seconds", "length", "words", "text"}]}

"missing" lists videos in the folder that the transcript doesn't cover yet. When it isn't empty, run the
transcriber again with --force, then run this again. "skipped" lists files that aren't videos, which the
transcriber ignores. Standard library only.
"""
import json
import pathlib
import sys

VIDEO = {".mov", ".mp4", ".mkv", ".m4v"}


def length(seconds):
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return
    folder = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "script-desk/old-reels")
    media = folder / "raw" if (folder / "raw").is_dir() else folder
    files = sorted(p for p in media.iterdir() if p.is_file() and not p.name.startswith(".")) \
        if media.is_dir() else []
    videos = [p.name for p in files if p.suffix.lower() in VIDEO]
    skipped = [p.name for p in files if p.suffix.lower() not in VIDEO]
    words_file = folder / "transcript" / "words.json"
    reels, covered = [], set()
    if words_file.exists():
        data = json.loads(words_file.read_text(encoding="utf-8"))
        for clip in data.get("clips", []):
            name = clip.get("clip") or pathlib.Path(clip.get("path", "")).name
            covered.add(name)
            text = " ".join(w["w"] for w in clip.get("words", []) if w.get("w")).strip()
            seconds = float(clip.get("duration") or 0)
            reels.append({
                "file": name,
                "seconds": round(seconds, 1),
                "length": length(seconds),
                "words": len(text.split()),
                "text": text or "(no speech found: music or on-screen text only)",
            })
    out = {"videos": videos, "missing": [v for v in videos if v not in covered], "skipped": skipped,
           "reels": reels}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
