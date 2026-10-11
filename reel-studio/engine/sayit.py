"""Say-it cues — direct the edit out loud while you film.

Say "cue" and what you want, right before the line it's for, e.g.
    "cue zoom — this is the part nobody tells you"
    "cue big text — three things you need"
    "cue b-roll — we packed every order by hand"
The cue words are cut out of the reel, and the next line gets that treatment. Also:
    "scratch that" / "cue cut"   -> the line you just said is dropped (then just say it again)

Spoken cue (after "cue")                  What happens to the next line
zoom · zoom in · punch in                 a quick punch-in on you
push in · slow zoom                       a slow push-in
big text · full screen · takeover         the line fills the screen as big text
title                                     an opening-style title
b-roll · cutaway                          marked "b-roll here" (we use a clip from your uploads, or ask)
flash · transition · switch               a transition into this line
sticker · emoji                           a sticker that fits what you say
note · aside                              a handwritten side note
gif                                       one of your brand's GIFs pops in
"""
import re

TRIGGERS = {"cue", "queue", "q", "kew"}           # how speech-to-text tends to hear "cue"
CUES = [  # (spoken words after the trigger, kind)
    (("zoom", "in"), "zoom"), (("zoom",), "zoom"), (("punch", "in"), "zoom"), (("punch",), "zoom"),
    (("push", "in"), "push"), (("slow", "zoom"), "push"),
    (("big", "text"), "takeover"), (("full", "screen"), "takeover"), (("fullscreen",), "takeover"),
    (("takeover",), "takeover"), (("take", "over"), "takeover"),
    (("title",), "title"),
    (("b", "roll"), "broll"), (("broll",), "broll"), (("bee", "roll"), "broll"), (("cutaway",), "broll"),
    (("cut", "away"), "broll"),
    (("flash",), "transition"), (("transition",), "transition"), (("switch",), "transition"),
    (("sticker",), "sticker"), (("emoji",), "sticker"),
    (("note",), "note"), (("aside",), "note"),
    (("gif",), "gif"), (("jif",), "gif"),
    (("cut",), "scratch"), (("scratch",), "scratch"), (("redo",), "scratch"),
]
SCRATCH = [("scratch", "that")]

DO = {"zoom": "zoom:punch", "push": "zoom:push", "takeover": "takeover", "title": "title",
      "broll": "broll-here", "transition": "transition", "sticker": "sticker:auto", "note": "note", "gif": "gif:auto"}


def _toks(w):
    return re.sub(r"[^a-z ]", " ", w["w"].lower().replace("-", " ")).split()


def extract(words):
    """-> (words without the spoken cues, [{"kind", "before_i", "phrase"}]).
    before_i = index ("i") of the word the cue applies to (the next word said); kind "scratch" = drop
    the line before it."""
    flat = []                                   # (token, word position) — "b-roll" -> "b", "roll"
    for k, w in enumerate(words):
        for t in _toks(w):
            flat.append((t, k))
    drop, cues = set(), []
    j = 0
    while j < len(flat):
        tok, k = flat[j]
        hit = None
        if tok in TRIGGERS:
            for phrase, kind in CUES:
                seg = [t for t, _ in flat[j + 1:j + 1 + len(phrase)]]
                if tuple(seg) == phrase:
                    hit = (kind, 1 + len(phrase))
                    break
        else:
            for phrase in SCRATCH:
                if tuple(t for t, _ in flat[j:j + len(phrase)]) == phrase:
                    hit = ("scratch", len(phrase))
                    break
        if hit:
            kind, n = hit
            ks = {flat[x][1] for x in range(j, min(j + n, len(flat)))}
            drop |= ks
            nxt = next((words[x] for x in range(max(ks) + 1, len(words)) if x not in drop), None)
            prev = next((words[x] for x in range(min(ks) - 1, -1, -1) if x not in drop), None)
            cues.append({"kind": kind, "phrase": " ".join(words[x]["w"] for x in sorted(ks)),
                         "before_i": nxt.get("i") if nxt else None, "after_i": prev.get("i") if prev else None})
            j += n
        else:
            j += 1
    return [w for k, w in enumerate(words) if k not in drop], cues


def attach(lines, cues):
    """Put each cue on its line: line["cues"] (kinds), and drop lines the speaker scratched."""
    where = {w.get("i"): ln for ln in lines for w in ln["words"]}
    for c in cues:
        if c["kind"] == "scratch":
            ln = where.get(c["after_i"])
            if ln:
                ln["keep"] = False
                ln["reason"] = "you said “scratch that”"
            continue
        ln = where.get(c["before_i"])
        if ln is not None:
            ln.setdefault("cues", []).append(c["kind"])
    return lines


def dos(line):
    """Beat actions for a line's spoken cues."""
    return [DO[k] for k in line.get("cues", []) if k in DO]
