"""Caption styles. Each takes a group of timed words + the index of the word being said.

karaoke      words light up in the highlight colour as they're said
single-word  one big word at a time
line         short clean lines
box          each line on a rounded box (classic social look)
highlight    the spoken word sits on a colour pill
bounce       the spoken word pops bigger in the highlight colour
outline      heavy caps with a thick colour outline
neon         glowing text in the highlight colour
build        words appear one by one as they're said
two-tone     key words (long words, numbers) in the highlight colour
elegant      lowercase serif italic with a soft shadow
shadow       clean white text, soft drop shadow (minimal)
stacked      each word in its own brand-coloured block (playful)
typewriter   monospace on a paper strip, typing along
pop          big bold caps, thick outline + shadow; key words bigger in the highlight colour,
             the spoken word pops (the viral "CapCut" look)
"""
import os, re
from PIL import Image, ImageColor, ImageDraw, ImageFilter
from .textfit import load_font

STYLES = {
    "karaoke": "words light up as you say them", "single-word": "one big word at a time",
    "line": "short, clean lines", "box": "lines on a rounded box", "highlight": "spoken word on a colour pill",
    "bounce": "spoken word pops bigger", "outline": "bold caps with a thick colour outline",
    "neon": "glowing highlight colour", "build": "words appear as you say them",
    "two-tone": "key words in your highlight colour", "elegant": "soft lowercase serif italic",
    "shadow": "clean white with a soft shadow", "stacked": "each word in a colour block",
    "typewriter": "typewriter strip that types along",
    "pop": "bold caps, key words bigger in your colour",
}
ACTIVE = {"karaoke", "highlight", "bounce", "build", "typewriter", "single-word", "pop"}
STOP = set("""a an the and or but so if of to in on at for with from by as is are was were be been am i
you he she it we they me my our your his her its their this that these those there here have has had
do does did not no yes just very really also too then than what when where who how which let's lets
it's i'm i've that's there's we're you're can could would should will about into out up down over""".split())
EMPHASIS = {"best", "wow", "amazing", "love", "never", "always", "strong", "thin", "beautiful", "perfect",
            "free", "new", "secret", "biggest", "worst", "insane", "crazy", "favourite", "favorite",
            "incredible", "only", "first", "must", "stop", "quality", "huge", "super", "comfortable"}


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEAK = set("""because especially actually really basically probably something anything everything
nothing someone everyone maybe always never just also very much many some other another those these
there where which while about after before again already still though through going gonna wanna
thing things stuff kind sort guys hey okay yeah like said says think know want make made makes get got
produces produce doing done itself themselves myself yourself have having been being would could should""".split())


def _score(word, prev):
    k = re.sub(r"[^a-z0-9']", "", word.lower())
    if not k or k in STOP or k in WEAK:
        return 0
    s = 1.0
    if k in EMPHASIS:
        s += 4
    if re.search(r"\d", k):
        s += 4
    if re.search(r"(est|ful|ous|able|ible|ive|less|ly)$", k) and not k.endswith("ly"):
        s += 1.5                                          # describing words: best, beautiful, comfortable
    if word[:1].isupper() and prev and not prev.rstrip().endswith((".", "!", "?")):
        s += 2                                            # names mid-sentence: China, Davey
    s += min(len(k), 10) / 10
    return s


def auto_keywords(words, every=3):
    """The words worth highlighting: emphasis words, numbers, describing words, names —
    about one per caption line, never filler like 'because' or 'actually'."""
    keys = set()
    for start in range(0, len(words), every):
        run = list(range(start, min(start + every, len(words))))
        scored = [(_score(words[i]["w"], words[i - 1]["w"] if i else ""), i) for i in run]
        best = max(scored)
        if best[0] >= 1.6:
            keys.add(best[1])
        keys |= {i for sc, i in scored if sc >= 5}         # always: emphasis words and numbers
    return sorted(keys)


