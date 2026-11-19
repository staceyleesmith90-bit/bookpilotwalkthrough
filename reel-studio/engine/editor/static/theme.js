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
