"""Export a reel as a CapCut project: everything stays editable in CapCut.

    python -m engine capcut <project> [--no-captions]

What lands in CapCut (one track each, bottom to top):
  Video     the footage with cuts, colour, camera moves and framed layouts (no text on it)
  Graphics  every title, sticker, badge, callout and pop-up card as its own image clip
  Text      takeovers, notes and labels as REAL CapCut text (retype, restyle, animate)
  Captions  the captions as real CapCut text (or skip them and use CapCut's auto-captions)
  Voice     the cleaned voice
  Music     the music bed
  Sounds    every sound effect as its own clip (move, swap or delete any of them)
  + the brand end screen at the end of the video track

Where it goes: on Windows/Mac with CapCut installed, straight into CapCut's projects folder so it
shows up on the CapCut home screen; otherwise projects/<p>/renders/capcut/<name>/ (copy that
folder into CapCut's projects folder).
Built on pycapcut (Apache-2.0), which writes CapCut desktop drafts (tested format: CapCut 6.x).
"""
import json, os, platform, re, tempfile

from . import packs, sfx
from .render import build_base, build_graphics, build_audio, item_image, caption_groups, _abs

W, H = 1080, 1920


def capcut_projects_folder():
    """CapCut's own drafts folder on this computer (None if CapCut isn't installed)."""
    home = os.path.expanduser("~")
    cands = []
    if platform.system() == "Windows":
        la = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        cands.append(os.path.join(la, "CapCut", "User Data", "Projects", "com.lveditor.draft"))
    elif platform.system() == "Darwin":
        cands.append(os.path.join(home, "Movies", "CapCut", "User Data", "Projects", "com.lveditor.draft"))
    return next((c for c in cands if os.path.isdir(c)), None)


def _rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def place(cx, cy, w, h):
    """CapCut clip position for an image of w×h px centred at (cx, cy) on the 1080×1920 canvas.
    CapCut fits every picture to the canvas at scale 1; moves are in half-canvas units, y up."""
    fit = min(W / w, H / h)
    return dict(scale=1.0 / fit, tx=(cx - W / 2) / (W / 2), ty=-(cy - H / 2) / (H / 2))


def plan(tl, pack, captions=True):
    """What goes where (pure data, so it can be tested without CapCut)."""
    out = {"graphics": [], "texts": [], "captions": [], "sounds": []}
    for it in tl.get("items", []):
        if it.get("role") == "logo" or "x" not in it:
            continue
        if it["type"] == "text":
            out["texts"].append({"text": it["text"], "start": it["start"], "end": it["end"],
                                 "x": it["x"], "y": it["y"], "role": it.get("role"),
                                 "size": 15 if it.get("role") in ("takeover", "hook") else 9,
                                 "colour": pack["colors"].get("pop" if it.get("role") == "takeover" else "ink", "#FFFFFF")})
        else:
            out["graphics"].append(it)
    cap = tl.get("captions") or {}
    if captions and cap.get("style", "off") != "off" and cap.get("words"):
        groups = caption_groups(cap)
        for gi, g in enumerate(groups):
            text = " ".join(w["w"] for w in g).strip()
            nxt = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else 1e9
            if text:                                # one caption track: never overlap the next line
                out["captions"].append({"text": text, "start": g[0]["start"],
                                        "end": max(g[0]["start"] + 0.1, min(g[-1]["end"] + 0.25, nxt))})
    # sound effects: cues that chain into each other (typing, a pop + its sparkle) become ONE clip
    cues = sorted(((c["t"], c["name"], c.get("gain", 0.7)) for c in (tl.get("audio") or {}).get("sfx", [])))
    for t, name, gain in cues:
        ev = name.split(":")[2] if name.startswith("sd:") and name.count(":") >= 2 else name
        last = out["sounds"][-1] if out["sounds"] else None
        if last and t - last["cues"][-1][0] < 0.35 and ((ev.startswith("typ")) == (last["label"] == "typing")):
            last["cues"].append((t, name, gain))
        else:
            out["sounds"].append({"t": t, "label": "typing" if ev.startswith("typ") else ev, "cues": [(t, name, gain)]})
    return out


