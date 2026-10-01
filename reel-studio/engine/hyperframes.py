"""HyperFrames effects (HeyGen, Apache-2.0) inside Reel Studio.

HyperFrames components are small web pages animated by a GSAP timeline. We open one in the hidden
browser (the same one that draws animation windows), swap in the reel's own words, timings and
length, step its timeline frame by frame and keep transparent PNG frames that the renderer lays over
the video — exactly like our own captions, so CapCut export, layers and fast re-renders all work.

Captions (by name):  "captions": "hf:pill-karaoke"  ·  hf:kinetic-slam · hf:highlight · …
List them:           python -m engine hf-captions
Components live unmodified in library/hyperframes/ (see NOTICE.md); frames cache in library/cache/hf/.
"""
import hashlib, json, os, pathlib, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library", "hyperframes", "captions")
CACHE = os.path.join(ROOT, "library", "cache", "hf")
FPS = 30
_WORDS_RE = re.compile(r"((?:var|const|let)\s+\w+\s*=\s*)\[\s*\{\s*(?:text|word)\s*:.*?\]\s*;", re.S)


UNSUPPORTED = {"blend-difference", "camera-follow", "texture", "glitch-rgb"}   # need their own demo footage/layout


def caption_styles():
    """{short name: title} for every caption component that takes a reel's own words."""
    out = {}
    for f in sorted(os.listdir(LIB)) if os.path.isdir(LIB) else []:
        if f.endswith(".json"):
            meta = json.load(open(os.path.join(LIB, f), encoding="utf-8"))
            short = meta["name"].replace("caption-", "")
            if short not in UNSUPPORTED:
                out[short] = meta.get("title", meta["name"])
    return out


def _groups(words, max_words=4, max_chars=22):
    """Caption groups as (first, last) word indexes: break on pauses, punctuation and length."""
    out, start = [], 0
    for i, w in enumerate(words):
        n = i - start + 1
        chars = sum(len(x["w"]) + 1 for x in words[start:i + 1])
        nxt = words[i + 1] if i + 1 < len(words) else None
        brk = (nxt is None or n >= max_words or chars >= max_chars or w["w"][-1:] in ".,!?:;"
               or (nxt["start"] - w["end"]) > 0.35)
        if brk:
            out.append((start, i))
            start = i + 1
    return out


def _replace_array(html, name, js):
    """Replace `var NAME = [ ... ];` (nested brackets allowed) with `var NAME = <js>;`."""
    m = re.search(r"((?:var|const|let)\s+" + name + r"\s*=\s*)\[", html)
    if not m:
        return html, False
    i, depth = m.end() - 1, 0
    for j in range(i, len(html)):
        if html[j] == "[":
            depth += 1
        elif html[j] == "]":
            depth -= 1
            if depth == 0:
                end = j + 1
                if html[end:end + 1] == ";":
                    end += 1
                return html[:m.start()] + m.group(1) + js + ";" + html[end:], True
    return html, False


