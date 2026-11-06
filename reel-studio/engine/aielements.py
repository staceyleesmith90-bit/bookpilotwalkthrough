"""AI elements: custom stickers / props for THIS reel, in one matching style, made by an image generator.

The idea: nobody has to sit in Canva. Claude reads the story, picks 4-8 elements that fit it (a sand bucket,
a splash, a "mom on duty" badge…), and ONE generation draws them all on one sheet in the reel's colours and
a chosen style, so they belong together. The studio then cuts the sheet into separate transparent stickers
(projects/<p>/elements/<name>.png) that plans use as {"image": "..."} stickers.

Generators are plug-ins (brand/ai.json → {"provider": "...", ...}; keys are never stored here — the network
proxy adds them for the host):
  cloudflare    Workers AI, FLUX.1 schnell — free daily allowance with a free account (needs "account_id")
  gemini        Google's Gemini image model — free tier with a free API key ("model" optional)
  huggingface   FLUX.1 schnell on HF inference — small free monthly credits
  reelstudio    Reel Studio's own service (cloud/elements-worker, on the owner's Cloudflare) — customers need nothing
  local         FLUX.1 schnell on this computer via stable-diffusion.cpp (MIT) — free + unlimited, needs ~10 GB
  hfspace       the public FLUX.1 schnell demo (Hugging Face Space) — free with no account from a home connection
                (small daily quota; shared cloud computers get none)
  pollinations  free, no account — low quality + watermark, last resort
  file          made anywhere else (Canva AI, ChatGPT, Higgsfield…): drop the image in elements/inbox/ and run
                `python -m engine elements-cut <p> <image>` — `elements-prompts` writes the exact prompt to paste.

    python -m engine elements <p> --items "sand bucket; splash; baby bottle" [--style clay] [--provider X]
    python -m engine elements-prompts <p> --items "..." [--style ...]     the prompt, for Canva / ChatGPT / anywhere
    python -m engine elements-cut <p> <sheet.png> [--items "..."]       cut a sheet into stickers
"""
import base64, json, os, re, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLES = {
    "paper":      "paper cut-out collage stickers, layered craft paper with visible paper grain, slightly uneven scissor-cut edges",
    "clay":       "cute 3D clay / plasticine figures, soft studio light, matte, rounded and chunky",
    "watercolour": "loose watercolour illustration stickers with soft washes and fine ink outlines",
    "doodle":     "hand-drawn marker doodles, thick wobbly outlines, flat fills, playful",
    "retro":      "retro risograph print stickers, grainy halftone, limited 2-3 ink colours, slight misregistration",
    "realistic":  "photo-realistic product shot of a real object, soft natural shadow, studio light",
    "3d":         "glossy 3D render icons, soft gradients, gentle shadow, like premium app emoji",
}
DEFAULT_STYLE = "paper"


def config():
    p = os.path.join(ROOT, "brand", "ai.json")
    try:
        return json.load(open(p))
    except Exception:
        return {"provider": "hfspace"}           # free, no account — works on the user's own computer


def prompt(items, style=DEFAULT_STYLE, colors=None, story=""):
    """One sheet, every element separate on pure white — the cut-out step depends on that."""
    look = STYLES.get(style, style)
    pal = ""
    if colors:
        pal = " Colour palette: " + ", ".join(c for c in colors if c) + "."
    n = len(items)
    cols = 3 if n > 4 else 2
    return (f"A sticker sheet with exactly {n} separate objects in a neat grid of {cols} columns, read left to right, "
            f"top to bottom: " + ", then ".join(items) + ". Draw exactly these objects and nothing else — no people, "
            f"no extra objects. Each one isolated with lots of empty space around it, nothing touching. "
            f"Style: {look}.{pal} " + (f"Mood: {story}. " if story else "") +
            "Flat pure white background, no drop shadows, no numbers, no letters, no labels, no border, high detail.")