def export(project_dir, tl, name=None, captions=True, dest=None, mode="editable"):
    """mode="editable": every graphic its own clip, text as real CapCut text (retype anything).
    mode="animated": the designed text + graphics arrive as two moving transparent layers (exactly as
    rendered, animations included) — move, resize or switch them off, but not retype."""
    import pycapcut as cc
    from PIL import Image
    pack = packs.load(tl.get("pack"))
    name = re.sub(r"[^A-Za-z0-9 _-]+", "", name or os.path.basename(project_dir.rstrip("/\\"))) or "Reel"
    dur = float(tl["duration"])
    root = dest or capcut_projects_folder() or os.path.join(project_dir, "renders", "capcut")
    os.makedirs(root, exist_ok=True)
    folder = cc.DraftFolder(root)
    script = folder.create_draft(name, W, H, 30, allow_replace=True)
    media = os.path.join(root, name, "reel-studio-media")      # media lives inside the draft folder
    os.makedirs(media, exist_ok=True)
    SEC = cc.SEC

    def tr(a, b):
        a = max(0.0, a)
        return cc.trange(int(a * SEC), max(1, int((min(b, dur) - a) * SEC)))

    # 1) the footage: cuts, colour, camera moves, framed layouts — no graphics on it
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "base.mp4")
    has_voice = build_base(tl, pack, base)
    video = os.path.join(media, "footage.mp4")
    build_graphics(tl, pack, base, video, layer="video")
    vm = cc.VideoMaterial(video)
    dur = min(dur, vm.duration / SEC)             # frame rounding: never ask for more than exists
    script.add_track(cc.TrackType.video, "Video")
    seg = cc.VideoSegment(vm, tr(0, dur), volume=0.0)       # its sound comes from the Voice track
    script.add_segment(seg, "Video")
    if (tl.get("end_card") or {}).get("enabled", True):
        from .endcard import make_card
        card = make_card(pack, tl.get("end_card") or {}, os.path.join(media, "end-screen.mp4"),
                         kit=tl.get("sound_kit", "clean"))
        script.add_segment(cc.VideoSegment(card, cc.trange(int(dur * SEC), int(2.6 * SEC))), "Video")

    if mode == "animated":
        import subprocess
        p = plan(tl, pack, captions)
        g = os.path.join(media, "graphics-animated.mov")
        build_graphics(json.loads(json.dumps(tl)), pack, base, g, layer="graphics")
        layers = [("Graphics (animated)", g)]
        if captions and (tl.get("captions") or {}).get("style", "off") != "off":
            c = os.path.join(media, "captions-animated.mov")
            build_graphics(json.loads(json.dumps(tl)), pack, base, c, layer="captions")
            layers.append(("Captions (animated)", c))
        for n_, (track, f) in enumerate(layers):
            vm2 = cc.VideoMaterial(f)
            script.add_track(cc.TrackType.video, track, relative_index=10 + n_)
            script.add_segment(cc.VideoSegment(vm2, cc.trange(0, min(vm2.duration, int(dur * SEC)))), track)
    else:
        p = plan(tl, pack, captions)
        # 2) graphics: each one its own clip, in the right place, easy to move or delete
        if p["graphics"]:
            script.add_track(cc.TrackType.video, "Graphics", relative_index=1)
            for i, it in enumerate(sorted(p["graphics"], key=lambda x: x["start"])):
                if it["type"] in ("window", "hf"):    # animation window / HyperFrames effect: a real moving clip
                    from .render import _window_frames, _hf_frames
                    frs = _window_frames(it, pack) if it["type"] == "window" else _hf_frames(it)
                    if not frs:
                        continue
                    fdir = tempfile.mkdtemp()
                    for k, (im, _) in enumerate(frs):
                        im.save(os.path.join(fdir, f"{k:04d}.png"))
                    clip = os.path.join(media, f"g{i:02d}-window.mov")
                    import subprocess
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "30", "-i", os.path.join(fdir, "%04d.png"),
                                    "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", clip], check=True)
                    k = it.get("scale", 1.0)
                    w0, h0 = frs[0][0].size
                    pl = place(it["x"], it["y"], w0 * k, h0 * k)
                    vm = cc.VideoMaterial(clip)
                    cs = cc.ClipSettings(scale_x=pl["scale"], scale_y=pl["scale"], transform_x=pl["tx"], transform_y=pl["ty"])
                    seg = cc.VideoSegment(vm, cc.trange(int(it["start"] * SEC), min(vm.duration, int((min(it["end"], dur) - it["start"]) * SEC))),
                                          clip_settings=cs)
                    track = f"Window {i + 1}"
                    script.add_track(cc.TrackType.video, track, relative_index=20 + i)
                    script.add_segment(seg, track)
                    continue
                try:
                    if it["type"] == "title":
                        from . import titles
                        img, off = titles.composite(titles.build(it["spec"], pack))
                        cx, cy = it["x"] + off[0], it["y"] + off[1]
                    else:
                        img = item_image(it, pack)
                        cx, cy = it["x"], it["y"]
                except Exception:
                    continue
                if img is None:
                    continue
                k = it.get("scale", 1.0)
                if k != 1.0:
                    img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))))
                png = os.path.join(media, f"g{i:02d}-{it['type']}.png")
                img.save(png)
                pl = place(cx, cy, img.width, img.height)
                cs = cc.ClipSettings(scale_x=pl["scale"], scale_y=pl["scale"], transform_x=pl["tx"],
                                     transform_y=pl["ty"], rotation=float(it.get("rotate", 0)))
                track = "Graphics"
                try:
                    script.add_segment(cc.VideoSegment(png, tr(it["start"], it["end"]), clip_settings=cs), track)
                except Exception:                      # overlapping graphics: give it its own track
                    track = f"Graphics {i + 2}"
                    script.add_track(cc.TrackType.video, track, relative_index=i + 2)
                    script.add_segment(cc.VideoSegment(png, tr(it["start"], it["end"]), clip_settings=cs), track)

        # 3) text you can retype in CapCut
        def add_texts(rows, track, style_fn):
            if not rows:
                return
            script.add_track(cc.TrackType.text, track)
            n = 0
            for r in sorted(rows, key=lambda x: x["start"]):
                st, cs = style_fn(r)
                t = cc.TextSegment(r["text"], tr(r["start"], r["end"]), style=st, clip_settings=cs,
                                   border=cc.TextBorder(color=(0, 0, 0), alpha=0.35, width=25))
                try:
                    script.add_segment(t, track)
                except Exception:
                    n += 1
                    script.add_track(cc.TrackType.text, f"{track} {n + 1}")
                    script.add_segment(t, f"{track} {n + 1}")

        add_texts(p["texts"], "Text", lambda r: (
            cc.TextStyle(size=r["size"], bold=True, color=_rgb(r["colour"]), align=1, auto_wrapping=True,
                         max_line_width=0.8),
            cc.ClipSettings(transform_x=(r["x"] - W / 2) / (W / 2), transform_y=-(r["y"] - H / 2) / (H / 2))))
        capd = tl.get("captions") or {}
        if captions and str(capd.get("style", "")).startswith("hf:") and capd.get("words"):
            # animated HyperFrames captions: one transparent clip on its own track (move / switch off in CapCut)
            from .render import hf_captions
            import subprocess
            hc = hf_captions(tl)
            if hc:
                from PIL import Image
                fdir = tempfile.mkdtemp()
                for k, fp in enumerate(hc["frames"]):
                    im = Image.open(fp).convert("RGBA")
                    if not hc.get("cropped"):
                        im = im.crop(tuple(hc["box"]))
                    if hc["k"] != 1:
                        im = im.resize((max(1, int(im.width * hc["k"])), max(1, int(im.height * hc["k"]))))
                    im.save(os.path.join(fdir, f"{k:05d}.png"))
                clip = os.path.join(media, "captions-animated.mov")
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "30", "-i", os.path.join(fdir, "%05d.png"),
                                "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", clip], check=True)
                vm = cc.VideoMaterial(clip)
                pl = place(hc["x"], hc["y"], vm.width, vm.height)
                script.add_track(cc.TrackType.video, "Captions (animated)", relative_index=40)
                script.add_segment(cc.VideoSegment(vm, cc.trange(0, min(vm.duration, int(dur * SEC))),
                                                   clip_settings=cc.ClipSettings(scale_x=pl["scale"], scale_y=pl["scale"],
                                                                                 transform_x=pl["tx"], transform_y=pl["ty"])),
                                   "Captions (animated)")
            p["captions"] = []
        ink = pack["colors"].get("caption", "#FFFFFF")
        add_texts(p["captions"], "Captions", lambda r: (
            cc.TextStyle(size=8, bold=True, color=_rgb(ink), align=1, auto_wrapping=True, max_line_width=0.78),
            cc.ClipSettings(transform_y=-0.42)))

    # 4) sound: voice, music and every sound effect as its own clip
    if has_voice:
        dry = json.loads(json.dumps(tl))
        dry["audio"] = dict(dry.get("audio") or {}, sfx=[], music=None)
        voice = os.path.join(media, "voice.wav")
        build_audio(dry, True, base, voice)
        script.add_track(cc.TrackType.audio, "Voice")
        am = cc.AudioMaterial(voice)
        script.add_segment(cc.AudioSegment(am, tr(0, min(dur, am.duration / SEC))), "Voice")
    music = (tl.get("audio") or {}).get("music")
    if music and os.path.exists(_abs(music["file"])):
        script.add_track(cc.TrackType.audio, "Music")
        mdur = cc.AudioMaterial(_abs(music["file"])).duration / SEC
        t0 = 0.0
        while t0 < dur - 0.05:                     # loop the bed to the reel's length
            seg_len = min(mdur, dur - t0)
            script.add_segment(cc.AudioSegment(_abs(music["file"]), cc.trange(int(t0 * SEC), int(seg_len * SEC)),
                                               volume=min(1.0, music.get("gain", 0.18) * 1.6)), "Music")
            t0 += seg_len
    if p["sounds"]:
        sfx_gain = (tl.get("audio") or {}).get("sfx_gain", 0.6)
        lanes = []                                 # clips may overlap: as few lanes as possible
        for n, snd in enumerate(p["sounds"]):
            t0 = snd["t"]
            rel = [(t - t0, name, gain * sfx_gain) for t, name, gain in snd["cues"]]
            try:
                x = sfx.mix_cues(rel, max(r[0] for r in rel) + 3.0)
            except Exception:
                continue
            import numpy as np
            peak = float(np.abs(x).max()) if len(x) else 0.0
            nz = np.nonzero(np.abs(x) > peak * 0.004)[0]     # trim the silent tail (-48 dB)
            if not peak or not len(nz):
                continue
            x = x[:nz[-1] + 1].copy()
            fade = min(len(x), int(0.03 * sfx.SR))
            x[-fade:] *= np.linspace(1, 0, fade)
            f = os.path.join(media, f"sound-{n + 1:03d}-{snd['label']}.wav")
            sfx.write_wav(f, x, peak=None)
            am = cc.AudioMaterial(f)
            ln = min(am.duration / SEC, dur - t0)
            if ln <= 0.02:
                continue
            lane = next((i for i, end in enumerate(lanes) if end <= t0), None)
            if lane is None:
                lanes.append(0)
                lane = len(lanes) - 1
                script.add_track(cc.TrackType.audio, f"Sounds {lane + 1}")
            lanes[lane] = t0 + ln + 0.001
            script.add_segment(cc.AudioSegment(am, cc.trange(int(t0 * SEC), int(ln * SEC))), f"Sounds {lane + 1}")
    script.save()
    return os.path.join(root, name), root == capcut_projects_folder()
