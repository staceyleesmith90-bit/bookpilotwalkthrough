"""Style plan -> timeline.

Claude writes a SHORT plan (a few lines of JSON per reel — cheap). This module does all
the heavy lifting locally: timings from the rough cut, layout, auto stickers, sound
cues, logo, captions. The result is timeline.json, which the renderer and the manual
editor both use.

Plan format:
{
  "format": "talking-head" | "faceless" | "voiceover",
  "pack": "brand" | "<preset>",           "grade": "<optional>",
  "captions": "karaoke" | "single-word" | "line" | "off",   (optional)
  "music": {"file": "inbox/song.mp3", "gain": 0.18},        (optional)
  "logo": true | false | {"file", "position", "width"},     (default: brand logo)
  "auto_stickers": true,
  "beats": [ {"line": 3, "do": ["takeover", "sticker:auto"]},        # talking head
             {"text": "Stop editing for hours", "do": ["takeover"]} ]  # faceless
}
Treatments ("do"): hook:<text> · takeover[:<text>] · punch-in · bubble:<text> ·
label:<text> · sticker:auto|<name> · emoji:<concept|char> · badge:<text> ·
broll:<file> · card:<text> · cta:<text> · reveal · sfx:<name>
"""
import math, os, re
from . import emoji, layout, packs, roughcut, stickers

W, H = 1080, 1920
FACE = (230, 380, 850, 1180)       # where a talking head's face + upper body usually is (prefer to keep clear)
HEAD = (360, 420, 720, 880)        # the head itself: never cover it
CAPTION_BOX = (60, 1150, 1020, 1340)
_ids = {}
# words too vague to trigger an automatic sticker (fine when Claude asks explicitly)
AUTO_SKIP = {"this", "here", "up", "next", "key", "yes", "no", "step", "top", "best", "look", "point",
             "new", "easy", "works", "done", "text", "post", "like", "home", "time"}


def _id(prefix):
    _ids[prefix] = _ids.get(prefix, 0) + 1
    return f"{prefix}{_ids[prefix]}"


def _words_time(words, tmap):
    out = []
    for w in words:
        a = tmap(w["start"])
        b = tmap(w["end"])
        if a is not None:
            out.append({"w": w["w"], "start": round(a, 3), "end": round(b if b is not None else a + 0.25, 3)})
    return out


TRANSITION_SFX = {"flash": "hit", "whip": "whoosh", "zoom-blur": "whoosh", "glitch": "click", "rgb-split": "swish",
                  "light-leak": "swish", "film-burn": "swish", "pixelate": "tick", "spin": "whoosh",
                  "blur": "swish", "shape-wipe": "swish", "dip-black": "swish", "dip-white": "swish"}
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_FACES = {}


def _faces_at(source, src_t):
    """Faces at src_t (on-device face detection), padded to cover hair and chin, cached."""
    key = (source, round(src_t, 1))
    if key not in _FACES:
        try:
            from .segment import face_boxes
            fs = face_boxes(os.path.join(ROOT_DIR, source), src_t)
        except Exception:
            fs = []
        _FACES[key] = [(max(0, x0 - (x1 - x0) * 0.35), max(0, y0 - (y1 - y0) * 0.6),
                        min(W, x1 + (x1 - x0) * 0.35), min(H, y1 + (y1 - y0) * 0.35)) for x0, y0, x1, y1, _ in fs]
    return _FACES[key]


def _head_at(source, src_t):
    """The speaker's head (biggest face, if it's a real on-camera face and not someone in a corner)."""
    for b in _faces_at(source, src_t)[:1]:
        w, cx = b[2] - b[0], (b[0] + b[2]) / 2
        if w >= 150 and W * 0.12 < cx < W * 0.88:
            return b
    return None


def _source_time(cuts, out_t):
    """Output time -> source time, through the rough-cut ranges."""
    acc = 0.0
    for a, b in cuts:
        if out_t <= acc + (b - a):
            return a + (out_t - acc)
        acc += b - a
    return cuts[-1][1] if cuts else out_t


