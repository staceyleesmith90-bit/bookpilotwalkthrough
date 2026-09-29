"""Rough cut: turn a word-timed transcript into kept lines + cut ranges.

Removes: long pauses (jump cuts), filler words, false starts and repeated takes
(keeps the LAST attempt, which is usually the confident one). Everything here is
local code — no Claude usage. Claude only reads the short line list for review.
"""
import re
from difflib import SequenceMatcher

FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm"}
GAP_CUT = 0.45      # pauses longer than this inside a line get cut out
LINE_GAP = 0.70     # a pause this long ends a line
PAD_IN, PAD_OUT = 0.06, 0.14
MAX_WORD = 1.0      # a "word" longer than this is really a hesitation: keep only its first 0.5s
# words that only sound smooth mid-sentence: dropped at the start/end of a line or when said
# on their own between pauses ("so… okay… yeah, and…")
EDGE_FILLERS = {"so", "and", "but", "okay", "ok", "yeah", "alright", "right", "well", "like"}
LONE_FILLERS = {"okay", "ok", "yeah", "alright", "right", "like"}
MAX_WORDS = 16


def _norm(s):
    return re.sub(r"[^a-z0-9' ]", "", s.lower()).split()


def join_words(ws):
    """Join word tokens into text, gluing pieces like '-at', ',000', "'s"."""
    out = ""
    for w in ws:
        t = w["w"]
        out += t if (not out or re.match(r"^[-,.'’?!%]|^,\d", t)) else " " + t
    return out.strip()


def remove_stutters(words, max_n=4):
    """Drop an immediately repeated run of 1-4 words ('how much to, how much to')."""
    ws = list(words)
    i = 0
    while i < len(ws):
        removed = False
        for n in range(max_n, 0, -1):
            a, b = ws[i:i + n], ws[i + n:i + 2 * n]
            if len(b) == n and [_norm(x["w"]) for x in a] == [_norm(x["w"]) for x in b] \
                    and (n > 1 or len(_norm(a[0]["w"])[0]) > 1 if _norm(a[0]["w"]) else False):
                del ws[i:i + n]
                removed = True
                break
        if not removed:
            i += 1
    return ws


def trim_long_words(words):
    """Whisper stretches a word over a pause ('okay…………'). Cut the stretch: if the next word
    follows straight on, the pause came before the word (keep its end), otherwise after it."""
    out = []
    for k, w in enumerate(words):
        if w["end"] - w["start"] > MAX_WORD:
            nxt = words[k + 1] if k + 1 < len(words) else None
            if nxt and nxt["start"] - w["end"] < 0.1:
                w = dict(w, start=round(w["end"] - 0.5, 3))
            else:
                w = dict(w, end=round(w["start"] + 0.5, 3))
        out.append(w)
    return out


def drop_soft_fillers(ws):
    """'so let's take a look and yeah okay' -> 'let's take a look'. Never empties a real line."""
    ws = list(ws)
    key = lambda w: (_norm(w["w"]) or [""])[0]
    while len(ws) > 3 and key(ws[0]) in EDGE_FILLERS:
        ws.pop(0)
    while len(ws) > 3 and key(ws[-1]) in EDGE_FILLERS:
        ws.pop()
    keep = []
    for k, w in enumerate(ws):
        if key(w) in LONE_FILLERS and 0 < k < len(ws) - 1:
            gap_before = w["start"] - ws[k - 1]["end"]
            gap_after = ws[k + 1]["start"] - w["end"]
            if max(gap_before, gap_after) > 0.2:
                continue
        keep.append(w)
    if keep and all(key(w) in EDGE_FILLERS for w in keep):
        return []
    return keep


def split_lines(words):
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["start"] - cur[-1]["end"] > LINE_GAP or len(cur) >= MAX_WORDS):
            lines.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def _similar(a, b):
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0
    # false start: a is (mostly) a prefix of b
    k = min(len(na), len(nb), 5)
    if len(na) <= len(nb) and na[:k] == nb[:k]:
        return 1.0
    return SequenceMatcher(None, " ".join(na), " ".join(nb[: len(na) + 3])).ratio()


