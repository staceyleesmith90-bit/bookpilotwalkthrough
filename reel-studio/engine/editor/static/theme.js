// Reelmate theme: big headings get one spring colour per letter (the colours live in theme.css).
(function () {
  const PICK = ".hero h1, .rowhead h2, .logo b, .fmt b, section > h2, header h1";
  function paint(el) {
    if (el.dataset.spring) return;
    el.dataset.spring = "1";
    const walk = (node) => {
      for (const n of Array.from(node.childNodes)) {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          for (const ch of n.textContent) {
            if (/\s/.test(ch)) { frag.appendChild(document.createTextNode(ch)); continue; }
            const s = document.createElement("span");
            s.textContent = ch;
            frag.appendChild(s);
          }
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && !["SMALL", "SVG", "svg", "BUTTON", "I"].includes(n.tagName)) {
          walk(n);
        }
      }
    };
    walk(el);
    el.classList.add("spring-letters");
    el.querySelectorAll("em").forEach((e) => e.classList.add("spring-letters"));
  }
  function run() { document.querySelectorAll(PICK).forEach(paint); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
  new MutationObserver(run).observe(document.documentElement, { childList: true, subtree: true });
})();

// Reel step bar: every page of one reel shows where you are — Cut → Storyboard → Sound & finish.
(function () {
  const slug = new URLSearchParams(location.search).get("p");
  const here = location.pathname;
  if (!slug || !["/review", "/storyboard", "/finish", "/editor", "/scenes"].includes(here)) return;
  fetch(`/api/p/${encodeURIComponent(slug)}/sound`).then(r => r.json()).then(info => {
    const steps = (info.has_source ? [["/review", "Cut"]] : []).concat([["/storyboard", "Storyboard"], ["/finish", "Sound & finish"]]);
    const bar = document.createElement("nav");
    bar.className = "rm-steps";
    bar.innerHTML = steps.map(([u, label], i) =>
      `<a href="${u}?p=${encodeURIComponent(slug)}" class="${u === here ? "on" : ""}"><b>${i + 1}</b>${label}</a>`).join('<span class="sep"></span>');
    const head = document.querySelector("header");
    if (head) head.after(bar); else document.body.prepend(bar);
  }).catch(() => {});
})();
