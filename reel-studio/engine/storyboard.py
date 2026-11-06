"""Storyboard: see the reel before it is built.

One still per moment (the footage with that moment's planned text, stickers and scene effect drawn on at
the point where everything has popped in), plus the cover, laid out on one page. The user ticks the
moments whose graphics they want, writes a note on any card, and only then is the full reel rendered.

Why: a full render + checking it costs time and Claude usage; changing your mind after the render costs
it twice. The storyboard is drawn by the engine (no Claude looking at frames), at half size, in seconds
per moment. Claude reads storyboard.json (a few lines) — never the pictures — to apply the ticks/notes.

    python -m engine storyboard <project>          draw it  → renders/storyboard/ + storyboard.json
    python -m engine storyboard-apply <project>    unticked moments → footage only (plan beats skip_graphics)

Studio page: /storyboard?p=<project>
"""
import json, os, subprocess, tempfile, shutil
from PIL import Image, ImageDraw

from . import project, render, packs
from .textfit import load_font

ROOT = project.ROOT
FONT = lambda n: os.path.join(ROOT, "library", "fonts", n)
SCALE = 0.5


def _moments(tl, plan):
    """[(start, end, beat index or None)] — one per plan beat for faceless plans, else per clip / scene."""
    beats = (plan or {}).get("beats") or []
    if beats and (plan or {}).get("format") == "faceless":
        out, t = [], 0.0
        for i, b in enumerate(beats):
            d = float(b.get("dur", 3))
            out.append((t, min(t + d, tl["duration"]), i))
            t += d
        return [m for m in out if m[1] - m[0] > 0.05]
    marks = sorted({round(x["start"], 2) for x in tl.get("broll", []) + tl.get("scenes", [])
                    if x.get("fx") not in ("series",)} | {0.0})
    if len(marks) < 2:                                   # a single shot: every ~3 s
        n = max(1, int(tl["duration"] // 3))
        marks = [i * tl["duration"] / n for i in range(n)]
    ends = marks[1:] + [tl["duration"]]
    return [(a, b, None) for a, b in zip(marks, ends) if b - a > 0.3]


def _settled(tl, a, b):
    """The moment to draw: after everything in the window has popped in, before it leaves."""
    t = a + min(max(1.0, (b - a) * 0.7), b - a - 0.12)
    for sc in tl.get("scenes", []):
        if sc["start"] <= a + 0.05 < sc["end"] and sc["fx"] == "pause_point":
            t = min(sc["start"] + 0.9, b - 0.1)
    return max(a, t)


def _describe(tl, a, b):
    """Plain-words list of what this moment shows (for the card and for Claude)."""
    from . import scenefx
    lines = []
    for sc in tl.get("scenes", []):
        if sc["fx"] in ("series",) or not (sc["start"] < b - 0.05 and sc["end"] > a + 0.05):
            continue
        sp = sc.get("spec") or {}
        name = "text + stickers" if sc["fx"] == "collage" and sp.get("overlay") else scenefx.LABELS.get(sc["fx"], sc["fx"])
        lines.append(f"effect: {name}")
        for k in ("kicker", "title", "text"):
            if sp.get(k):
                lines.append(f'"{sp[k]}"')
        for lab in sp.get("labels", []):
            lines.append(f'"{lab["text"] if isinstance(lab, dict) else lab}"')
        if sp.get("items"):
            lines.append("list: " + " / ".join(map(str, sp["items"])))
        st = [s.get("emoji") or os.path.splitext(os.path.basename(s.get("image", "")))[0].replace("_", " ")
              for s in sp.get("stickers", [])]
        if st:
            lines.append("stickers: " + ", ".join(x for x in st if x))
    for it in tl.get("items", []):
        if it["start"] < b - 0.05 and it["end"] > a + 0.05 and it.get("type") not in ("caption",):
            lines.append(f'{it.get("type")}: "{it["text"]}"' if it.get("text") else str(it.get("type")))
    return lines or ["footage only"]


def _file(slug, *p):
    return project.path(slug, "renders", "storyboard", *p)


def make(slug):
    tl = project.load(slug, "timeline.json")
    if not tl:
        raise SystemExit(f"No timeline for {slug} yet: run `python -m engine timeline {slug}` first.")
    plan = project.load(slug, "plan.json") or {}
    pack = packs.load(tl.get("pack"))
    old = {m["n"]: m for m in (project.load(slug, "storyboard.json") or {}).get("moments", [])}
    os.makedirs(_file(slug), exist_ok=True)
    cache = project.path(slug, "renders", "cache")
    os.makedirs(cache, exist_ok=True)
    base, _ = render.build_base_cached(tl, pack, cache, SCALE)
    fps = tl.get("fps", 30)
    tmp = tempfile.mkdtemp(prefix="sb-")
    moments = []
    try:
        for n, (a, b, bi) in enumerate(_moments(tl, plan), 1):
            t = _settled(tl, a, b)
            f = min(int(round(t * fps)), int(tl["duration"] * fps) - 1)
            vid = os.path.join(tmp, f"{n}.mp4")
            render.build_graphics(json.loads(json.dumps(tl)), pack, base, vid, SCALE, frames=(f, f + 1))
            jpg = _file(slug, f"{n:02d}.jpg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-frames:v", "1", "-q:v", "3", jpg], check=True)
            keep = not (plan.get("beats") and bi is not None and plan["beats"][bi].get("skip_graphics"))
            moments.append({"n": n, "start": round(a, 2), "end": round(b, 2), "beat": bi, "img": f"{n:02d}.jpg",
                            "shows": _describe(tl, a, b), "keep": old.get(n, {}).get("keep", keep),
                            "note": old.get(n, {}).get("note", "")})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    from . import cover
    sp = cover.spec_of(tl)
    if sp:                                               # the cover, drawn exactly as the render will make it
        tl2 = dict(tl)
        try:
            pic = (Image.open(os.path.join(ROOT, sp["photo"])) if sp.get("photo")
                   else cover._frame(base, float(sp.get("at", 1.0)), 540, 960))
            cover.design(pic, sp.get("title", ""), sp.get("kicker", ""), pack.get("colors", {}), 540, 960,
                         float(sp.get("y", 0.72))).save(_file(slug, "cover.jpg"), quality=88)
        except Exception as e:
            print(f"[storyboard] cover preview skipped ({e})")
    sb = {"project": slug, "cover": bool(sp) and os.path.exists(_file(slug, "cover.jpg")),
          "cover_text": [sp.get("kicker", ""), sp.get("title", "")] if sp else None,
          "duration": tl["duration"], "moments": moments}
    project.save(slug, "storyboard.json", sb)
    sheet(slug, sb)
    return sb


def sheet(slug, sb=None):
    """Everything on one image (contact-sheet style): how Claude or the user sees the whole plan at once."""
    sb = sb or project.load(slug, "storyboard.json")
    cards = ([("cover", _file(slug, "cover.jpg"), ["the cover (before play)"])] if sb.get("cover") else []) + \
            [(str(m["n"]), _file(slug, m["img"]), m["shows"]) for m in sb["moments"]]
    cw, ch, cap, cols = 216, 384, 120, min(5, len(cards))
    rows = (len(cards) + cols - 1) // cols
    W, H = cols * (cw + 16) + 16, rows * (ch + cap + 16) + 16
    out = Image.new("RGB", (W, H), (243, 245, 251))
    d = ImageDraw.Draw(out)
    fb, fs = load_font(FONT("Inter-Variable.ttf"), 15, 700), load_font(FONT("Inter-Variable.ttf"), 12, 400)
    for i, (lab, path, shows) in enumerate(cards):
        x, y = 16 + (i % cols) * (cw + 16), 16 + (i // cols) * (ch + cap + 16)
        try:
            out.paste(Image.open(path).convert("RGB").resize((cw, ch)), (x, y))
        except Exception:
            pass
        m = next((m for m in sb["moments"] if str(m["n"]) == lab), None)
        if m and not m.get("keep", True):                 # unticked: greyed out
            g = Image.new("RGB", (cw, ch), (243, 245, 251))
            out.paste(Image.blend(out.crop((x, y, x + cw, y + ch)), g, 0.65), (x, y))
        d.rounded_rectangle([x + 6, y + 6, x + 6 + 18 + 9 * len(lab), y + 30], 8, fill=(14, 22, 56))
        d.text((x + 15, y + 9), lab, font=fb, fill=(255, 255, 255))
        ty = y + ch + 6
        for ln in shows[:6]:
            while fs.getlength(ln) > cw and len(ln) > 4:
                ln = ln[:-2]
            d.text((x, ty), ln, font=fs, fill=(14, 22, 56)); ty += 17
    p = _file(slug, "storyboard.jpg")
    out.save(p, quality=85)
    return p


def save_choices(slug, choices):
    """choices: [{"n": 1, "keep": true, "note": "..."}] from the Studio page."""
    sb = project.load(slug, "storyboard.json") or {"moments": []}
    by = {int(c["n"]): c for c in choices}
    for m in sb["moments"]:
        c = by.get(m["n"])
        if c:
            m["keep"], m["note"] = bool(c.get("keep", True)), str(c.get("note", ""))[:500]
    project.save(slug, "storyboard.json", sb)
    sheet(slug, sb)
    return sb


def apply(slug):
    """Unticked moments → their plan beat becomes footage only. Returns the notes Claude still has to act on."""
    sb = project.load(slug, "storyboard.json") or {"moments": []}
    plan = project.load(slug, "plan.json")
    changed = 0
    if plan and plan.get("beats"):
        for m in sb["moments"]:
            if m.get("beat") is None:
                continue
            beat = plan["beats"][m["beat"]]
            want_skip = not m.get("keep", True)
            if bool(beat.get("skip_graphics")) != want_skip:
                beat["skip_graphics"] = want_skip
                if not want_skip:
                    beat.pop("skip_graphics")
                changed += 1
        project.save(slug, "plan.json", plan)
    notes = [f'moment {m["n"]} ({m["start"]}-{m["end"]}s): {m["note"]}' for m in sb["moments"] if m.get("note")]
    return {"changed": changed, "notes": notes}