# ---------------------------------------------------------------- generators
def _post(url, body, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=dict({"Content-Type": "application/json"}, **headers))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def generate(text, out, provider=None, size=1024, seed=None):
    """Draw `text` with the configured generator into `out` (PNG). Returns out. Raises with a plain message."""
    cfg = config()
    provider = provider or cfg.get("provider", "hfspace")
    if provider == "cloudflare":
        acc = cfg.get("account_id") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        if not acc:
            raise RuntimeError("Cloudflare needs your account id in brand/ai.json (\"account_id\").")
        model = cfg.get("model", "@cf/black-forest-labs/flux-1-schnell")
        raw, _ = _post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}",
                       {"prompt": text, "steps": 8, **({"seed": seed} if seed is not None else {})}, {})
        img = base64.b64decode(json.loads(raw)["result"]["image"])
    elif provider == "gemini":
        model = cfg.get("model", "gemini-2.5-flash-image")
        raw, _ = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                       {"contents": [{"parts": [{"text": text}]}]}, {})
        parts = json.loads(raw)["candidates"][0]["content"]["parts"]
        img = next(base64.b64decode(p["inlineData"]["data"]) for p in parts if "inlineData" in p)
    elif provider == "huggingface":
        model = cfg.get("model", "black-forest-labs/FLUX.1-schnell")
        img, ct = _post(f"https://router.huggingface.co/hf-inference/models/{model}", {"inputs": text}, {})
        if "json" in ct:
            raise RuntimeError(img.decode()[:300])
    elif provider == "reelstudio":               # Reel Studio's own service (cloud/elements-worker): no account
        url = cfg.get("url", "").rstrip("/")     # needed by the customer, their licence key is enough
        if not url:
            raise RuntimeError("The Reel Studio elements service isn't switched on yet (cloud/elements-worker).")
        req = urllib.request.Request(url + "/v1/elements", data=json.dumps({"prompt": text, "size": size,
                                     **({"seed": seed} if seed is not None else {})}).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + cfg.get("key", "")})
        with urllib.request.urlopen(req, timeout=180) as r:
            img = r.read()
    elif provider == "local":                    # FLUX.1 schnell on this computer (stable-diffusion.cpp, MIT):
        import subprocess                        # free + unlimited; fast on a GPU / Apple Silicon, slow on CPU
        d = cfg.get("models", os.path.join(ROOT, "library", "models", "flux"))
        sd = cfg.get("sd_bin", "sd-cli")
        tmp = out + ".raw.png"
        subprocess.run([sd, "--diffusion-model", os.path.join(d, "flux1-schnell-q4_0.gguf"),
                        "--vae", os.path.join(d, "ae.safetensors"), "--clip_l", os.path.join(d, "clip_l.safetensors"),
                        "--t5xxl", os.path.join(d, "t5-v1_1-xxl-encoder-Q4_K_M.gguf"), "-p", text,
                        "--cfg-scale", "1.0", "--sampling-method", "euler", "--steps", "4",
                        "-W", str(cfg.get("size", 768)), "-H", str(cfg.get("size", 768)),
                        "--seed", str(seed if seed is not None else 42), "-o", tmp], check=True)
        img = open(tmp, "rb").read()
        os.remove(tmp)
    elif provider == "hfspace":                  # the public FLUX.1 schnell demo: free, no account on a home
        from gradio_client import Client         # connection (small daily GPU quota; a free HF token adds more)
        c = Client(cfg.get("space", "black-forest-labs/FLUX.1-schnell"), hf_token=os.environ.get("HF_TOKEN"), verbose=False)
        r = c.predict(prompt=text, seed=seed or 0, randomize_seed=seed is None, width=size, height=size,
                      num_inference_steps=4, api_name="/infer")
        img = open(r[0] if isinstance(r, (list, tuple)) else r, "rb").read()
    elif provider == "pollinations":
        q = urllib.parse.quote(text)
        url = f"https://image.pollinations.ai/prompt/{q}?width={size}&height={size}&nologo=true" + (f"&seed={seed}" if seed else "")
        with urllib.request.urlopen(url, timeout=180) as r:
            img = r.read()
    else:
        raise RuntimeError("No image generator connected yet. Use elements-prompts and make the sheet in Canva AI, "
                           "ChatGPT or Higgsfield, then elements-cut it — or connect a free one in brand/ai.json.")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(img)
    Image.open(out).convert("RGB").save(out)
    return out


