"""The effects library page — one place to see, hear and copy everything the engine can do.

    python -m engine library        -> out/effects-library.html (opens in the browser)

Tabs: Effects (built-in moments) · Captions · Premium (~400 HyperFrames effects, played live on
click when online) · Sounds (every sound, playable — including the user's own) · What to say.
Each card has a copy button with the exact words to say. Runs from the user's own computer.
"""
import glob, html, json, os, webbrowser

from . import hyperframes, mysounds, rules, styleplan
from .captions import STYLES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "effects-library.html")
CDN = "https://cdn.jsdelivr.net/gh/heygen-com/hyperframes@{commit}/registry/{kind}/{name}/"

from .prompts import LIBRARY as _PROMPTS
SAY = [(f"{ic} {g}", [say for _, say in items]) for g, ic, items in _PROMPTS]


def _sounds():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "library", "sfx", "uisfx", "*", "*.wav"))):
        feel, ev = f.split(os.sep)[-2], os.path.splitext(os.path.basename(f))[0]
        rows.append({"group": f"Interface · {feel}", "name": ev, "src": f})
    for f in sorted(glob.glob(os.path.join(ROOT, "library", "sfx", "foley", "*.wav"))):
        rows.append({"group": "Real recordings", "name": os.path.splitext(os.path.basename(f))[0], "src": f})
    for f in sorted(glob.glob(os.path.join(ROOT, "library", "sfx", "cc0pack", "*.wav"))):
        rows.append({"group": "Air · glass · taps", "name": os.path.splitext(os.path.basename(f))[0], "src": f})
    for f in sorted(glob.glob(os.path.join(mysounds.MINE, "*", "*.wav"))):
        rows.append({"group": "Yours", "name": f"{os.path.basename(os.path.dirname(f))}: "
                     + os.path.splitext(os.path.basename(f))[0], "src": f})
    out_dir = os.path.dirname(OUT)
    for r in rows:
        try:
            r["src"] = os.path.relpath(r["src"], out_dir).replace(os.sep, "/")
        except ValueError:                       # Windows: page and sounds on different drives
            import pathlib
            r["src"] = pathlib.Path(r["src"]).resolve().as_uri()
    return rows


