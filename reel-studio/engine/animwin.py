"""Animation windows: little motion graphics that SHOW what is being said.

Beat treatment:  window:<kind>|<text>[|<more>]      e.g.
  window:app|Exporting your reel          an app window renders a video: progress bar -> "Done"
  window:chat|Edit my reel for me|On it!  a chat box types the message, then a reply bubble
  window:checklist|Film;Drop it in;Post   items tick off one by one
  window:stat|4 hours|saved every week    a big number counts up with a label
  window:doc|The part that matters        a page where one line gets highlighted
  window:product|Soft pastel pads|file.jpg  a product card slides in with a price-tag style label

Built from HTML in the brand's colours and fonts, drawn frame by frame in a hidden browser
(Chromium via Playwright), transparent background. Frames are cached per design, so re-renders
are instant. Our own designs — nothing copied.
"""
import hashlib, html, json, os, pathlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "library", "cache", "windows")
FPS = 30
KINDS = ("app", "chat", "checklist", "stat", "doc", "product")


def _font_url(pack, role):
    f = pack["fonts"].get(role) or pack["fonts"]["main"]
    p = f["file"] if os.path.isabs(f["file"]) else os.path.join(ROOT, f["file"])
    return pathlib.Path(p).resolve().as_uri()        # file:///C:/... on Windows, file:///Users/... on Mac


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Head;src:url('__HEAD__');}
@font-face{font-family:Body;src:url('__BODY__');}
:root{--pop:__POP__;--acc:__ACC__;--ink:#14161f;--mute:#8a8fa3;--paper:#ffffff;--line:#e7e9f0}
html,body{margin:0;background:transparent;width:__W__px;height:__H__px;overflow:hidden}
body{font-family:Body,Inter,system-ui,sans-serif;color:var(--ink)}
.stage{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.win{width:86%;background:var(--paper);border-radius:34px;box-shadow:0 30px 70px rgba(10,15,40,.28),0 4px 14px rgba(10,15,40,.12);overflow:hidden}
.bar{height:62px;display:flex;align-items:center;gap:12px;padding:0 26px;border-bottom:1px solid var(--line);background:#fafbfd}
.dot{width:16px;height:16px;border-radius:50%}
.bar .t{margin-left:14px;font:600 24px Head,Body,sans-serif;color:#5a6075}
.body{padding:34px 38px 40px}
.h{font:700 40px Head,Body,sans-serif;margin:0 0 20px}
.thumb{height:250px;border-radius:22px;background:linear-gradient(135deg,var(--pop),var(--acc));position:relative;overflow:hidden}
.thumb:after{content:"";position:absolute;inset:0;background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.35),transparent 55%)}
.play{position:absolute;left:50%;top:50%;width:84px;height:84px;margin:-42px;border-radius:50%;background:rgba(255,255,255,.9)}
.play:after{content:"";position:absolute;left:34px;top:26px;border-left:26px solid var(--pop);border-top:16px solid transparent;border-bottom:16px solid transparent}
.track{height:18px;border-radius:9px;background:var(--line);margin-top:30px;overflow:hidden}
.fill{height:100%;border-radius:9px;background:linear-gradient(90deg,var(--pop),var(--acc))}
.row{display:flex;justify-content:space-between;align-items:center;margin-top:18px;font:600 26px Body,sans-serif;color:var(--mute)}
.pill{padding:12px 26px;border-radius:40px;background:var(--pop);color:#fff;font:700 26px Head,Body,sans-serif}
.done{background:#18b26b}
.input{border:2px solid var(--line);border-radius:28px;padding:26px 30px;font:500 34px Body,sans-serif;min-height:48px;display:flex;align-items:center;gap:10px}
.caret{width:3px;height:40px;background:var(--pop)}
.send{margin-left:auto;width:62px;height:62px;border-radius:50%;background:var(--line);flex:none}
.send.on{background:var(--pop)}
.bub{margin-top:26px;display:inline-block;padding:22px 28px;border-radius:26px 26px 26px 8px;background:#f1f3f8;font:500 32px Body,sans-serif}
.me{display:flex;justify-content:flex-end}.me .bub{background:var(--pop);color:#fff;border-radius:26px 26px 8px 26px}
.item{display:flex;align-items:center;gap:22px;padding:20px 0;border-bottom:1px solid var(--line);font:600 36px Body,sans-serif}
.box{width:46px;height:46px;border-radius:14px;border:3px solid var(--line);flex:none;position:relative}
.box.on{background:var(--pop);border-color:var(--pop)}
.box.on:after{content:"";position:absolute;left:14px;top:5px;width:12px;height:24px;border:solid #fff;border-width:0 5px 5px 0;transform:rotate(45deg)}
.item.on span{color:var(--mute);text-decoration:line-through;text-decoration-color:var(--pop);text-decoration-thickness:4px}
.big{font:800 150px Head,Body,sans-serif;letter-spacing:-4px;line-height:1;background:linear-gradient(135deg,var(--pop),var(--acc));-webkit-background-clip:text;color:transparent}
.lab{font:600 38px Body,sans-serif;color:var(--mute);margin-top:12px}
.ln{height:20px;border-radius:10px;background:#eceef4;margin:18px 0}
.hl{position:relative;font:600 36px Body,sans-serif;padding:8px 6px;margin:18px 0;display:inline-block}
.hl i{position:absolute;left:0;top:12%;height:76%;border-radius:8px;background:var(--acc);opacity:.35;z-index:0}
.hl b{position:relative;z-index:1;font-weight:600}
.pimg{height:330px;border-radius:22px;background:#f1f3f8 center/cover no-repeat}
.tag{position:absolute;right:40px;top:40px;padding:14px 26px;border-radius:18px;background:var(--pop);color:#fff;font:700 30px Head,Body,sans-serif;transform:rotate(4deg)}
</style></head><body><div class="stage"><div class="win" id="w"></div></div>
<script>
const D = __DATA__;
const E = p => 1 - Math.pow(1 - Math.min(Math.max(p, 0), 1), 3);
const back = p => { p = Math.min(Math.max(p, 0), 1); const c = 1.7; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
function chrome(title){return `<div class="bar"><div class="dot" style="background:#ff5f57"></div><div class="dot" style="background:#febc2e"></div><div class="dot" style="background:#28c840"></div><div class="t">${title}</div></div>`}
function draw(t){
  const w = document.getElementById('w'), dur = D.dur;
  const inP = back(t / 0.45), out = E((t - (dur - 0.3)) / 0.3);
  w.style.transform = `translateY(${(1 - inP) * 60}px) scale(${0.9 + 0.1 * inP - 0.04 * out})`;
  w.style.opacity = Math.min(1, t / 0.2) * (1 - out);
  const k = D.kind, a = D.args;
  if (k === 'app') {
    const p = E((t - 0.5) / Math.max(dur - 1.6, 0.8)); const pct = Math.round(p * 100); const done = pct >= 100;
    w.innerHTML = chrome(D.app || 'Reel Studio') + `<div class="body"><div class="thumb"><div class="play"></div></div>
      <div class="track"><div class="fill" style="width:${pct}%"></div></div>
      <div class="row"><span>${done ? (a[1] || 'Ready to post') : (a[0] || 'Exporting') + '…'}</span>
      <span class="pill ${done ? 'done' : ''}" style="transform:scale(${done ? back((t - (0.5 + Math.max(dur - 1.6, 0.8))) / 0.3) : 1})">${done ? 'Done ✓' : pct + '%'}</span></div></div>`;
  } else if (k === 'chat') {
    const msg = a[0] || ''; const n = Math.floor(Math.max(0, t - 0.4) * 24); const typed = msg.slice(0, n); const sent = t > 0.4 + msg.length / 24 + 0.35;
    const reply = a[1] ? `<div class="bub" style="opacity:${E((t - (0.9 + msg.length / 24)) / 0.3)};transform:translateY(${(1 - E((t - (0.9 + msg.length / 24)) / 0.3)) * 20}px)">${a[1]}</div>` : '';
    w.innerHTML = chrome(D.app || 'Chat') + `<div class="body">${sent ? `<div class="me"><div class="bub">${msg}</div></div>` + reply :
      `<div class="input"><span>${typed}</span><span class="caret" style="opacity:${Math.floor(t * 2.5) % 2 ? 0.2 : 1}"></span><span class="send ${n >= msg.length ? 'on' : ''}"></span></div>`}</div>`;
  } else if (k === 'checklist') {
    const items = (a[0] || '').split(';').filter(Boolean); const step = Math.max((dur - 1.2) / Math.max(items.length, 1), 0.35);
    w.innerHTML = chrome(D.app || 'Today') + `<div class="body">${a[1] ? `<div class="h">${a[1]}</div>` : ''}` + items.map((x, i) => {
      const on = t > 0.6 + step * (i + 0.6); return `<div class="item ${on ? 'on' : ''}"><div class="box ${on ? 'on' : ''}" style="transform:scale(${on ? back((t - 0.6 - step * (i + 0.6)) / 0.25) : 1})"></div><span>${x}</span></div>`; }).join('') + '</div>';
  } else if (k === 'stat') {
    const m = (a[0] || '100').match(/^([^\d]*)([\d.,]+)(.*)$/) || ['', '', a[0], ''];
    const target = parseFloat(m[2].replace(/,/g, '')); const dec = (m[2].split('.')[1] || '').length;
    const v = target * E((t - 0.35) / Math.max(dur - 1.3, 0.8));
    const shown = v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec});
    w.innerHTML = `<div class="body" style="padding:60px 50px;text-align:center"><div class="big">${m[1]}${shown}${m[3]}</div><div class="lab">${a[1] || ''}</div></div>`;
  } else if (k === 'doc') {
    const p = E((t - 0.7) / 0.8);
    w.innerHTML = chrome(D.app || 'Notes.pdf') + `<div class="body"><div class="ln" style="width:92%"></div><div class="ln" style="width:78%"></div>
      <div class="hl"><i style="width:${p * 100}%"></i><b>${a[0] || ''}</b></div><div class="ln" style="width:85%"></div><div class="ln" style="width:60%"></div></div>`;
  } else if (k === 'product') {
    const p = back((t - 0.45) / 0.35);
    w.innerHTML = `<div class="body" style="position:relative"><div class="pimg" style="background-image:url('${D.img || ''}')"></div>
      <div class="h" style="margin-top:26px">${a[0] || ''}</div>${a[2] ? `<div class="lab" style="margin:0">${a[2]}</div>` : ''}
      <div class="tag" style="transform:rotate(4deg) scale(${Math.max(p, 0)})">${a[3] || 'NEW'}</div></div>`;
  }
}
</script></body></html>"""


def parse(arg):
    kind, _, rest = arg.partition("|")
    kind = kind.strip().lower() or "app"
    return (kind if kind in KINDS else "app"), [html.escape(x.strip()) for x in rest.split("|")] if rest else []


def build_html(kind, args, pack, dur, size=(1000, 900), app=None, img=None):
    c = pack["colors"]
    data = {"kind": kind, "args": args, "dur": dur, "app": html.escape(app or pack.get("label", "") or ""), "img": img}
    return (PAGE.replace("__HEAD__", _font_url(pack, "headline")).replace("__BODY__", _font_url(pack, "main"))
            .replace("__POP__", c.get("pop", "#1E63FF")).replace("__ACC__", c.get("accent", c.get("pop", "#6A11CB")))
            .replace("__W__", str(size[0])).replace("__H__", str(size[1])).replace("__DATA__", json.dumps(data)))


def frames(it, pack, fps=FPS):
    """PNG frame paths for a window item (cached by design + text + colours)."""
    kind, args = parse(it.get("window", "app"))
    dur = round(it["end"] - it["start"], 2)
    img = None
    if kind == "product" and len(args) > 1 and args[1]:
        p = args[1] if os.path.isabs(args[1]) else os.path.join(ROOT, args[1])
        img = pathlib.Path(p).resolve().as_uri() if os.path.exists(p) else None
    page = build_html(kind, args, pack, dur, img=img)
    key = hashlib.md5((page + str(fps)).encode()).hexdigest()[:16]
    folder = os.path.join(CACHE, key)
    n = int(dur * fps)
    if os.path.isdir(folder) and len(os.listdir(folder)) >= n:
        return [os.path.join(folder, f"{i:04d}.png") for i in range(n)]
    os.makedirs(folder, exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = os.environ.get("REEL_CHROMIUM")
        try:
            b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        except Exception:
            import glob
            cands = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
            if not cands:
                raise
            b = p.chromium.launch(executable_path=cands[0])
        pg = b.new_page(viewport={"width": 1000, "height": 900})
        html_path = os.path.join(folder, "page.html")
        open(html_path, "w", encoding="utf-8").write(page)
        pg.goto(pathlib.Path(html_path).resolve().as_uri())
        pg.wait_for_timeout(250)
        for i in range(n):
            pg.evaluate(f"draw({i / fps})")
            pg.screenshot(path=os.path.join(folder, f"{i:04d}.png"), omit_background=True)
        b.close()
    return [os.path.join(folder, f"{i:04d}.png") for i in range(n)]
