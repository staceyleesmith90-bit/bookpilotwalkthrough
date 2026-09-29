"""Auto director: watches the footage and plans the camera work, like a CapCut editor would.

Raw phone videos (handheld, unplanned angles, one long take) look amateur because nothing
moves with intent. The director looks at the actual pixels — locally, no Claude credits —
and plans:
  • stabilisation, if the footage is shaky (two-pass vidstab, cached per project)
  • framing: every jump cut alternates wide / punched-in, centred on the speaker's real face
    (so cuts feel deliberate and the face stays in the top third)
  • slow push-ins on shots without a face (product, hands, b-roll)
  • emphasis bumps on the words that matter ("best", "wow", numbers…)
  • transitions only where the angle really changes (a jump cut on the same shot is hidden by
    the zoom change instead — that's what pros do)
Explicit zooms/transitions from the plan always win; the director fills the rest.
"""
import os, subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AW, AH, AFPS = 90, 160, 6          # analysis frame size / rate (tiny = fast)
FRAMING = (1.0, 1.16, 1.06, 1.26)  # jump-cut framing cycle
EMPHASIS = {"best", "wow", "amazing", "love", "never", "always", "strong", "thin", "beautiful", "perfect",
            "free", "new", "secret", "biggest", "worst", "insane", "crazy", "favourite", "favorite",
            "incredible", "every", "only", "first", "must", "stop", "quality", "huge", "super"}


def frames(source, fps=AFPS):
    """Tiny grey frames of the whole video: (times, array[n, AH, AW])."""
    cmd = ["ffmpeg", "-loglevel", "error", "-i", source, "-vf",
           f"fps={fps},scale={AW}:{AH}:force_original_aspect_ratio=increase,crop={AW}:{AH},format=gray",
           "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, AH, AW).astype(np.float32)
    return np.arange(len(arr)) / fps, arr


def _shift(a, b):
    """Global (dx, dy) between two frames by phase correlation."""
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.abs(np.fft.ifft2(r))
    y, x = np.unravel_index(np.argmax(c), c.shape)
    if y > AH // 2:
        y -= AH
    if x > AW // 2:
        x -= AW
    return x, y


def analyse(source):
    """Shakiness (px of jitter in 1080-wide space) and per-frame visual change."""
    t, f = frames(source)
    if len(f) < 3:
        return {"t": t, "frames": f, "jitter": 0.0}
    sh = np.array([_shift(f[i], f[i + 1]) for i in range(len(f) - 1)], np.float32)
    traj = np.cumsum(sh, axis=0)
    k = max(3, AFPS)                                  # ~1s smoothing = the "intended" camera path
    pad = np.pad(traj, ((k, k), (0, 0)), mode="edge")
    smooth = np.stack([np.convolve(pad[:, j], np.ones(2 * k + 1) / (2 * k + 1), "same")[k:-k] for j in (0, 1)], 1)
    jitter = float(np.abs(traj - smooth).mean() * 1080 / AW)
    return {"t": t, "frames": f, "jitter": jitter}


def change_between(info, t_a, t_b):
    """How different the picture is at two source times (0 = same shot, ~1 = new angle)."""
    f, n = info["frames"], len(info["frames"])
    if not n:
        return 0.0
    a = f[min(n - 1, int(round(t_a * AFPS)))]
    b = f[min(n - 1, int(round(t_b * AFPS)))]
    a, b = (a - a.mean()) / (a.std() + 1e-6), (b - b.mean()) / (b.std() + 1e-6)
    return float(max(0.0, 1 - (a * b).mean()) / 2)   # 1 - correlation, scaled to 0..1


def stabilise(source, out):
    """Two-pass vidstab (cached). Returns out, or the source if stabilising isn't available."""
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(source):
        return out
    trf = out + ".trf"
    try:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", source, "-vf",
                        f"vidstabdetect=shakiness=6:accuracy=12:result={trf}", "-f", "null", "-"], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", source, "-vf",
                        f"vidstabtransform=input={trf}:smoothing=18:zoom=4:optzoom=0:interpol=bicubic,unsharp=5:5:0.6",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-c:a", "copy", out], check=True)
        return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return source


def plan_camera(tl, words, head_at, taken_zooms=(), taken_transitions=(), pack_transition="whip",
                info=None, style="auto"):
    """Add framing zooms, emphasis bumps and angle-change transitions to a talking timeline.

    tl: timeline with "cuts" (source ranges) · words: [{w, start, end}] in OUTPUT time ·
    head_at(src_t) -> head box or None · taken_*: explicit zooms/transitions from the plan.
    """
    zooms, transitions, notes = [], [], []
    out_t, segs = 0.0, []
    for a, b in tl["cuts"]:
        segs.append((out_t, out_t + (b - a), a, b))
        out_t += b - a

    def busy(s, e):
        return any(z["start"] < e and s < z["end"] for z in taken_zooms)

    frame_i = 0
    last_tr = -10.0
    for k, (s, e, a, b) in enumerate(segs):
        head = head_at((a + b) / 2)
        if k > 0 and info is not None:
            change = change_between(info, segs[k - 1][3] - 0.1, a + 0.1)
            if change > 0.35 and s - last_tr > 4 and not any(abs(tr["t"] - s) < 0.5 for tr in taken_transitions):
                transitions.append({"t": round(s, 3), "type": pack_transition if k % 2 else "zoom-blur", "dur": 0.32})
                last_tr = s
                frame_i = 0                     # new angle: start wide again
        if busy(s, e) or e - s < 0.5:
            continue
        if head:
            hx = (head[0] + head[2]) / 2
            hh = head[3] - head[1]
            scale = FRAMING[frame_i % len(FRAMING)]
            frame_i += 1
            if scale > 1.01:
                zooms.append({"start": round(s, 3), "end": round(e, 3), "type": "punch", "scale": scale,
                              "cx": round(hx, 1), "cy": round(head[1] + hh * 1.4, 1), "auto": True})
        else:                                   # product / hands / b-roll: slow push in
            zooms.append({"start": round(s, 3), "end": round(e, 3), "type": "push",
                          "scale": 1.12 if e - s < 4 else 1.2, "auto": True})
    # emphasis bumps on words that matter (max one per ~6s)
    last = -10.0
    for w in words:
        key = "".join(ch for ch in w["w"].lower() if ch.isalnum())
        if (key in EMPHASIS or key.isdigit()) and w["start"] - last > 6 and not busy(w["start"], w["start"] + 0.4):
            zooms.append({"start": round(w["start"], 3), "end": round(w["start"] + 0.4, 3), "type": "pulse",
                          "scale": 1.07, "auto": True})
            last = w["start"]
    return zooms, transitions
