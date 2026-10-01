"""Reel Studio command line. Claude runs these; users can too.

  python -m engine setup-check                 are ffmpeg / yt-dlp / python libs installed?
  python -m engine new <video|-> [--name N]     start a project (- = script-only/faceless)
  python -m engine roughcut <project>           transcribe + rough cut -> line list
  python -m engine review <project>             open the review page
  python -m engine timeline <project>           plan.json -> timeline.json (+ plain-language plan)
  python -m engine render <project> [--preview] render video (+ cover image)
  python -m engine studio                       open the Reel Studio app (home, questionnaire, titles)
  python -m engine editor [<project>]           open the manual timeline editor
  python -m engine music <project> [--options N] [--eleven]  music from the brief (free built-in; --eleven = paid)
  python -m engine titles                       list title templates
  python -m engine templates                    list reel templates (ideas to copy)
  python -m engine template <id> [--clips DIR] [--name N]  start a text/photo/clip reel from a template
  python -m engine inspire <url|file> [--name]  learn the style of a reel they love
  python -m engine brand-site <url>             colours/fonts/logo from a website
  python -m engine brand-image <file>           colours from a logo/photo/mood board
  python -m engine brand-starters "<vibe words>" three starter looks (+ preview images)
  python -m engine brand-preview [<pack>]       one still in the brand/preset look
  python -m engine batch <folder> --pack P      one faceless/b-roll reel per clip
  python -m engine sounds                       trending sounds you've saved + where to find more
  python -m engine sounds-add "Song — Artist" [--mood a,b] [--tempo T] [--business] [--link URL]
  python -m engine sounds-suggest <project> [--business]  best trending sound for this reel + how to add it
  python -m engine share <project> [--name T] [--options v2]  branded review page with feedback notes
  python -m engine hf-captions                  premium animated caption styles (HyperFrames)
  python -m engine hf-find <words>              search ~400 HyperFrames effects (lower thirds, follow cards, charts…)
  python -m engine hf-add <project> --name <effect>  fetch one into the project to adapt its words
  python -m engine styleplan <project>          the plan in plain words — show it, get a "go", then build
  python -m engine effects                      named effects (built-in + the user's own)
  python -m engine effect-save <name> --options "punch-in;label:{text}" [--name "what it does"]
  python -m engine capcut <project> [--name N] [--no-captions] [--options animated]
                                                CapCut project: editable (default) or animated layers
  python -m engine layers <project>             editable layers (video · graphics · captions · audio) for any editor
  python -m engine chop <file|folder> [--options SECONDS]  long clips -> best short b-roll clips
  python -m engine trial <trial.json>           hook-on-b-roll trial reels + captions map
  python -m engine learn-me <profile|reel url> [--options N]  learn the user's voice from their last N reels
  python -m engine update                       get the latest Reel Studio (keeps your brand + projects)
  python -m engine fonts                        list fonts (yours + library) and the sticker fonts in use
  python -m engine font-add <file.ttf|otf> [--role R]  use your own font (not on Google), e.g. --role sticker
  python -m engine font-use <font|auto> --role R  e.g. font-use "Satisfy" --role sticker (auto = brand match)
  python -m engine brands                       the brands you make content for (one is in use)
  python -m engine brand-new "<name>" | brand-use "<name>" | brand-delete "<name>"
  python -m engine brand-setup <route> "<value>" [--name "<brand>"]  route: design|file|website|image|video|vibe
  python -m engine designs                      the ready-made designs (HyperFrames presets) to pick from
  python -m engine look-from-video <project|video>  3 looks made from the colours in the video
  python -m engine look-use <1|2|3> [--name "<brand>"]  use one of those looks as the brand
  python -m engine library                      the effects library page (see, hear, copy what to say)
  python -m engine sounds-learn [<folder>] [--options capcut --name "<CapCut project>"] [--role EVENT]
                                                learn the user's own sounds (inbox/sound-effects by default)
  python -m engine my-sounds | sounds-forget [<name>|all]
  python -m engine remember "<rule>" [--name "<phrase>"] | rules | forget-rule <number|words>
  python -m engine style-from <design file> [--preview]  brand look from DESIGN.md/CSS/JSON/Canva values
  python -m engine report                       a private problem report (no footage, no keys)
  python -m engine sticker-requests             stickers made on the fly (Claude can draw illustrated versions)
"""
import argparse, json, os, shutil, subprocess, sys
from . import brand, packs, project, roughcut

ROOT = project.ROOT


