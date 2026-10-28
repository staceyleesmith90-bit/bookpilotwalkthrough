"""Scene effects — full-frame effects that change the picture itself (not stickers on top of it).

Twenty named effects in the style of AI-edited "effects" reels, all drawn here in the brand's colours:
the person is cut out (segment.PersonMasker) so backgrounds can change behind them, text can sit
behind their head and the frame can break, fold into an app or a phone. Each effect has its own
sounds (SOUNDS), its own default length and settings, and is used from a plan beat:

    "do": ["scene:paper_cutout"],  "scene": {"dur": 2}

Effects (settings, all optional):
  orbit           icons orbiting the head (icons[], speed)
  chat_takeover   video folds into an AI chat that ticks off the edit (app, prompt, steps[])
  frame_escape    video becomes a photo card and the person steps out of it
  snap_zoom       hard punch-ins with a blur snap (steps[] e.g. [1.3, 1.6])
  checklist_pop   ticked pills pop beside the head (items[])
  headline_storm  news strips slam in behind the person (headlines[])
  zoom_portal     a mini-you in a ring, then the camera dives into it
  growth_curve    dark chart backdrop, curve climbs behind you, counter (to, label, note)
  studio_reveal   studio lights flick on, ON AIR sign (sign)
  broll_overlay   the shot folds into an editor timeline and a b-roll clip drops in (image, label)
  paper_cutout    sticker-outlined cut-out on a bold paper collage
  dolly_zoom      the room pulls away while the person stays still (amount)
  magazine_cover  masthead behind your head, cover lines, barcode, badge (title, big, inside[], badge)
  liquid_glass    a glass lens glides over the shot
  zoom_through    zoom-through cut (fast push in, flash, land)
  green_screen    green backdrop that keys to a new scene (image, or the built-in city)
  frame_break     the previous look cracks and shatters away (at: [x, y])
  digital_zoom    camera viewfinder: REC, 1.0x -> 1.6x -> 2.6x with focus hunting
  phone_mockup    the reel shrinks into a phone with a Reels-style screen (handle)
  recap           full-screen checklist that counts up (items[], title, sub)
Overlays for a whole "series" reel: series (top title + numbered effect name + progress dashes),
tag_wall (effect names listed down both sides).
CLI preview strip: python -m engine scene-preview <effect> [--photos clip.mp4]
"""
import math, os, random, subprocess
from datetime import date
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .motiongfx import _back, _colors, _ease, _font, _rgb, _shadow

LABELS = {
    "orbit": "Orbit", "chat_takeover": "Chat Takeover", "frame_escape": "Frame Escape", "snap_zoom": "Snap Zoom",
    "checklist_pop": "Checklist Pop", "headline_storm": "Headline Storm", "zoom_portal": "Zoom Portal",
    "growth_curve": "Growth Curve", "studio_reveal": "Studio Reveal", "broll_overlay": "B-roll Overlay",
    "paper_cutout": "Paper Cutout", "dolly_zoom": "Dolly Zoom", "magazine_cover": "Magazine Cover",
    "liquid_glass": "Liquid Glass", "zoom_through": "Zoom Through Cut", "green_screen": "Green Screen",
    "frame_break": "Frame Break", "digital_zoom": "Digital Zoom", "phone_mockup": "Phone Mockup",
    "recap": "Checklist",
}
OVERLAYS = ("series", "tag_wall")
# one line each, for the Studio's Scene effects page
ABOUT = {
    "orbit": "App icons circle your head and pass behind you.", "chat_takeover": "Your video folds into an AI chat that ticks off the edit.",
    "frame_escape": "You become a photo card — then step out of it.", "snap_zoom": "Hard punch-ins with a blur snap.",
    "checklist_pop": "Ticked pills pop up beside your head.", "headline_storm": "News strips slam in behind you.",
    "zoom_portal": "A mini-you in a ring — then the camera dives in.", "growth_curve": "A chart climbs behind you with a counter.",
    "studio_reveal": "Studio lights flick on, ON AIR sign lights up.", "broll_overlay": "Your shot folds into an editor timeline.",
    "paper_cutout": "Sticker-outlined you on a bold paper collage.", "dolly_zoom": "The room pulls away while you stay still.",
    "magazine_cover": "You're the cover: masthead behind your head.", "liquid_glass": "A glass lens glides over the shot.",
    "zoom_through": "Fast push in, flash, land — a cut with punch.", "green_screen": "A green backdrop that keys to a new scene.",
    "frame_break": "The last look cracks and shatters away.", "digital_zoom": "Camera viewfinder: REC, 1.6x, 2.6x, focus hunting.",
    "phone_mockup": "The reel shrinks into a phone screen.", "recap": "A full-screen checklist that counts up.",
}
# default length (s) when a beat doesn't say; short ones are transitions
DUR = {"zoom_through": 0.8, "frame_break": 1.4, "snap_zoom": 1.8, "liquid_glass": 1.5, "phone_mockup": 1.6}
# effects that need the person cut out (or the head position)
PERSON = {"orbit", "frame_escape", "snap_zoom", "checklist_pop", "headline_storm", "zoom_portal", "growth_curve",
          "studio_reveal", "paper_cutout", "dolly_zoom", "magazine_cover", "liquid_glass", "zoom_through",
          "green_screen", "digital_zoom"}
# sounds: (seconds from the start — negative = from the end, or "p0.5" = halfway, event[, gain])
SOUNDS = {
    "orbit": [(0.0, "air"), (0.05, "pill_in"), (0.2, "pill_in"), (0.36, "pill_in")],
    "chat_takeover": [(0.0, "window_in"), ("p0.33", "notify"), ("p0.42", "tick"), ("p0.54", "tick"),
                      ("p0.66", "tick"), (-0.3, "air")],
    "frame_escape": [(0.0, "whoosh"), ("p0.27", "thump")],
    "snap_zoom": [(0.0, "zoom_in"), (-0.15, "swish")],
    "checklist_pop": [(0.1, "pill_in"), (0.45, "pill_in"), (0.8, "pill_in")],
    "headline_storm": [(0.0 + 0.11 * k, "slam") for k in range(8)],
    "zoom_portal": [(0.05, "pill_in"), ("p0.68", "whoosh"), ("p0.92", "boom", 1.3)],
    "growth_curve": [(0.0, "air"), (0.15, "chart_grow")] + [(0.3 + 0.17 * k, "tick", 0.7) for k in range(7)]
                    + [("p0.85", "reveal")],
    "studio_reveal": [("p0.12", "lights"), ("p0.22", "lights"), ("p0.32", "notify")],
    "broll_overlay": [(0.0, "window_in"), ("p0.18", "click"), (-0.3, "air")],
    "paper_cutout": [(0.0, "page"), (0.1, "pill_in")],
    "dolly_zoom": [(0.0, "riser")],
    "magazine_cover": [(0.0, "shutter"), (0.25, "pill_in"), (0.45, "pill_in"), (0.65, "thump")],
    "liquid_glass": [(0.0, "glass"), ("p0.4", "sparkle")],
    "zoom_through": [(0.0, "whoosh"), ("p0.45", "boom", 1.3)],
    "green_screen": [(0.0, "air"), ("p0.48", "sparkle")],
    "frame_break": [(0.0, "crack", 1.2), ("p0.22", "shatter", 2.2)],      # the loudest moment, like the reference
    "digital_zoom": [("p0.12", "camera"), ("p0.45", "camera"), ("p0.8", "camera")],
    "phone_mockup": [(0.0, "window_in")],
    "recap": [("p%.2f" % (0.05 + 0.7 * k / 19), "tick", 0.6) for k in range(0, 20, 2)] + [("p0.8", "cta")],
}


