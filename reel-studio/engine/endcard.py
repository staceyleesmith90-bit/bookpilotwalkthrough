"""Intro + outro: no reel should start or stop abruptly.

  intro   fade in from black (0.35 s), a gentle zoom-out and a soft whoosh (planned in plan.py)
  outro   picture and sound fade out, then a brand end screen: logo, brand name, @handle and the
          call to action in the brand colours, with a soft chime (2.6 s)
Timeline key "end_card": {"title", "handle", "cta", "enabled"}; defaults come from the brand.
"""
import os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ease(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def card_frames(pack, spec, W=1080, H=1920, fps=30, dur=2.6):
    from .textfit import load_font
    from .titles import fonts_for
    c = pack["colors"]
    bg = Image.new("RGBA", (W, H), c.get("bg", "#FFFFFF"))
    # soft brand-colour glow behind the logo
    glow = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W * 0.1, H * 0.22, W * 0.9, H * 0.62), fill=c.get("pop", "#1E63FF") + "33")
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    logo = None
    lf = pack.get("logo", {}).get("file") if isinstance(pack.get("logo"), dict) else None
    if lf and os.path.exists(os.path.join(ROOT, lf)):
        logo = Image.open(os.path.join(ROOT, lf)).convert("RGBA")
        logo.thumbnail((int(W * 0.42), int(H * 0.16)))
    ink = c.get("ink", "#111111")
    tf = fonts_for(pack)
    title_font = load_font(pack["fonts"]["main"]["file"], 84, pack["fonts"]["main"].get("weight"))
    script = tf.get("brush") or tf["script"]
    cta_font = load_font(script["file"], 70, script.get("weight"))
    small = load_font(pack["fonts"].get("caption", pack["fonts"]["main"])["file"], 44, 600)
    title = spec.get("title") or pack.get("label") or ""
    handle = spec.get("handle") or pack.get("handle") or ""
    cta = spec.get("cta") or "Follow for more"
    n = int(dur * fps)
    for i in range(n):
        t = i / fps
        fr = bg.copy()
        d = ImageDraw.Draw(fr)
        y = H * 0.36
        if logo is not None:
            s = 0.8 + 0.2 * _ease(t / 0.45)
            lg = logo.resize((max(1, int(logo.width * s)), max(1, int(logo.height * s))))
            a = int(255 * _ease(t / 0.3))
            lg.putalpha(lg.split()[3].point(lambda v: v * a // 255))
            fr.alpha_composite(lg, (int(W / 2 - lg.width / 2), int(y - lg.height / 2)))
            y += logo.height / 2 + 90
        for k, (txt, font, col, t0) in enumerate(((title, title_font, ink, 0.25), (cta, cta_font, c.get("pop", ink), 0.5),
                                                  (handle, small, ink, 0.75))):
            if not txt:
                continue
            p = _ease((t - t0) / 0.4)
            if p <= 0:
                y += font.size * 1.25
                continue
            r, g, b = [int(col[j:j + 2], 16) for j in (1, 3, 5)]
            d.text((W / 2, y + (1 - p) * 30), txt, font=font, fill=(r, g, b, int(255 * p)), anchor="mm")
            y += font.size * 1.25
        # fade in from the reel's last frame colour (black) during the first 0.25 s
        if t < 0.25:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.25))))
            fr.alpha_composite(ov)
        yield fr


def make_card(pack, spec, out, W=1080, H=1920, fps=30, dur=2.6, kit="clean"):
    from . import sfx, sounddesign
    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "card.wav")
    cues = [sounddesign.cue("reveal", 0.2, 7, kit, 0.45), sounddesign.cue("cta", 0.55, 8, kit, 0.35)]
    x = sfx.mix_cues(cues, dur)
    sfx.write_wav(wav, x * 0.5, peak=None)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", out],
                           stdin=subprocess.PIPE)
    for fr in card_frames(pack, spec, W, H, fps, dur):
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


def finish(main, out, pack, spec, kit="clean", speed=1.0):
    """Fade the reel in/out, optional speed-up, then append the brand end screen."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", main],
                               capture_output=True, text=True).stdout.strip())
    tmp = tempfile.mkdtemp()
    parts = []
    vf = f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(dur / speed - 0.45, 0):.2f}:d=0.45"
    af = f"afade=t=in:st=0:d=0.15,afade=t=out:st={max(dur / speed - 0.9, 0):.2f}:d=0.9"
    if speed != 1.0:
        vf = f"setpts=PTS/{speed}," + vf
        af = f"atempo={speed}," + af
    fc = f"[0:v]{vf}[v0];[0:a]{af}[a0]"
    inputs = ["-i", main]
    if spec.get("enabled", True):
        card = make_card(pack, spec, os.path.join(tmp, "card.mp4"), kit=kit)
        inputs += ["-i", card]
        fc += ";[v0][a0][1:v][1:a]concat=n=2:v=1:a=1[v][a]"
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        maps = ["-map", "[v0]", "-map", "[a0]"]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + inputs + ["-filter_complex", fc] + maps +
                   ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", out], check=True)
    return out