def setup_check():
    ok = True
    for b in ("ffmpeg", "ffprobe", "yt-dlp"):
        found = shutil.which(b)
        print(("✓" if found else "✗"), b, found or "(missing)")
        ok &= bool(found) or b == "yt-dlp"
    for m in ("PIL", "resvg_py", "numpy", "faster_whisper", "mediapipe", "pycapcut", "playwright"):
        try:
            __import__(m)
            print("✓", m)
        except Exception:
            print("✗", m, "(pip install -r requirements.txt)")
            ok = False
    try:                                   # the hidden browser that draws animation windows
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p_:
            print("✓ browser for animation windows", p_.chromium.executable_path if os.path.exists(p_.chromium.executable_path) else "")
            if not os.path.exists(p_.chromium.executable_path):
                raise FileNotFoundError
    except Exception:
        print("• animation windows need: python -m playwright install chromium")
    print("✓ brand set up" if packs.has_brand() else "• brand not set up yet (run the onboarding)")
    from .update import check
    note = check()
    if note:
        print(note)
    return ok


def _as_list(v):
    if not v:
        return []
    return [x.strip().lower() for x in (v if isinstance(v, list) else str(v).split(",")) if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m engine", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--pack")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-captions", action="store_true", help="capcut: leave captions out (use CapCut auto-captions)")
    ap.add_argument("--language")
    ap.add_argument("--options")
    ap.add_argument("--clips")
    ap.add_argument("--eleven", action="store_true", help="use Eleven Music (paid) instead of the free composer")
    ap.add_argument("--mood", help="comma-separated moods for sounds-add, e.g. cosy,calm")
    ap.add_argument("--tempo", help="slow / medium / fast (sounds-add)")
    ap.add_argument("--link", help="TikTok sound link (sounds-add)")
    ap.add_argument("--role", help="font role: headline, accent, caption, script, serif, sans, sticker, sticker_label")
    ap.add_argument("--business", action="store_true", help="sound is approved for business accounts")
    a = ap.parse_args(argv)
    c = a.cmd

    if c == "setup-check":
        sys.exit(0 if setup_check() else 1)
    if c == "new":
        slug = project.new(None if a.arg in (None, "-") else a.arg, a.name)
        print(slug)
    elif c == "roughcut":
        rc = project.do_roughcut(a.arg, a.language)
        print(roughcut.summary(rc))
    elif c == "review":
        from .editor.server import serve
        print(f"Open http://localhost:{a.port}/review?p={a.arg}")
        if not a.no_browser:
            import webbrowser, threading
            threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{a.port}/review?p={a.arg}")).start()
        serve(a.port, open_browser=False)
    elif c == "timeline":
        from .plan import summary
        tl = project.build_timeline(a.arg)
        print(summary(tl))
    elif c == "render":
        out = project.do_render(a.arg, preview=a.preview)
        print(out)
        rep = project.load(a.arg, "renders/qa.json")
        if rep and not a.preview:
            print("\nWhat I did:\n" + "\n".join("  • " + x for x in rep["did"]))
            print("Checks: " + " · ".join(rep["checks"]))
            if rep["problems"]:
                print("PROBLEMS (fix before showing the user): " + " · ".join(rep["problems"]))
    elif c == "studio":
        from .editor.server import serve
        serve(a.port, open_browser=not a.no_browser)
    elif c == "music":
        from . import music
        brief = project.load(a.arg, "brief.json") or {}
        tl = project.load(a.arg, "timeline.json") or {}
        mb = {k: brief.get(k) for k in ("mood", "genre", "tempo", "instruments", "energy", "describe", "vocals") if brief.get(k)}
        files, prompt = music.generate(project.path(a.arg), mb, tl.get("duration", brief.get("goal", 30)),
                                       int(a.options or 2), provider="elevenlabs" if a.eleven else "free")
        print("prompt:", prompt)
        for f in files:
            print(os.path.relpath(f, ROOT))
    elif c == "sounds":
        from . import trends
        print(trends.summary())
    elif c == "sounds-add":
        from . import trends
        i = trends.add(a.arg, [m.strip() for m in (a.mood or "").split(",") if m.strip()], a.tempo,
                       a.business, a.link)
        print("saved:", i["title"], "—", i["artist"] or "?")
    elif c == "sounds-suggest":
        from . import trends
        brief = project.load(a.arg, "brief.json") or {}
        b = {"mood": _as_list(brief.get("mood")), "vibe": _as_list(brief.get("vibe")), "tempo": brief.get("tempo")}
        picks = trends.suggest(b, business=a.business)
        if not picks:
            print("No saved trending sounds match yet. Add some: python -m engine sounds-add \"Song — Artist\" --mood cosy")
        for i in picks:
            print(f"• {i['title']}{' — ' + i['artist'] if i['artist'] else ''}"
                  f"{' ✅ business-safe' if i.get('business_ok') else ''}")
        print("\nPost the 'final-for-trending-sound.mp4' version, then in TikTok:")
        for n, step in enumerate(trends.HOW_TO["tiktok"], 1):
            print(f"  {n}. {step}")
    elif c == "fonts":
        p = packs.load()
        print("Your fonts (brand/fonts) and the bundled library:")
        for f in packs.all_fonts():
            print(("  ★ " if "/brand/" in f.replace(os.sep, "/") else "    ") + os.path.basename(f))
        from .stickers import sticker_font
        print("Sticker lettering:", os.path.basename(sticker_font(p, "lettering")["file"]),
              "(chosen)" if p.get("sticker", {}).get("font") else "(automatic: your brand's script font)")
        print("Badge/stamp text: ", os.path.basename(sticker_font(p, "label")["file"]),
              "(chosen)" if p.get("sticker", {}).get("label_font") else "(automatic: your brand's headline font)")
    elif c == "font-add":
        out = brand.add_font(a.arg, a.role)
        print("added", os.path.relpath(out, ROOT) + (f" as your {a.role} font" if a.role else ""))
    elif c == "font-use":
        brand.set_font_role(a.role or "sticker", a.arg)
        print(f"{a.role or 'sticker'} font -> {a.arg}")
    elif c == "sticker-requests":
        from .stickers import REQUESTS
        req = json.load(open(REQUESTS)) if os.path.exists(REQUESTS) else {}
        if not req:
            print("No sticker requests: every sticker used so far is in the library.")
        for w, n in sorted(req.items(), key=lambda x: -x[1]):
            print(f"{n:3}× {w}   (made as a lettered sticker; ask Claude to draw an illustrated one)")
    elif c == "templates":
        from .templates import all_templates
        for k, t in all_templates().items():
            print(f"{k:24} {t['category']:14} {t['format']:13} {t['name']} — {t['why']}")
    elif c == "template":
        from . import templates as tpl
        from .plan import summary, to_timeline
        clips = tpl.list_clips(a.clips) if a.clips else []
        t = tpl.get(a.arg)
        slug = project.new(None, a.name or t["name"])
        plan = tpl.to_plan(a.arg, {"topic": a.name or ""}, clips)
        project.save(slug, "plan.json", plan)
        if plan["format"] != "talking-head":
            tl = project.build_timeline(slug)
            print(summary(tl))
        print("project:", slug)
    elif c == "titles":
        from .titles import TEMPLATES
        for k, (_, d) in TEMPLATES.items():
            print(f"{k:10} {d}")
    elif c == "editor":
        from .editor.server import serve
        serve(a.port, open_browser=not a.no_browser, slug=a.arg)
    elif c == "inspire":
        from .inspire import analyse
        p = analyse(a.arg, a.name)
        print(json.dumps(p, indent=2))
    elif c == "brand-site":
        print(json.dumps(brand.from_website(a.arg), indent=2))
    elif c == "brand-image":
        pal = brand.from_image(a.arg)
        print(json.dumps({"palette": pal, "suggested_roles": brand.assign_roles(pal)}, indent=2))
    elif c == "brand-starters":
        os.makedirs(os.path.join(ROOT, "brand", "previews"), exist_ok=True)
        for i, d in enumerate(brand.starter_directions(a.arg or "")):
            out = os.path.join(ROOT, "brand", "previews", f"starter-{i + 1}.jpg")
            brand.preview(brand.direction_pack(d), out)
            print(f"{i + 1}. {d['name']}: colours {', '.join(d['colors'])} · fonts {d['fonts'][0]} + "
                  f"{d['fonts'][1]} · stickers {d['sticker']} -> {os.path.relpath(out, ROOT)}")
    elif c == "brand-preview":
        out = os.path.join(ROOT, "brand", "previews", f"{a.arg or 'brand'}.jpg")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pack = packs.load(a.arg)
        brand.preview(pack, out)
        for w in packs.check(pack):
            print("⚠", w)
        print(os.path.relpath(out, ROOT))
    elif c == "share":
        from .share import build
        rep = project.load(a.arg, "renders/qa.json") or {}
        brief = project.load(a.arg, "brief.json") or {}
        out = build(project.path(a.arg), a.name or brief.get("topic"), a.options or "v1", rep.get("did"))
        print("review page:", os.path.relpath(out, ROOT), "-> publish index.html with its media as a page (db capability)")
    elif c == "layers":
        from .render import export_layers
        out = export_layers(project.path(a.arg, "timeline.json"), project.path(a.arg, "renders", "layers"))
        print("layers:", os.path.relpath(out, ROOT))
    elif c == "hf-captions":
        from .hyperframes import caption_styles
        print("HyperFrames caption styles (HeyGen, Apache-2.0) — use as \"captions\": \"hf:<name>\":")
        for k, v in caption_styles().items():
            print(f"  hf:{k:22s} {v}")
    elif c == "hf-find":
        from .hyperframes import catalog
        items = catalog(" ".join(x for x in [a.arg, a.options] if x))
        for i in items[:60]:
            d = i.get("dimensions") or {}
            print(f"  {i['name']:30s} {i['title'] or ''} — {i['description'][:90]}"
                  + (f"  [{d.get('width')}x{d.get('height')}, {i.get('duration')}s]" if d else ""))
        print(f"{len(items)} effect(s). Use in a beat: \"hf:<name>\" (Claude adapts its words: hf-add first).")
    elif c == "hf-add":
        from .hyperframes import fetch
        path = fetch(a.options or a.name, project.path(a.arg))
        print("Added:", os.path.relpath(path, ROOT), "— edit its demo words to the reel's, then use \"hf:" + (a.options or a.name) + "\" in a beat.")
    elif c == "styleplan":
        from .styleplan import summary
        print(summary(project.load(a.arg, "plan.json") or {}, project.load(a.arg, "roughcut.json") or {}))
    elif c == "effects":
        from .styleplan import effects
        for k, v in effects().items():
            print(f"  {k:24s} {v.get('about', '')}  [{' + '.join(v['do'])}]")
    elif c == "effect-save":
        from .styleplan import save_effect
        e = save_effect(a.arg, [x.strip() for x in (a.options or "").split(";") if x.strip()], a.name or "")
        print("saved:", a.arg, "=", " + ".join(e["do"]))
    elif c == "capcut":
        from .capcut import export
        tl = project.load(a.arg, "timeline.json")
        folder, inside = export(project.path(a.arg), tl, a.name, captions=not a.no_captions,
                                mode="animated" if (a.options or "").startswith("anim") else "editable")
        print(("Open CapCut: the project is on your home screen as" if inside else
               "CapCut project folder (copy it into CapCut's projects folder):"), folder)
    elif c == "chop":
        from .chop import chop
        made = chop([a.arg], float(a.options or 6))
        for i, m in enumerate(made, 1):
            print(f"{i:2d}. {m['file']}  (from {m['from']} at {m['at']}s, quality {m['score']})")
        print(f"{len(made)} clips · contact sheet: inbox/broll-cuts/contact-sheet.jpg")
    elif c == "trial":
        from .chop import trial
        print("trial reels + captions map:", os.path.relpath(trial(a.arg), ROOT))
    elif c == "learn-me":
        from .voicehub import learn
        res = learn([a.arg] + ([a.name] if a.name else []), int(a.options or 15))
        ok = [r for r in res if "transcript" in r]
        print(f"learned from {len(ok)} reels -> brand/voice/reels.json. Claude now writes brand/voice.md.")
        for r in res:
            if "error" in r:
                print("  skipped:", r["url"], r["error"][-80:])
    elif c == "update":
        from .update import update
        print(update())
    elif c == "brands":
        from . import brands
        rows = brands.listing()
        if not rows:
            print("No brands yet. Set one up, or I'll make a look from your first video.")
        for sl, label, on in rows:
            print(("▶ " if on else "  ") + label + ("  (in use)" if on else ""))
    elif c == "brand-new":
        from . import brands
        s_ = brands.new(a.arg or a.name)
        print(f"New brand '{a.arg or a.name}' started (your other brands are kept). Next: set it up, "
              "or make a look from a video with look-from-video.")
    elif c == "brand-use":
        from . import brands
        print("Now using:", brands.use(a.arg or a.name))
    elif c == "brand-delete":
        from . import brands
        print("Deleted:", brands.delete(a.arg or a.name))
    elif c == "designs":
        from .brandsetup import designs
        for d in designs():
            c_ = d["colors"]
            print(f"  {d['name']:18s} {d['title']:20s} {d['about']}  [{c_.get('accent')} on {c_.get('background')}]")
    elif c == "brand-setup":
        from . import brandsetup
        route, value = a.arg, a.options
        sheet, looks = brandsetup.run(route, value, a.name or "My brand")
        for i, lk in enumerate(looks, 1):
            print(f"  {i}. {lk['feel']}: accent {lk['pack']['colors']['pop']}" + "".join("  • " + n for n in lk.get("notes", [])))
        print("Looks:", sheet, "\nSave one with: python -m engine look-use <number>")
    elif c == "look-from-video":
        from . import autolook
        src = a.arg if os.path.isfile(a.arg or "") else project.source_of(a.arg)
        sheet, looks = autolook.make_looks(src, a.name or "My brand")
        for i, lk in enumerate(looks, 1):
            c_ = lk["pack"]["colors"]
            print(f"  {i}. {lk['feel']}: accent {c_['pop']} · full-screen {c_['bg']}")
        print("Looks (drawn on your own video):", sheet)
    elif c == "look-use":
        from . import autolook
        pack = autolook.use(a.arg or 1, a.name)
        print(f"Saved '{pack['label']}' as your brand look.")
    elif c == "library":
        from .library_page import build
        print("Effects library:", build(open_it=not a.no_browser))
    elif c == "sounds-learn":
        from . import mysounds
        if (a.options or "").lower() == "capcut":
            r = mysounds.learn_capcut(a.name or a.arg or "my favorites")
            if not r["ok"]:
                print("Couldn't read it:", r["why"])
                if r.get("projects"):
                    print("CapCut projects on this computer:", ", ".join(r["projects"]))
            else:
                print(f"From CapCut project '{r['project']}':")
                for n, ev in r["learned"]:
                    print(f"  ✓ {n} → {', '.join(ev)}")
                if r["not_downloaded"]:
                    print("  not on this computer yet (play each once in CapCut, close CapCut, run again):",
                          ", ".join(r["not_downloaded"]))
                for p_ in r["pairs"]:
                    print(f"  ✓ text '{p_['animation']}' gets '{p_['sound']}'")
        elif a.arg and os.path.isfile(a.arg):
            print("learned:", ", ".join(mysounds.learn(a.arg, as_event=a.role)))
        else:
            folder = a.arg or os.path.join(ROOT, "inbox", "sound-effects")
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
                print("Put sound files in", folder, "(sub-folders like 'typing', 'pop', 'whoosh' name their use), then run again.")
            for n, ev in mysounds.learn_folder(folder):
                print(f"  ✓ {n} → {', '.join(ev)}")
        print(mysounds.summary())
    elif c == "my-sounds":
        from . import mysounds
        print(mysounds.summary())
    elif c == "sounds-forget":
        from . import mysounds
        print(mysounds.forget(None if (a.arg or "all") == "all" else a.arg))
    elif c == "remember":
        from . import rules
        n = rules.remember(a.arg or "", name=a.name)
        print(f"Saved as rule {n}. I'll apply it to every reel from now on.")
        print(rules.listing())
    elif c == "rules":
        from . import rules
        print(rules.listing())
    elif c == "forget-rule":
        from . import rules
        gone = rules.forget(a.arg)
        print(("Forgot: " + gone["rule"]) if gone else "No rule like that.")
    elif c == "style-from":
        from . import stylesheet
        spec = stylesheet.read(a.arg)
        pack, notes = stylesheet.make_pack(spec, a.name or "My style", save=not a.preview)
        out = stylesheet.overview(pack, os.path.join(ROOT, "brand", "previews", "style-overview.jpg"))
        print("Colours:", spec["colors"], "\nFonts:", spec["fonts"])
        for n_ in notes:
            print("•", n_)
        print(("Preview only (not saved): " if a.preview else "Saved as your brand. Overview: ") + out)
    elif c == "report":
        from .report import write
        print("Report:", write())
    elif c == "batch":
        from .plan import to_timeline
        from .render import render
        folder = a.arg
        clips = sorted(f for f in os.listdir(folder) if f.lower().endswith((".mp4", ".mov", ".m4v")))
        for i, f in enumerate(clips, 1):
            slug = project.new(os.path.join(folder, f), f"batch-{i:02d}-{os.path.splitext(f)[0]}")
            print(f"{i:02d} {slug}")
        print("Projects created. Claude writes a plan.json for each, then runs timeline + render.")
    else:
        ap.print_help()


if __name__ == "__main__":
    import sys as _sys
    if os.name == "nt" and not _sys.flags.utf8_mode:
        # Windows: run in UTF-8 mode so emoji, accents and curly quotes never crash a read or a print
        import subprocess as _sp
        raise SystemExit(_sp.call([_sys.executable, "-X", "utf8", "-m", "engine"] + _sys.argv[1:]))
    main()
