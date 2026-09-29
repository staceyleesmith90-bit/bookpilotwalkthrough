"""Render a timeline.json to MP4.

Pass 1 (ffmpeg): base video — cut A-roll (or plain background), punch-ins, b-roll, colour grade.
Pass 2 (Python): graphics — text, bubbles, stickers, badges, logos/overlays, captions.
Pass 3 (ffmpeg): audio — voice + sound effects + music (ducked under the voice).

All of this runs locally. Claude never has to look at frames to render.
"""
import re, json, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageChops, ImageFilter
from . import captions, fx, grades, layout, packs, sfx, stickers, textfit, titles

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])


# ---------------------------------------------------------------- pass 1: base video
def build_base(tl, pack, out, scale=1.0, crf=18):
    W, H = [int(v * scale) // 2 * 2 for v in tl["size"]]
    dur = tl["duration"]
    fps = tl.get("fps", 30)
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={fps}"
    inputs, fc, v = [], [], None
    has_voice = False
    if tl.get("source"):
        src = _abs(tl["source"])
        inputs += ["-i", src]
        from .transcribe import has_audio
        has_voice = has_audio(src)
        parts = []
        for k, (a, b) in enumerate(tl["cuts"]):
            fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,{cover}[v{k}]")
            if has_voice:
                fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,"
                          f"afade=t=out:st={max(b - a - 0.015, 0)}:d=0.015[a{k}]")
            parts.append(f"[v{k}]" + (f"[a{k}]" if has_voice else ""))
        n = len(tl["cuts"])
        fc.append("".join(parts) + f"concat=n={n}:v=1:a={1 if has_voice else 0}[vb]" + ("[voice]" if has_voice else ""))
        v = "vb"
    else:
        inputs += ["-f", "lavfi", "-i", f"color=c={tl.get('background') or pack['colors']['bg']}:s={W}x{H}:r={fps}:d={dur}"]
        fc.append(f"[0:v]setsar=1[vb]")
        v = "vb"

    # b-roll: laid over the A-roll picture, A-roll audio keeps playing
    for k, br in enumerate(tl.get("broll", [])):
        s, d, si = br["start"], br["dur"], br.get("src_in", 0)
        if br["file"].lower().endswith((".jpg", ".jpeg", ".png", ".webp")):  # photos: hold as a still
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", str(d + 0.2), "-i", _abs(br["file"])]
            si = 0
        else:
            inputs += ["-i", _abs(br["file"])]
        idx = len([x for x in inputs if x == "-i"]) - 1
        fc.append(f"[{idx}:v]trim={si}:{si + d},setpts=PTS-STARTPTS+{s}/TB,{cover}[br{k}]")
        fc.append(f"[{v}][br{k}]overlay=eof_action=pass:enable='between(t,{s},{s + d})'[vbr{k}]")
        v = f"vbr{k}"

    # premium picture: measured correction + subtle finish, then the chosen grade on top
    from .picture import filters as pic_filters
    pf = pic_filters(tl.get("picture"), finish=tl.get("finish", True) and bool(tl.get("source") or tl.get("broll")))
    if pf:
        fc.append(f"[{v}]{pf}[vpic]")
        v = "vpic"
    # zooms and transitions are applied per frame in pass 2 (engine/fx.py)
    fc.append(grades.graph(tl.get("grade", pack.get("grade")), v, "vout"))
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]"]
    if has_voice:
        cmd += ["-map", "[voice]", "-c:a", "aac"]
    cmd += ["-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-movflags", "+faststart", out]
    _run(cmd)
    return has_voice


