"""The style plan: a short table the user approves BEFORE the (slow) build.

    python -m engine styleplan <project>      -> prints the plan in plain words

Beat · line · what happens there (in plain words), plus the look, captions and sound plan.
The user answers "go" or changes anything in plain words ("make beat 1 a full-screen
takeover"); Claude edits plan.json and only then builds. Approving first means the result
matches their taste the first time — fewer rebuilds, fewer tokens.

Named effects: a beat can use "fx:<name>" — a saved recipe of treatments. Built-ins live in
library/effects.json; the user's own in brand/effects.json ("save that as 'spotlight'").
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILTIN = os.path.join(ROOT, "library", "effects.json")
MINE = os.path.join(ROOT, "brand", "effects.json")

PLAIN = {
    "takeover": "full-screen takeover (big type fills the screen)",
    "hook": "hook card on the first frames",
    "title": "designed title",
    "punch-in": "quick punch-in on the face",
    "zoom": "camera move",
    "bubble": "speech bubble",
    "label": "small label",
    "note": "handwritten note",
    "sticker": "sticker",
    "emoji": "emoji",
    "badge": "badge",
    "icon": "icon",
    "callout": "callout line pointing at the product",
    "broll": "b-roll clip",
    "card": "text card",
    "cta": "call to action",
    "reveal": "reveal",
    "frame": "framed card (you shrink into a rounded card)",
    "popup": "pop-up picture in a corner",
    "comment": "comment bubble",
    "comments": "comment collage",
    "story": "brand-story card",
    "window": "animation window",
    "keep-footage": "plain footage",
    "sfx": "sound",
}


def effects():
    """All named effects: built-in + the user's own (the user's win on a name clash)."""
    out = {}
    for p in (BUILTIN, MINE):
        if os.path.exists(p):
            out.update(json.load(open(p)))
    return out


def save_effect(name, treatments, description=""):
    """Teach a new named effect, e.g. save_effect("spotlight", ["punch-in", "label:{text}"])."""
    mine = json.load(open(MINE)) if os.path.exists(MINE) else {}
    mine[name.strip().lower()] = {"do": list(treatments), "about": description}
    os.makedirs(os.path.dirname(MINE), exist_ok=True)
    json.dump(mine, open(MINE, "w"), indent=2)
    return mine[name.strip().lower()]


def expand(do, text=""):
    """Replace fx:<name> entries by their saved treatments ({text} = the beat's words)."""
    fx = effects()
    out = []
    for d in do:
        kind, _, arg = d.partition(":")
        if kind == "fx" and arg.strip().lower() in fx:
            out += [t.replace("{text}", text) for t in fx[arg.strip().lower()]["do"]]
        else:
            out.append(d)
    return out


def describe(d):
    kind, _, arg = d.partition(":")
    if kind == "fx":
        e = effects().get(arg.strip().lower())
        return f"'{arg}' effect" + (f" ({e['about']})" if e and e.get("about") else "")
    words = PLAIN.get(kind, kind)
    arg = arg.split("|")[0].split("@")[0]
    return f"{words}: {arg}" if arg and kind not in ("zoom", "sticker", "sfx") else words


def table(plan, roughcut):
    lines = {l["id"]: l for l in roughcut.get("lines", []) if l.get("keep", True)}
    by_line = {b.get("line"): b for b in plan.get("beats", []) if b.get("line") is not None}
    rows = []
    for n, (lid, l) in enumerate(lines.items(), 1):
        b = by_line.get(lid, {})
        do = b.get("do", [])
        rows.append({"beat": n, "line": lid, "text": l["text"],
                     "seconds": round(l.get("duration", l.get("end", 0) - l.get("start", 0)), 1),
                     "treatment": " + ".join(describe(d) for d in do) or "plain footage, captions running"})
    return rows


def summary(plan, roughcut):
    look = plan.get("look", "clean")
    cap = plan.get("captions") or ("quiet single words" if look == "clean" else "brand captions")
    from .sounddesign import KIT_FOR_LOOK, DEFAULT_KIT
    kit = plan.get("sound_kit") or KIT_FOR_LOOK.get(look, DEFAULT_KIT)
    sound = {"soft": "soft real sounds only (click, pop, tap, soft whoosh), nothing repeats back to back",
             "clean": "clean clicks and pops", "luxe": "glassy taps and chimes", "playful": "bouncy pops",
             "digital": "digital blips"}.get(kit, kit)
    rows = table(plan, roughcut)
    out = [f"STYLE PLAN — look: {look} · captions: {cap} · sound: {sound}"
           + (f" · speed {plan['speed']}x" if plan.get("speed") else ""), ""]
    for r in rows:
        out.append(f"{r['beat']:>2}. ({r['seconds']}s) “{r['text'][:70]}”")
        out.append(f"      → {r['treatment']}")
    out += ["", "Say “go” to build, or tell me what to change (e.g. “beat 1: full-screen takeover”)."]
    return "\n".join(out)