def data():
    cat = json.load(open(os.path.join(ROOT, "library", "hyperframes", "catalog.json"), encoding="utf-8"))
    premium = [{"name": i["name"], "title": i.get("title") or i["name"], "about": i.get("description", "")[:160],
                "tags": i.get("tags", [])[:6], "kind": i["kind"], "file": next((f for f in i.get("files", [])
                                                                                if f.endswith(".html")), None),
                "vertical": (i.get("dimensions") or {}).get("height", 0) > (i.get("dimensions") or {}).get("width", 1)}
               for i in cat["items"]]
    effects = [{"name": k, "about": v.get("about", ""), "say": f"Use the {k} effect on the line about …"}
               for k, v in styleplan.effects().items()]
    effects += [{"name": v.split(" (")[0], "about": v, "say": f"Put a {v.split(' (')[0]} on the line about …"}
                for k, v in styleplan.PLAIN.items() if k not in ("keep-footage", "sfx", "hook", "zoom")]
    caps = [{"name": k, "about": v, "say": f"Do my captions in {k}"} for k, v in STYLES.items()]
    caps += [{"name": v, "about": "premium animated (HyperFrames)", "say": f"Do my captions in {v}",
              "hf": k} for k, v in hyperframes.caption_styles().items()]
    return {"premium": premium, "effects": effects, "captions": caps, "sounds": _sounds(), "say": SAY,
            "cdn": CDN.replace("{commit}", cat["commit"]), "rules": rules.load()}


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Effects Library</title>
<style>
:root{--bg:#f6f4f0;--card:#fff;--ink:#16181d;--mute:#6b7079;--line:#e4e0d8;--acc:#2f5bea;--chip:#eef1fb}
@media (prefers-color-scheme:dark){:root{--bg:#121316;--card:#1c1e23;--ink:#eceef2;--mute:#9aa0aa;--line:#2b2e35;--acc:#7c9bff;--chip:#232838}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:28px 16px 8px;max-width:1180px;margin:auto}h1{margin:0 0 4px;font-size:28px}header p{margin:0;color:var(--mute)}
nav{position:sticky;top:0;background:var(--bg);z-index:5;border-bottom:1px solid var(--line)}
nav .in{max-width:1180px;margin:auto;padding:10px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:8px 14px;border-radius:999px;cursor:pointer;font:inherit}
nav button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
#q{flex:1;min-width:160px;padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit}
main{max-width:1180px;margin:auto;padding:16px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:8px}
.card h3{margin:0;font-size:15px}.card p{margin:0;color:var(--mute);font-size:13px}
.tags{display:flex;gap:5px;flex-wrap:wrap}.tags span{background:var(--chip);border-radius:6px;padding:1px 7px;font-size:11px;color:var(--mute)}
.row{display:flex;gap:6px;margin-top:auto;flex-wrap:wrap}.row button{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;padding:6px 10px;cursor:pointer;font:inherit;font-size:13px}
.row button.copy{background:var(--acc);border-color:var(--acc);color:#fff}
.stage{aspect-ratio:16/9;border-radius:10px;overflow:hidden;background:#000;display:none}.stage.v{aspect-ratio:9/16;max-height:420px;margin:auto}
.stage iframe{width:100%;height:100%;border:0}.grp{margin:22px 0 8px;font-weight:600}
.say{display:flex;justify-content:space-between;gap:10px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:6px 0}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:10px;opacity:0;transition:.2s}.toast.on{opacity:1}
.note{color:var(--mute);font-size:13px;margin:0 0 12px}
</style></head><body>
<header><h1>Effects Library</h1><p>Everything your editor can do. Tap a card to copy what to say, then paste it to Claude.</p></header>
<nav><div class="in" id="tabs"></div></nav><main id="main"></main><div class="toast" id="toast">Copied</div>
<script>
const D=__DATA__;const tabs=[["effects","Moments"],["captions","Captions"],["premium","Premium effects"],["sounds","Sounds"],["say","What to say"],["rules","Your rules"]];
let cur="effects";
const PLAYER=`<script>setTimeout(()=>{const r=document.querySelector("[data-width]")||document.body.firstElementChild;if(!r)return;
const w=+(r.dataset.width||1920),h=+(r.dataset.height||1080);document.documentElement.style.overflow="hidden";document.body.style.margin=0;
r.style.position="absolute";r.style.left=0;r.style.top=0;r.style.transformOrigin="0 0";r.style.transform="scale("+Math.min(innerWidth/w,innerHeight/h)+")";
const T=window.__timelines||{};Object.values(T).forEach(t=>{try{t.repeat(-1);t.repeatDelay&&t.repeatDelay(0.8);t.play(0)}catch(e){}})},400)<\/script>`;const $=s=>document.querySelector(s);
function toast(t){const e=$("#toast");e.textContent=t;e.classList.add("on");setTimeout(()=>e.classList.remove("on"),1300)}
function copy(t){(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>toast("Copied: "+t)).catch(()=>prompt("Copy this:",t))}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function nav(){$("#tabs").innerHTML=tabs.map(([k,l])=>`<button data-k="${k}" class="${k==cur?"on":""}">${l}</button>`).join("")+`<input id="q" placeholder="Search…">`;
 document.querySelectorAll("#tabs button").forEach(b=>b.onclick=()=>{cur=b.dataset.k;nav();draw()});$("#q").oninput=draw}
function match(o){const q=($("#q")||{}).value;if(!q)return true;return JSON.stringify(o).toLowerCase().includes(q.toLowerCase())}
function card(o,extra=""){return `<div class="card"><h3>${esc(o.name||o.title)}</h3><p>${esc(o.about||"")}</p>${extra}<div class="row"><button class="copy" data-say="${esc(o.say)}">Copy what to say</button></div></div>`}
async function play(i,btn){const o=D.premium[i];const st=document.getElementById("st"+i);st.style.display="block";btn.textContent="Loading…";
 try{const base=D.cdn.replace("{kind}",o.kind).replace("{name}",o.name);const r=await fetch(base+o.file);let h=await r.text();
  h=h.replace(/<head([^>]*)>/i,`<head$1><base href="${base}">`).replace(/https?:\/\/[^"']*gsap[^"']*\.js/g,"https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js");
  h=h.replace(/<\/body>/i,PLAYER+"</body>");st.innerHTML=`<iframe sandbox="allow-scripts" srcdoc="${esc(h)}"></iframe>`;btn.textContent="Replay"}
 catch(e){st.innerHTML='<p style="color:#fff;padding:12px">Needs the internet to play here. It still works in your reels.</p>';btn.textContent="Play"}}
function draw(){const m=$("#main");let h="";
 if(cur=="effects")h=`<p class="note">Moments your editor builds in your style pack.</p><div class="grid">`+D.effects.filter(match).map(o=>card(o)).join("")+"</div>";
 if(cur=="captions")h=`<div class="grid">`+D.captions.filter(match).map(o=>card(o)).join("")+"</div>";
 if(cur=="premium")h=`<p class="note">${D.premium.length} ready-made effects from HyperFrames (open source by HeyGen). Press Play to watch one. Your editor swaps in your own words, numbers and handles.</p><div class="grid">`+
  D.premium.map((o,i)=>[o,i]).filter(([o])=>match(o)).slice(0,120).map(([o,i])=>`<div class="card"><h3>${esc(o.title)}</h3><p>${esc(o.about)}</p><div class="tags">${o.tags.map(t=>`<span>${esc(t)}</span>`).join("")}</div><div class="stage ${o.vertical?"v":""}" id="st${i}"></div><div class="row"><button onclick="play(${i},this)">Play</button><button class="copy" data-say="Use the ${esc(o.title)} effect (${esc(o.name)}) on the line about …">Copy what to say</button></div></div>`).join("")+"</div>"+
  (D.premium.filter(match).length>120?`<p class="note">Showing 120 — search to narrow it down.</p>`:"");
 if(cur=="sounds"){let g="";h=`<p class="note">Press to listen. Sounds you teach (CapCut favourites, your inbox) appear under “Yours” and are used first.</p>`;
  D.sounds.filter(match).forEach((s,i)=>{if(s.group!=g){g=s.group;h+=`<div class="grp">${esc(g)}</div>`}h+=`<button class="snd" style="margin:3px;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer" data-src="${esc(s.src)}">▶ ${esc(s.name)}</button>`})}
 if(cur=="say")h=D.say.map(([g,l])=>`<div class="grp">${esc(g)}</div>`+l.filter(x=>match(x)).map(x=>`<div class="say"><span>“${esc(x)}”</span><div class="row" style="margin:0"><button class="copy" data-say="${esc(x)}">Copy</button></div></div>`).join("")).join("");
 if(cur=="rules")h=D.rules.length?D.rules.map((r,i)=>`<div class="say"><span>${i+1}. <b>${esc(r.area)}</b> — ${esc(r.rule)}</span></div>`).join(""):`<p class="note">Nothing taught yet. After any change you want every time, say “remember that”.</p>`;
 m.innerHTML=h;m.querySelectorAll(".copy").forEach(b=>b.onclick=()=>copy(b.dataset.say));
 m.querySelectorAll(".snd").forEach(b=>b.onclick=()=>new Audio(b.dataset.src).play().catch(()=>toast("Couldn't play — open this page in your browser")))}
nav();draw();
</script></body></html>"""


def build(open_it=True):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    blob = json.dumps(data(), ensure_ascii=False).replace("</", "<\\/")
    open(OUT, "w", encoding="utf-8").write(PAGE.replace("__DATA__", blob))
    if open_it:
        try:
            webbrowser.open("file://" + OUT.replace(os.sep, "/") if os.name != "nt" else OUT)
        except Exception:
            pass
    return OUT