# ---------------------------------------------------------------- pass 2: graphics
def ease_back(p):
    p = min(max(p, 0.0), 1.0)
    return 1 + 2.70158 * (p - 1) ** 3 + 1.70158 * (p - 1) ** 2


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def item_image(it, pack):
    """The RGBA image for one timeline item at full (1080-wide) scale. Also used by the editor."""
    t = it["type"]
    c = pack["colors"]
    if t == "text":
        f = pack["fonts"][it.get("font_role", "main")]
        text = it["text"]
        case = f.get("case")
        text = text.upper() if case == "upper" else text.lower() if case == "lower" else text
        fit = textfit.fit_text(text, f["file"], it.get("w", 900), it.get("h", 700),
                               max_px=it.get("max_px", 190), min_px=it.get("min_px", 40),
                               weight=f.get("weight"), max_lines=it.get("max_lines", 5))
        col = c.get(it.get("color", "ink"), it.get("color", c["ink"]))
        stroke = it.get("stroke", 0)
        if it.get("on_video"):  # text over footage needs an outline to stay readable
            stroke = stroke or max(4, fit["size"] // 14)
        stroke_col = c["bg"] if packs.contrast(col, c["bg"]) > 3 else "#000000"
        return textfit.render_block(fit, col, stroke=stroke, stroke_color=it.get("stroke_color", stroke_col))
    if t == "bubble":
        return layout.bubble_with_text(it["text"], pack, width=it.get("width", 640))
    if t == "sticker":
        return stickers.render(it["name"], pack, it.get("size", 300), it.get("colour", "accent"),
                               it.get("seed", 0), it.get("style"), it.get("font"))
    if t == "comment":
        from .story import comment_bubble
        return comment_bubble(it["handle"], it["text"], pack, it.get("size", 620))
    if t == "story":
        from .story import story_card
        return story_card(it, pack)
    if t == "photo":
        from .premium import photo_card
        if it.get("file"):
            src = Image.open(_abs(it["file"]))
        else:                                   # a still grabbed from the video itself
            import tempfile as _tf
            png = os.path.join(_tf.mkdtemp(), "grab.png")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(it.get("grab_t", 0)), "-i", _abs(it["grab_from"]),
                            "-frames:v", "1", "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,crop=900:900:90:600", png])
            src = Image.open(png)
        return photo_card(src, it.get("size", 380), it.get("label"), pack, it.get("rotate", 0))
    if t == "callout":
        from .premium import callout
        return callout(it["text"], pack, it.get("sub"), it.get("length", 200), it.get("side", "right"),
                       it.get("size", 320), it.get("colour", "pop"), it.get("max_w"))
    if t == "badge":
        return stickers.badge(it["text"], pack, it.get("shape", "burst"), it.get("size", 300), it.get("colour", "pop"),
                              it.get("font"))
    if t == "overlay":
        img = layout.load_overlay(_abs(it["file"]), it.get("knock_out_white", False))
        if it.get("contrast_fix", True):
            img = layout.ensure_contrast(img, c["bg"], c["paper"])
        w = it.get("width", 260)
        return img.resize((w, max(1, int(img.height * w / img.width))), Image.LANCZOS)
    if t == "title":  # layered designed title (see titles.py); composite = final state
        comp, _ = titles.composite(titles.build(it["spec"], pack))
        return comp
    if t == "card":  # full-frame designed card (title / "designed moment")
        W, H = 1080, 1920
        card = Image.new("RGBA", (W, H), c.get(it.get("bg", "bg"), c["bg"]))
        f = pack["fonts"]["main"]
        fit = textfit.fit_text(it["text"], f["file"], 860, 900, max_px=170, min_px=50, weight=f.get("weight"))
        im = textfit.render_block(fit, c.get(it.get("color", "ink"), c["ink"]))
        card.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))
        if it.get("kicker"):
            fa = pack["fonts"]["accent"]
            k = textfit.render_block(textfit.fit_text(it["kicker"], fa["file"], 700, 120, 80, 30, weight=fa.get("weight")), c["accent"])
            card.alpha_composite(k, ((W - k.width) // 2, (H - im.height) // 2 - k.height - 40))
        return card
    raise ValueError(f"unknown item type {t}")


def _anim(it, t):
    """(scale, alpha, dx, dy, reveal) for an item at time t."""
    a_in = it.get("anim", "pop")
    lt, rem = t - it["start"], it["end"] - t
    dur = 0.28
    s, alpha, dx, dy, reveal = 1.0, 1.0, 0, 0, 1.0
    if a_in == "pop":
        s = ease_back(lt / dur)
    elif a_in == "fade":
        alpha = ease_out(lt / 0.25)
    elif a_in == "slide":
        dy = (1 - ease_out(lt / 0.3)) * 120
        alpha = ease_out(lt / 0.2)
    elif a_in == "type":
        reveal = min(lt / it.get("type_dur", max(0.35, 0.03 * len(it.get("text", "")))), 1.0)
    elif a_in == "drop":
        dy = -(1 - ease_back(lt / 0.35)) * 200
    if it.get("float"):  # gentle bob for stickers
        dy += np.sin(lt * 2.4 + hash(it["id"]) % 7) * 6
    if it.get("exit", "fade") == "fade" and rem < 0.15:
        alpha *= max(rem / 0.15, 0)
    return max(s, 0), alpha, dx, dy, reveal


def _place(frame, img, it, t, scale):
    s, alpha, dx, dy, reveal = _anim(it, t)
    k = scale * it.get("scale", 1.0) * s
    if k <= 0.02 or alpha <= 0.01:
        return
    im = img
    glass = img.info.get("glass")
    if reveal < 1:
        im = im.crop((0, 0, max(1, int(im.width * reveal)), im.height))
    w, h = max(1, int(im.width * k)), max(1, int(im.height * k))
    im = im.resize((w, h), Image.BILINEAR)
    if it.get("rotate"):
        im = im.rotate(-it["rotate"], expand=True, resample=Image.BICUBIC)
    if alpha < 1:
        a = im.split()[3].point(lambda v: int(v * alpha))
        im.putalpha(a)
    cx = (it["x"] + dx) * scale
    cy = (it["y"] + dy) * scale
    if reveal < 1:  # typewriter grows from the left edge of the full block
        cx = cx - img.width * k / 2 + w / 2
    x0, y0 = int(cx - im.width / 2), int(cy - im.height / 2)
    if glass is not None and reveal >= 1:  # frosted glass: blur the live video behind the panel
        m = glass.resize((w, h), Image.BILINEAR)
        if it.get("rotate"):
            m = m.rotate(-it["rotate"], expand=True, resample=Image.BICUBIC)
        if alpha < 1:
            m = m.point(lambda v: int(v * alpha))
        box = (max(0, x0), max(0, y0), min(frame.width, x0 + m.width), min(frame.height, y0 + m.height))
        if box[2] > box[0] and box[3] > box[1]:
            region = frame.crop(box).filter(ImageFilter.GaussianBlur(max(6, 20 * scale)))
            frame.paste(region, box, m.crop((box[0] - x0, box[1] - y0, box[2] - x0, box[3] - y0)))
    frame.alpha_composite(im, (x0, y0))


def _draw(frame, img, cx, cy, alpha=1.0, scale=1.0, rotate=0):
    if scale <= 0.02 or alpha <= 0.01:
        return
    im = img
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rotate:
        im = im.rotate(-rotate, expand=True, resample=Image.BICUBIC)
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def title_draws(it, layers, t, scale):
    """(behind, front) draw lists for a layered title at time t."""
    behind, front = [], []
    comp_off = it.get("_off", (0, 0))
    k = it.get("scale", 1.0)
    for l in layers:
        st = titles.layer_state(l, t - it["start"], it["end"] - t)
        if not st:
            continue
        img, dx, dy, a, s = st
        cx = (it["x"] + (l["dx"] - comp_off[0] + dx) * k) * scale
        cy = (it["y"] + (l["dy"] - comp_off[1] + dy) * k) * scale
        d = (img, cx, cy, a, s * k * scale, l.get("rotate", 0) + it.get("rotate", 0))
        (behind if l.get("behind") else front).append(d)
    return behind, front


def caption_groups(cap):
    words, n = cap.get("words", []), max(1, cap.get("words_per_line", 3))
    style = cap.get("style", "karaoke")
    if style == "single-word":
        n = 1
    groups, cur = [], []
    if style == "kinetic":
        n = max(n, 5)
    max_chars = 17 if style == "pop" else 24 if style in ("duo", "rainbow", "boxed", "popin", "stack") else \
        30 if style == "kinetic" else 10 ** 6    # big caps: keep each line short so it stays big
    for w in words:
        if cur and (len(cur) >= n or w["start"] - cur[-1]["end"] > 0.5
                    or sum(len(x["w"]) + 1 for x in cur) + len(w["w"]) > max_chars):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_graphics(tl, pack, base, out, scale=1.0, layer=None):
    """layer=None: the finished picture. For the layers export: "video" (footage + camera moves
    only), "graphics" (titles/stickers on transparent), "captions" (captions on transparent)."""
    W, H = [int(v * scale) // 2 * 2 for v in tl["size"]]
    fps = tl.get("fps", 30)
    n_frames = int(tl["duration"] * fps)
    items = sorted(tl.get("items", []), key=lambda i: i.get("z", 0))
    cache, tlayers = {}, {}
    for it in items:
        if it["type"] == "title":
            tlayers[it["id"]] = titles.build(it["spec"], pack)
            comp, off = titles.composite(tlayers[it["id"]])
            it["_off"] = off
            cache[it["id"]] = comp
        else:
            cache[it["id"]] = item_image(it, pack)
    items = [it for it in items if cache[it["id"]] is not None]
    masker = None
    if any(l.get("behind") for ls in tlayers.values() for l in ls) and tl.get("source"):
        try:
            from .segment import PersonMasker
            masker = PersonMasker()
        except Exception as e:  # never fail a render over the cut-out: text goes in front instead
            print(f"[reel] person cut-out unavailable ({e}); 'behind' text will render in front")
    zooms, trans = tl.get("zooms", []), tl.get("transitions", [])
    anim = {}  # animated stickers: id -> [(frame, seconds)]
    for it in items:
        if it.get("type") == "sticker" and str(it.get("name", "")).startswith("anim:"):
            from .iconstickers import animated
            anim[it["id"]] = animated(it["name"][5:], it.get("size", 300))
    cap = tl.get("captions") or {}
    groups = caption_groups(cap) if cap.get("style", "off") != "off" else []
    # which words get the highlight colour: the plan's picks (words or indexes) or automatic
    kw_src = cap.get("keywords")
    if kw_src is None:
        kw = set(captions.auto_keywords(cap.get("words", [])))
    else:
        want = {str(x).lower() for x in kw_src}
        kw = {i for i, w in enumerate(cap.get("words", [])) if i in kw_src or re.sub(r"[^a-z0-9']", "", w["w"].lower()) in want}
    g_off, _o = [], 0
    for _g in groups:
        g_off.append(_o)
        _o += len(_g)
    cap_cache = {}
    hide_caps = [(it["start"], it["end"]) for it in items if it.get("hide_captions")]

    dec = subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-i", base, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if layer in ("graphics", "captions"):   # transparent layers: ProRes 4444 with alpha (CapCut/Premiere/Resolve/FCP)
        vcodec = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
    else:
        vcodec = ["-c:v", "libx264", "-preset", "fast" if scale == 1 else "veryfast",
                  "-crf", "20", "-maxrate", "10M", "-bufsize", "20M",  # Instagram-friendly size
                  "-pix_fmt", "yuv420p"]
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-"] + vcodec + [out], stdin=subprocess.PIPE)
    if layer == "video":
        items, groups = [], []
    fsize = W * H * 4
    last = None
    for fi in range(n_frames):
        buf = dec.stdout.read(fsize)
        if len(buf) == fsize:
            last = buf
        frame = Image.frombuffer("RGBA", (W, H), last, "raw", "RGBA", 0, 1).copy()
        t = fi / fps
        if zooms or trans:
            frame = fx.apply(frame, t, zooms, trans, pack["colors"]["pop"])
        if tl.get("layouts"):
            frame = fx.apply_layouts(frame, t, tl["layouts"], pack["colors"]["pop"])
        video = frame
        if layer in ("graphics", "captions"):
            frame = Image.new("RGBA", (W, H))
        behind, fronts = [], []
        for it in items:
            if it["start"] <= t < it["end"] and it["type"] == "title":
                b, f = title_draws(it, tlayers[it["id"]], t, scale)
                behind += b
                fronts.append((it, f))
        if behind and layer == "graphics":  # text behind the person: cut the person out of the text layer
            txt = Image.new("RGBA", (W, H))
            for d in behind:
                _draw(txt, *d)
            if masker:
                inv = masker.mask(video, t * 1000).point(lambda v: 255 - v)
                a = ImageChops.multiply(txt.split()[3], inv)
                txt.putalpha(a)
            frame.alpha_composite(txt)
        elif behind:
            orig = frame.copy()
            for d in behind:
                _draw(frame, *d)
            if masker:  # put the person back on top of the text
                person = orig
                person.putalpha(masker.mask(orig, t * 1000))
                frame.alpha_composite(person)
        for it in (items if layer != "captions" else []):
            if it["start"] <= t < it["end"]:
                if it["type"] == "title":
                    for d in dict((id(x[0]), x[1]) for x in fronts).get(id(it), []):
                        _draw(frame, *d)
                elif it["id"] in anim and anim[it["id"]]:
                    frs = anim[it["id"]]
                    total = sum(d for _, d in frs)
                    lt = (t - it["start"]) % total
                    for img_f, dd in frs:
                        if lt < dd:
                            break
                        lt -= dd
                    _place(frame, img_f, it, t, scale)
                else:
                    _place(frame, cache[it["id"]], it, t, scale)
        if groups and layer != "graphics" and not any(a <= t < b for a, b in hide_caps):
            for gi, g in enumerate(groups):
                if g[0]["start"] <= t < (groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.3):
                    active = max((k for k, w in enumerate(g) if w["start"] <= t), default=0)
                    kinetic = cap.get("style") in captions.KINETIC
                    phase = min(int((t - g[active]["start"]) * fps / 1.5), captions.PHASES) if kinetic else 0
                    key = (gi, active if cap.get("style", "karaoke") in captions.ACTIVE else 0, phase)
                    if key not in cap_cache:
                        ccap = dict(cap, _keys_in_group=[k - g_off[gi] for k in kw if g_off[gi] <= k < g_off[gi] + len(g)])
                        lp = (cap.get("layout_plan") or [{}] * len(groups))[gi % max(len(cap.get("layout_plan") or [1]), 1)]
                        if cap.get("style") == "kinetic":
                            ccap["_layout"] = lp.get("layout", captions.KIN_LAYOUTS[gi % len(captions.KIN_LAYOUTS)])
                            cap_cache[key] = captions.render_kinetic_layout(g, active, phase, pack, ccap)
                        else:
                            cap_cache[key] = (captions.render_kinetic(g, active, phase, pack, ccap) if kinetic
                                              else captions.render(g, active, pack, ccap))
                    im = cap_cache[key]
                    if scale != 1:
                        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))))
                    if cap.get("style") == "kinetic":        # each line lands in its own spot
                        lp = (cap.get("layout_plan") or [{}])[gi % max(len(cap.get("layout_plan") or [1]), 1)]
                        maxw = 900 * scale
                        if im.width > maxw:
                            im = im.resize((int(maxw), int(im.height * maxw / im.width)))
                        cx, cy = lp.get("x", 540) * scale, lp.get("y", 1240) * scale
                        al = lp.get("align", "center")
                        x0 = cx if al == "left" else cx - im.width if al == "right" else cx - im.width / 2
                        x0 = min(max(x0, 50 * scale), W - 50 * scale - im.width)
                        y0 = min(max(cy - im.height / 2, 200 * scale), H - 420 * scale - im.height)
                        frame.alpha_composite(im, (int(x0), int(y0)))
                    else:
                        y = cap.get("y", 1240) * scale
                        frame.alpha_composite(im, (int(W / 2 - im.width / 2), int(y - im.height / 2)))
                    break
        enc.stdin.write(frame.tobytes())
    enc.stdin.close()
    enc.wait()
    if masker:
        masker.close()
    dec.kill()
    dec.wait()


