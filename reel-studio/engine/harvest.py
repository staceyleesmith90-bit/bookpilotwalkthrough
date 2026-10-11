"""Clip Harvest — several short reels out of one long video (a podcast, a live, a talk, a long vlog).

    python -m engine harvest <video> [--options 6]            -> the best moments, numbered, for approval
    python -m engine harvest-make <video> --options "1,3,4"   -> one new reel project per chosen moment

The long video is transcribed once (cached). Moments start at the beginning of a sentence and end at the
end of one, 15–60 seconds long, and are ranked by how well they'd work as a reel: a strong first line
(a question, "you", a number, a bold claim), a complete thought, and good energy. Claude shows the list,
the person ticks the ones they want, and each becomes its own reel that goes through the normal edit.
"""
import json, os, re, subprocess

from . import project
from .transcribe import transcribe

ROOT = project.ROOT
CACHE = os.path.join(ROOT, "out", "harvest")
HOOKY = re.compile(r"\b(you|your|why|how|what|stop|never|always|secret|mistake|nobody|everyone|best|worst|"
                   r"truth|actually|biggest|first|only|need|should|wish|if)\b", re.I)
WEAK_START = re.compile(r"^(and|so|um|uh|but|like|yeah|okay|ok|right|anyway)\b", re.I)


def _sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]) or (len(cur) > 45):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"text": " ".join(x["w"] for x in s), "start": s[0]["start"], "end": s[-1]["end"], "n": len(s)} for s in out if s]


def _score(sents):
    first = sents[0]["text"]
    s = 0.0
    s += 2.0 if first.endswith("?") else 0
    s += 1.2 * min(3, len(HOOKY.findall(first)))
    s += 1.0 if re.search(r"\d", first) else 0
    s -= 2.5 if WEAK_START.search(first) else 0
    s += 1.0 if len(first.split()) <= 14 else -0.5                       # short, punchy opener
    dur = sents[-1]["end"] - sents[0]["start"]
    wps = sum(x["n"] for x in sents) / max(dur, 1)
    s += min(2.0, max(0.0, (wps - 1.8) * 1.5))                           # energy
    s += 0.8 if sents[-1]["text"].endswith((".", "!")) else 0           # lands the thought
    return round(s, 2)


def moments(video, n=6, min_s=15, max_s=60):
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r"[^a-z0-9]+", "-", os.path.basename(video).lower())[:50]
    t = transcribe(video, cache=os.path.join(CACHE, key + ".words.json"))
    sents = _sentences(t["words"])
    cands = []
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            dur = sents[j]["end"] - sents[i]["start"]
            if dur > max_s:
                break
            if dur >= min_s:
                group = sents[i:j + 1]
                cands.append({"start": round(max(0, group[0]["start"] - 0.25), 2), "end": round(group[-1]["end"] + 0.35, 2),
                              "first": group[0]["text"], "score": _score(group), "text": " ".join(x["text"] for x in group)})
    cands.sort(key=lambda c: -c["score"])
    picked = []
    for c in cands:
        if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
            picked.append(c)
        if len(picked) >= n:
            break
    picked.sort(key=lambda c: c["start"])
    for k, c in enumerate(picked, 1):
        c["n"] = k
        c["seconds"] = round(c["end"] - c["start"], 1)
    json.dump({"video": video, "moments": picked}, open(os.path.join(CACHE, key + ".json"), "w"), indent=1)
    return picked


def make(video, chosen):
    """chosen = list of moment numbers. -> new project slugs."""
    key = re.sub(r"[^a-z0-9]+", "-", os.path.basename(video).lower())[:50]
    data = json.load(open(os.path.join(CACHE, key + ".json")))
    slugs = []
    for m in data["moments"]:
        if m["n"] not in chosen:
            continue
        clip = os.path.join(CACHE, f"{key}-{m['n']:02d}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(m["start"]), "-to", str(m["end"]), "-i", video,
                        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-c:a", "aac", "-b:a", "256k", clip], check=True)
        name = " ".join(m["first"].split()[:6]).strip(" ,.?!") or f"clip {m['n']}"
        slug = project.new(clip, name)
        project.save(slug, "brief.json", {"topic": name, "from_long_video": os.path.basename(video), "moment": m["n"]})
        os.remove(clip)
        slugs.append(slug)
    return slugs