# ---------------------------------------------------------------- sheet → stickers
def _background_mask(rgb, tol=28):
    """True where the pixel is background: near-white AND connected to the sheet's edge (white inside a
    sticker stays)."""
    import cv2
    a = rgb.astype(np.int16)
    corners = np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3), a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners, 0)
    # near the sheet colour, OR a pale grey/white with almost no colour (the soft drop shadows generators add)
    sat = a.max(2) - a.min(2)
    near = ((np.abs(a - bg).max(2) < tol) | ((a.min(2) > bg.min() - 80) & (sat < 32))).astype(np.uint8)
    n, lab = cv2.connectedComponents(near, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    return np.isin(lab, list(edge)) & (near > 0)


def _ai_alpha(im):
    """Alpha mask (uint8 H×W) from rembg's general-purpose cut-out model, or None if rembg isn't installed."""
    if os.environ.get("REEL_NO_REMBG"):
        return None
    try:
        from rembg import new_session, remove
    except Exception:
        return None
    global _REMBG
    try:
        _REMBG
    except NameError:
        _REMBG = new_session("isnet-general-use")
    try:
        out = remove(im, session=_REMBG, only_mask=True)
        return np.asarray(out.convert("L"))
    except Exception:
        return None


def cut(sheet, out_dir, names=None, border=0, min_area=0.004):
    """Cut a sticker sheet into transparent PNGs (reading order). Returns [paths]."""
    import cv2
    im = Image.open(sheet).convert("RGB")
    if max(im.size) > 1600:
        im.thumbnail((1600, 1600), Image.LANCZOS)
    rgb = np.asarray(im)
    H, W = rgb.shape[:2]
    ai = _ai_alpha(im)                                                  # AI cut-out (rembg, MIT) when installed
    if ai is not None:
        soft = ai
        fg = (ai > 110).astype(np.uint8)
    else:
        fg = (~_background_mask(rgb)).astype(np.uint8)
        soft = None
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    blob = cv2.dilate(fg, np.ones((15, 15), np.uint8))                 # join a sticker's loose bits (eyes, sparkles)
    n, lab, stats, cen = cv2.connectedComponentsWithStats(blob, connectivity=8)
    boxes = [tuple(stats[i][:4]) + (i,) for i in range(1, n) if stats[i][4] > min_area * W * H]
    if not boxes:
        return []
    rowh = np.median([b[3] for b in boxes]) * 0.6                       # reading order: rows, then left → right
    boxes.sort(key=lambda b: (round((b[1] + b[3] / 2) / rowh), b[0]))
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    if soft is not None:                                                # the model's own soft edge
        alpha_full = Image.fromarray(soft)
    else:
        fg = cv2.erode(fg, np.ones((3, 3), np.uint8))                   # shave the last pale fringe pixel
        alpha_full = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    for k, (x, y, w, h, i) in enumerate(boxes):
        pad = 8
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
        own = (lab[y0:y1, x0:x1] == i)
        a = np.asarray(alpha_full)[y0:y1, x0:x1] * own
        piece = im.crop((x0, y0, x1, y1)).convert("RGBA")
        piece.putalpha(Image.fromarray(a.astype(np.uint8)))
        if border:                                                      # die-cut white edge
            r = int(border)
            edge = Image.fromarray(cv2.dilate((a > 40).astype(np.uint8) * 255, np.ones((2 * r + 1, 2 * r + 1), np.uint8)))
            canvas = Image.new("RGBA", piece.size, (255, 255, 255, 0))
            white = Image.new("RGBA", piece.size, (255, 255, 255, 255))
            canvas.paste(white, (0, 0), edge.filter(ImageFilter.GaussianBlur(1)))
            canvas.alpha_composite(piece)
            piece = canvas
        name = _slug(names[k]) if names and k < len(names) else f"element_{k + 1}"
        p = os.path.join(out_dir, name + ".png")
        piece.save(p)
        paths.append(p)
    return paths


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "element"


def colors_of(slug):
    from . import project, packs
    tl = project.load(slug, "timeline.json") or project.load(slug, "plan.json") or {}
    try:
        c = packs.load(tl.get("pack")).get("colors", {})
    except Exception:
        c = {}
    return [c.get(k) for k in ("pop", "accent", "paper", "ink") if c.get(k)]


def make(slug, items, style=DEFAULT_STYLE, provider=None, story="", seed=None):
    """Prompt → one generated sheet → stickers in projects/<p>/elements/. Returns (paths, prompt)."""
    from . import project
    text = prompt(items, style, colors_of(slug), story)
    d = project.path(slug, "elements")
    sheet = os.path.join(d, "sheets", f"sheet-{len(os.listdir(os.path.join(d, 'sheets'))) + 1 if os.path.isdir(os.path.join(d, 'sheets')) else 1}.png")
    generate(text, sheet, provider, seed=seed)
    return cut(sheet, d, items, border=int(config().get("border", 0))), text