# ---------------------------------------------------------------- pass 3: audio
# Phone audio -> clear "podcast" voice: remove rumble + background hiss, tame boominess,
# add presence so words cut through music, and even out loud/quiet moments.
VOICE_CHAIN = ("highpass=f=85,"
               "equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3.5,equalizer=f=9500:t=q:w=1:g=1.5,"
               "acompressor=threshold=0.09:ratio=3:attack=6:release=120:makeup=2")
# Final loudness for social apps (TikTok/Instagram play around -14 LUFS), stereo 48 kHz.
MASTER = "alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11,aformat=sample_rates=48000:channel_layouts=stereo"


def build_audio(tl, base_has_voice, base, out_wav):
    dur = tl["duration"]
    a = tl.get("audio", {})
    cues = [(c["t"], c["name"], c.get("gain", 0.7)) for c in a.get("sfx", [])]
    fx = sfx.mix_cues(cues, dur) * a.get("sfx_gain", 0.6)
    tmp = tempfile.mkdtemp()
    fx_wav = os.path.join(tmp, "fx.wav")
    sfx.write_wav(fx_wav, fx, peak=None)
    inputs, labels, fc = ["-i", fx_wav], ["[0:a]"], []
    if base_has_voice:
        deep = False
        voice_src = base
        noise = a.get("noise") or {}
        if a.get("enhance_voice", True) and a.get("denoise", "auto") != "light" and noise.get("level") in ("some", "noisy"):
            from .audiocheck import deepfilter, elevenlabs_isolate
            cleaned = None
            if a.get("denoise") == "elevenlabs":         # paid studio tier (user's own key)
                cleaned = elevenlabs_isolate(base, os.path.join(tmp, "voice-clean.wav"))
            if not cleaned:                              # default: neural speech cleaner (offline, free)
                cleaned = deepfilter(base, os.path.join(tmp, "voice-clean.wav"),
                                     strength=None if noise["level"] == "noisy" else 30)
            if cleaned:
                voice_src, deep = cleaned, True
        inputs += ["-i", voice_src]
        if a.get("enhance_voice", True):
            from .audiocheck import chain
            clean = chain(a.get("noise"), deep=deep)     # measured per video (see audiocheck)
            gate = chain(a.get("noise"), post=True)
            fc.append(f"[1:a]aformat=channel_layouts=mono,{clean + ',' if clean else ''}{VOICE_CHAIN}"
                      f"{',' + gate if gate else ''}[v0]")
            labels.append("[v0]")
        else:
            labels.append("[1:a]")
    music = a.get("music")
    if music:
        inputs += ["-stream_loop", "-1", "-i", _abs(music["file"])]
        mi = len([x for x in inputs if x == "-i"]) - 1
        g = music.get("gain", 0.18)
        if base_has_voice and music.get("duck", True):
            fc.append(f"{labels[1]}asplit[vo][sc]")
            labels[1] = "[vo]"
            # carve a pocket in the music where the voice lives (1–4 kHz) so words sit on top
            fc.append(f"[{mi}:a]volume={g},equalizer=f=2200:t=q:w=1.1:g=-5,afade=t=out:st={max(dur - 1, 0)}:d=1[m0]")
            # gentle ducking: music dips under the voice but stays audible
            fc.append(f"[m0][sc]sidechaincompress=threshold=0.06:ratio=3:attack=30:release=450[m]")
        else:
            fc.append(f"[{mi}:a]volume={g},afade=t=out:st={max(dur - 1, 0)}:d=1[m]")
        labels.append("[m]")
    fc.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,"
              f"atrim=0:{dur},{MASTER}[aout]")
    _run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc),
                                                          "-map", "[aout]", "-ar", "48000", "-ac", "2", out_wav])