def _font_for(style, pack, size):
    f = pack["fonts"]["caption"]
    if style == "elegant":
        tf = pack.get("title_fonts", {}).get("serif")
        it = os.path.join(ROOT, "library", "fonts", "PlayfairDisplay-Italic-Variable.ttf")
        return load_font(it, size, 500) if os.path.exists(it) else load_font(tf["file"], size, tf.get("weight"))
    if style == "typewriter":
        return load_font(os.path.join(ROOT, "library", "fonts", "CourierPrime-Regular.ttf"), size)
    if style in ("outline", "stacked"):
        m = pack["fonts"]["main"]
        return load_font(m["file"], size, m.get("weight"))
    return load_font(f["file"], size, f.get("weight"))


def _key_word(w):
    return bool(re.search(r"\d", w)) or len(re.sub(r"[^A-Za-z]", "", w)) >= 6


def _render_pop(group, active, pack, cap):
    """Big bold caps on a shared baseline; key words bigger + in the highlight colour;
    the spoken word pops a little bigger. Thick dark outline + soft shadow = readable on
    any footage."""
    from .packs import _lum
    c = pack["colors"]
    base = cap.get("size", 88)
    keyset = set(cap.get("_keys_in_group", []))
    words = [w["w"].upper().strip(",.!?") for w in group]
    m = dict(pack["fonts"]["main"], weight=cap.get("weight", pack["fonts"]["main"].get("weight")))
    dark = min([v for v in c.values() if isinstance(v, str) and v.startswith("#")], key=_lum)
    dark = dark if _lum(dark) < 0.05 else "#0B0B0B"
    pop = c.get("caption_active", c["pop"])
    white = c.get("caption", "#FFFFFF")

    def sizes(k):
        return [int(base * k * (1.24 if i in keyset else 1.0)) for i in range(len(words))]   # no size change per word: no jumping

    k = 1.0
    for _ in range(12):
        fonts = [load_font(m["file"], sz, m.get("weight")) for sz in sizes(k)]
        gap = base * k * 0.28
        total = sum(f.getlength(wd) for f, wd in zip(fonts, words)) + gap * (len(words) - 1)
        if total <= 920:
            break
        k *= 0.9
    asc = max(f.getmetrics()[0] for f in fonts)
    desc = max(f.getmetrics()[1] for f in fonts)
    stroke = max(5, int(base * k / 9))
    pad = stroke * 4
    W, H = int(total) + pad * 2, asc + desc + pad * 2
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    x, base_y = pad, pad + asc
    for i, (f, wd) in enumerate(zip(fonts, words)):
        col = pop if i in keyset else white
        d.text((x, base_y), wd, font=f, fill=col, stroke_width=stroke, stroke_fill=dark, anchor="ls")
        x += f.getlength(wd) + gap
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(stroke * 1.2)).point(lambda v: int(v * 0.55)))
    out = Image.new("RGBA", im.size)
    out.alpha_composite(sh, (0, stroke))
    out.alpha_composite(im)
    return out.crop(out.getbbox() or (0, 0, 1, 1))


