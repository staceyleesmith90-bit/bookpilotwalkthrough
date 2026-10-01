"""One folder per reel: projects/<slug>/

  source/<clip>      copy of the original (the original is never touched)
  transcript.json    word timings (local whisper)
  roughcut.json      lines, kept/removed, notes
  review.json        what the user changed in the review page
  plan.json          Claude's short style plan
  timeline.json      exact layout + timing (manual editor edits this)
  proxy.mp4          half-size base video for the editor
  renders/           previews and finals, thumbnail
"""
import json, os, re, shutil, time
from . import plan as planner, render, roughcut, transcribe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "projects")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "reel"


def path(slug, *parts):
    return os.path.join(PROJECTS, slug, *parts)


def load(slug, name):
    p = path(slug, name)
    return json.load(open(p)) if os.path.exists(p) else None


def save(slug, name, data):
    os.makedirs(path(slug), exist_ok=True)
    json.dump(data, open(path(slug, name), "w"), indent=1)
    return path(slug, name)


def new(source=None, name=None):
    """Create a project. source=None for a faceless/script-only reel."""
    base = name or (os.path.splitext(os.path.basename(source))[0] if source else "script-reel")
    slug = slugify(base)
    if os.path.exists(path(slug)):
        slug = f"{slug}-{time.strftime('%m%d%H%M')}"
    os.makedirs(path(slug, "source"), exist_ok=True)
    os.makedirs(path(slug, "renders"), exist_ok=True)
    from .brands import active
    meta = {"slug": slug, "created": time.strftime("%Y-%m-%d %H:%M"), "source": None, "brand": active()}
    if source:
        dst = path(slug, "source", os.path.basename(source))
        shutil.copy2(source, dst)
        meta["source"] = os.path.relpath(dst, ROOT)
    save(slug, "project.json", meta)
    return slug


def source_of(slug):
    s = load(slug, "project.json")["source"]
    return os.path.join(ROOT, s) if s else None


def do_roughcut(slug, language=None):
    src = source_of(slug)
    t = transcribe.transcribe(src, cache=path(slug, "transcript.json"), language=language)
    rc = roughcut.rough_cut(t)
    save(slug, "roughcut.json", rc)
    return rc


def apply_review(slug):
    rc, rv = load(slug, "roughcut.json"), load(slug, "review.json")
    if rc and rv:
        rc = roughcut.apply_review(rc, rv)
        save(slug, "roughcut.json", rc)
    return rc


def rough_preview(slug):
    """Quick video of the rough cut only (no graphics) for the review page."""
    rc = load(slug, "roughcut.json")
    tl = {"size": [1080, 1920], "fps": 30, "source": os.path.relpath(source_of(slug), ROOT),
          "cuts": [list(r) for r in roughcut.kept_ranges(rc)], "grade": "none", "pack": "bold"}
    tl["duration"] = round(sum(b - a for a, b in tl["cuts"]), 3)
    out = path(slug, "renders", "rough.mp4")
    render.build_base(tl, render.packs.load("bold"), out, 0.5, crf=28)
    return out


def build_timeline(slug):
    p = load(slug, "plan.json")
    rc = load(slug, "roughcut.json")
    src = source_of(slug)
    from .brands import active
    made_for = (load(slug, "project.json") or {}).get("brand")
    if made_for and made_for != active() and p.get("pack") in (None, "brand"):
        p = dict(p, pack="brand:" + made_for)              # a project always keeps the brand it was made for
    tl = planner.to_timeline(p, rc if src else None, os.path.relpath(src, ROOT) if src else None)
    save(slug, "timeline.json", tl)
    return tl


def do_render(slug, preview=False):
    name = "preview.mp4" if preview else "final.mp4"
    out = path(slug, "renders", name)
    extra = None if preview else path(slug, "renders", "final-for-trending-sound.mp4")
    render.render(path(slug, "timeline.json"), out, preview=preview, no_music_out=extra)
    if not preview:
        render.thumbnail(path(slug, "timeline.json"), path(slug, "renders", "cover.jpg"))
        from . import qa
        notes, problems = qa.check_render(out)
        tl = load(slug, "timeline.json") or {}
        save(slug, "renders/qa.json", {"did": qa.summary(tl), "checks": notes, "problems": problems})
    return out


def proxy(slug):
    out = path(slug, "proxy.mp4")
    render.base_proxy(path(slug, "timeline.json"), out)
    return out


def list_projects():
    if not os.path.isdir(PROJECTS):
        return []
    return sorted(d for d in os.listdir(PROJECTS) if os.path.exists(path(d, "project.json")))