def rough_cut(transcript, retake_threshold=0.72):
    words = [dict(w, i=k) for k, w in enumerate(transcript["words"])
             if _norm(w["w"]) and _norm(w["w"])[0] not in FILLERS]
    words = trim_long_words(words)
    groups = [g for g in (drop_soft_fillers(remove_stutters(g)) for g in split_lines(words)) if g]
    lines = []
    for i, g in enumerate(groups):
        text = join_words(g)
        lines.append({"id": i + 1, "text": text, "start": g[0]["start"], "end": g[-1]["end"],
                      "words": g, "keep": True, "reason": "", "note": "", "attach": None})
    # retakes: compare each line with the next 3; if a later one restarts it, drop this one
    for i, ln in enumerate(lines):
        for j in range(i + 1, min(i + 4, len(lines))):
            if _similar(ln["text"], lines[j]["text"]) >= retake_threshold:
                ln["keep"] = False
                ln["reason"] = f"retake (kept line {lines[j]['id']})"
                break
    for ln in lines:
        ln["ranges"] = _ranges(ln["words"])
        ln["duration"] = round(sum(b - a for a, b in ln["ranges"]), 2)
    return {"lines": lines, "source_duration": transcript.get("duration")}


def _ranges(words):
    """Speech ranges for one line, cutting pauses > GAP_CUT (jump cuts)."""
    out = []
    a = words[0]["start"] - PAD_IN
    for w0, w1 in zip(words, words[1:]):
        removed_between = w1.get("i", 0) != w0.get("i", -1) + 1 and "i" in w0
        if w1["start"] - w0["end"] > GAP_CUT or removed_between:
            out.append((max(a, 0), w0["end"] + (PAD_OUT if not removed_between else 0.02)))
            a = w1["start"] - (PAD_IN if not removed_between else 0.01)
    out.append((max(a, 0), words[-1]["end"] + PAD_OUT))
    return [(round(x, 3), round(y, 3)) for x, y in out]


def kept_ranges(rc):
    """Merged source ranges for all kept lines, in order."""
    rs = [r for ln in rc["lines"] if ln["keep"] for r in ln["ranges"]]
    merged = []
    for a, b in rs:
        if merged and a <= merged[-1][1] + 0.02:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def time_map(ranges):
    """Function source_time -> output_time (None if that moment was cut)."""
    offsets, acc = [], 0.0
    for a, b in ranges:
        offsets.append((a, b, acc))
        acc += b - a

    def f(t):
        for a, b, o in offsets:
            if a <= t <= b:
                return o + (t - a)
        return None
    return f, acc


def apply_review(rc, review):
    """review = {"lines": [{"id", "keep", "note", "attach"}]} from the review page."""
    by_id = {r["id"]: r for r in review.get("lines", [])}
    for ln in rc["lines"]:
        r = by_id.get(ln["id"])
        if r:
            ln["keep"] = r.get("keep", ln["keep"])
            ln["note"] = r.get("note", ln["note"]) or ""
            ln["attach"] = r.get("attach", ln["attach"])
            if not ln["keep"] and not ln["reason"]:
                ln["reason"] = "removed in review"
    return rc


def summary(rc):
    """Short text for Claude/the user (cheap to read — no frames needed)."""
    kept = [l for l in rc["lines"] if l["keep"]]
    after = sum(l["duration"] for l in kept)
    before = rc.get("source_duration") or 0
    lines = [f"{before:.0f}s → {after:.0f}s ({(1 - after / before) * 100:.0f}% cut)" if before else ""]
    for l in rc["lines"]:
        mark = "✓" if l["keep"] else "✗"
        extra = f"  [{l['reason']}]" if not l["keep"] else (f"  note: {l['note']}" if l["note"] else "")
        lines.append(f"{mark} {l['id']:>2} ({l['duration']:.1f}s) {l['text']}{extra}")
    return "\n".join(lines)