def render(group, active, pack, cap):
    c = pack["colors"]
    style = cap.get("style", "karaoke")
    if style == "pop":
        return _render_pop(group, active, pack, cap)
    base_size = cap.get("size", {"single-word": 118, "outline": 86, "stacked": 70, "typewriter": 60,
                                 "elegant": 84}.get(style, 78))
    words = [w["w"] for w in group]
    case = cap.get("case") or ("upper" if style in ("outline", "stacked") else
                               "lower" if style in ("karaoke", "single-word", "highlight", "bounce", "build",
                                                    "elegant", "neon") else None)
    if case == "upper":
        words = [x.upper() for x in words]
    elif case == "lower":
        words = [x.lower() for x in words]
    if style == "single-word":
        words, active = [words[min(active, len(words) - 1)]], 0

    font = _font_for(style, pack, base_size)
    space = font.getlength(" ") * (1.6 if style in ("stacked", "highlight") else 1) + max(4, base_size // 12)
    widths = [font.getlength(x) for x in words]
    if style == "bounce" and words:  # leave room for the bigger spoken word
        widths[min(active, len(words) - 1)] *= 1.3
    total = sum(widths) + space * (len(words) - 1)
    if total > 900:  # never overflow
        font = _font_for(style, pack, int(base_size * 900 / total))
        space = font.getlength(" ") * (1.6 if style in ("stacked", "highlight") else 1) + max(4, font.size // 12)
        widths = [font.getlength(x) for x in words]
        if style == "bounce" and words:
            widths[min(active, len(words) - 1)] *= 1.3
        total = sum(widths) + space * (len(words) - 1)
    size = font.size
    asc, desc = font.getmetrics()
    lh = asc + desc
    pad = int(size * 0.6)
    W, H = int(total) + pad * 2, int(lh * 1.5) + pad * 2
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    stroke = max(4, size // 12)
    white, dark = c.get("caption", "#FFFFFF"), "#000000"
    from .packs import _lum, contrast
    darkest = min([v for v in c.values() if isinstance(v, str) and v.startswith("#")], key=_lum)
    paper = c.get("paper", "#FFFFFF")
    on_paper = max([c.get("ink", "#111111"), darkest, "#111111"], key=lambda v: contrast(v, paper))
    pop = c.get("caption_active", c["pop"])
    y = pad + int(lh * 0.25)

    if style in ("box", "typewriter"):  # background strip behind the line
        shown = len(words) if style == "box" else active + 1
        wline = sum(widths[:shown]) + space * (shown - 1)
        fill = c.get("paper", "#FFFFFF")
        d.rounded_rectangle((pad - size * 0.35, y - size * 0.18, pad + wline + size * 0.35, y + lh + size * 0.12),
                            radius=size * (0.35 if style == "box" else 0.08), fill=fill)
    x = pad
    for i, (wd, ww) in enumerate(zip(words, widths)):
        col, st, stc = white, stroke, dark
        if style == "karaoke" and i == active:
            col = pop
        elif style == "two-tone" and _key_word(wd):
            col = pop
        elif style in ("box", "typewriter"):
            col, st = on_paper if style == "box" else "#1E1E1E", 0
            if style == "typewriter" and i > active:
                col = (0, 0, 0, 0)
        elif style == "highlight" and i == active:
            d.rounded_rectangle((x - size * 0.22, y - size * 0.12, x + ww + size * 0.22, y + lh + size * 0.05),
                                radius=size * 0.28, fill=pop)
            st = 0
        elif style == "outline":
            stc, st = pop, max(6, size // 7)
        elif style == "build" and i > active:
            col, st = (0, 0, 0, 0), 0
        elif style == "stacked":
            blk = [c["pop"], c["accent"], darkest][i % 3]
            d.rounded_rectangle((x - size * 0.2, y - size * 0.1, x + ww + size * 0.2, y + lh + size * 0.04),
                                radius=size * 0.12, fill=blk)
            col = "#FFFFFF" if contrast("#FFFFFF", blk) >= contrast("#111111", blk) else "#111111"
            st = 0
        elif style in ("elegant", "shadow", "neon"):
            st = 0
        if style == "bounce" and i == active:
            big = _font_for(style, pack, int(size * 1.28))
            d.text((x + ww / 2, y + lh / 2), wd, font=big, fill=pop, stroke_width=stroke, stroke_fill=dark, anchor="mm")
        else:
            d.text((x, y), wd, font=font, fill=col, stroke_width=st, stroke_fill=stc)
        x += ww + space

    if style in ("elegant", "shadow"):
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        a = im.split()[3].filter(ImageFilter.GaussianBlur(size * 0.09))
        sh.putalpha(a.point(lambda v: int(v * 0.7)))
        out = Image.new("RGBA", im.size)
        out.alpha_composite(sh, (0, int(size * 0.05)))
        out.alpha_composite(im)
        im = out
    if style == "neon":
        glow = Image.new("RGBA", im.size, pop)
        glow.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(size * 0.16)).point(lambda v: min(255, v * 2)))
        out = Image.new("RGBA", im.size)
        out.alpha_composite(glow)
        out.alpha_composite(glow)
        out.alpha_composite(im)
        im = out
    if style in ("build", "typewriter"):
        return im  # keep full width so the line doesn't shift as words appear
    return im.crop(im.getbbox() or (0, 0, 1, 1))


# ---------------------------------------------------------------- kinetic styles
KINETIC = {"duo", "rainbow", "boxed", "popin", "stack"}
STYLES.update({
    "duo": "clean caps + the key word in your script font, bigger and coloured",
    "rainbow": "key words in different brand colours",
    "boxed": "the key word on a colour block",
    "popin": "each word pops onto the screen as it's said",
    "stack": "words fade and slide in, the key word big on its own line",
})
ACTIVE |= KINETIC
PHASES = 6          # animation frames rendered for the newest word (then it rests)


def _pop_scale(phase):
    """Gentle pop for a word appearing: 0.82 -> 1.06 -> 1.0 (subtle — big bounces distract)."""
    return [0.82, 0.94, 1.06, 1.03, 1.0, 1.0, 1.0][min(phase, PHASES)]


def _fonts(pack, cap, size):
    from .titles import fonts_for
    f = pack["fonts"].get("caption") or pack["fonts"]["main"]
    main = load_font(f["file"], int(size), cap.get("weight", 700))
    tf = fonts_for(pack)
    alt_spec = tf.get(cap.get("accent_font", "brush"), tf["script"])
    return main, (lambda s: load_font(alt_spec["file"], int(s), alt_spec.get("weight"))), \
        (lambda s: load_font(f["file"], int(s), cap.get("weight", 700)))


def render_kinetic(group, active, phase, pack, cap):
    """Kinetic caption line. `phase` = frames since the active word started (0..PHASES)."""
    from .packs import _lum, contrast
    c = pack["colors"]
    style = cap.get("style")
    base = cap.get("size", 86)
    keyset = set(cap.get("_keys_in_group", []))
    darkest = min([v for v in c.values() if isinstance(v, str) and v.startswith("#")], key=_lum)
    dark = darkest if _lum(darkest) < 0.05 else "#0B0B0B"
    white = c.get("caption", "#FFFFFF")
    palette = [c.get("caption_active", c["pop"]), c.get("accent", c["pop"]), "#FFD23F"]
    main, alt_font, main_at = _fonts(pack, cap, base)
    show_upto = active if style in ("popin", "stack") else len(group) - 1
    words = []
    for i, w in enumerate(group):
        txt = w["w"].strip(",.!?")
        key = i in keyset
        if style in ("duo", "stack") and key:
            txt = txt[:1].upper() + txt[1:].lower()
        else:
            txt = txt.upper()
        scale = 1.0
        if style in ("duo", "stack") and key:
            scale = 1.35
        elif key:
            scale = 1.15
        pop = _pop_scale(phase) if (i == active and style in ("popin", "stack", "rainbow", "boxed", "duo")) else 1.0
        colour = white
        if key:
            colour = palette[(sum(1 for k in keyset if k < i)) % len(palette)] if style == "rainbow" else palette[0]
        if style == "boxed" and key:
            colour = "#FFFFFF" if contrast("#FFFFFF", palette[0]) >= contrast("#111111", palette[0]) else "#111111"
        font = alt_font(base * scale) if (style in ("duo", "stack") and key) else main_at(base * scale)
        words.append({"t": txt, "f": font, "col": colour, "key": key, "vis": i <= show_upto,
                      "new": i == active, "w": font.getlength(txt), "pop": pop, "size": base * scale,
                      "alt": style in ("duo", "stack") and key})
    # layout: fit on one line if possible, else two lines (stack: key word on its own line)
    gap = base * 0.26
    lines = []
    if style == "stack" and any(w["key"] for w in words):
        cur = []
        for w in words:
            if w["key"]:
                if cur:
                    lines.append(cur)
                lines.append([w])
                cur = []
            else:
                cur.append(w)
        if cur:
            lines.append(cur)
    else:
        cur, width = [], 0
        for w in words:
            if cur and width + gap + w["w"] > 900:
                lines.append(cur)
                cur, width = [], 0
            cur.append(w)
            width += (gap if len(cur) > 1 else 0) + w["w"]
        lines.append(cur)
    stroke = max(3, int(base / 14))
    pad = stroke * 5
    line_h = [max(w["f"].getmetrics()[0] + w["f"].getmetrics()[1] for w in ln) for ln in lines]
    W = int(min(1000, max(sum(w["w"] for w in ln) + gap * (len(ln) - 1) for ln in lines))) + pad * 2
    H = int(sum(line_h) * 0.95) + pad * 2
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    y = pad
    for ln, lh in zip(lines, line_h):
        total = sum(w["w"] for w in ln) + gap * (len(ln) - 1)
        x = (W - total) / 2
        base_y = y + lh * 0.78
        for w in ln:
            if w["vis"]:
                off_y = 0
                alpha = 255
                if style == "stack" and w["new"]:        # slide up + fade in
                    p = min(phase / PHASES, 1)
                    off_y = (1 - p) * base * 0.5
                    alpha = int(255 * min(1, 0.3 + p))
                # the word keeps its slot; a popping word scales around the slot's centre only
                f = w["f"]
                wx, ww = x, w["w"]
                if abs(w["pop"] - 1) > 0.01:
                    f = (alt_font if w["alt"] else main_at)(w["size"] * w["pop"])
                    ww = f.getlength(w["t"])
                    wx = x + (w["w"] - ww) / 2
                if style == "boxed" and w["key"]:
                    asc = w["f"].getmetrics()[0]
                    d.rounded_rectangle((x - base * 0.16, base_y - asc * 0.92 + off_y, x + w["w"] + base * 0.16,
                                         base_y + base * 0.16 + off_y), radius=base * 0.18, fill=palette[0])
                    d.text((wx, base_y + off_y), w["t"], font=f, fill=w["col"], anchor="ls")
                else:
                    col = w["col"]
                    if alpha < 255:
                        r, g, b = ImageColor.getrgb(col)[:3]
                        col = (r, g, b, alpha)
                    d.text((wx, base_y + off_y), w["t"], font=f, fill=col,
                           stroke_width=stroke, stroke_fill=dark, anchor="ls")
            x += w["w"] + gap
        y += lh * 0.95
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(stroke * 1.4)).point(lambda v: int(v * 0.5)))
    out = Image.new("RGBA", im.size)
    out.alpha_composite(sh, (0, stroke))
    out.alpha_composite(im)
    return out   # full size (not cropped) so the line doesn't jump as words appear


