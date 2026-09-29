"""Voice hub — learn how the user talks from their own recent reels.

  python -m engine learn-me <profile-or-reel-url> [more urls...] [--options N]
Downloads the audio of their last N reels (default 15) with yt-dlp, transcribes them locally,
keeps each post's caption, and saves brand/voice/reels.json. Claude then reads that ONCE and
writes brand/voice.md (hook patterns, phrases they use, tone, topics, CTA habits, words they
never use). CLAUDE.md tells Claude to read brand/voice.md every session, so hooks, captions and
scripts sound like the user, not like AI.

Profile listing works for TikTok/YouTube; Instagram profiles usually need individual reel links.
"""
import json, os, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "brand", "voice")


def _urls(url, n):
    r = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", str(n), "--print", "url", url],
                       capture_output=True, text=True)
    urls = [u.strip() for u in r.stdout.splitlines() if u.strip().startswith("http")]
    return urls or [url]


def learn(urls, n=15):
    from faster_whisper import WhisperModel
    os.makedirs(DIR, exist_ok=True)
    todo = []
    for u in urls:
        todo += _urls(u, n)
    todo = todo[:n]
    model = WhisperModel("base", compute_type="int8")
    out = []
    for u in todo:
        tmp = tempfile.mkdtemp()
        r = subprocess.run(["yt-dlp", "-q", "-x", "--audio-format", "mp3", "-o", os.path.join(tmp, "a.%(ext)s"),
                            "--print-to-file", "%(description)s", os.path.join(tmp, "caption.txt"), u],
                           capture_output=True, text=True)
        audio = next((os.path.join(tmp, f) for f in os.listdir(tmp) if f.startswith("a.")), None)
        if not audio:
            out.append({"url": u, "error": (r.stderr or "download failed")[-200:]})
            continue
        segs, info = model.transcribe(audio, vad_filter=True)
        text = " ".join(s.text.strip() for s in segs)
        cap = open(os.path.join(tmp, "caption.txt")).read().strip() if os.path.exists(os.path.join(tmp, "caption.txt")) else ""
        out.append({"url": u, "language": info.language, "transcript": text, "caption": cap})
    json.dump(out, open(os.path.join(DIR, "reels.json"), "w"), indent=1, ensure_ascii=False)
    return out