def render(timeline, out, preview=False, no_music_out=None):
    """no_music_out: also write a copy with voice + sound effects only (no background music),
    so a trending sound can be added inside TikTok/Instagram. Costs one extra audio mix only."""
    tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
    pack = packs.load(tl.get("pack"))
    scale = 0.5 if preview else 1.0
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "base.mp4")
    has_voice = build_base(tl, pack, base, scale)
    gfx = os.path.join(tmp, "gfx.mp4")
    build_graphics(tl, pack, base, gfx, scale)
    wav = os.path.join(tmp, "mix.wav")
    build_audio(tl, has_voice, base, wav)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    raw = os.path.join(tmp, "raw.mp4")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", gfx, "-i", wav, "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", raw])
    # finish: fade in/out, optional speed-up, brand end screen (engine/endcard.py)
    from .endcard import finish
    spec = dict({"enabled": not preview}, **(tl.get("end_card") or {}))
    kit, speed = tl.get("sound_kit", "clean"), float(tl.get("speed", 1.0))
    finish(raw, out, pack, spec, kit, speed)
    if no_music_out:
        dry = json.loads(json.dumps(tl))
        dry.setdefault("audio", {}).pop("music", None)
        wav2 = os.path.join(tmp, "nomusic.wav")
        build_audio(dry, has_voice, base, wav2)
        raw2 = os.path.join(tmp, "raw2.mp4")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", gfx, "-i", wav2, "-map", "0:v", "-map", "1:a",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", raw2])
        finish(raw2, no_music_out, pack, spec, kit, speed)
    return out


