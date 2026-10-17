/* Reel Studio chat box: type a change, Claude makes it and renders a preview.
   Include with <script src="/chat.js"></script> on any page that has ?p=<project>. */
(function () {
  const slug = new URLSearchParams(location.search).get("p");
  if (!slug) return;
  const css = `
  #rs-chat{position:fixed;right:18px;bottom:18px;width:360px;max-width:calc(100vw - 36px);z-index:9999;font:14px/1.45 Inter,system-ui,sans-serif;color:#0E1638}
  #rs-chat .bar{display:flex;align-items:center;gap:8px;background:#0A1240;color:#fff;border-radius:14px 14px 0 0;padding:10px 14px;cursor:pointer}
  #rs-chat .bar b{font-weight:700} #rs-chat .bar span{margin-left:auto;opacity:.7;font-size:12px}
  #rs-chat.min .body{display:none} #rs-chat.min .bar{border-radius:14px}
  #rs-chat .body{background:#fff;border:1px solid #E3E7F2;border-top:0;border-radius:0 0 14px 14px;box-shadow:0 18px 40px -20px rgba(10,18,64,.45)}
  #rs-chat .log{max-height:320px;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
  #rs-chat .m{padding:8px 11px;border-radius:12px;max-width:85%;white-space:pre-wrap}
  #rs-chat .you{align-self:flex-end;background:#2E5BFF;color:#fff}
  #rs-chat .claude{align-self:flex-start;background:#EEF1F9}
  #rs-chat .steps{align-self:flex-start;font-size:12.5px;color:#5F6889;display:flex;align-items:center;gap:6px}
  #rs-chat .dot{width:8px;height:8px;border-radius:50%;background:#2E5BFF;animation:rsb 1s infinite alternate}
  @keyframes rsb{from{opacity:.25}to{opacity:1}}
  #rs-chat form{display:flex;gap:8px;padding:10px;border-top:1px solid #EEF1F9}
  #rs-chat textarea{flex:1;resize:none;border:1px solid #E3E7F2;border-radius:10px;padding:8px 10px;font:inherit;min-height:40px;max-height:110px}
  #rs-chat button{border:0;border-radius:10px;padding:0 14px;background:linear-gradient(100deg,#18A9F5,#3D5CFF 42%,#8A3BF0 75%,#E64BC8);color:#fff;font-weight:600;cursor:pointer}
  #rs-chat button:disabled{opacity:.5;cursor:default}
  #rs-chat .hint{font-size:12px;color:#8C93AE;padding:0 12px 10px}
  #rs-chat a.pv{display:inline-block;margin-top:6px;font-weight:600;color:#2E5BFF}`;
  const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  const box = document.createElement("div"); box.id = "rs-chat";
  box.innerHTML = `<div class="bar"><b>Ask Claude</b><span>change anything in words</span></div>
    <div class="body"><div class="log" aria-live="polite"></div>
    <form><textarea rows="1" placeholder="e.g. make NEVER bigger and put it behind me"></textarea><button>Send</button></form>
    <div class="hint"></div></div>`;
  document.body.appendChild(box);
  const log = box.querySelector(".log"), ta = box.querySelector("textarea"), btn = box.querySelector("button"),
        hint = box.querySelector(".hint");
  box.querySelector(".bar").onclick = () => box.classList.toggle("min");
  try { if (localStorage.getItem("rs-chat-min") === "1") box.classList.add("min"); } catch (e) {}
  box.querySelector(".bar").addEventListener("click", () => { try { localStorage.setItem("rs-chat-min", box.classList.contains("min") ? "1" : "0"); } catch (e) {} });
  let seen = -1, timer = null;
  function draw(d) {
    const msgs = d.history || [];
    if (msgs.length !== seen || d.status.state === "working") {
      log.innerHTML = msgs.map(m => `<div class="m ${m.role === "you" ? "you" : "claude"}">${esc(m.text)}${
        m.preview ? `<br><a class="pv" href="/api/p/${slug}/render/preview.mp4?t=${Math.round(m.t)}" target="_blank">▶ Watch the new preview</a>` : ""}</div>`).join("");
      if (d.status.state === "working") {
        const s = d.status.steps || [];
        log.insertAdjacentHTML("beforeend", `<div class="steps"><span class="dot"></span>${esc(s[s.length - 1] || "Working")}…</div>`);
      }
      log.scrollTop = log.scrollHeight; seen = msgs.length;
    }
    btn.disabled = d.status.state === "working";
    hint.textContent = d.available ? "Claude changes this reel and renders a quick preview." :
      "Claude Code isn't running here — your request is saved and done next time you open Reel Studio.";
    clearTimeout(timer);
    if (d.status.state === "working") timer = setTimeout(load, 1500);
  }
  function esc(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]); }
  async function load() { try { draw(await (await fetch(`/api/p/${slug}/chat`)).json()); } catch (e) {} }
  box.querySelector("form").onsubmit = async e => {
    e.preventDefault();
    const msg = ta.value.trim(); if (!msg) return;
    ta.value = ""; btn.disabled = true;
    await fetch(`/api/p/${slug}/chat`, { method: "POST", body: JSON.stringify({ message: msg }) });
    seen = -1; load();
  };
  ta.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); box.querySelector("form").requestSubmit(); } });
  load();
})();