def _box(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


SIZE_LABEL = {"s": "Small", "m": "Medium", "l": "Large", "xl": "Extra large", "xxl": "XXL"}
SIZE_WORDS = {"s": ["small"], "m": ["medium"], "l": ["large"], "xl": ["extra", "xl"], "xxl": ["xxl", "double"]}


def _takeover_parts(txt):
    """'M · L · XL' -> ['M', 'L', 'XL']; 'best of the best' -> ['best of', 'the best'] (short lines)."""
    if re.search(r"\s[·|/•]\s|,", txt):
        return [p.strip() for p in re.split(r"\s*[·|/•,]\s*", txt) if p.strip()]
    words = txt.split()
    if len(words) <= 2 or len(txt) <= 12:
        return [txt]
    n_lines = 2 if len(txt) <= 26 else 3
    target = len(txt) / n_lines                 # balanced lines, like an editor would break them
    lines, cur = [], ""
    for w in words:
        if cur and len(lines) < n_lines - 1 and len(cur) + 1 + len(w) / 2 > target:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines


def _spoken_times(parts, ws, a, b_end):
    """When each part is said (its first word, or the size word for S/M/L/XL); evenly spread if unsure."""
    out, i = [], 0
    norm = [re.sub(r"[^a-z0-9]", "", w.get("w", "").lower()) for w in (ws or [])]
    for k, p in enumerate(parts):
        key = re.sub(r"[^a-z0-9 ]", "", p.lower()).split()
        cands = SIZE_WORDS.get(key[0], [key[0]]) if key else []
        hit = next((j for j in range(i, len(norm)) if norm[j] in cands), None)
        if hit is None:
            out.append(None)
        else:
            out.append(ws[hit]["start"])
            i = hit + 1
    span = max(b_end - a, 0.6)
    for k, t in enumerate(out):                 # fill gaps evenly, keep order
        if t is None:
            out[k] = a + 0.15 + span * 0.6 * k / max(len(out), 1)
    for k in range(1, len(out)):
        out[k] = max(out[k], out[k - 1] + 0.12)
    return [round(min(t, b_end - 0.3), 3) for t in out]


def _spot(size, taken, near, shrink=True, min_k=0.68):
    """Nearest free spot. Keeps stickers readable: first try clear of the whole face/body area,
    then allow overlapping shoulders/background (never the head), and only then shrink (to 68%
    minimum — smaller stickers are unreadable on a phone). Returns (cx, cy, box, scale)."""
    relaxed = [HEAD if t == FACE else t for t in taken]
    tries = [(k, taken) for k in ((1.0, 0.82) if shrink else (1.0,))]
    if relaxed != taken:
        tries += [(k, relaxed) for k in ((1.0, 0.82) if shrink else (1.0,))]
    if shrink and min_k <= 0.68:
        tries += [(0.68, taken), (0.68, relaxed), (0.55, taken), (0.55, relaxed)]
    tries = [(k, tk) for k, tk in tries if k >= min_k or not shrink] or tries
    for k, tk in tries:
        sz = (size[0] * k + 30, size[1] * k + 30)  # room for pop/float animation
        r = layout.free_spot(sz, tk, near=near)
        if r:
            return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r, k
    x0, y0, x1, y1 = layout.SAFE_BOX
    taken = relaxed
    k = max(min_k, 0.55) if shrink else 1.0
    sz = (size[0] * k, size[1] * k)
    # still no room: slide down from the target until clear of everything
    cx = min(max(near[0], x0 + sz[0] / 2), x1 - sz[0] / 2) if sz[0] < x1 - x0 else W / 2
    for cy in range(int(near[1]), int(y1 - sz[1] / 2), 10):
        r = (cx - sz[0] / 2, cy - sz[1] / 2, cx + sz[0] / 2, cy + sz[1] / 2)
        if not any(layout.overlaps(r, t) for t in taken):
            return cx, cy, r, k
    cx = min(max(near[0], x0 + sz[0] / 2), x1 - sz[0] / 2)
    cy = min(max(near[1], y0 + sz[1] / 2), y1 - sz[1] / 2)
    return cx, cy, (cx - sz[0] / 2, cy - sz[1] / 2, cx + sz[0] / 2, cy + sz[1] / 2), k


def _logo_item(plan, pack, dur):
    spec = plan.get("logo", True)
    brand_logo = pack.get("logo")
    if spec is False or (spec is True and not brand_logo):
        return None
    spec = dict(brand_logo or {}, **(spec if isinstance(spec, dict) else {}))
    if not spec.get("file"):
        return None
    it = {"id": "logo", "type": "overlay", "file": spec["file"], "start": 0, "end": dur,
          "width": spec.get("width", 230), "anim": "fade", "exit": "none", "z": 50,
          "knock_out_white": spec.get("knock_out_white", True), "role": "logo"}
    from .render import item_image
    img = item_image(it, pack)
    pos = spec.get("position", "top-left")
    if "x" in spec and "y" in spec:
        it["x"], it["y"] = spec["x"], spec["y"]
    else:
        fx, fy = layout.POSITIONS[pos]
        x0, y0, x1, y1 = layout.SAFE_BOX
        it["x"] = x0 + 24 + img.width / 2 + fx * (x1 - x0 - img.width - 48)
        it["y"] = y0 + 24 + img.height / 2 + fy * (y1 - y0 - img.height - 48)
    it["_box"] = _box(it["x"], it["y"], img.width, img.height)
    return it


def to_timeline(plan, rc=None, source=None):
    _ids.clear()
    pack = packs.load(plan.get("pack"))
    for k in ("transition", "zoom"):  # plan/template can override the pack's defaults
        if plan.get(k):
            pack[k] = plan[k]
    fmt = plan.get("format", "talking-head" if rc else "faceless")
    beats = plan.get("beats", [])
    items, cues, zooms, broll, transitions = [], [], [], [], []
    layouts = []
    if plan.get("inspiration"):                   # "make it feel like this reel": its settings fill the gaps
        import json as _json
        pth = os.path.join(ROOT_DIR, "brand", "inspiration", f"{plan['inspiration']}.json")
        if os.path.exists(pth):
            prof = _json.load(open(pth))
            from .inspire import plan_settings
            plan = dict({k: v for k, v in plan_settings(prof).items() if v}, **plan)
    tl = {"version": 1, "pack": plan.get("pack", "brand"), "fps": 30, "size": [W, H], "format": fmt}
    cam_info = None
    if plan.get("grade"):
        tl["grade"] = plan["grade"]

    # ---- timing windows per beat
    windows = []
    if rc is not None:
        ranges = roughcut.kept_ranges(rc)
        tmap, dur = roughcut.time_map(ranges)
        tl.update(source=source, cuts=[list(r) for r in ranges])
        if source and plan.get("auto_camera", True):
            from . import director
            src_abs = os.path.join(ROOT_DIR, source)
            cam_info = director.analyse(src_abs)
            tl["shake"] = round(cam_info["jitter"], 1)
            if plan.get("stabilize", "auto") is True or (plan.get("stabilize", "auto") == "auto" and cam_info["jitter"] > 4):
                d, f = os.path.split(src_abs)
                stable = director.stabilise(src_abs, os.path.join(d, "stable-" + os.path.splitext(f)[0] + ".mp4"))
                if stable != src_abs:
                    source = os.path.relpath(stable, ROOT_DIR)
                    tl.update(source=source, stabilized=True)
        lines = {l["id"]: l for l in rc["lines"] if l["keep"]}
        all_words = _words_time([w for l in rc["lines"] if l["keep"] for w in l["words"]], tmap)
        by_line = {}
        for b in beats:
            by_line[b.get("line")] = b
        # every kept line becomes a beat (plain if Claude gave no treatment)
        for lid, l in lines.items():
            ws = _words_time(l["words"], tmap)
            if not ws:
                continue
            b = by_line.get(lid, {"line": lid, "do": []})
            windows.append((ws[0]["start"], ws[-1]["end"] + 0.12, b, l["text"], ws))
        # the "clean" look (default): quiet single words, small — the footage and ONE treatment
        # per moment do the talking. Any caption style the user/plan names wins.
        clean = plan.get("look", "clean") == "clean"
        cap_style = plan.get("captions") or ("single-word" if clean else pack["captions"]["style"])
        wpl = pack["captions"].get("words_per_line", 3)
        if cap_style == "single-word":
            wpl = 1
        elif cap_style != pack["captions"]["style"] and wpl < 3:
            wpl = 3                                # e.g. a one-word pack switched to karaoke
        tl["captions"] = {"style": cap_style, "words_per_line": wpl,
                          "words": all_words, "y": 1245}
        if clean and not plan.get("captions"):
            tl["captions"].update(size=62, case="lower")
    else:
        t = 0.0
        for b in beats:
            n = len(b.get("text", "").split())
            d = b.get("dur") or max(1.6, 0.32 * n + 0.6)
            windows.append((t, t + d, b, b.get("text", ""), []))
            t += d
        dur = t
        tl["background"] = pack["colors"]["bg"]
        tl["captions"] = {"style": "off"}
    tl["duration"] = round(dur, 3)

    logo = _logo_item(plan, pack, dur)
    fixed = [logo["_box"]] if logo else []
    base_on_video = rc is not None
    auto = plan.get("auto_stickers", plan.get("look", "clean") != "clean")   # clean: no filler stickers
    sticker_budget = max(2, int(dur / 6))          # ~1 sticker per 6s by default
    used_stickers = set()
    # premium by default: frosted-glass stickers, serif words, glass badges. A playful brand can
    # opt out with "look": "playful" (uses the brand's own sticker style) or set "sticker_style".
    look = plan.get("look", "clean")
    sticker_style = plan.get("sticker_style") or ("glass" if look in ("premium", "clean") else None)
    style = sticker_style or pack.get("sticker", {}).get("style", "doodle")
    # clean look: badges are CapCut-style text labels (flat rounded box), not glass or stickers
    badge_shape = plan.get("badge_shape") or ("label" if look == "clean" else "glass" if style == "glass" else "chip")

    for bi, (a, b_end, beat, text, ws) in enumerate(windows):
        from .styleplan import expand
        do = expand(list(beat.get("do", [])), text)       # named effects (fx:<name>) -> treatments
        on_video = base_on_video or any(d.startswith("broll:") for d in do)
        taken = list(fixed) + ([FACE, CAPTION_BOX] if on_video else [])
        if base_on_video and source and not beat.get("broll"):
            mid = _source_time(tl["cuts"], (a + b_end) / 2)
            faces = _faces_at(source, mid)
            if faces:                              # protect every face where it really is, not a guess
                taken = [t for t in taken if t != FACE] + faces
        big_text = None
        if not on_video and not any(d.split(":")[0] in ("takeover", "card", "bubble", "cta", "title", "keep-footage",
                                                           "broll", "label") for d in do):
            do.insert(0, "takeover")               # faceless: every beat shows its words
        if auto and not any(d.startswith(("sticker", "emoji", "badge", "icon", "3d", "anim", "stamp", "callout"))
                            for d in do) and len(used_stickers) < sticker_budget:
            do.append("sticker:auto")

        for d in do:
            kind, _, arg = d.partition(":")
            if kind == "hook":
                it = {"id": _id("hook"), "type": "text", "role": "hook", "text": arg or text, "start": 0,
                      "end": max(b_end, 2.5), "w": 820, "h": 280, "max_px": 110,
                      "anim": "pop", "on_video": on_video, "z": 10,
                      "color": "caption" if on_video else "ink"}
                from .render import item_image
                img = item_image(it, pack)
                # top of the safe zone, but below the logo if they'd touch
                it["x"], it["y"], r, it["scale"] = _spot(img.size, list(fixed), (W / 2, 330), shrink=False)
                items.append(it)
                taken.append(r)
                cues.append((0.0, pack["sfx"]["hook"], 0.8))
            elif kind == "takeover" and on_video and look == "clean":
                # CapCut way: each part pops in as a clean label the moment it's said, stacked
                parts = _takeover_parts(arg or text)
                times = _spoken_times(parts, ws, a, b_end)
                parts = [SIZE_LABEL.get(p.lower(), p) for p in parts]      # show the word she says, not a code
                n = len(parts)
                y0 = 760 - (n - 1) * 75
                for k, (part, t_in) in enumerate(zip(parts, times)):
                    last = k == n - 1
                    it = {"id": _id("take"), "type": "badge", "shape": "label", "text": part,
                          "label_style": "pop" if last and n > 1 else "label", "px": 84 if n > 1 else 96,
                          "start": t_in, "end": b_end, "x": W / 2, "y": y0 + k * 150, "anim": "pop",
                          "rotate": 0, "z": 12, "role": "takeover", "hide_captions": True}
                    items.append(it)
                    cues.append((t_in, "pop", 0.5))
                big_text = _box(W / 2, y0 + (n - 1) * 75, 760, n * 150)
                taken.append(big_text)
            elif kind == "takeover":
                txt = arg or text
                box_h = 820 if on_video else 680
                cy = 800 if on_video else 980
                it = {"id": _id("take"), "type": "text", "role": "takeover", "text": txt, "start": a, "end": b_end,
                      "x": 495, "y": cy, "w": 820, "h": box_h, "max_px": 200, "min_px": 56, "anim": "pop",
                      "on_video": on_video, "hide_captions": True, "z": 10,
                      "color": "caption" if on_video else "ink"}
                from .render import item_image
                img = item_image(it, pack)
                items.append(it)
                big_text = _box(495, cy, img.width + 40, img.height + 40)
                taken.append(big_text)
                cues.append((a, pack["sfx"]["hook"] if bi == 0 else pack["sfx"]["text_in"], 0.75))
            elif kind == "title":
                # "title:<template>:<text>"  or beat["title"] = {template, title, kicker, sub, behind...}
                spec = dict(beat.get("title") or {})
                if arg:
                    tpl, _, ttxt = arg.partition(":")
                    spec.setdefault("template", tpl or "with-me")
                    if ttxt:
                        spec["title"] = ttxt
                spec.setdefault("template", plan.get("title_template") or "with-me")
                spec.setdefault("title", text)
                if not on_video:
                    spec["behind"] = False
                    spec.setdefault("ink", pack["colors"]["ink"])
                from . import titles
                layers = titles.build(spec, pack)
                comp, off = titles.composite(layers)
                # behind-the-person titles sit at hairline height so the head overlaps them
                ty = (1330 if spec["template"] == "location" else
                      spec.get("y") or (560 if spec.get("behind") and on_video else 780 if on_video else 860))
                if spec.get("behind") and on_video and not spec.get("y") and source:
                    from .segment import head_top
                    src_t = _source_time(tl["cuts"], a + 0.5)
                    top = head_top(os.path.join(ROOT_DIR, source), src_t)
                    if top is not None:
                        # letters' lower ~40% tucked behind the top of the head
                        ty = max(layout.SAFE_BOX[1] + comp.height / 2, top + comp.height * 0.12)
                # white title over a bright background disappears: switch to the brand's strongest colour
                if on_video and cam_info is not None and not spec.get("ink") and len(cam_info["frames"]):
                    from .director import AFPS, AH
                    fr = cam_info["frames"][min(len(cam_info["frames"]) - 1,
                                                int(_source_time(tl["cuts"], a + 0.5) * AFPS))]
                    y0 = int(max(0, ty - comp.height / 2) * AH / H)
                    y1 = int(min(H, ty + comp.height / 2) * AH / H)
                    if (fr[y0:max(y1, y0 + 1)] > 175).mean() > 0.3:   # a third of the area is bright
                        c = pack["colors"]
                        # the brand colour if it reads well on light footage, else the brand's dark ink
                        spec["ink"] = next((v for v in (c["pop"], c["accent"]) if packs.contrast(v, "#F2F2F2") >= 3.2),
                                           c.get("ink", "#111111"))
                        layers = titles.build(spec, pack)
                        comp, off = titles.composite(layers)
                dur_needed = max((l["delay"] + l.get("type_dur", 0.9) for l in layers), default=1) + 1.2
                if spec["template"] == "tag" and not spec.get("y"):
                    ty = 930                             # quiet label just above the middle, like a watermark
                hold = spec.get("hold", spec["template"] == "tag")   # vlog labels stay the whole reel
                it = {"id": _id("title"), "type": "title", "spec": spec, "start": a,
                      "end": tl["duration"] if hold else max(b_end, a + dur_needed), "x": W / 2, "y": ty, "z": 15,
                      "hide_captions": spec["template"] not in ("location", "tag"), "anim": "none"}
                items.append(it)
                taken.append(_box(W / 2 + off[0], ty + off[1], comp.width + 30, comp.height + 30))
                big_text = taken[-1]
                cues.append((a, pack["sfx"].get("title", "swish"), 0.55))
                for l in layers:  # a key click per typed character, a soft swish per script write-on
                    if l["anim"] == "type":
                        n = min(l.get("chars", 10), 40)
                        for c in range(n):
                            cues.append((a + l["delay"] + c * l["type_dur"] / max(n, 1), "click", 0.22))
                    elif l["anim"] == "write":
                        cues.append((a + l["delay"], "swish", 0.25))
            elif kind == "note":
                # handwritten aside + a drawn arrow pointing at the subject
                it = {"id": _id("note"), "type": "text", "role": "note", "text": arg or text, "font_role": "accent",
                      "start": a + 0.2, "end": b_end, "w": 520, "h": 200, "max_px": 80, "anim": "type",
                      "color": "caption" if on_video else "accent", "on_video": on_video, "z": 25}
                from .render import item_image
                im = item_image(it, pack)
                it["x"], it["y"], r, it["scale"] = _spot(im.size, taken, (W * 0.3, 470), shrink=False)
                taken.append(r)
                items.append(it)
                target = ((FACE[0] + FACE[2]) / 2, FACE[1] + 60) if on_video else (W / 2, H / 2)
                ang = math.degrees(math.atan2(target[1] - it["y"], target[0] - it["x"]))
                arr = {"id": _id("arr"), "type": "sticker", "name": "arrow", "start": a + 0.5, "end": b_end,
                       "size": 190, "colour": "paper" if on_video else "accent", "anim": "pop", "z": 25,
                       "style": "doodle", "rotate": ang + 30,
                       "x": it["x"] + math.cos(math.radians(ang)) * (im.width * 0.35 + 90),
                       "y": it["y"] + math.sin(math.radians(ang)) * (im.height * 0.5 + 80)}
                items.append(arr)
                cues.append((a + 0.2, "click", 0.3))
                cues.append((a + 0.5, pack["sfx"]["sticker_in"], 0.45))
            elif kind == "punch-in":
                zooms.append({"start": a, "end": b_end, "type": "punch", "scale": float(arg or 1.12)})
            elif kind == "zoom":
                # zoom:<punch|push|pull|whip|shake|pulse|focus|drift>[:scale]
                ztype, _, zs = arg.partition(":")
                ztype = ztype or pack.get("zoom", "push")
                default_s = {"push": 1.12, "pull": 1.12, "whip": 1.2, "pulse": 1.08, "focus": 1.3, "drift": 1.08}.get(ztype, 1.15)
                z = {"start": a, "end": b_end if ztype not in ("shake", "pulse") else min(b_end, a + 0.6),
                     "type": ztype, "scale": float(zs or default_s)}
                if ztype == "focus" and on_video:
                    z["cx"], z["cy"] = (FACE[0] + FACE[2]) / 2, (FACE[1] + FACE[3]) / 2 - 80
                zooms.append(z)
                if ztype in ("whip", "shake"):
                    cues.append((a, "whoosh" if ztype == "whip" else "hit", 0.5))
            elif kind == "transition":
                ttype = arg or pack.get("transition", "whip")
                transitions.append({"t": round(a, 3), "type": ttype, "dur": 0.36})
                cues.append((max(a - 0.12, 0), TRANSITION_SFX.get(ttype, "whoosh"), 0.5))
            elif kind == "bubble":
                from .render import item_image
                it = {"id": _id("bub"), "type": "bubble", "text": arg or text, "start": a + 0.15, "end": b_end,
                      "width": 620, "anim": "pop", "z": 20}
                img = item_image(it, pack)
                it["x"], it["y"], r, it["scale"] = _spot(img.size, taken, (W / 2, 560 if on_video else 800), shrink=False)
                taken.append(r)
                items.append(it)
                cues.append((a + 0.15, pack["sfx"]["text_in"], 0.6))
            elif kind == "label":
                it = {"id": _id("lab"), "type": "text", "role": "label", "text": arg, "font_role": "accent",
                      "start": a + 0.2, "end": b_end, "w": 600, "h": 160, "max_px": 90, "anim": "type",
                      "color": "accent", "on_video": on_video, "z": 20}
                from .render import item_image
                img = item_image(it, pack)
                it["x"], it["y"], r, it["scale"] = _spot(img.size, taken, (W / 2, 460))
                taken.append(r)
                items.append(it)
                cues.append((a + 0.2, "click", 0.4))
            elif kind in ("sticker", "emoji", "badge", "icon", "3d", "anim", "stamp"):
                name, t0 = None, a + 0.3
                if kind == "sticker" and arg in ("", "auto"):
                    # pick from the words, timed to the moment the word is said
                    for w in ws or [{"w": x, "start": a + 0.3} for x in text.split()]:
                        wl0 = re.sub(r"[^a-z']", "", w["w"].lower())
                        if wl0 in AUTO_SKIP or len(wl0) < 3:
                            continue
                        cand = stickers.find(wl0, strict=True)
                        if cand and cand not in used_stickers:
                            name, t0 = cand, w["start"]
                            break
                        wl = re.sub(r"[^a-z']", "", w["w"].lower())
                        if style == "emoji" and emoji.known(wl) and f"emoji:{wl}" not in used_stickers:
                            name, t0 = f"emoji:{wl}", w["start"]
                            break
                    if not name and beat.get("custom_sticker"):
                        name = "custom:" + beat["custom_sticker"]
                    if not name:
                        continue
                elif kind == "emoji":
                    name = f"emoji:{arg}"
                elif kind == "badge":
                    name = f"badge:{arg}"
                elif kind in ("icon", "3d", "anim", "stamp"):
                    name = f"{kind}:{arg}"
                else:
                    name = arg
                used_stickers.add(name)
                size = 300 if kind != "badge" else 320
                colour = "pop" if len(used_stickers) % 2 else "accent"
                it = {"id": _id("stk"), "type": "sticker", "name": name, "start": max(a, t0 - 0.05),
                      "end": b_end, "size": size, "colour": colour, "seed": bi, "anim": "pop",
                      "float": True, "z": 30, "rotate": [-8, 6, -4, 9][bi % 4]}
                if kind == "sticker" and arg in ("", "auto"):
                    it["auto_pick"] = True
                if kind == "badge":
                    it.update(type="badge", text=arg, shape=badge_shape)
                    if badge_shape == "label":
                        it.update(rotate=[-3, 3][bi % 2], float=False, px=74)
                elif sticker_style and not name.startswith(("emoji:", "3d:", "anim:")) and \
                        (sticker_style == "glass" or not name.startswith(("stamp:", "custom:"))):
                    it["style"] = sticker_style               # one consistent sticker look for this reel
                from .render import item_image
                img = item_image(it, pack)
                if img is None:
                    continue
                near = (big_text[2] - 60, big_text[1] + 40) if big_text else (W * 0.72, 520 if on_video else 560)
                wide_glass = it.get("shape") == "glass" or img.width > 700
                if wide_glass:                       # wide premium labels: free band at the top, keep them big
                    near = (W / 2, 330)
                it["x"], it["y"], r, it["scale"] = _spot(img.size, taken, near, min_k=0.86 if wide_glass else 0.68)
                if it.get("auto_pick") and any(layout.overlaps(r, t) for t in taken):
                    continue                          # no clear space: skip it (clean beats clutter)
                taken.append(r)
                items.append(it)
                cues.append((it["start"], pack["sfx"]["sticker_in"], 0.55))
            elif kind == "broll":
                broll.append({"file": arg, "start": a, "dur": round(b_end - a, 3)})
                ttype = pack.get("transition", "whip")
                transitions.append({"t": round(a, 3), "type": ttype, "dur": 0.3})
                cues.append((max(a - 0.1, 0), TRANSITION_SFX.get(ttype, pack["sfx"]["transition"]), 0.45))
            elif kind == "card":
                items.append({"id": _id("card"), "type": "card", "text": arg or text, "start": a, "end": b_end,
                              "x": W / 2, "y": H / 2, "anim": "fade", "z": 5, "hide_captions": True})
                cues.append((max(a - 0.1, 0), pack["sfx"]["transition"], 0.5))
            elif kind == "cta":
                it = {"id": _id("cta"), "type": "badge", "text": arg or "Follow for more",
                      "shape": badge_shape if badge_shape in ("glass", "label") else "pill",
                      "size": 420 if badge_shape == "glass" else 760, "colour": "pop", "start": a, "end": b_end,
                      "anim": "slide", "z": 40, "px": 66, "label_style": "pop"}
                from .render import item_image
                img = item_image(it, pack)
                it["x"], it["y"], r, it["scale"] = _spot(img.size, taken, (W / 2, 1060 if on_video else 1200))
                taken.append(r)
                items.append(it)
                cues.append((a, pack["sfx"]["cta"], 0.7))
            elif kind == "callout":
                # callout:<LABEL>[|<sub line>][@x,y]  — a dot on the product + hairline + label
                txt, _, at = arg.partition("@")
                label, _, sub = txt.partition("|")
                ax, ay = (float(v) for v in at.split(",")) if at else (W * 0.5, 1030 if on_video else 900)
                room_r, room_l = layout.SAFE_BOX[2] + 60 - ax, ax - 30
                side = "right" if room_r >= room_l else "left"
                it = {"id": _id("call"), "type": "callout", "text": label.strip(), "sub": sub.strip() or None,
                      "side": side, "length": 150, "size": 330, "colour": "pop", "start": a + 0.2, "end": b_end,
                      "anim": "fade", "z": 32,
                      "max_w": int((layout.SAFE_BOX[2] + 60 - ax) if side == "right" else (ax - 30))}
                from .render import item_image
                img = item_image(it, pack)
                axo, ayo = img.info["anchor"]
                it["x"], it["y"] = ax + img.width / 2 - axo, ay + img.height / 2 - ayo
                if it["x"] + img.width / 2 > layout.SAFE_BOX[2] + 60 or it["x"] - img.width / 2 < 0:
                    it["length"] = max(60, it["length"] - int(max(it["x"] + img.width / 2 - layout.SAFE_BOX[2] - 60,
                                                                   -(it["x"] - img.width / 2))) - 10)
                    img = item_image(it, pack)
                    axo, ayo = img.info["anchor"]
                    it["x"], it["y"] = ax + img.width / 2 - axo, ay + img.height / 2 - ayo
                items.append(it)
                taken.append(_box(it["x"], it["y"], img.width, img.height))
                cues.append((it["start"], "click", 0.45))
            elif kind in ("comment", "comments"):  # REAL comments only: comment:@handle|their words
                entries = [e for e in arg.split(";;") if "|" in e]
                for n, e in enumerate(entries[:4]):
                    handle, _, words = e.partition("|")
                    it = {"id": _id("cmt"), "type": "comment", "handle": handle.strip(), "text": words.strip(),
                          "size": 620, "start": a + 0.25 * n, "end": b_end, "anim": "pop", "z": 36,
                          "x": W / 2 + (-60 if n % 2 else 60) * (n > 0), "y": 360 + n * 190, "rotate": [0, -2, 2, -1][n]}
                    items.append(it)
                    cues.append((it["start"], "pop", 0.45))
            elif kind == "story":                 # story:word:TEXT | story:year:1886|label | story:person:file|NAME|role | story:logo
                sk, _, rest = arg.partition(":")
                parts = rest.split("|")
                it = {"id": _id("story"), "type": "story", "kind": sk, "text": parts[0] if parts else "",
                      "start": a, "end": b_end, "x": W / 2, "y": H / 2, "anim": "fade", "z": 4, "hide_captions": True,
                      "bg": ["pop", "paper", "ink"][sum(1 for i in items if i["type"] == "story") % 3]}
                if sk == "year" and len(parts) > 1:
                    it["label"] = parts[1]
                if sk == "person":
                    it.update(file=parts[0], text=parts[1] if len(parts) > 1 else "", label=parts[2] if len(parts) > 2 else "")
                items.append(it)
                cues.append((a, "hit" if sk in ("word", "year") else "whoosh", 0.5))
            elif kind == "frame":                 # framed-card layout for this beat
                layouts.append({"start": round(a, 3), "end": round(b_end, 3)})
            elif kind == "popup":                 # popup:<seconds or file>|<label>
                what, _, label = arg.partition("|")
                it = {"id": _id("pop"), "type": "photo", "label": label.strip() or None, "size": 360,
                      "start": a + 0.3, "end": min(b_end, a + 3.2), "anim": "pop", "z": 34,
                      "rotate": [5, -4][len(items) % 2]}
                if what.strip() in ("", "auto") and source:     # a still from this very moment
                    it.update(grab_from=source, grab_t=_source_time(tl["cuts"], (a + b_end) / 2))
                elif re.match(r"^[\d.]+$", what.strip()) and source:
                    it.update(grab_from=source, grab_t=_source_time(tl["cuts"], float(what)))
                else:
                    it["file"] = what.strip()
                it["x"], it["y"] = (820, 380) if it["rotate"] > 0 else (260, 1180)
                items.append(it)                    # its camera-shutter sound comes from sound design
            elif kind == "window":                # window:<app|chat|checklist|stat|doc|product>|<text>|...
                from .animwin import parse
                wk, wargs = parse(arg)
                need = {"chat": 1.8 + len((wargs or [""])[0]) / 24, "checklist": 1.4 + 0.6 * len((wargs or [""])[0].split(";"))}.get(wk, 2.8)
                it = {"id": _id("win"), "type": "window", "window": arg, "start": a + 0.1,
                      "end": a + 0.1 + min(max(b_end - a, need, 2.4), 5.0), "x": 540, "y": 1180,
                      "scale": 0.92, "z": 36, "anim": "none", "hide_captions": True}
                items.append(it)
            elif kind == "reveal":
                cues.append((max(a - 1.2, 0), "riser", 0.5))
                cues.append((a, "hit", 0.8))
            elif kind == "sfx":
                cues.append((a, arg, 0.7))

    if logo:
        logo.pop("_box", None)
        items.append(logo)
    tl["items"] = items
    # faceless reels: a transition between every beat, in the pack's style
    if not base_on_video and plan.get("auto_transitions", True):
        ttype = pack.get("transition", "shape-wipe")
        for (a, _, _, _, _) in windows[1:]:
            if not any(abs(tr["t"] - a) < 0.2 for tr in transitions):
                transitions.append({"t": round(a, 3), "type": ttype, "dur": 0.36})
    # auto director: framing on the real face, push-ins on product shots, emphasis bumps,
    # transitions only where the angle changes
    if base_on_video and source and plan.get("auto_camera", True):
        from . import director
        z, tr = director.plan_camera(tl, tl.get("captions", {}).get("words", []),
                                     lambda st: _head_at(source, st), zooms, transitions,
                                     pack.get("transition", "whip"), cam_info)
        zooms += z
        transitions += tr
        cues += [(t["t"] - 0.15, pack["sfx"].get("transition", "whoosh"), 0.5) for t in tr]
    tl["zooms"] = zooms
    tl["transitions"] = sorted(transitions, key=lambda x: x["t"])
    tl["broll"] = broll
    # framed-card layouts: a few longer talking stretches become a card over a designed background,
    # each with a pop-up still of the product taken from the product shots in this same video
    if base_on_video and source and plan.get("framed", "auto") == "auto" and not layouts:
        out_t, segs = 0.0, []
        for a0, b0 in tl["cuts"]:
            segs.append((out_t, out_t + b0 - a0, a0, b0))
            out_t += b0 - a0
        product = [(s0, e0, sa, sb) for s0, e0, sa, sb in segs if e0 - s0 > 1.2 and not _head_at(source, (sa + sb) / 2)]
        busy = [(i["start"], i["end"]) for i in items if i.get("role") in ("takeover", "hook") or i["type"] == "title"]
        budget, used, k = tl.get("duration", out_t) * 0.3, 0.0, 0
        for s0, e0, sa, sb in segs:
            if e0 - s0 < 3.5 or s0 < 4 or used > budget or not _head_at(source, (sa + sb) / 2):
                continue
            if any(x < e0 and s0 < y for x, y in busy):
                continue
            k += 1
            if k % 2:                          # every other long talking stretch: keep variety
                continue
            layouts.append({"start": round(s0, 3), "end": round(e0, 3), "auto": True})
            used += e0 - s0
            near = min(product, key=lambda p: abs(p[0] - s0), default=None)
            if near:
                rot = [5, -4][len(layouts) % 2]
                items.append({"id": _id("pop"), "type": "photo", "grab_from": source,
                              "grab_t": round((near[2] + near[3]) / 2, 2), "size": 330, "label": None,
                              "start": round(s0 + 0.6, 3), "end": round(min(e0 - 0.3, s0 + 3.4), 3), "anim": "pop",
                              "z": 34, "rotate": rot, "x": 850 if rot > 0 else 230, "y": 330 if rot > 0 else 1150})
                cues.append((s0 + 0.6, "whoosh", 0.25))
    tl["layouts"] = layouts
    # intro: a gentle zoom-out + soft whoosh so the reel never starts abruptly (the fade is in render)
    if plan.get("intro", True) and not any(z["start"] < 0.8 for z in zooms):
        zooms.append({"start": 0.0, "end": 0.8, "type": "pull", "scale": 1.1, "auto": True, "intro": True})
        cues.append((0.0, "swish", 0.35))
    # outro: brand end screen (logo, name, handle, call to action)
    cta_text = next((d.split(":", 1)[1] for b in plan.get("beats", []) for d in b.get("do", []) if d.startswith("cta:")), None)
    tl["end_card"] = dict({"title": pack.get("label", ""), "handle": pack.get("handle", ""),
                           "cta": cta_text or "Follow for more", "enabled": True}, **(plan.get("end_card") or {}))
    if plan.get("speed"):
        tl["speed"] = float(plan["speed"])
    # sound design: one coherent kit per reel, a sound for every move, variety every time
    from . import sounddesign
    kit = plan.get("sound_kit") or sounddesign.KIT_FOR_LOOK.get(look, sounddesign.DEFAULT_KIT)
    sounddesign.vary_entrances(tl["items"])
    cues = sounddesign.design(tl, cues, kit)
    tl["sound_kit"] = kit
    tl["audio"] = {"sfx": [{"t": round(t, 3), "name": n, "gain": g} for t, n, g in sorted(cues)],
                   "music": plan.get("music"), "sfx_gain": 0.6,
                   "denoise": plan.get("denoise", "auto")}      # auto (AI cleaner) · light · elevenlabs
    # quality check + auto-fix (static stretches, hook, clutter, faces, captions)
    from . import qa
    faces_fn = (lambda t: _faces_at(source, _source_time(tl["cuts"], t))) if (base_on_video and source) else None
    qa.fix_timeline(tl, faces_fn, pack)
    # kinetic captions: every line gets its own layout and its own spot, clear of faces and graphics
    if tl.get("captions", {}).get("style") == "kinetic" and tl["captions"].get("words"):
        from .render import caption_groups, item_image
        from .captions import KIN_LAYOUTS
        zones = [(540, 1180, "center"), (90, 470, "left"), (990, 820, "right"), (540, 330, "center"),
                 (90, 1000, "left"), (990, 1180, "right"), (540, 700, "center")]
        boxes = []                                   # graphics on screen: (start, end, box)
        for it in tl["items"]:
            if it.get("role") == "logo" or "x" not in it:
                continue
            try:
                im = item_image(it, pack)
            except Exception:
                im = None
            k = it.get("scale", 1.0)
            if im is None:                           # e.g. a pop-up photo whose frame isn't grabbed yet
                sz = it.get("size", 300) * 1.15
                boxes.append((it["start"], it["end"], _box(it["x"], it["y"], sz * k, sz * k)))
                continue
            boxes.append((it["start"], it["end"], _box(it["x"], it["y"], im.width * k, im.height * k)))
        plan_l, zi, last = [], 0, None
        for gi, g in enumerate(caption_groups(tl["captions"])):
            t0, t1 = g[0]["start"], g[-1]["end"]
            avoid = [b for s0, e0, b in boxes if s0 < t1 and t0 < e0]
            if base_on_video and source:
                avoid += _faces_at(source, _source_time(tl["cuts"], (t0 + t1) / 2))
            # the key word is set huge (~70 px per letter), so size the box from the longest word
            w = min(1000, max(560, 72 * max(len(x.get("w", x.get("word", "")).strip(".,!?")) for x in g)))
            pick = None
            for tries in range(len(zones)):
                x, y, al = zones[(zi + tries) % len(zones)]
                if (x, y) == last:
                    continue
                box = (x - (0 if al == "left" else w if al == "right" else w / 2), y - 170,
                       x + (w if al == "left" else 0 if al == "right" else w / 2), y + 170)
                if not any(layout.overlaps(box, f, pad=30) for f in avoid):
                    pick, zi = (x, y, al), (zi + tries + 1) % len(zones)
                    break
            if pick is None:                         # everything busy: the zone that covers graphics least
                def _cover(z):
                    x, y, al = z
                    b = (x - (0 if al == "left" else w if al == "right" else w / 2), y - 170,
                         x + (w if al == "left" else 0 if al == "right" else w / 2), y + 170)
                    return sum(max(0, min(b[2], f[2]) - max(b[0], f[0])) * max(0, min(b[3], f[3]) - max(b[1], f[1]))
                               for f in avoid) + (1 if (x, y) == last else 0)
                pick = min(zones, key=_cover)
            last = pick[:2]
            plan_l.append({"layout": KIN_LAYOUTS[gi % len(KIN_LAYOUTS)], "x": pick[0], "y": pick[1], "align": pick[2]})
        tl["captions"]["layout_plan"] = plan_l
    if base_on_video and source:                  # measured picture correction (colour cast, exposure)
        from . import picture
        try:
            tl["picture"] = picture.plan(picture.analyse(os.path.join(ROOT_DIR, source), tl["cuts"]))
        except Exception:
            pass
    if base_on_video and source:                  # always check the background noise
        from . import audiocheck
        try:
            tl["audio"]["noise"] = audiocheck.analyse(os.path.join(ROOT_DIR, source), tl["cuts"])
        except Exception:
            pass
    return tl


def summary(tl):
    """Plain-language style plan table for the user to approve."""
    rows = ["| When | What happens |", "|---|---|"]
    for it in sorted(tl["items"], key=lambda i: i["start"]):
        if it.get("role") == "logo":
            continue
        what = {"title": f"Title ({it.get('spec', {}).get('template')}): “{it.get('spec', {}).get('title', '')}”"
                          + (" — behind you" if it.get('spec', {}).get('behind') else ""),
                "text": f"{it.get('role', 'text').title()}: “{it.get('text', '')}”",
                "bubble": f"Thought bubble: “{it['text']}”" if it["type"] == "bubble" else "",
                "sticker": f"Sticker: {it.get('name', '').replace('emoji:', 'emoji ')}",
                "badge": f"Badge: {it.get('text', '')}", "card": f"Designed card: “{it.get('text', '')}”",
                "overlay": "Image overlay", "callout": f"Callout: {it.get('text', '')}"}.get(it["type"], it["type"])
        rows.append(f"| {it['start']:.1f}s | {what} |")
    names = {"punch": "Punch-in", "push": "Slow push-in", "pull": "Pull-out", "whip": "Whip zoom", "shake": "Camera shake",
             "pulse": "Emphasis bump", "focus": "Focus zoom", "drift": "Drift"}
    for z in tl.get("zooms", []):
        who = " (auto, on your face)" if z.get("auto") and z.get("cx") else " (auto)" if z.get("auto") else ""
        rows.append(f"| {z['start']:.1f}s | {names.get(z.get('type'), 'Zoom')} ×{z.get('scale', 1.15):.2f}{who} |")
    for t in tl.get("transitions", []):
        rows.append(f"| {t['t']:.1f}s | Transition: {t['type']} |")
    for b in tl.get("broll", []):
        rows.append(f"| {b['start']:.1f}s | B-roll: {os.path.basename(b['file'])} |")
    rows.append(f"\nLook: {tl['pack']} · grade {tl.get('grade', 'pack default')} · captions "
                f"{tl.get('captions', {}).get('style', 'off')} · {len(tl['audio']['sfx'])} sound effects · "
                f"{tl['duration']:.0f}s" + (" · stabilised (shaky footage)" if tl.get("stabilized") else ""))
    if tl.get("audio", {}).get("noise"):
        from .audiocheck import describe
        rows.append("Sound: " + describe(tl["audio"]["noise"]))
    if tl.get("qa", {}).get("plan_notes"):
        rows.append("Quality check: " + " · ".join(tl["qa"]["plan_notes"]))
    if tl.get("picture", {}).get("notes"):
        rows.append("Picture: " + " · ".join(tl["picture"]["notes"]) + " · premium finish (sharpen, fine grain, soft vignette)")
    return "\n".join(rows)
