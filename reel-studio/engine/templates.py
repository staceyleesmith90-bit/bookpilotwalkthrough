"""Reel template library (library/templates.json): ideas people can browse, copy and fill.

Each template has: what to film (shot list), a script prompt, a title design, a beat
structure, captions/grade/transition/zoom, sticker feel and a music brief.
Unlike app templates it adapts to the user's brand and their own footage.

    python -m engine templates                    list
    python -m engine template <id> [--clips DIR]  start a project from a template
"""
import json, os, re, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library", "templates.json")
MEDIA = (".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".webp")


def all_templates():
    return json.load(open(LIB))


def get(tid):
    return all_templates()[tid]


def _fill(s, fields, counters):
    """Replace {placeholders}; list values are consumed in order ({time} → next time)."""
    def rep(m):
        k = m.group(1)
        v = fields.get(k)
        if isinstance(v, list):
            i = counters.get(k, 0)
            counters[k] = i + 1
            return str(v[i % len(v)]) if v else ""
        if v is None:
            return {"date": time.strftime("%B %Y"), "n": "1"}.get(k, "")
        return str(v)
    return re.sub(r"\{(\w+)\}", rep, s)


def to_plan(tid, fields=None, clips=None, pack="brand"):
    """Plan for faceless / voiceover templates (clips = list of media files, used in order).
    Talking-head templates return plan *settings* plus hints; Claude maps them to the lines."""
    t = get(tid)
    fields = dict(fields or {})
    counters = {}
    title = {k: _fill(v, fields, counters) if isinstance(v, str) else v for k, v in t["title"].items()}
    plan = {"format": "faceless" if t["format"] != "talking-head" else "talking-head", "pack": pack,
            "captions": t.get("captions", "karaoke"), "grade": t.get("grade"), "template": tid,
            "music_brief": t.get("music")}
    if t["format"] == "talking-head":
        plan["hints"] = {"title": title, "beats": t["beats"], "film": t["film"], "script": t["script"]}
        return plan
    clips = list(clips or [])
    beats, ci = [], 0
    dur = t.get("beat_seconds")
    for b in t["beats"]:
        b = _fill(b, fields, counters)
        beat = {"text": fields.get("topic", ""), "do": []}
        if b == "title":
            beat["do"] = ["title"]
            beat["title"] = title
            beat["text"] = title.get("title", "")
            beat["dur"] = 2.8
        elif b == "photo":
            beat["do"] = []
            beat["text"] = ""
            beat["dur"] = dur or 0.8
        else:
            kind, _, arg = b.partition(":")
            beat["do"] = [b]
            beat["text"] = arg if kind in ("takeover", "card", "label") else fields.get("topic", "")
            if kind == "label":
                beat["dur"] = dur or 2.2
        if ci < len(clips):  # footage in order under each beat (the title too)
            beat["do"].append(f"broll:{clips[ci]}")
            ci += 1
        if t.get("zoom") and any(x.startswith("broll:") for x in beat["do"]):
            beat["do"].append(f"zoom:{t['zoom']}")
        # labels and photo beats sit on footage, so they don't need a full-screen takeover
        if not any(d.split(":")[0] in ("takeover", "card", "title", "cta") for d in beat["do"]):
            beat["do"].append("keep-footage")
        beats.append(beat)
    plan["beats"] = beats
    plan["transition"] = t.get("transition")
    return plan


def list_clips(folder):
    if not folder or not os.path.isdir(folder):
        return []
    return [os.path.relpath(os.path.join(folder, f), ROOT) for f in sorted(os.listdir(folder)) if f.lower().endswith(MEDIA)]