# ---------------------------------------------------------------- kinetic typography
# Studied from top CapCut edits: every caption line is a small DESIGNED layout — the key word
# huge (tall condensed display, script or italic serif), the other words small, stacked on 2–3
# lines — and each line lands in a different part of the screen. Words appear as they're said.
KINETIC |= {"kinetic"}
STYLES["kinetic"] = "designed word layouts: key word huge, mixed fonts, moving around the screen"
ACTIVE |= {"kinetic"}
KIN_LAYOUTS = ("stack", "script", "italic", "side")
FONT_DISPLAY = os.path.join(ROOT, "library", "fonts", "BebasNeue-Regular.ttf")
FONT_ITALIC = os.path.join(ROOT, "library", "fonts", "PlayfairDisplay-Italic-Variable.ttf")


def kinetic_key(group, keyset):
    if keyset:
        return min(keyset)
    scored = [(len(re.sub(r"[^A-Za-z]", "", w["w"])), i) for i, w in enumerate(group)
              if re.sub(r"[^a-z']", "", w["w"].lower()) not in STOP]
    return max(scored)[1] if scored else len(group) - 1


def render_kinetic_layout(group, active, phase, pack, cap):
    """One designed caption composition (fixed canvas; words fade/slide in as spoken)."""
    from .packs import _lum
    from .titles import fonts_for
    c = pack["colors"]
    layout = cap.get("_layout", "stack")
    keyset = set(cap.get("_keys_in_group", []))
    k = kinetic_key(group, keyset)
    base = cap.get("size", 72)
    pop = c.get("caption_active", c["pop"])
    white = c.get("caption", "#FFFFFF")
    darkest = min([v for v in c.values() if isinstance(v, str) and v.startswith("#")], key=_lum)
    dark = darkest if _lum(darkest) < 0.05 else "#0B0B0B"
    cf = pack["fonts"].get("caption") or pack["fonts"]["main"]
    small = lambda s: load_font(cf["file"], int(s), cap.get("weight", 700))
    script_spec = fonts_for(pack).get("brush") or fonts_for(pack)["script"]
    words = [w["w"].strip(",.!?") for w in group]
    before, key, after = words[:k], words[k], words[k + 1:]
    # build lines: list of (text, font, colour, word_indexes)
    if layout == "stack":
        kf = load_font(FONT_DISPLAY, int(base * 2.6))
        lines = [(" ".join(before).upper(), small(base * 0.72), white, list(range(0, k))),
                 (key.upper(), kf, pop, [k]),
                 (" ".join(after).upper(), small(base * 0.72), white, list(range(k + 1, len(words))))]
        align = "left"
    elif layout == "script":
        kf = load_font(script_spec["file"], int(base * 1.8), script_spec.get("weight"))
        lines = [(" ".join(before).upper(), small(base * 0.78), white, list(range(0, k))),
                 (key[:1].upper() + key[1:].lower(), kf, pop, [k]),
                 (" ".join(after).upper(), small(base * 0.78), white, list(range(k + 1, len(words))))]
        align = "center"
    elif layout == "italic":
        kf = load_font(FONT_ITALIC, int(base * 1.5), 600)
        lines = [(" ".join(before).upper(), small(base * 0.78), white, list(range(0, k))),
                 (key.lower(), kf, pop, [k]),
                 (" ".join(after).upper(), small(base * 0.72), white, list(range(k + 1, len(words))))]
        align = "right"
    else:  # side: huge key on the left, the rest small beside it
        kf = load_font(FONT_DISPLAY, int(base * 2.8))
        rest = before + after
        idx = [i for i in range(len(words)) if i != k]
        half = (len(rest) + 1) // 2
        lines = [("side", kf, pop, [k], [(" ".join(rest[:half]).upper(), idx[:half]),
                                         (" ".join(rest[half:]).upper(), idx[half:])])]
        align = "left"
    stroke = max(3, int(base / 16))
    pad = stroke * 6
    if layout == "side":
        _, kfnt, kcol, _, parts = lines[0]
        sf = small(base * 0.72)
        kw = kfnt.getlength(key.upper())
        ka, kd = kfnt.getmetrics()
        sw = max([sf.getlength(t) for t, _ in parts if t] or [0])
        W, H = int(kw + base * 0.3 + sw) + pad * 2, int(ka + kd * 0.3) + pad * 2
        im = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(im)
        vis = lambda ids: all(i <= active for i in ids) if ids else False
        if k <= active:
            d.text((pad, pad + ka), key.upper(), font=kfnt, fill=kcol, anchor="ls", stroke_width=stroke, stroke_fill=dark)
        y = pad + ka * 0.42
        for t, ids in parts:
            if t and vis(ids):
                d.text((pad + kw + base * 0.3, y), t, font=sf, fill=white, anchor="ls", stroke_width=stroke, stroke_fill=dark)
            y += base * 0.78
    else:
        lines = [ln for ln in lines if ln[0]]
        widths = [f.getlength(t) for t, f, _, _ in lines]
        heights = [sum(f.getmetrics()) for _, f, _, _ in lines]
        W = int(max(widths)) + pad * 2
        H = int(sum(h * 0.86 for h in heights)) + pad * 2
        im = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(im)
        y = pad
        for (t, f, col, ids), w, h in zip(lines, widths, heights):
            x = pad if align == "left" else (W - w) / 2 if align == "center" else W - pad - w
            if ids and all(i <= active for i in ids):
                new = active in ids
                off = (1 - min(phase / PHASES, 1)) * base * 0.35 if new else 0
                a = int(255 * min(1, 0.35 + phase / PHASES)) if new else 255
                r, g, b = ImageColor.getrgb(col)[:3]
                d.text((x, y + f.getmetrics()[0] + off), t, font=f, fill=(r, g, b, a), anchor="ls",
                       stroke_width=stroke, stroke_fill=dark)
            y += h * 0.86
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(stroke * 1.6)).point(lambda v: int(v * 0.55)))
    out = Image.new("RGBA", im.size)
    out.alpha_composite(sh, (0, stroke))
    out.alpha_composite(im)
    return out