def export_layers(timeline, out_dir):
    """The 'keep editing' export: clean footage (cuts, colour, camera moves), a transparent
    graphics layer, a transparent captions layer and the mixed audio — stack them in any editor
    (CapCut, Premiere, DaVinci Resolve, Final Cut) to tweak anything."""
    tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
    pack = packs.load(tl.get("pack"))
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "base.mp4")
    has_voice = build_base(tl, pack, base)
    build_graphics(tl, pack, base, os.path.join(out_dir, "1-video.mp4"), layer="video")
    build_graphics(tl, pack, base, os.path.join(out_dir, "2-graphics.mov"), layer="graphics")
    if (tl.get("captions") or {}).get("style", "off") != "off":
        build_graphics(tl, pack, base, os.path.join(out_dir, "3-captions.mov"), layer="captions")
    build_audio(tl, has_voice, base, os.path.join(out_dir, "4-audio.wav"))
    open(os.path.join(out_dir, "README.txt"), "w").write(
        "Stack these in your editor, bottom to top:\n"
        "  1-video.mp4     your footage: cuts, colour, zooms (no text)\n"
        "  2-graphics.mov  titles, stickers, callouts (transparent)\n"
        "  3-captions.mov  captions (transparent)\n"
        "  4-audio.wav     voice (cleaned), music, sound effects\n"
        "All layers start at 0:00 and have the same length.\n")
    return out_dir


def base_proxy(timeline, out):
    """Half-size base video (cuts, b-roll, zooms, grade — no graphics) for the manual editor."""
    tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
    build_base(tl, packs.load(tl.get("pack")), out, 0.5, crf=28)
    return out


def thumbnail(timeline, out, t=None):
    """Cover image: a frame (default: the designed title, else the first takeover/hook) with graphics."""
    tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
    pack = packs.load(tl.get("pack"))
    if t is None:
        hooks = ([i for i in tl.get("items", []) if i.get("type") == "title"] or
                 [i for i in tl.get("items", []) if i.get("role") in ("hook", "takeover")])
        t = hooks[0]["start"] + 0.4 if hooks else 0.5
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "b.mp4")
    build_base(tl, pack, base)
    png = os.path.join(tmp, "f.png")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", base, "-frames:v", "1", png])
    frame = Image.open(png).convert("RGBA")
    for it in tl.get("items", []):
        if it["start"] <= t < it["end"]:
            it2 = dict(it, start=t - 1, anim="none")
            _place(frame, item_image(it, pack), it2, t, 1.0)
    frame.convert("RGB").save(out, quality=92)
    return out
