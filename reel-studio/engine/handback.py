"""Hand-back — the CapCut round trip.

The person opens our CapCut version, fixes something by hand (cuts a bit out, trims a pause, moves a
piece earlier), closes CapCut and says "I'm done in CapCut" / "take it back". We read their edited
CapCut project, work out which parts of the reel they kept and in what order, and carry that into the
reel: the cut, the captions, every graphic, zoom and sound move with it. Then it's rebuilt as normal.

    python -m engine handback <project> [--name "<CapCut project name>"]

Works on the plain project files CapCut writes. If a CapCut version locks its project file, we say so
and offer the simple route: export the video from CapCut into the inbox and continue from that.
"""
import json, os, shutil

from . import project

SEC = 1_000_000


def _drafts_root():
    from .capcut import capcut_projects_folder
    return capcut_projects_folder()


def _find_draft(slug, name=None):
    meta = project.load(slug, "project.json") or {}
    names = [name] if name else list(reversed(meta.get("capcut_drafts", [])))
    roots = [r for r in (_drafts_root(), project.path(slug, "renders", "capcut")) if r and os.path.isdir(r)]
    for n in names:
        for r in roots:
            p = os.path.join(r, n)
            if os.path.isdir(p):
                return p
    return None


def _read(folder):
    for fn in ("draft_content.json", "draft_info.json"):
        p = os.path.join(folder, fn)
        if os.path.exists(p):
            try:
                return json.loads(open(p, "rb").read().decode("utf-8"))
            except Exception:
                return None
    return None


def kept_ranges(draft):
    """[(start, end)] in the OLD reel's seconds, in their new order, from the footage track."""
    vids = {m["id"]: m for m in draft.get("materials", {}).get("videos", [])}
    best = []
    for tr in draft.get("tracks", []):
        if tr.get("type") != "video":
            continue
        segs = [s for s in tr.get("segments", [])
                if os.path.basename(vids.get(s.get("material_id"), {}).get("path", "")) == "footage.mp4"]
        if len(segs) > len(best):
            best = segs
    best.sort(key=lambda s: s["target_timerange"]["start"])
    return [(s["source_timerange"]["start"] / SEC, (s["source_timerange"]["start"] + s["source_timerange"]["duration"]) / SEC)
            for s in best]


def remap(tl, kept, min_len=0.12):
    """A new timeline where only the kept parts of the old one remain, in the given order."""
    kept = [(a, b) for a, b in kept if b - a >= min_len]
    if not kept:
        raise ValueError("Nothing of the footage was left in the CapCut project.")
    out_off, offs = 0.0, []
    for a, b in kept:
        offs.append((a, b, out_off))
        out_off += b - a
    new_dur = round(out_off, 3)

    def f(t):
        for a, b, o in offs:
            if a - 1e-3 <= t <= b + 1e-3:
                return round(o + min(max(t, a), b) - a, 3)
        return None

    def span(s, e):
        """Map an old [s, e] to the new timeline: the first kept part it overlaps."""
        for a, b, o in offs:
            if s < b and e > a:
                return round(o + max(s, a) - a, 3), round(o + min(e, b) - a, 3)
        return None

    # the cut: old reel time -> source time through the old cuts
    src, acc = [], 0.0
    for a, b in tl.get("cuts", []):
        src.append((acc, acc + (b - a), a))
        acc += b - a
    new_cuts = []
    for ka, kb in kept:
        for ra, rb, sa in src:
            lo, hi = max(ka, ra), min(kb, rb)
            if hi - lo > 1e-3:
                new_cuts.append([round(sa + lo - ra, 3), round(sa + hi - ra, 3)])
    out = json.loads(json.dumps(tl))
    if tl.get("cuts"):
        out["cuts"] = new_cuts
    out["duration"] = new_dur
    items = []
    for it in tl.get("items", []):
        sp = span(it["start"], it["end"])
        if sp and sp[1] - sp[0] >= 0.2:
            it = dict(it, start=sp[0], end=sp[1])
            items.append(it)
    out["items"] = items
    cap = out.get("captions") or {}
    if cap.get("words"):
        words = []
        for w in cap["words"]:
            sp = span(w["start"], w["end"])
            if sp:
                words.append(dict(w, start=sp[0], end=max(sp[1], sp[0] + 0.05)))
        cap["words"] = words
    for key in ("zooms", "broll", "layouts"):
        moved = []
        for z in tl.get(key, []):
            s0 = z.get("start", 0)
            e0 = z.get("end", s0 + z.get("dur", 0))
            sp = span(s0, e0)
            if sp:
                z = dict(z, start=sp[0])
                if "end" in z:
                    z["end"] = sp[1]
                if "dur" in z:
                    z["dur"] = round(sp[1] - sp[0], 3)
                moved.append(z)
        out[key] = moved
    out["transitions"] = [dict(t_, t=f(t_["t"])) for t_ in tl.get("transitions", []) if f(t_["t"]) is not None]
    aud = out.get("audio") or {}
    if isinstance(aud.get("cues"), list):
        aud["cues"] = [[f(c[0])] + list(c[1:]) for c in aud["cues"] if f(c[0]) is not None]
    return out


def hand_back(slug, name=None):
    """-> message for the person. Never touches their CapCut project."""
    folder = _find_draft(slug, name)
    if not folder:
        return ("I couldn't find the CapCut project for this reel. Tell me its name as it shows in CapCut, "
                "e.g. \"take back Factory visit 2\".")
    draft = _read(folder)
    if draft is None:
        return ("Your CapCut version keeps its project file locked, so I can't read the changes directly. "
                "Easy way round: in CapCut press Export, save the video into your Reel Studio inbox, and say "
                "\"continue from my CapCut video\".")
    kept = kept_ranges(draft)
    if not kept:
        return "I couldn't find the footage track in that CapCut project (was the footage clip replaced?)."
    tl = project.load(slug, "timeline.json")
    old = tl["duration"]
    new = remap(tl, kept)
    shutil.copy(project.path(slug, "timeline.json"), project.path(slug, "timeline.before-capcut.json"))
    project.save(slug, "timeline.json", new)
    removed = round(old - new["duration"], 1)
    moved = any(kept[i][0] > kept[i + 1][0] for i in range(len(kept) - 1))
    return (f"Took your CapCut changes back from “{os.path.basename(folder)}”: "
            + (f"{removed}s cut out" if removed > 0.05 else "same length")
            + (", pieces moved" if moved else "") + f". The reel is now {new['duration']:.1f}s, with every caption, "
            "graphic and sound moved to match. Render it again to see it (the old version is kept).")