# ---------------------------------------------------------------- shared context
class Ctx:
    """What effects share while one piece of the reel renders: size, colours, the person cut-out."""

    def __init__(self, W, H, pack, base=None, fps=30, scenes=()):
        self.W, self.H, self.u = W, H, W / 1080
        self.pack, self.col, self.base, self.fps = pack, _colors(pack), base, fps
        self.scenes = list(scenes)
        self._maskers, self._mask_key, self._mask, self._head = {}, None, None, None
        self._store = {}

    # person cut-out ---------------------------------------------------------------
    def _masker(self, which):
        if which not in self._maskers:
            try:
                from .segment import PersonMasker
                self._maskers[which] = [PersonMasker(), 0]
            except Exception as e:  # never fail a render over the cut-out
                print(f"[reel] person cut-out unavailable ({e}); using a soft centre shape")
                self._maskers[which] = None
        return self._maskers[which]

    def mask(self, frame, t, live=True):
        key = (live, round(t * 1000))
        if live and key == self._mask_key:
            return self._mask
        m = self._masker("live" if live else "still")
        if m is None:
            out = self._fallback()
        else:
            m[1] = max(m[1] + 1, int(t * 1000)) if live else m[1] + 40
            out = m[0].mask(frame, m[1])
        if live:
            self._mask_key, self._mask = key, out
        return out

    def _fallback(self):
        if "fallback" not in self._store:
            W, H = self.W, self.H
            m = Image.new("L", (W, H))
            d = ImageDraw.Draw(m)
            d.ellipse((W * 0.33, H * 0.22, W * 0.67, H * 0.5), fill=255)
            d.rounded_rectangle((W * 0.12, H * 0.47, W * 0.88, H * 1.1), int(W * 0.2), fill=255)
            self._store["fallback"] = m.filter(ImageFilter.GaussianBlur(6 * self.u))
        return self._store["fallback"]

    def head(self, m):
        """(cx, cy, r) of the head from the mask, smoothed over time."""
        a = np.asarray(m.resize((self.W // 8, self.H // 8)), np.float32) > 127
        rows = np.where(a.mean(1) > 0.02)[0]
        if len(rows) < 3:
            h = (self.W / 2, self.H * 0.38, self.W * 0.14)
        else:
            y0 = rows[0]
            band = a[y0:y0 + max(3, int(a.shape[0] * 0.1))]
            cols = np.where(band.mean(0) > 0.25)[0]
            if not len(cols):
                cols = np.where(band.any(0))[0]
            r = max((cols[-1] - cols[0] + 1) * 4.0, self.W * 0.09)
            h = ((cols[0] + cols[-1] + 1) * 4.0, y0 * 8 + r * 1.15, r)
        if self._head:
            h = tuple(0.65 * a_ + 0.35 * b_ for a_, b_ in zip(self._head, h))
        self._head = h
        return h

    def frame_at(self, t):
        """One frame of the cut footage (for freeze-frames)."""
        k = ("frame", round(t, 3))
        if k not in self._store:
            if not self.base:
                return None
            raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{max(t, 0):.3f}", "-i", self.base, "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True).stdout
            if len(raw) < self.W * self.H * 4:
                return None
            self._store[k] = Image.frombuffer("RGBA", (self.W, self.H), raw[:self.W * self.H * 4], "raw", "RGBA", 0, 1).copy()
        return self._store[k]

    def store(self, key, make):
        if key not in self._store:
            self._store[key] = make()
        return self._store[key]

    def close(self):
        for m in self._maskers.values():
            if m:
                m[0].close()


def person(frame, m):
    p = frame.copy()
    p.putalpha(m)
    return p


# ---------------------------------------------------------------- drawing helpers
def _scale_about(img, k, cx, cy, size=None, fill=None):
    """img zoomed by k so the point (cx, cy) stays put (k < 1 shrinks; the outside is `fill`)."""
    W, H = size or img.size
    return img.transform((W, H), Image.AFFINE, (1 / k, 0, cx - cx / k, 0, 1 / k, cy - cy / k),
                         resample=Image.BILINEAR, fillcolor=fill)


def _zoom_blur(img, k, cx, cy, amount, n=5):
    """Zoom with a radial streak (several slightly bigger copies averaged), drawn at half size."""
    if amount < 0.004:
        return _scale_about(img, k, cx, cy) if abs(k - 1) > 1e-3 else img
    W, H = img.size
    small = img.resize((W // 2, H // 2), Image.BILINEAR)
    acc = None
    for i in range(n):
        z = _scale_about(small, k * (1 + amount * i / (n - 1)), cx / 2, cy / 2)
        a = np.asarray(z, np.float32)
        acc = a if acc is None else acc + a
    out = Image.fromarray((acc / n).astype(np.uint8), "RGBA").resize((W, H), Image.BILINEAR)
    return out


def _gradient(W, H, top, bottom):
    t = np.linspace(0, 1, H)[:, None, None]
    a = np.array(top, np.float32)[None, None, :] * (1 - t) + np.array(bottom, np.float32)[None, None, :] * t
    return Image.fromarray(np.repeat(a, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")


def _mix(c1, c2, k):
    return tuple(int(a * (1 - k) + b * k) for a, b in zip(c1[:3], c2[:3]))


def dark_bg(ctx):
    """Deep studio backdrop: near-black with a brand glow at the top and a cool glow low down."""
    def make():
        W, H = ctx.W, ctx.H
        w, h = max(W // 6, 2), max(H // 6, 2)
        bg = _gradient(w, h, (16, 14, 20), (8, 10, 22))
        glow = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(glow)
        d.ellipse((w * 0.15, -h * 0.1, w * 0.85, h * 0.1), fill=_rgb(ctx.col["pop"], 70))
        d.ellipse((w * 0.05, h * 0.7, w * 0.95, h * 1.25), fill=_mix(_rgb(ctx.col["accent"]), (30, 60, 190), 0.75) + (80,))
        bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(w * 0.16)))
        return bg.resize((W, H), Image.BICUBIC)
    return ctx.store("dark_bg", make).copy()


def _rr_mask(w, h, r):
    m = Image.new("L", (max(1, int(w)), max(1, int(h))), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), int(r), fill=255)
    return m


def _place_rect(canvas, img, rect, radius=0, shadow=0.0, border=0, border_col=(255, 255, 255, 255)):
    """Fit img (cover) into rect=(x0, y0, x1, y1) with rounded corners, border and soft shadow."""
    x0, y0, x1, y1 = [int(v) for v in rect]
    w, h = max(2, x1 - x0), max(2, y1 - y0)
    tile = ImageOps.fit(img.convert("RGBA"), (w, h), Image.BILINEAR)
    if border:
        b = Image.new("RGBA", (w + 2 * border, h + 2 * border), border_col)
        b.alpha_composite(tile, (border, border))
        tile, x0, y0, w, h = b, x0 - border, y0 - border, w + 2 * border, h + 2 * border
    m = _rr_mask(w, h, radius)
    tile.putalpha(ImageChops.multiply(tile.split()[3], m))
    if shadow:
        sh = Image.new("RGBA", (w + 120, h + 120))
        sm = Image.new("L", (w + 120, h + 120))
        sm.paste(m, (60, 70))
        sh.putalpha(sm.point(lambda v: int(v * shadow)).filter(ImageFilter.GaussianBlur(26)))
        canvas.alpha_composite(sh, (x0 - 60, y0 - 60))
    canvas.alpha_composite(tile, (x0, y0))


def _lerp_rect(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def _dilate(m, px):
    """Grow a mask by px (for sticker outlines)."""
    if px < 1:
        return m
    s = 4
    small = m.resize((max(1, m.width // s), max(1, m.height // s)), Image.BILINEAR)
    grown = small.filter(ImageFilter.GaussianBlur(px / s * 0.7)).point(lambda v: min(255, v * 4))   # round, not boxy
    big = grown.resize(m.size, Image.BICUBIC)
    return big.point(lambda v: 0 if v < 100 else 255 if v > 160 else (v - 100) * 255 // 60)


def _text_w(text, f):
    return f.getlength(text)


def _spin_check(d, cx, cy, r, col, k=1.0):
    """A filled circle with a white tick (k = how much of the tick is drawn)."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    pts = [(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)]
    if k > 0:
        if k < 0.5:
            q = k / 0.5
            pts = [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * q, pts[0][1] + (pts[1][1] - pts[0][1]) * q)]
        elif k < 1:
            q = (k - 0.5) / 0.5
            pts = [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * q, pts[1][1] + (pts[2][1] - pts[1][1]) * q)]
        d.line(pts, fill=(255, 255, 255, 255), width=max(2, int(r * 0.28)), joint="curve")


def _paste_center(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _seg(lt, a, b):
    """0..1 progress of lt through [a, b]."""
    return min(max((lt - a) / max(b - a, 1e-6), 0.0), 1.0)


# ---------------------------------------------------------------- 01 orbit
def _icon(kind, col, s, style):
    s = int(s)
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    bg, fg = [(_rgb(col["paper"]), _rgb(col["ink"])), ((22, 22, 26, 255), (255, 255, 255, 255)),
              (_rgb(col["pop"]), (255, 255, 255, 255))][style % 3]
    d.rounded_rectangle((0, 0, s - 1, s - 1), int(s * 0.28), fill=bg)
    c, lw = s / 2, max(2, int(s * 0.06))
    if kind == "cc":
        d.rounded_rectangle((s * .2, s * .3, s * .8, s * .7), int(s * .1), outline=fg, width=lw)
        d.text((c, c + s * 0.01), "CC", font=_font(s * 0.24, 800), fill=fg, anchor="mm")
    elif kind == "aa":
        d.text((c, c + s * 0.02), "Aa", font=_font(s * 0.4, 700), fill=fg, anchor="mm")
    elif kind == "play":
        d.polygon([(s * .38, s * .3), (s * .38, s * .7), (s * .72, s * .5)], fill=fg)
    elif kind == "cut":
        d.ellipse((s * .22, s * .58, s * .42, s * .78), outline=fg, width=lw)
        d.ellipse((s * .58, s * .58, s * .78, s * .78), outline=fg, width=lw)
        d.line((s * .38, s * .6, s * .66, s * .22), fill=fg, width=lw)
        d.line((s * .62, s * .6, s * .34, s * .22), fill=fg, width=lw)
    elif kind == "plus":
        d.rounded_rectangle((s * .46, s * .26, s * .54, s * .74), 3, fill=fg)
        d.rounded_rectangle((s * .26, s * .46, s * .74, s * .54), 3, fill=fg)
    elif kind == "wave":
        for i, hh in enumerate((0.16, 0.3, 0.42, 0.26, 0.14)):
            x = s * (0.28 + i * 0.11)
            d.rounded_rectangle((x - lw / 2, c - s * hh / 2, x + lw / 2, c + s * hh / 2), lw, fill=fg)
    else:  # spark
        pts = []
        for i in range(8):
            a = math.pi / 4 * i - math.pi / 2
            rr = s * (0.3 if i % 2 == 0 else 0.1)
            pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
        d.polygon(pts, fill=fg)
    return _shadow(im, int(s * 0.12), 0.32, int(s * 0.06))


def fx_orbit(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    kinds = spec.get("icons") or ["cc", "aa", "play", "cut", "plus", "wave", "spark"]
    icons = ctx.store(("orbit", tuple(kinds)), lambda: [_icon(k, ctx.col, 124 * u, i) for i, k in enumerate(kinds)])
    cx, cy = hx, hy + r * 0.75
    rx, ry, tilt = W * 0.42, H * 0.07, math.radians(-8)
    w = spec.get("speed", 1.5)
    back, front = Image.new("RGBA", (W, H)), Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(back)
    appear = _ease(lt / 0.35)
    for i in range(72):                                 # dashed orbit line
        if i % 2:
            continue
        a0, a1 = 2 * math.pi * i / 72, 2 * math.pi * (i + 1) / 72
        p0 = (cx + rx * math.cos(a0) * math.cos(tilt) - ry * math.sin(a0) * math.sin(tilt),
              cy + rx * math.cos(a0) * math.sin(tilt) + ry * math.sin(a0) * math.cos(tilt))
        p1 = (cx + rx * math.cos(a1) * math.cos(tilt) - ry * math.sin(a1) * math.sin(tilt),
              cy + rx * math.cos(a1) * math.sin(tilt) + ry * math.sin(a1) * math.cos(tilt))
        d.line((p0, p1), fill=(255, 255, 255, int(150 * appear * (1 - _seg(lt, dur - 0.3, dur)))), width=max(2, int(3 * u)))
    out_k = 1 - _ease(_seg(lt, dur - 0.3, dur))
    for i, ic in enumerate(icons):
        a = 2 * math.pi * i / len(icons) + w * lt
        depth = math.sin(a)                              # +1 = closest to camera (lower edge of the ring)
        x = cx + rx * math.cos(a) * math.cos(tilt) - ry * math.sin(a) * math.sin(tilt)
        y = cy + rx * math.cos(a) * math.sin(tilt) + ry * math.sin(a) * math.cos(tilt)
        k = _back(_seg(lt, 0.06 * i, 0.06 * i + 0.32)) * out_k
        _paste_center(front if depth > 0 else back, ic, x, y, k * (0.78 + 0.22 * depth), 1.0 if depth > 0 else 0.85)
    out = frame.copy()
    out.alpha_composite(back)
    out.alpha_composite(person(frame, m))           # the person goes back on top of what passes behind them
    out.alpha_composite(front)
    return out


# ---------------------------------------------------------------- 02 chat takeover
def _wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t2 = (cur + " " + w).strip()
        if f.getlength(t2) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t2
    if cur:
        lines.append(cur)
    return lines


def fx_chat_takeover(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    win = (W * 0.04, H * 0.2, W * 0.96, H * 0.76)
    tile = (W * 0.56, H * 0.3, W * 0.56 + W * 0.34, H * 0.3 + W * 0.34 * 16 / 9)
    k_in, k_out = _ease(_seg(lt, 0, 0.38)), _ease(_seg(lt, dur - 0.32, dur))
    alpha = k_in * (1 - k_out)
    rect = _lerp_rect((0, 0, W, H), tile, k_in) if k_out == 0 else _lerp_rect(tile, (0, 0, W, H), k_out)
    out = dark_bg(ctx)

    def window():
        im = Image.new("RGBA", (int(win[2] - win[0]), int(win[3] - win[1])))
        d = ImageDraw.Draw(im)
        ww, wh = im.size
        d.rounded_rectangle((0, 0, ww - 1, wh - 1), int(26 * u), fill=(250, 249, 247, 255), outline=(225, 222, 218, 255), width=2)
        for i, c in enumerate(("#E0DDD8", "#E0DDD8", "#E0DDD8")):
            d.ellipse((22 * u + i * 22 * u, 22 * u, 36 * u + i * 22 * u, 36 * u), fill=_rgb(c))
        d.rounded_rectangle((100 * u, 17 * u, 124 * u, 41 * u), int(6 * u), fill=_rgb(col["pop"]))
        d.text((134 * u, 29 * u), spec.get("app", "Claude"), font=_font(24 * u, 700), fill=_rgb(col["ink"]), anchor="lm")
        d.text((ww - 26 * u, 29 * u), "VIDEO EDIT", font=_font(17 * u, 600), fill=(160, 156, 150, 255), anchor="rm")
        d.line((0, 56 * u, ww, 56 * u), fill=(232, 229, 225, 255), width=2)
        # user's message above the video tile
        f = _font(23 * u, 500)
        lines = _wrap(spec.get("prompt", "Edit this video, caption every word, then add these effects."), f, W * 0.36)
        bh = len(lines) * 32 * u + 26 * u
        bx1, by0 = ww - 30 * u, 74 * u
        bw = max(f.getlength(x) for x in lines) + 36 * u
        d.rounded_rectangle((bx1 - bw, by0, bx1, by0 + bh), int(18 * u), fill=(236, 233, 228, 255))
        for i, ln in enumerate(lines):
            d.text((bx1 - bw + 18 * u, by0 + 14 * u + i * 32 * u), ln, font=f, fill=_rgb(col["ink"]))
        # reply box
        d.rounded_rectangle((26 * u, wh - 84 * u, ww - 26 * u, wh - 26 * u), int(29 * u), fill=(255, 255, 255, 255),
                            outline=(226, 222, 218, 255), width=2)
        d.text((52 * u, wh - 55 * u), spec.get("reply_hint", "Reply to Claude…"), font=_font(22 * u, 500), fill=(170, 166, 160, 255), anchor="lm")
        d.ellipse((ww - 76 * u, wh - 74 * u, ww - 38 * u, wh - 36 * u), fill=_rgb(col["pop"]))
        d.polygon([(ww - 57 * u, wh - 66 * u), (ww - 47 * u, wh - 53 * u), (ww - 67 * u, wh - 53 * u)], fill=(255, 255, 255, 255))
        return im
    wimg = ctx.store(("chatwin", spec.get("prompt"), spec.get("app")), window).copy()
    d = ImageDraw.Draw(wimg)
    ax, ay = 34 * u, 0.36 * H - win[1]
    steps = spec.get("steps") or ["Cut the pauses", "Caption every word", "Add the effects"]
    pk = p
    if 0.16 < pk < 0.34:                                   # thinking dots
        d.rounded_rectangle((ax, ay, ax + 26 * u, ay + 26 * u), int(6 * u), fill=_rgb(col["pop"]))
        for i in range(3):
            yy = ay + 13 * u - 4 * u * abs(math.sin(lt * 9 + i))
            d.ellipse((ax + 40 * u + i * 16 * u, yy - 4 * u, ax + 48 * u + i * 16 * u, yy + 4 * u), fill=(150, 146, 140, 255))
    if pk >= 0.33:
        d.rounded_rectangle((ax, ay, ax + 26 * u, ay + 26 * u), int(6 * u), fill=_rgb(col["pop"]))
        d.text((ax + 40 * u, ay + 13 * u), spec.get("reply", "On it."), font=_font(25 * u, 700), fill=_rgb(col["ink"]), anchor="lm")
        for i, s in enumerate(steps):
            st = 0.42 + 0.12 * i
            if pk < st:
                break
            yy = ay + 62 * u + i * 44 * u
            k = _seg(pk, st, st + 0.08)
            last = i == len(steps) - 1 and pk < st + 0.16
            if last:
                d.arc((ax + 6 * u, yy - 12 * u, ax + 30 * u, yy + 12 * u), lt * 400, lt * 400 + 270, fill=_rgb(col["pop"]), width=max(2, int(3 * u)))
            else:
                _spin_check(d, ax + 18 * u, yy, 12 * u, _rgb(col["pop"]), k * 2)
            d.text((ax + 44 * u, yy), s, font=_font(22 * u, 500), fill=_rgb(col["ink"], int(255 * k)), anchor="lm")
    win_alpha = wimg.split()[3].point(lambda v: int(v * alpha))
    wimg.putalpha(win_alpha)
    out.alpha_composite(wimg, (int(win[0]), int(win[1])))
    _place_rect(out, frame, rect, radius=18 * u * k_in * (1 - k_out), shadow=0.3 * alpha)
    return out


# ---------------------------------------------------------------- 03 frame escape
def fx_frame_escape(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    m = ctx.mask(frame, t)
    sf_end = 0.8
    a = _ease(_seg(lt, 0, 0.42))                        # shrink into a card
    b = _ease(_seg(lt, 0.42, 0.8))                      # the background falls away above the card
    back = _ease(_seg(lt, dur - 0.3, dur))              # and back to full screen
    sf = 1 + (sf_end - 1) * a
    sf = sf + (1 - sf) * back
    S = frame.resize((int(W * sf), int(H * sf)), Image.BILINEAR)
    Sm = m.resize(S.size, Image.BILINEAR)
    top_full = H * 0.5 - S.height / 2
    top_end = H * 0.80 - S.height * 0.92
    sy = top_full + (top_end - top_full) * a
    sy = sy + (H * 0.5 - S.height / 2 - sy) * back
    sx = (W - S.width) / 2
    card_top = sy + (H * 0.555 - sy) * b * (1 - back)
    card_bot = min(sy + S.height, H * 0.80 + (H - H * 0.8) * back) if a > 0.99 else sy + S.height
    if back > 0:
        card_bot = sy + S.height
    layer = Image.new("RGBA", (W, H))
    bord = int(14 * u * min(a, 1 - back))
    clip = S.crop((0, int(card_top - sy), S.width, int(card_bot - sy)))
    card = Image.new("RGBA", (clip.width + 2 * bord, clip.height + 2 * bord), (255, 255, 255, 255))
    card.alpha_composite(clip, (bord, bord))
    layer.alpha_composite(card, (int(sx - bord), int(card_top - bord)))
    if b > 0 and back < 1:                              # the person keeps going above the card
        pp = person(S, Sm)
        above = pp.crop((0, 0, S.width, max(1, int(card_top - sy + 4))))
        layer.alpha_composite(above, (int(sx), int(sy)))
    ang = (-4 * a + 7 * b) * (1 - back)
    rot = layer.rotate(ang, center=(W / 2, card_top + (card_bot - card_top) / 2), resample=Image.BICUBIC)
    out = dark_bg(ctx) if a > 0.001 or back < 1 else frame.copy()
    sh = rot.split()[3].point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(22 * u))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shadow.putalpha(sh)
    out.alpha_composite(shadow, (0, int(14 * u)))
    out.alpha_composite(rot)
    return out


# ---------------------------------------------------------------- 04 snap zoom
def fx_snap_zoom(frame, p, lt, dur, spec, ctx, t):
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    steps = spec.get("steps") or [1.3, 1.6]
    seg = (dur - 0.2) / len(steps)
    k, prev, blur = 1.0, 1.0, 0.0
    for i, z in enumerate(steps):
        s0 = i * seg
        if lt >= s0:
            q = _seg(lt, s0, s0 + 0.09)
            k = prev + (z - prev) * _ease(q)
            blur = max(blur, 0.09 * (1 - abs(2 * q - 1)) if q < 1 else 0)
            prev = z
    q = _seg(lt, dur - 0.12, dur)
    if q > 0:
        k = prev + (1 - prev) * _ease(q)
        blur = 0.09 * (1 - abs(2 * q - 1))
    cy = hy + r * 0.3
    return _zoom_blur(frame, k, hx, cy, blur).convert("RGBA")


# ---------------------------------------------------------------- 05 checklist pop
def fx_checklist_pop(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    items = spec.get("items") or ["Edit", "Captions", "Effects"]
    f = _font(36 * u, 700)
    x0 = min(hx + r * 1.25, W - max(f.getlength(s) for s in items) - 110 * u)
    out = frame.copy()
    for i, s in enumerate(items):
        st = 0.1 + 0.35 * i
        k = _back(_seg(lt, st, st + 0.3))
        if k <= 0:
            continue
        k *= 1 - _ease(_seg(lt, dur - 0.25, dur))
        w, h = int(f.getlength(s) + 104 * u), int(70 * u)
        pil = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(pil)
        d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=_rgb(col["paper"]))
        _spin_check(d, 35 * u, h / 2, 20 * u, _rgb(col["pop"]), _seg(lt, st + 0.1, st + 0.35) * 2)
        d.text((66 * u, h / 2), s, font=f, fill=_rgb(col["ink"]), anchor="lm")
        pil = _shadow(pil, int(12 * u), 0.3, int(6 * u))
        _paste_center(out, pil, x0 + w / 2, hy - r * 0.55 + i * 88 * u, k)
    return out


# ---------------------------------------------------------------- 06 headline storm
def _strip(text, tag, col, u, dark):
    f, ft = _font(34 * u, 800), _font(16 * u, 800)
    tw = ft.getlength(tag) + 22 * u
    w, h = int(tw + f.getlength(text) + 60 * u), int(62 * u)
    im = Image.new("RGBA", (w, h), (20, 20, 22, 255) if dark else _rgb(col["paper"]))
    d = ImageDraw.Draw(im)
    d.rectangle((12 * u, 15 * u, 12 * u + tw, h - 15 * u), fill=_rgb(col["pop"]))
    d.text((12 * u + tw / 2, h / 2), tag, font=ft, fill=(255, 255, 255, 255), anchor="mm")
    d.text((30 * u + tw, h / 2), text, font=f, fill=(255, 255, 255, 255) if dark else _rgb(col["ink"]), anchor="lm")
    return _shadow(im, int(10 * u), 0.35, int(6 * u))


def fx_headline_storm(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    m = ctx.mask(frame, t)
    heads = spec.get("headlines") or ["NEW EDIT JUST DROPPED", "ONE PROMPT. FULL EDIT.", "EVERY WORD CAPTIONED",
                                      "EDITORS ON NOTICE", "THE AI EDIT IS HERE", "MADE IN MINUTES", "WATCH TILL THE END",
                                      "BUILT IN REEL STUDIO"]
    tags = ["BREAKING", "JUST IN", "UPDATE", "BREAKING", "LIVE"]

    def make():
        rnd = random.Random(7)
        out = []
        for i, h in enumerate(heads):
            im = _strip(h, tags[i % len(tags)], ctx.col, u, dark=i % 3 == 2)
            ang = rnd.uniform(2, 7) * (1 if i % 2 else -1)
            y = H * (0.13 + 0.5 * ((i * 0.618) % 1))
            side = 1 if i % 2 else -1
            rest = W * (0.5 + side * rnd.uniform(0.05, 0.22))
            out.append((im.rotate(ang, expand=True, resample=Image.BICUBIC), y, side, rest))
        return out
    strips = ctx.store(("storm", tuple(heads)), make)
    layer = Image.new("RGBA", (W, H))
    for i, (im, y, side, rest) in enumerate(strips):
        st = 0.11 * i
        k = _ease(_seg(lt, st, st + 0.16))
        if k <= 0:
            continue
        ko = _ease(_seg(lt, dur - 0.22, dur))
        start = W / 2 - side * (W * 0.5 + im.width / 2)
        x = start + (rest - start) * k + side * W * 1.2 * ko
        layer.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    out = frame.copy()
    out.alpha_composite(layer)
    out.alpha_composite(person(frame, m))
    return out


# ---------------------------------------------------------------- 07 zoom portal
def fx_zoom_portal(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    R = W * 0.12
    cx = max(R + 30 * u, min(hx - r * 2.3, W - R - 30 * u))
    cy = hy - r * 0.15
    box = (hx - r * 1.3, hy - r * 1.3, hx + r * 1.3, hy + r * 1.3)
    face = frame.crop(tuple(int(v) for v in box)).resize((int(2 * R), int(2 * R)), Image.BILINEAR)
    mk = Image.new("L", face.size, 0)
    ImageDraw.Draw(mk).ellipse((0, 0, face.width - 1, face.height - 1), fill=255)
    face.putalpha(mk)
    ring = Image.new("RGBA", (int(2 * R + 24 * u), int(2 * R + 24 * u)))
    d = ImageDraw.Draw(ring)
    d.ellipse((0, 0, ring.width - 1, ring.height - 1), outline=_rgb(col["pop"]), width=max(3, int(9 * u)))
    ring.alpha_composite(face, (int(12 * u), int(12 * u)))
    k = _back(_seg(lt, 0.0, 0.35))
    out = frame.copy()
    _paste_center(out, _shadow(ring, int(14 * u), 0.35, int(6 * u)), cx, cy, k)
    zq = _seg(p, 0.68, 1.0)
    if zq > 0:
        z = 1 + 7 * zq ** 2.2
        out = _zoom_blur(out, z, cx, cy, 0.12 * math.sin(math.pi * min(zq * 1.2, 1)))
    return out


# ---------------------------------------------------------------- 08 growth curve
def _grid_bg(ctx):
    def make():
        W, H, u = ctx.W, ctx.H, ctx.u
        bg = _gradient(W, H, (10, 14, 34), (6, 8, 18))
        d = ImageDraw.Draw(bg)
        step = int(90 * u)
        for x in range(0, W, step):
            d.line((x, 0, x, H), fill=(255, 255, 255, 14), width=1)
        for y in range(0, H, step):
            d.line((0, y, W, y), fill=(255, 255, 255, 14), width=1)
        return bg
    return ctx.store("grid_bg", make).copy()


def fx_growth_curve(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    out = _grid_bg(ctx)
    q = _ease(_seg(lt, 0.15, dur * 0.85))
    n = 120
    pts = []
    for i in range(int(n * q) + 1):
        x = i / n
        y = (math.exp(4.2 * x) - 1) / (math.exp(4.2) - 1)
        pts.append((W * (0.0 + 0.97 * x), H * (0.9 - 0.68 * y)))
    if len(pts) > 1:
        area = Image.new("RGBA", (W, H))
        ImageDraw.Draw(area).polygon(pts + [(pts[-1][0], H), (pts[0][0], H)], fill=_mix(_rgb(col["accent"]), (40, 80, 255), 0.55) + (150,))
        grad = Image.fromarray((np.linspace(1, 0.15, H)[:, None] * np.ones((1, W)) * 255).astype(np.uint8), "L")
        area.putalpha(ImageChops.multiply(area.split()[3], grad))
        out.alpha_composite(area)
        line = Image.new("RGBA", (W, H))
        dl = ImageDraw.Draw(line)
        dl.line(pts, fill=_rgb(col["pop"]), width=max(3, int(8 * u)), joint="curve")
        glow = line.filter(ImageFilter.GaussianBlur(12 * u))
        out.alpha_composite(glow)
        out.alpha_composite(line)
        tx, ty = pts[-1]
        dd = ImageDraw.Draw(out)
        dd.ellipse((tx - 13 * u, ty - 13 * u, tx + 13 * u, ty + 13 * u), fill=(255, 255, 255, 255), outline=_rgb(col["pop"]), width=max(2, int(4 * u)))
    d = ImageDraw.Draw(out)
    d.ellipse((60 * u, H * 0.205 - 5 * u, 70 * u, H * 0.205 + 5 * u), fill=_rgb(col["pop"]))
    d.text((80 * u, H * 0.205), spec.get("note", "SAMPLE DATA"), font=_font(17 * u, 700), fill=(200, 200, 210, 200), anchor="lm")
    to = float(spec.get("to", 10))
    val = 1 + (to - 1) * q
    big, small = f"{int(round(val))}{spec.get('unit', '×')}", spec.get("label", "growth").upper()
    fb, fs = _font(52 * u, 800), _font(15 * u, 800)
    bw = int(fb.getlength(big) + fs.getlength(small) + 46 * u)
    bx1, by = W - 46 * u, H * 0.24
    d.rounded_rectangle((bx1 - bw, by - 40 * u, bx1, by + 40 * u), int(12 * u), fill=_rgb(col["pop"]))
    d.text((bx1 - bw + 18 * u, by), big, font=fb, fill=(255, 255, 255, 255), anchor="lm")
    d.text((bx1 - 16 * u, by + 12 * u), small, font=fs, fill=(255, 255, 255, 255), anchor="rm")
    out.alpha_composite(person(frame, m))
    return out


# ---------------------------------------------------------------- 09 studio reveal
def fx_studio_reveal(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    left = p > 0.12 and not (0.15 < p < 0.17)
    right = p > 0.22
    sign = p > 0.32

    def stage(l_on, r_on):
        bg = _gradient(W, H, (6, 6, 9), (10, 14, 30))
        glow = Image.new("RGBA", (W, H))
        for on, cx, ang in ((l_on, W * 0.08, 14), (r_on, W * 0.92, -14)):
            box = Image.new("RGBA", (int(W * 0.34), int(W * 0.26)))
            ImageDraw.Draw(box).rounded_rectangle((0, 0, box.width - 1, box.height - 1), int(10 * u),
                                                  fill=(250, 250, 255, 255) if on else (36, 36, 42, 255))
            box = box.rotate(ang, expand=True, resample=Image.BICUBIC)
            if on:
                g = Image.new("RGBA", (W, H))
                g.alpha_composite(box, (int(cx - box.width / 2), int(H * 0.36 - box.height / 2)))
                glow.alpha_composite(g.filter(ImageFilter.GaussianBlur(70 * u)))
                glow.alpha_composite(g.filter(ImageFilter.GaussianBlur(20 * u)))
            bg.alpha_composite(box, (int(cx - box.width / 2), int(H * 0.36 - box.height / 2)))
        bg.alpha_composite(glow)
        return bg
    out = ctx.store(("studio", left, right), lambda: stage(left, right)).copy()
    lit = (0.35 + 0.65 * (left + right) / 2)
    pp = person(frame, m)
    if lit < 0.99:
        rgb = pp.convert("RGB").point(lambda v: int(v * lit))
        rgb.putalpha(m)
        pp = rgb
    out.alpha_composite(pp)
    d = ImageDraw.Draw(out)
    fs = _font(28 * u, 800)
    text = spec.get("sign", "ON AIR")
    w = fs.getlength(text) + 60 * u
    cx, cy = W / 2, H * 0.215
    if sign:
        g = Image.new("RGBA", (W, H))
        ImageDraw.Draw(g).rounded_rectangle((cx - w / 2, cy - 30 * u, cx + w / 2, cy + 30 * u), int(10 * u), fill=_rgb(col["pop"]))
        out.alpha_composite(g.filter(ImageFilter.GaussianBlur(18 * u)))
    d.rounded_rectangle((cx - w / 2, cy - 30 * u, cx + w / 2, cy + 30 * u), int(10 * u),
                        fill=_rgb(col["pop"]) if sign else (60, 22, 18, 255), outline=(255, 255, 255, 90 if sign else 30), width=2)
    d.text((cx, cy), text, font=fs, fill=(255, 255, 255, 255 if sign else 90), anchor="mm")
    return out


# ---------------------------------------------------------------- 10 b-roll overlay
def fx_broll_overlay(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    win = (W * 0.03, H * 0.2, W * 0.97, H * 0.52)
    ph = win[3] - win[1] - 150 * u
    pw = ph * 9 / 16
    tile = (W / 2 - pw / 2, win[1] + 60 * u, W / 2 + pw / 2, win[1] + 60 * u + ph)
    k_in, k_out = _ease(_seg(lt, 0, 0.35)), _ease(_seg(lt, dur - 0.3, dur))
    out = dark_bg(ctx)
    d = ImageDraw.Draw(out)
    a = int(255 * k_in * (1 - k_out))
    d.rounded_rectangle(win, int(16 * u), fill=(18, 19, 24, a), outline=(255, 255, 255, int(a * 0.15)), width=2)
    tag = spec.get("label", "B-ROLL · REEL STUDIO")
    ft = _font(17 * u, 800)
    d.rounded_rectangle((win[0] + 18 * u, win[1] + 16 * u, win[0] + 40 * u + ft.getlength(tag), win[1] + 46 * u), int(6 * u),
                        fill=_rgb(col["pop"], a))
    d.text((win[0] + 29 * u, win[1] + 31 * u), tag, font=ft, fill=(255, 255, 255, a), anchor="lm")
    play = 0.08 + 0.86 * _seg(lt, 0.3, dur - 0.3)
    b0, b1 = 0.38, 0.72
    br_on = b0 <= play <= b1 and _seg(lt, 0.3, 0.6) > 0.5
    # filmstrip under the preview
    fy = win[3] - 70 * u
    for i in range(18):
        x = win[0] + 30 * u + i * (win[2] - win[0] - 60 * u) / 18
        d.rectangle((x, fy, x + (win[2] - win[0] - 60 * u) / 18 - 4 * u, fy + 36 * u), fill=(60, 62, 70, a))
    px = win[0] + 30 * u + (win[2] - win[0] - 60 * u) * play
    # tracks below the window
    ty = (H * 0.56, H * 0.6)
    tx0, tx1 = W * 0.08, W * 0.94
    d.text((W * 0.04, ty[0]), "V2", font=_font(16 * u, 700), fill=(150, 150, 160, a), anchor="lm")
    d.text((W * 0.04, ty[1]), "V1", font=_font(16 * u, 700), fill=(150, 150, 160, a), anchor="lm")
    d.rounded_rectangle((tx0, ty[1] - 22 * u, tx1, ty[1] + 22 * u), int(8 * u), fill=_mix(_rgb(col["accent"]), (40, 90, 230), 0.6) + (a,))
    d.text((tx0 + 14 * u, ty[1]), spec.get("main", "Talking head"), font=_font(18 * u, 700), fill=(255, 255, 255, a), anchor="lm")
    grow = _ease(_seg(lt, 0.3, 0.6))
    if grow > 0:
        bx0 = tx0 + (tx1 - tx0) * b0
        bx1 = bx0 + (tx1 - tx0) * (b1 - b0) * grow
        d.rounded_rectangle((bx0, ty[0] - 22 * u, bx1, ty[0] + 22 * u), int(8 * u), fill=_rgb(col["pop"], a))
        d.text((bx0 + 14 * u, ty[0]), "B-roll", font=_font(18 * u, 700), fill=(255, 255, 255, a), anchor="lm")
    hx = tx0 + (tx1 - tx0) * play
    d.line((hx, ty[0] - 40 * u, hx, ty[1] + 30 * u), fill=(255, 255, 255, a), width=max(2, int(3 * u)))
    d.line((px, fy - 8 * u, px, fy + 44 * u), fill=(255, 255, 255, a), width=max(2, int(3 * u)))
    shot = frame
    if br_on and spec.get("image"):
        from .motiongfx import _photo
        try:
            shot = ctx.store(("broll", spec["image"]), lambda: _photo(spec["image"]).convert("RGBA"))
        except Exception:
            shot = frame
    rect = _lerp_rect((0, 0, W, H), tile, k_in) if k_out == 0 else _lerp_rect(tile, (0, 0, W, H), k_out)
    _place_rect(out, shot, rect, radius=10 * u * k_in * (1 - k_out), shadow=0.25)
    return out


# ---------------------------------------------------------------- 11 paper cutout
def fx_paper_cutout(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    out = Image.new("RGBA", (W, H), _rgb(spec.get("color", col["pop"])))
    sh = Image.new("RGBA", (W, H))
    fg = Image.new("RGBA", (W, H))
    ds, df = ImageDraw.Draw(sh), ImageDraw.Draw(fg)
    k = _back(_seg(lt, 0, 0.35))
    wob = lambda i: (math.sin(lt * 1.6 + i) * 8 * u, math.cos(lt * 1.3 + i) * 8 * u)
    accent = _mix(_rgb(col["accent"]), (40, 80, 230), 0.5) + (255,)
    shapes = [("circle", W * 0.82, H * 0.27, W * 0.15, accent), ("star", W * 0.12, H * 0.31, W * 0.07, (20, 20, 22, 255)),
              ("circle", W * 0.06, H * 0.5, W * 0.018, accent), ("circle", W * 0.9, H * 0.53, W * 0.025, (255, 255, 255, 255))]
    for i, (kind, x, y, r, c) in enumerate(shapes):
        ox, oy = wob(i)
        r *= k
        x, y = x + ox, y + oy
        if kind == "circle":
            ds.ellipse((x - r + 8 * u, y - r + 12 * u, x + r + 8 * u, y + r + 12 * u), fill=(0, 0, 0, 70))
            df.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            pts = [(x + r * (1 if j % 2 == 0 else 0.42) * math.cos(-math.pi / 2 + j * math.pi / 5),
                    y + r * (1 if j % 2 == 0 else 0.42) * math.sin(-math.pi / 2 + j * math.pi / 5)) for j in range(10)]
            ds.polygon([(a + 8 * u, b + 12 * u) for a, b in pts], fill=(0, 0, 0, 70))
            df.polygon(pts, fill=c)
    for (x0, y0, x1, y1, c) in ((W * 0.5, H * 0.64, W * 1.2, H * 0.55, (20, 20, 22, 255)),
                                (-W * 0.2, H * 0.7, W * 0.42, H * 0.61, (255, 255, 255, 255))):
        xm = x0 + (x1 - x0) * k
        ym = y0 + (y1 - y0) * k
        ds.line((x0 + 8 * u, y0 + 12 * u, xm + 8 * u, ym + 12 * u), fill=(0, 0, 0, 70), width=int(52 * u))
        df.line((x0, y0, xm, ym), fill=c, width=int(52 * u))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6 * u)))
    out.alpha_composite(fg)
    rim = _dilate(m, 18 * u)
    white = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    white.putalpha(rim)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shadow.putalpha(rim.point(lambda v: int(v * 0.35)).filter(ImageFilter.GaussianBlur(14 * u)))
    out.alpha_composite(shadow, (int(10 * u), int(16 * u)))
    out.alpha_composite(white)
    out.alpha_composite(person(frame, m))
    return out


# ---------------------------------------------------------------- 12 dolly zoom
def fx_dolly_zoom(frame, p, lt, dur, spec, ctx, t):
    W, H = ctx.W, ctx.H
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    k = 1 - spec.get("amount", 0.24) * _ease(p)
    under = frame.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
    under = Image.blend(under, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.55)
    bg = _scale_about(frame, k, hx, hy + r * 1.5, fill=(0, 0, 0, 0))
    under.alpha_composite(bg)
    edge = Image.new("RGBA", (W, H))
    x0, y0 = hx + (0 - hx) * k, hy + r * 1.5 + (0 - hy - r * 1.5) * k
    x1, y1 = hx + (W - hx) * k, hy + r * 1.5 + (H - hy - r * 1.5) * k
    ImageDraw.Draw(edge).rectangle((x0, y0, x1, y1), outline=(0, 0, 0, 80), width=max(2, int(6 * ctx.u)))
    under.alpha_composite(edge.filter(ImageFilter.GaussianBlur(6 * ctx.u)))
    under.alpha_composite(person(frame, m))
    return under


# ---------------------------------------------------------------- 13 magazine cover
def _fit_font(text, maxw, px, weight=900):
    f = _font(px, weight)
    while f.getlength(text) > maxw and px > 20:
        px *= 0.95
        f = _font(px, weight)
    return f


def fx_magazine_cover(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    m = ctx.mask(frame, t)
    ink, pop = _rgb(col["ink"]), _rgb(col["pop"])
    paper = _mix(_rgb(col.get("paper", "#F5EFE6")), (240, 232, 218), 0.35) + (255,)
    title = spec.get("title") or (ctx.pack.get("name") or "THE EDIT").upper()

    def back_layer():
        im = Image.new("RGBA", (W, H), paper)
        d = ImageDraw.Draw(im)
        f = _fit_font(title, W * 0.93, 190 * u)
        d.text((W / 2, H * 0.205), title, font=f, fill=pop, anchor="ms")
        fi = _font(15 * u, 800)
        d.text((W * 0.035, H * 0.125), spec.get("issue", "THE AI EDIT ISSUE"), font=fi, fill=ink, anchor="ls")
        d.text((W * 0.965, H * 0.125), spec.get("date", "NO. 01 · " + date.today().strftime("%b %Y").upper()), font=fi, fill=ink, anchor="rs")
        return im
    out = ctx.store(("mag", title), back_layer).copy()
    out.alpha_composite(person(frame, m))
    d = ImageDraw.Draw(out)
    a1 = _ease(_seg(lt, 0.15, 0.4))
    if a1:
        d.text((W * 0.04, H * 0.25), "COVER STORY", font=_font(17 * u, 800), fill=pop[:3] + (int(255 * a1),), anchor="ls")
        d.text((W * 0.035, H * 0.33), spec.get("big", "20"), font=_font(140 * u, 900), fill=pop[:3] + (int(255 * a1),), anchor="ls")
        for i, ln in enumerate(spec.get("story", ["One prompt.", "Full edit."])):
            d.text((W * 0.04, H * 0.355 + i * 26 * u), ln, font=_font(21 * u, 600), fill=ink[:3] + (int(255 * a1),), anchor="ls")
    a2 = _ease(_seg(lt, 0.35, 0.6))
    if a2:
        d.text((W * 0.96, H * 0.28), "INSIDE", font=_font(17 * u, 800), fill=pop[:3] + (int(255 * a2),), anchor="rs")
        for i, ln in enumerate(spec.get("inside", ["CLAUDE", "EDITS", "VIDEO"])):
            d.text((W * 0.96, H * 0.315 + i * 40 * u), ln, font=_font(40 * u, 900), fill=ink[:3] + (int(255 * a2),), anchor="rs")
        for i, ln in enumerate(spec.get("inside_sub", ["Every word,", "captioned."])):
            d.text((W * 0.96, H * 0.4 + i * 24 * u), ln, font=_font(19 * u, 500), fill=ink[:3] + (int(220 * a2),), anchor="rs")
    a3 = _ease(_seg(lt, 0.5, 0.7))
    if a3:                                              # barcode
        bx, by, bw, bh = W * 0.04, H * 0.84, W * 0.16, H * 0.045
        d.rectangle((bx, by, bx + bw, by + bh), fill=(255, 255, 255, int(255 * a3)))
        rnd = random.Random(3)
        x = bx + 8 * u
        while x < bx + bw - 8 * u:
            wdt = rnd.choice((1, 1, 2, 3)) * u * 2
            d.rectangle((x, by + 6 * u, x + wdt, by + bh - 18 * u), fill=(0, 0, 0, int(255 * a3)))
            x += wdt + rnd.choice((2, 3, 4)) * u
        d.text((bx + bw / 2, by + bh - 4 * u), "9 780000 000126", font=_font(11 * u, 600), fill=(0, 0, 0, int(255 * a3)), anchor="ms")
    k4 = _back(_seg(lt, 0.62, 0.95))
    if k4 > 0:                                          # round badge
        R = int(80 * u)
        b = Image.new("RGBA", (2 * R, 2 * R))
        db = ImageDraw.Draw(b)
        db.ellipse((0, 0, 2 * R - 1, 2 * R - 1), fill=pop)
        lines = spec.get("badge", ["20", "EFFECTS", "INSIDE"])
        db.text((R, R * 0.78), lines[0], font=_font(56 * u, 900), fill=(255, 255, 255, 255), anchor="mm")
        for i, ln in enumerate(lines[1:]):
            db.text((R, R * 1.25 + i * 20 * u), ln, font=_font(16 * u, 800), fill=(255, 255, 255, 255), anchor="mm")
        _paste_center(out, _shadow(b, int(10 * u), 0.3, int(5 * u)), W * 0.85, H * 0.84, k4, rot=12)
    return out


# ---------------------------------------------------------------- 14 liquid glass
def _bilinear(arr, sx, sy):
    h, w = arr.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    a = arr[y0, x0] * (1 - fx) + arr[y0, x0 + 1] * fx
    b = arr[y0 + 1, x0] * (1 - fx) + arr[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def fx_liquid_glass(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    q = _ease(p) if p < 1 else 1
    R = W * spec.get("size", 0.17)
    cx = hx - W * 0.33 + W * 0.62 * (0.5 - 0.5 * math.cos(math.pi * p))
    cy = hy + r * 0.25 + math.sin(lt * 3) * 18 * u
    appear = _ease(_seg(lt, 0, 0.2)) * (1 - _ease(_seg(lt, dur - 0.2, dur)))
    if appear <= 0:
        return frame
    arr = np.asarray(frame.convert("RGB"), np.float32)
    x0, x1 = int(max(0, cx - R * 1.2)), int(min(W, cx + R * 1.2))
    y0, y1 = int(max(0, cy - R * 1.2)), int(min(H, cy + R * 1.2))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return frame
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    th = np.arctan2(dy, dx)
    Rr = R * appear * (1 + 0.06 * np.sin(3 * th + lt * 5) + 0.03 * np.sin(5 * th - lt * 3))
    d = np.sqrt(dx * dx + dy * dy) / Rr
    inside = d < 1
    mag = 0.62 + 0.38 * d ** 2
    edge = np.clip((d - 0.82) / 0.18, 0, 1)
    mag = mag + 0.25 * edge ** 2
    out = arr.copy()
    patch = out[y0:y1, x0:x1]
    sx, sy = cx + dx * mag, cy + dy * mag
    samp = _bilinear(arr, sx, sy)
    red = _bilinear(arr, cx + dx * mag * 1.012, cy + dy * mag * 1.012)[..., 0]
    blue = _bilinear(arr, cx + dx * mag * 0.988, cy + dy * mag * 0.988)[..., 2]
    samp[..., 0] = samp[..., 0] * (1 - edge) + red * edge
    samp[..., 2] = samp[..., 2] * (1 - edge) + blue * edge
    hl = np.clip(1 - np.abs(d - 0.9) / 0.07, 0, 1) * np.clip(np.cos(th + 2.3), 0, 1) * 0.75
    sh = np.clip(1 - np.abs(d - 0.95) / 0.05, 0, 1) * np.clip(np.cos(th - 0.8), 0, 1) * 0.25
    samp = samp * 1.04 + (255 - samp) * hl[..., None] - samp * sh[..., None]
    soft = np.clip((1 - d) / 0.03, 0, 1)[..., None]
    patch[:] = np.where(inside[..., None], patch * (1 - soft) + samp * soft, patch)
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return res


# ---------------------------------------------------------------- 15 zoom through cut
def fx_zoom_through(frame, p, lt, dur, spec, ctx, t):
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    cx, cy = hx, hy + r * 0.2
    if p < 0.45:
        q = p / 0.45
        k, blur, light = 1 + 1.4 * q ** 2, 0.18 * q, 0.45 * q ** 2
    else:
        q = (p - 0.45) / 0.55
        k, blur, light = 1.8 - 0.8 * _ease(q), 0.16 * (1 - q), 0.45 * (1 - _ease(q))
    out = _zoom_blur(frame, k, cx, cy, blur)
    if light > 0.01:
        out = Image.blend(out, Image.new("RGBA", out.size, (255, 255, 255, 255)), light)
    return out


# ---------------------------------------------------------------- 16 green screen
def _chroma(ctx):
    def make():
        W, H = ctx.W, ctx.H
        x = np.linspace(0, 1, W)
        fold = 0.86 + 0.08 * np.sin(x * 38) + 0.05 * np.sin(x * 11 + 1.3)
        y = np.linspace(0, 1, H)[:, None]
        vig = 1 - 0.25 * ((x[None, :] - 0.5) ** 2 * 2.5 + (y - 0.45) ** 2 * 1.6)
        g = (fold[None, :] * vig)[..., None] * np.array([18, 178, 62], np.float32)[None, None, :]
        return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return ctx.store("chroma", make)


def _city(ctx, seed=4):
    def make():
        W, H, u = ctx.W, ctx.H, ctx.u
        sky = _gradient(W, int(H * 0.62), (22, 40, 140), (225, 92, 60))
        bg = Image.new("RGBA", (W, H), (10, 10, 14, 255))
        bg.alpha_composite(sky)
        d = ImageDraw.Draw(bg)
        rnd = random.Random(seed)
        x = -20 * u
        while x < W:
            w = rnd.uniform(70, 150) * u
            top = H * rnd.uniform(0.42, 0.56)
            d.rectangle((x, top, x + w, H), fill=(8, 8, 12, 255))
            for wy in np.arange(top + 18 * u, H, 30 * u):
                for wx in np.arange(x + 12 * u, x + w - 12 * u, 26 * u):
                    if rnd.random() < 0.18:
                        d.rectangle((wx, wy, wx + 8 * u, wy + 10 * u), fill=_mix((255, 190, 90), (255, 120, 60), rnd.random()) + (255,))
            x += w + rnd.uniform(0, 10) * u
        for tx in (W * 0.62, W * 0.22):
            d.rectangle((tx - 18 * u, H * 0.3, tx + 18 * u, H * 0.5), fill=(8, 8, 12, 255))
            d.line((tx, H * 0.2, tx, H * 0.3), fill=(8, 8, 12, 255), width=int(6 * u))
            d.polygon([(tx - 40 * u, H * 0.33), (tx + 40 * u, H * 0.33), (tx, H * 0.29)], fill=(8, 8, 12, 255))
        return bg
    return ctx.store(("city", seed), make)


def fx_green_screen(frame, p, lt, dur, spec, ctx, t):
    W, H = ctx.W, ctx.H
    m = ctx.mask(frame, t)
    if spec.get("image"):
        from .motiongfx import _photo
        scene = ctx.store(("gsimg", spec["image"]), lambda: ImageOps.fit(_photo(spec["image"]).convert("RGBA"), (W, H)))
    else:
        scene = _city(ctx)
    out = _chroma(ctx).copy()
    q = _ease(_seg(p, 0.45, 0.62))
    if q > 0:
        mk = Image.new("L", (W, H), 0)
        R = q * H * 1.3
        ImageDraw.Draw(mk).ellipse((W * 0.1 - R, -R, W * 0.1 + R, R), fill=255)
        out.paste(scene, (0, 0), mk.filter(ImageFilter.GaussianBlur(10 * ctx.u)))
    out.alpha_composite(person(frame, m))
    return out


# ---------------------------------------------------------------- 17 frame break
def _frozen_look(ctx, sc, t0):
    """The picture as it looked just before this effect (the previous effect included), frozen."""
    f = ctx.frame_at(max(t0 - 1.0 / ctx.fps, 0))
    if f is None:
        return None
    look = f
    for o in ctx.scenes:
        if o is sc or o["fx"] in OVERLAYS or not (o["start"] <= t0 - 0.02 < o["end"]):
            continue
        e = EFFECTS.get(o["fx"])
        if e:
            dur = o["end"] - o["start"]
            lt = t0 - 0.02 - o["start"]
            sub = Ctx(ctx.W, ctx.H, ctx.pack, ctx.base, ctx.fps, ctx.scenes)
            sub.mask = lambda fr, tt, live=True, _c=ctx: _c.mask(fr, tt, live=False)
            look = e(look, lt / dur, lt, dur, o.get("spec", {}), sub, t0 - 0.02)
    return look


def fx_frame_break(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    sc = ctx._current
    look = ctx.store(("frozen", sc["start"]), lambda: _frozen_look(ctx, sc, sc["start"]))
    if look is None:
        return frame
    ix, iy = [v * s for v, s in zip(spec.get("at", [0.68, 0.36]), (W, H))]
    rnd = random.Random(11)
    rays = 13
    angs = sorted(2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / rays for i in range(rays))
    rings = [0.05, 0.13, 0.25, 0.42, 0.7, 1.5]
    pts = [[(ix + H * rr * (1 + rnd.uniform(-0.12, 0.12)) * math.cos(a), iy + H * rr * (1 + rnd.uniform(-0.12, 0.12)) * math.sin(a))
            for rr in rings] for a in angs]
    crack = _seg(p, 0, 0.2)
    fly = _seg(p, 0.2, 0.85)
    if fly <= 0:
        out = look.copy()
        d = ImageDraw.Draw(out)
        lw = max(2, int(3 * u))
        for i in range(rays):
            n = 1 + int(crack * (len(rings) - 1) + 0.5)
            line = [(ix, iy)] + pts[i][:n]
            d.line(line, fill=(255, 255, 255, 230), width=lw)
        for j in range(min(len(rings) - 1, int(crack * 5))):
            for i in range(rays):
                if (i + j) % 2 == 0:
                    d.line((pts[i][j], pts[(i + 1) % rays][j]), fill=(255, 255, 255, 200), width=max(1, lw - 1))
        return out

    def shards():
        out = []
        for i in range(rays):
            for j in range(len(rings) - 1):
                inner_a = pts[i][j - 1] if j else (ix, iy)
                inner_b = pts[(i + 1) % rays][j - 1] if j else (ix, iy)
                poly = [inner_a, pts[i][j], pts[(i + 1) % rays][j], inner_b]
                xs, ys = [q[0] for q in poly], [q[1] for q in poly]
                bx0, by0, bx1, by1 = int(max(min(xs), 0)), int(max(min(ys), 0)), int(min(max(xs), W)), int(min(max(ys), H))
                if bx1 - bx0 < 3 or by1 - by0 < 3:
                    continue
                crop = look.crop((bx0, by0, bx1, by1))
                mk = Image.new("L", crop.size, 0)
                dm = ImageDraw.Draw(mk)
                rel = [(x - bx0, y - by0) for x, y in poly]
                dm.polygon(rel, fill=255)
                crop.putalpha(mk)
                ImageDraw.Draw(crop).line(rel + [rel[0]], fill=(255, 255, 255, 200), width=max(1, int(2 * u)))
                cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                ang = math.atan2(cy - iy, cx - ix)
                out.append((crop, cx, cy, ang, j, rnd.uniform(0.7, 1.3), rnd.uniform(-160, 160)))
        return out
    out = frame.copy()
    for crop, cx, cy, ang, j, sp, rot in ctx.store(("shards", sc["start"]), shards):
        q = _seg(fly, j * 0.08, 1)
        if q >= 1:
            continue
        dist = (q ** 1.6) * H * 0.9 * sp
        x = cx + math.cos(ang) * dist
        y = cy + math.sin(ang) * dist + 900 * u * q * q
        _paste_center(out, crop, x, y, 1 + 0.25 * q, 1 - q ** 3, rot * q)
    return out


# ---------------------------------------------------------------- 18 digital zoom
def fx_digital_zoom(frame, p, lt, dur, spec, ctx, t):
    W, H, u = ctx.W, ctx.H, ctx.u
    m = ctx.mask(frame, t)
    hx, hy, r = ctx.head(m)
    steps = spec.get("steps") or [[0.08, 1.6], [0.42, 2.6], [0.78, 1.0]]
    k, prev, blur = 1.0, 1.0, 0.0
    for st, z in steps:
        s0 = st * dur
        if lt >= s0:
            q = _ease(_seg(lt, s0, s0 + 0.12))
            k = prev + (z - prev) * q
            blur = max(blur, 26 * u * max(0.0, 1 - (lt - s0) / 0.35))
            prev = z
    out = _scale_about(frame, k, hx, hy + r * 0.3)
    if blur > 0.5:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    d = ImageDraw.Draw(out)
    lw, L = max(2, int(4 * u)), 50 * u
    x0, y0, x1, y1 = W * 0.05, H * 0.19, W * 0.95, H * 0.9
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=(255, 255, 255, 230), width=lw)
        d.line((x, y, x, y + sy * L), fill=(255, 255, 255, 230), width=lw)
    f = _font(20 * u, 700)
    if int(lt * 2) % 2 == 0:
        d.ellipse((x0 + 16 * u, y0 + 22 * u, x0 + 32 * u, y0 + 38 * u), fill=(235, 50, 40, 255))
    d.text((x0 + 42 * u, y0 + 30 * u), "REC", font=f, fill=(255, 255, 255, 240), anchor="lm")
    fr = int(t * ctx.fps) % ctx.fps
    d.text((x1 - 16 * u, y0 + 30 * u), f"00:42:{int(t) % 60:02d}:{fr:02d}", font=_font(18 * u, 600), fill=(255, 255, 255, 220), anchor="rm")
    zt = f"{k:.1f}×"
    pw = f.getlength(zt) + 34 * u
    d.rounded_rectangle((W / 2 - pw / 2, y0 + 12 * u, W / 2 + pw / 2, y0 + 48 * u), int(18 * u), fill=(0, 0, 0, 110))
    d.text((W / 2, y0 + 30 * u), zt, font=f, fill=(255, 210, 60, 255), anchor="mm")
    return out


# ---------------------------------------------------------------- 19 phone mockup
def fx_phone_mockup(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    pw = W * 0.5
    ph = pw * 2.08
    cx, cy = W / 2, H * 0.56
    body = (cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2)
    bz = 14 * u
    screen = (body[0] + bz, body[1] + bz, body[2] - bz, body[3] - bz)
    k_in, k_out = _ease(_seg(lt, 0, 0.4)), _ease(_seg(lt, dur - 0.25, dur))
    out = dark_bg(ctx)
    a = k_in * (1 - k_out)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle(body, int(64 * u), fill=(14, 14, 16, int(255 * a)), outline=(90, 90, 96, int(255 * a)), width=max(2, int(3 * u)))
    rect = _lerp_rect((0, 0, W, H), screen, k_in) if k_out == 0 else _lerp_rect(screen, (0, 0, W, H), k_out)
    _place_rect(out, frame, rect, radius=52 * u * k_in * (1 - k_out), shadow=0.2)
    if a > 0.05:
        d = ImageDraw.Draw(out)
        al = int(255 * a)
        d.rounded_rectangle((cx - 52 * u, screen[1] + 16 * u, cx + 52 * u, screen[1] + 46 * u), int(15 * u), fill=(0, 0, 0, al))
        d.text((screen[0] + 26 * u, screen[1] + 78 * u), "Reels", font=_font(24 * u, 800), fill=(255, 255, 255, al), anchor="lm")
        by = screen[3] - 70 * u
        d.ellipse((screen[0] + 22 * u, by - 20 * u, screen[0] + 62 * u, by + 20 * u), fill=_rgb(col["pop"], al), outline=(255, 255, 255, al), width=2)
        d.text((screen[0] + 74 * u, by), spec.get("handle", "@yourbrand"), font=_font(20 * u, 700), fill=(255, 255, 255, al), anchor="lm")
        ix = screen[2] - 40 * u
        for i in range(3):
            iy = screen[3] - 330 * u + i * 86 * u
            if i == 0:
                d.polygon([(ix, iy + 16 * u), (ix - 18 * u, iy - 2 * u), (ix - 10 * u, iy - 14 * u), (ix, iy - 6 * u),
                           (ix + 10 * u, iy - 14 * u), (ix + 18 * u, iy - 2 * u)], fill=(255, 255, 255, al))
            elif i == 1:
                d.ellipse((ix - 17 * u, iy - 15 * u, ix + 17 * u, iy + 15 * u), outline=(255, 255, 255, al), width=max(2, int(4 * u)))
            else:
                d.polygon([(ix - 16 * u, iy - 4 * u), (ix + 18 * u, iy - 16 * u), (ix + 4 * u, iy + 18 * u)], outline=(255, 255, 255, al), width=max(2, int(4 * u)))
    return out


# ---------------------------------------------------------------- 20 recap checklist
def fx_recap(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    items = spec.get("items") or [LABELS[k] for k in LABELS]
    out = dark_bg(ctx)
    d = ImageDraw.Draw(out)
    done = int(min(len(items), (len(items) + 1) * _seg(p, 0.05, 0.8)))
    fb = _font(130 * u, 900)
    num = str(done)
    d.text((W * 0.06, H * 0.27), num, font=fb, fill=_rgb(col["pop"]), anchor="ls")
    nx = W * 0.06 + fb.getlength(num) + 16 * u
    d.text((nx, H * 0.248), spec.get("title", f"/ {len(items)} effects."), font=_font(34 * u, 800), fill=(255, 255, 255, 255), anchor="ls")
    d.text((nx, H * 0.27), spec.get("sub", "All made by Claude."), font=_font(30 * u, 700), fill=(255, 255, 255, 230), anchor="ls")
    half = (len(items) + 1) // 2
    f = _font(25 * u, 600)
    for i, s in enumerate(items):
        x = W * (0.07 if i < half else 0.53)
        y = H * 0.33 + (i % half) * 58 * u
        on = i < done
        if on:
            d.rounded_rectangle((x, y - 15 * u, x + 30 * u, y + 15 * u), int(6 * u), fill=_rgb(col["pop"]))
            d.line([(x + 7 * u, y), (x + 13 * u, y + 7 * u), (x + 24 * u, y - 8 * u)], fill=(255, 255, 255, 255), width=max(2, int(4 * u)))
        else:
            d.rounded_rectangle((x, y - 15 * u, x + 30 * u, y + 15 * u), int(6 * u), outline=(120, 120, 130, 160), width=2)
        d.text((x + 44 * u, y), s, font=f, fill=(255, 255, 255, 255 if on else 110), anchor="lm")
    return out


# ---------------------------------------------------------------- overlays: series header, tag wall
def fx_series(frame, p, lt, dur, spec, ctx, t):
    """Top title + "04 Snap Zoom" chip + progress dashes. spec: title, steps [[reel_time, label], ...], total."""
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    steps = sorted(spec.get("steps") or [], key=lambda s: s[0])
    cur = [i for i, s in enumerate(steps) if s[0] <= t]
    idx = cur[-1] if cur else -1
    big = 1 - _ease(_seg(t, steps[0][0] - 0.3, steps[0][0])) if steps else 0
    out = frame.copy()
    lines = spec.get("title", "20 Video Effects\nCreated by Claude").split("\n")
    px = (30 + 34 * big) * u
    f = _font(px, 800)
    w = max(f.getlength(x) for x in lines) + px * 0.9
    h = len(lines) * px * 1.12 + px * 0.5
    cy = H * (0.085 + 0.04 * big)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((W / 2 - w / 2, cy - h / 2, W / 2 + w / 2, cy + h / 2), int(px * 0.3), fill=(255, 255, 255, 245))
    for i, ln in enumerate(lines):
        d.text((W / 2, cy - h / 2 + px * 0.25 + i * px * 1.12 + px * 0.56), ln, font=f, fill=_rgb(col["ink"]), anchor="mm")
    if idx >= 0 and big < 1:
        label = steps[idx][1]
        k = _back(_seg(t, steps[idx][0], steps[idx][0] + 0.3))
        fl, fn = _font(30 * u, 800), _font(26 * u, 900)
        num = f"{idx + 1:02d}"
        lw = fl.getlength(label) + 34 * u
        nw = 52 * u
        chip = Image.new("RGBA", (int(nw + 8 * u + lw), int(52 * u)))
        dc = ImageDraw.Draw(chip)
        dc.rounded_rectangle((0, 0, nw, 52 * u - 1), int(10 * u), fill=_rgb(col["pop"]))
        dc.text((nw / 2, 26 * u), num, font=fn, fill=(255, 255, 255, 255), anchor="mm")
        dc.rounded_rectangle((nw + 8 * u, 0, chip.width - 1, 52 * u - 1), int(10 * u), fill=(255, 255, 255, 250))
        dc.text((nw + 8 * u + lw / 2, 26 * u), label, font=fl, fill=_rgb(col["ink"]), anchor="mm")
        _paste_center(out, chip, W / 2, cy + h / 2 + 40 * u, 0.8 + 0.2 * k, min(1, k + 0.2))
        n = spec.get("total", len(steps))
        dw, gap = W * 0.62 / n, 6 * u
        x0, yb = W / 2 - W * 0.31, cy + h / 2 + 80 * u
        d = ImageDraw.Draw(out)
        for i in range(n):
            d.rounded_rectangle((x0 + i * dw, yb, x0 + (i + 1) * dw - gap, yb + 5 * u), int(2 * u),
                                fill=_rgb(col["pop"]) if i <= idx else (255, 255, 255, 110))
    return out


def fx_tag_wall(frame, p, lt, dur, spec, ctx, t):
    W, H, u, col = ctx.W, ctx.H, ctx.u, ctx.col
    items = spec.get("items") or [LABELS[k] for k in LABELS]
    half = (len(items) + 1) // 2
    out = frame.copy()
    f = _font(22 * u, 700)
    hot = int(lt * 6) % len(items)
    fade = 1 - _ease(_seg(lt, dur - 0.25, dur))
    for i, s in enumerate(items):
        k = _back(_seg(lt, 0.03 * i, 0.03 * i + 0.25)) * fade
        if k <= 0:
            continue
        left = i < half
        y = H * 0.33 + (i % half) * 46 * u
        w = f.getlength(s) + 26 * u
        tag = Image.new("RGBA", (int(w), int(36 * u)))
        dt = ImageDraw.Draw(tag)
        dt.rounded_rectangle((0, 0, tag.width - 1, tag.height - 1), int(8 * u), fill=_rgb(col["pop"]) if i == hot else (18, 18, 22, 225))
        dt.text((w / 2, 18 * u), s, font=f, fill=(255, 255, 255, 255), anchor="mm")
        x = 30 * u + w / 2 if left else W - 30 * u - w / 2
        _paste_center(out, tag, x, y, k)
    return out


EFFECTS = {"orbit": fx_orbit, "chat_takeover": fx_chat_takeover, "frame_escape": fx_frame_escape,
           "snap_zoom": fx_snap_zoom, "checklist_pop": fx_checklist_pop, "headline_storm": fx_headline_storm,
           "zoom_portal": fx_zoom_portal, "growth_curve": fx_growth_curve, "studio_reveal": fx_studio_reveal,
           "broll_overlay": fx_broll_overlay, "paper_cutout": fx_paper_cutout, "dolly_zoom": fx_dolly_zoom,
           "magazine_cover": fx_magazine_cover, "liquid_glass": fx_liquid_glass, "zoom_through": fx_zoom_through,
           "green_screen": fx_green_screen, "frame_break": fx_frame_break, "digital_zoom": fx_digital_zoom,
           "phone_mockup": fx_phone_mockup, "recap": fx_recap, "series": fx_series, "tag_wall": fx_tag_wall}


# ---------------------------------------------------------------- the renderer's entry point
def apply(frame, t, ctx):
    """Run every scene effect on screen at time t (effects first, overlays last)."""
    active = [s for s in ctx.scenes if s["start"] <= t < s["end"] and s["fx"] in EFFECTS]
    if not active:
        return frame
    active.sort(key=lambda s: (s["fx"] in OVERLAYS, s.get("z", 0)))
    for s in active:
        dur = s["end"] - s["start"]
        lt = t - s["start"]
        ctx._current = s
        try:
            frame = EFFECTS[s["fx"]](frame, lt / dur, lt, dur, s.get("spec") or {}, ctx, t)
        except Exception as e:  # one broken effect never breaks the reel
            print(f"[reel] scene effect {s['fx']} skipped at {t:.2f}s: {e}")
    return frame


def needs_person(scenes):
    return any(s["fx"] in PERSON for s in scenes)


def sounds(scene):
    """(reel time, event, gain) for one scene."""
    dur = scene["end"] - scene["start"]
    out = []
    for c in SOUNDS.get(scene["fx"], []):
        at, ev = c[0], c[1]
        g = c[2] if len(c) > 2 else 1.0
        if isinstance(at, str):
            at = float(at[1:]) * dur
        elif at < 0:
            at = dur + at
        if 0 <= at < dur:
            out.append((scene["start"] + at, ev, g))
    if scene["fx"] == "series":
        out = [(s[0], "tick", 0.5) for s in (scene.get("spec") or {}).get("steps", [])]
    return out


def _clip_frames(clip, dur, W, H, at=0.0, fps=30):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{at:.2f}", "-i", clip, "-t", f"{dur:.2f}", "-vf",
                          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps}",
                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True).stdout
    n = W * H * 4
    return [Image.frombuffer("RGBA", (W, H), raw[i:i + n], "raw", "RGBA", 0, 1) for i in range(0, len(raw) - n + 1, n)]


def _run(fx, clip, pack, spec, dur, W, H, at=0.0, keep=None):
    """Play one effect over a clip; keep(i) says which frames to return."""
    frames = _clip_frames(clip, dur, W, H, at)
    if not frames:
        raise RuntimeError("could not read the clip")
    dur = min(dur, len(frames) / 30)
    sc = {"fx": fx, "start": 0.0, "end": dur, "spec": spec or {}}
    if fx == "series":
        sc["spec"] = dict({"steps": [[0.3, "Paper Cutout"], [dur / 2, "Snap Zoom"]], "total": 20}, **sc["spec"])
    ctx = Ctx(W, H, pack, base=None, fps=30, scenes=[sc])
    ctx.frame_at = lambda t: frames[min(int(t * 30), len(frames) - 1)]
    out = []
    for i, fr in enumerate(frames):            # every frame goes through, so time-smoothed things settle
        if fx in PERSON or keep(i, len(frames)):
            res = apply(fr.copy(), i / 30, ctx)
            if keep(i, len(frames)):
                out.append(res.convert("RGB"))
    ctx.close()
    return out


def preview(fx, clip, pack, spec=None, n=6, dur=None, size=(270, 480)):
    """A strip of n frames of one effect on a short clip (for checking looks)."""
    dur = dur or DUR.get(fx, 2.0)
    pick = lambda i, total: i in {int(round(k * (total - 1) / max(n - 1, 1))) for k in range(n)}
    shots = [s.resize(size, Image.LANCZOS) for s in _run(fx, clip, pack, spec, dur, 1080, 1920, keep=pick)]
    strip = Image.new("RGB", (size[0] * len(shots), size[1]))
    for i, s in enumerate(shots):
        strip.paste(s, (i * size[0], 0))
    return strip


def preview_anim(fx, clip, out, pack, spec=None, at=0.0, size=(270, 480), fps=15):
    """A short looping animated WebP of one effect on the person's own footage (Studio cards)."""
    dur = DUR.get(fx, 2.0) + 0.3
    W, H = size[0] * 2, size[1] * 2                # drawn at half size: fast, still sharp on a card
    shots = _run(fx, clip, pack, spec, dur, W, H, at, keep=lambda i, total: i % (30 // fps) == 0)
    shots = [s.resize(size, Image.LANCZOS) for s in shots]
    shots[0].save(out, save_all=True, append_images=shots[1:], duration=int(1000 / fps), loop=0, quality=72)
    return out
