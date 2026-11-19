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

// Voice notes: every box where people can type feedback gets a 🎤 button. Speak, press stop, the words appear.
// The recording is turned into text on this computer (faster-whisper) — free, private, no Claude usage.
(function () {
  const PICK = "textarea:not([readonly]), input[data-voice]";
  if (!navigator.mediaDevices || !window.MediaRecorder) return;
  function add(field) {
    if (field.dataset.voiced || field.dataset.voice === "no" || field.closest("[data-novoice]")) return;
    field.dataset.voiced = "1";
    const b = document.createElement("button");
    b.type = "button";
    b.className = "rm-mic";
    b.innerHTML = "🎤 <span>Voice note</span>";
    b.title = "Say it instead of typing";
    if (field.closest("#rs-chat")) { b.classList.add("in-chat"); b.innerHTML = "🎤"; }
    field.insertAdjacentElement("afterend", b);
    let rec = null, chunks = [], timer = null, t0 = 0;
    const label = (txt) => { const s = b.querySelector("span"); if (s) s.textContent = txt; else b.title = txt; };
    b.onclick = async (e) => {
      e.preventDefault();
      if (rec && rec.state === "recording") { rec.stop(); return; }
      let stream;
      try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
      catch (err) { alert("Reelmate needs your microphone for voice notes. Allow it in the browser bar and try again."); return; }
      chunks = [];
      rec = new MediaRecorder(stream);
      rec.ondataavailable = (ev) => ev.data.size && chunks.push(ev.data);
      rec.onstop = async () => {
        clearInterval(timer);
        stream.getTracks().forEach((t) => t.stop());
        b.classList.remove("rec"); b.classList.add("busy"); label("Writing it down…");
        try {
          const r = await (await fetch("/api/transcribe", { method: "POST", body: new Blob(chunks, { type: rec.mimeType }) })).json();
          if (r.text) {
            field.value = (field.value.trim() ? field.value.trim() + " " : "") + r.text;
            field.dispatchEvent(new Event("input", { bubbles: true }));
            field.dispatchEvent(new Event("change", { bubbles: true }));
            field.focus();
          } else alert(r.error || "I couldn't hear anything. Try again a bit closer to the mic.");
        } catch (err) { alert("That voice note didn't work. Try again."); }
        b.classList.remove("busy"); label("Voice note");
      };
      rec.start();
      t0 = Date.now();
      b.classList.add("rec"); label("Stop 0:00");
      timer = setInterval(() => { const s = Math.floor((Date.now() - t0) / 1000); label(`Stop ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`); }, 500);
    };
  }
  function run() { document.querySelectorAll(PICK).forEach(add); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
  new MutationObserver(run).observe(document.documentElement, { childList: true, subtree: true });
})();