def adapt(html, words, duration):
    """Swap the demo words + length in a component for ours. Returns None if it can't be adapted."""
    data = json.dumps([{"text": w["w"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in words])
    m = _WORDS_RE.search(html)
    if not m:
        return None
    html = html[:m.start()] + m.group(1) + data + ";" + html[m.end():]
    groups = _groups(words)
    from .captions import auto_keywords
    try:
        keys = set(auto_keywords(words))
    except Exception:
        keys = set()
    # word-index group tables some components keep (rebuilt from OUR words)
    html, _ = _replace_array(html, "RAW_GROUPS", json.dumps([[a, b] for a, b in groups]))
    objs = []
    for k, (a, b) in enumerate(groups):
        nxt = words[groups[k + 1][0]]["start"] if k + 1 < len(groups) else duration
        objs.append({"wordStart": a, "wordEnd": b, "start": round(words[a]["start"], 3),
                     "end": round(max(words[b]["end"], min(words[b]["end"] + 0.5, nxt - 0.05)), 3)})
    if re.search(r"(?:var|const|let)\s+GROUPS\s*=\s*\[\s*\{\s*wordStart", html):
        html, _ = _replace_array(html, "GROUPS", json.dumps(objs))
    if re.search(r"BLOCKS\s*=\s*\[\s*\{\s*line1", html):          # two lines, emphasis word marked "e"
        blocks = []
        for a, b in groups:
            idx = list(range(a, b + 1))
            cut = max(1, (len(idx) + 1) // 2) if len(idx) > 1 else 1
            tag = lambda i: [i, "e" if i in keys else "n"]
            blocks.append({"line1": [tag(i) for i in idx[:cut]], "line2": [tag(i) for i in idx[cut:]]})
        html, _ = _replace_array(html, "BLOCKS", json.dumps(blocks))
    elif re.search(r"BLOCKS\s*=\s*\[\s*\{\s*behind", html):        # one big word behind, the rest in front
        blocks = []
        for a, b in groups:
            idx = list(range(a, b + 1))
            kw = next((i for i in idx if i in keys), None)
            front = [[i] for i in idx if i != kw]
            blocks.append({"behind": [[kw]] if kw is not None else None, "front": front or None})
        html, _ = _replace_array(html, "BLOCKS", json.dumps(blocks))
    gsap = pathlib.Path(os.path.join(ROOT, "library", "hyperframes", "gsap.min.js")).resolve().as_uri()
    html = re.sub(r'<script src="https://[^"]*gsap[^"]*"></script>', f'<script src="{gsap}"></script>', html)  # offline + fast
    html = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{duration:.2f}"', html)
    html = re.sub(r"((?:var|const|let)\s+DURATION\s*=\s*)[0-9.]+", lambda k: k.group(1) + f"{duration:.2f}", html)
    html = re.sub(r"(:\s*)8\.0(\s*;)", lambda k: k.group(1) + f"{duration:.2f}" + k.group(2), html)   # demo end time
    return html


def _browser(p):
    exe = os.environ.get("REEL_CHROMIUM")
    try:
        return p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    except Exception:
        import glob
        c = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
        if not c:
            raise
        return p.chromium.launch(executable_path=c[0])


def caption_frames(style, words, duration, fps=FPS):
    """PNG frame paths (cropped to where the captions ever appear) + the crop box, cached."""
    name = style.replace("hf:", "").replace("caption-", "")
    src = os.path.join(LIB, f"caption-{name}.html")
    if not os.path.exists(src):
        raise ValueError(f"No HyperFrames caption style called '{name}'. Try: " + ", ".join(caption_styles()))
    page = adapt(open(src, encoding="utf-8").read(), words, duration)
    if page is None:
        raise ValueError(f"The '{name}' caption style can't take new words automatically.")
    key = hashlib.md5((page + str(fps)).encode()).hexdigest()[:16]
    folder = os.path.join(CACHE, key)
    n = int(duration * fps)
    done = os.path.join(folder, "frames.json")
    if os.path.exists(done):
        return json.load(open(done))
    os.makedirs(folder, exist_ok=True)
    html_path = os.path.join(folder, "page.html")
    open(html_path, "w", encoding="utf-8").write(page)
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as p:
        b = _browser(p)
        ctx = b.new_context(viewport={"width": 1920, "height": 1080},
                            ignore_https_errors=os.environ.get("REEL_IGNORE_TLS") == "1")
        pg = ctx.new_page()
        pg.goto(pathlib.Path(html_path).resolve().as_uri())
        pg.wait_for_function("window.__timelines && Object.keys(window.__timelines).length > 0", timeout=20000)
        pg.evaluate("document.fonts && document.fonts.ready")
        pg.wait_for_timeout(300)
        paths = []
        for i in range(n):
            pg.evaluate(f"(() => {{ const tl = Object.values(window.__timelines)[0]; tl.seek({i / fps}, false); }})()")
            fp = os.path.join(folder, f"{i:05d}.png")
            pg.screenshot(path=fp, omit_background=True)
            paths.append(fp)
        b.close()
    box = None                                     # one crop for every frame, so the captions never jump
    for fp in paths[::3]:
        bb = Image.open(fp).getbbox()
        if bb:
            box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
    result = {"frames": paths, "box": box, "fps": fps}
    json.dump(result, open(done, "w"))
    return result
