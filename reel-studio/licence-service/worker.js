// Reel Studio licence service (Cloudflare Worker).
//
// It knows ONLY licence keys and subscription status — never videos, brands or projects.
//   GET  /buy                      -> sends the customer to PayFast's monthly subscription checkout
//   POST /api/payfast/itn          -> PayFast tells us about payments / cancellations (verified)
//   GET  /welcome?ref=…            -> after paying: shows their licence key + how to install
//   POST /api/licence/validate     -> the extension checks a key {key, machine} -> {valid, renews, message}
//   POST /api/admin/issue|revoke   -> manual keys (PayPal customers, testers), Bearer ADMIN_TOKEN
//   GET  /api/update/latest        -> the newest release {version, notes, sha256, size, min_extension}
//   POST /api/update/download      -> the release zip, only for an active subscription {key, machine}
//   POST /api/admin/release        -> publish a release (after uploading its zip to R2), Bearer ADMIN_TOKEN
//
// Storage (Workers KV): "key:<KEY>" -> {email, status, renews, machines[], token, ref}; "ref:<REF>" -> KEY;
//   "release:latest" -> {version, notes, sha256, size, min_extension}. Release zips live in R2 (binding RELEASES)
//   at "releases/<version>.zip" — the app only, never anyone's files.

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    try {
      if (url.pathname === "/buy") return buy(url, env);
      if (url.pathname === "/api/payfast/itn" && req.method === "POST") return await itn(req, env);
      if (url.pathname === "/welcome") return await welcome(url, env);
      if (url.pathname === "/api/licence/validate" && req.method === "POST") return await validate(req, env);
      if (url.pathname === "/api/update/latest") return json(JSON.parse(await env.LICENCES.get("release:latest") || "{}"));
      if (url.pathname === "/api/update/download" && req.method === "POST") return await download(req, env);
      if (url.pathname.startsWith("/api/admin/") && req.method === "POST") return await admin(req, env, url);
      return new Response("Reel Studio licence service", { status: 200 });
    } catch (e) {
      return json({ error: "server_error" }, 500);
    }
  },
};

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json" } });
const page = (title, body) => new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title><body style="font:16px/1.6 Inter,system-ui,sans-serif;background:#06123D;color:#fff;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px">
<main style="max-width:560px;background:#0C1638;border-radius:18px;padding:28px">${body}</main></body>`, { headers: { "content-type": "text/html; charset=utf-8" } });

function newKey() {
  const a = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789", b = crypto.getRandomValues(new Uint8Array(12));
  let s = "RS-";
  b.forEach((v, i) => { s += a[v % a.length]; if (i % 4 === 3 && i < 11) s += "-"; });
  return s;
}

// ---------------------------------------------------------------- PayFast
// PHP-style urlencode (spaces as +, uppercase hex) — what PayFast signs with
const pfEncode = v => encodeURIComponent(String(v).trim()).replace(/%20/g, "+").replace(/[!'()*~]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
function pfSignature(pairs, passphrase) {
  let s = pairs.filter(([k, v]) => k !== "signature" && v !== "" && v !== undefined).map(([k, v]) => `${k}=${pfEncode(v)}`).join("&");
  if (passphrase) s += `&passphrase=${pfEncode(passphrase)}`;
  return md5(s);
}

function buy(url, env) {
  const ref = crypto.randomUUID().replace(/-/g, "");
  const pairs = [
    ["merchant_id", env.PAYFAST_MERCHANT_ID], ["merchant_key", env.PAYFAST_MERCHANT_KEY],
    ["return_url", `${env.PUBLIC_URL}/welcome?ref=${ref}`], ["cancel_url", `${env.PUBLIC_URL}/`],
    ["notify_url", `${env.PUBLIC_URL}/api/payfast/itn`],
    ["m_payment_id", ref], ["amount", env.PRICE_ZAR], ["item_name", env.PRODUCT],
    ["subscription_type", "1"], ["frequency", "3"], ["cycles", "0"],          // monthly, until cancelled
  ];
  const sig = pfSignature(pairs, env.PAYFAST_PASSPHRASE);
  const inputs = pairs.concat([["signature", sig]]).map(([k, v]) => `<input type="hidden" name="${k}" value="${String(v).replace(/"/g, "&quot;")}">`).join("");
  return page("Reel Studio — checkout", `<h1 style="font-family:Poppins,sans-serif">Reel Studio</h1><p>Taking you to PayFast to start your monthly subscription…</p>
<form id="f" method="post" action="https://${env.PAYFAST_HOST}/eng/process">${inputs}<button style="padding:12px 20px;border-radius:999px;border:0;background:#1E63FF;color:#fff;font-weight:600">Continue to PayFast</button></form>
<script>document.getElementById("f").submit()</script>`);
}

async function itn(req, env) {
  const body = await req.text();
  const pairs = body.split("&").filter(Boolean).map(p => { const [k, v = ""] = p.split("="); return [decodeURIComponent(k), decodeURIComponent(v.replace(/\+/g, " "))]; });
  const data = Object.fromEntries(pairs);
  // 1) signature (in the order PayFast sent the fields)
  if (pfSignature(pairs, env.PAYFAST_PASSPHRASE) !== data.signature) return new Response("bad signature", { status: 400 });
  // 2) ask PayFast to confirm the notification is genuine
  const check = await fetch(`https://${env.PAYFAST_HOST}/eng/query/validate`, {
    method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
    body: pairs.filter(([k]) => k !== "signature").map(([k, v]) => `${k}=${pfEncode(v)}`).join("&"),
  });
  if ((await check.text()).trim() !== "VALID") return new Response("not valid", { status: 400 });
  const ref = data.m_payment_id;
  let key = await env.LICENCES.get(`ref:${ref}`);
  let rec = key ? JSON.parse(await env.LICENCES.get(`key:${key}`) || "{}") : null;
  if (data.payment_status === "COMPLETE") {
    if (Math.abs(parseFloat(data.amount_gross) - parseFloat(env.PRICE_ZAR)) > 0.01) return new Response("amount mismatch", { status: 400 });
    if (!key) { key = newKey(); rec = { machines: [], ref }; await env.LICENCES.put(`ref:${ref}`, key); }
    rec.email = data.email_address || rec.email || "";
    rec.token = data.token || rec.token;
    rec.status = "active";
    rec.renews = Date.now() + 33 * 86400e3;                  // a month + a few days' grace for the next debit
    await env.LICENCES.put(`key:${key}`, JSON.stringify(rec));
  } else if (data.payment_status === "CANCELLED" && key) {
    rec.status = "cancelled";                                  // keeps working until the paid month ends
    await env.LICENCES.put(`key:${key}`, JSON.stringify(rec));
  }
  return new Response("OK");
}

async function welcome(url, env) {
  const ref = url.searchParams.get("ref") || "";
  const key = ref && await env.LICENCES.get(`ref:${ref}`);
  if (!key) return page("Reel Studio — almost there", `<h1>Payment received?</h1><p>We're confirming it with PayFast — this page will show your licence key in a few seconds.</p><script>setTimeout(()=>location.reload(),4000)</script>`);
  return page("Welcome to Reel Studio", `<h1 style="font-family:Poppins,sans-serif">You're in 🎬</h1>
<p>Your licence key:</p><p style="font:700 22px ui-monospace,monospace;background:#16224A;padding:12px 16px;border-radius:12px;user-select:all">${key}</p>
<ol><li>Download <a style="color:#00B5D9" href="${env.PUBLIC_URL}/download">Reel Studio for Claude</a> (Windows or Mac).</li>
<li>Double-click the file — Claude opens and asks to install it. Click <b>Install</b>.</li>
<li>Paste your licence key when Claude asks. Done — say “edit my reel”.</li></ol>
<p style="color:#A5B0CF">Keep this key safe. It works on up to ${env.MAX_MACHINES} computers.</p>`);
}

async function validate(req, env) {
  const { key = "", machine = "" } = await req.json().catch(() => ({}));
  const raw = await env.LICENCES.get(`key:${String(key).trim().toUpperCase()}`);
  if (!raw) return json({ valid: false, message: "That licence key wasn't found. Check it in your Reel Studio welcome page." });
  const rec = JSON.parse(raw);
  const paidUp = rec.renews && rec.renews > Date.now();
  if (rec.status === "revoked" || !paidUp)
    return json({ valid: false, message: "Your Reel Studio subscription has ended. Renew it to keep editing." });
  const machines = rec.machines || [];
  if (machine && !machines.includes(machine)) {
    if (machines.length >= parseInt(env.MAX_MACHINES || "2")) return json({ valid: false, message: `This key is already used on ${machines.length} computers. Contact support to move it.` });
    machines.push(machine); rec.machines = machines;
    await env.LICENCES.put(`key:${String(key).trim().toUpperCase()}`, JSON.stringify(rec));
  }
  return json({ valid: true, plan: "monthly", renews: new Date(rec.renews).toISOString().slice(0, 10),
                message: rec.status === "cancelled" ? "Subscription cancelled — works until the paid month ends." : "Subscription active." });
}

async function activeKey(key, machine, env) {
  const raw = await env.LICENCES.get(`key:${String(key).trim().toUpperCase()}`);
  if (!raw) return false;
  const rec = JSON.parse(raw);
  return rec.status !== "revoked" && rec.renews > Date.now() && (!machine || (rec.machines || []).includes(machine));
}

async function download(req, env) {
  const { key = "", machine = "" } = await req.json().catch(() => ({}));
  if (!(await activeKey(key, machine, env))) return json({ error: "Updates are included while your subscription is active." }, 403);
  const rel = JSON.parse(await env.LICENCES.get("release:latest") || "{}");
  if (!rel.version || !env.RELEASES) return json({ error: "No release published yet." }, 404);
  const obj = await env.RELEASES.get(`releases/${rel.version}.zip`);
  if (!obj) return json({ error: "Release file missing." }, 404);
  return new Response(obj.body, { headers: { "content-type": "application/zip", "x-version": rel.version } });
}

async function admin(req, env, url) {
  if ((req.headers.get("authorization") || "") !== `Bearer ${env.ADMIN_TOKEN}` || !env.ADMIN_TOKEN) return json({ error: "unauthorised" }, 401);
  const b = await req.json().catch(() => ({}));
  if (url.pathname === "/api/admin/release") {          // after: npx wrangler r2 object put reel-releases/releases/<v>.zip
    if (!/^\d+(\.\d+)*$/.test(b.version || "") || !/^[0-9a-f]{64}$/.test(b.sha256 || "")) return json({ error: "need version + sha256" }, 400);
    await env.LICENCES.put("release:latest", JSON.stringify({ version: b.version, notes: b.notes || "", sha256: b.sha256,
      size: b.size || 0, min_extension: b.min_extension || "0", published: new Date().toISOString().slice(0, 10) }));
    return json({ ok: true });
  }
  if (url.pathname === "/api/admin/issue") {             // e.g. PayPal customers, testers, founders
    const key = newKey();
    await env.LICENCES.put(`key:${key}`, JSON.stringify({ email: b.email || "", status: "active", machines: [],
      renews: Date.now() + (b.days || 31) * 86400e3, source: b.source || "manual" }));
    return json({ key });
  }
  if (url.pathname === "/api/admin/revoke" || url.pathname === "/api/admin/extend") {
    const raw = await env.LICENCES.get(`key:${b.key}`);
    if (!raw) return json({ error: "not_found" }, 404);
    const rec = JSON.parse(raw);
    if (url.pathname.endsWith("revoke")) rec.status = "revoked";
    else { rec.status = "active"; rec.renews = Math.max(rec.renews || 0, Date.now()) + (b.days || 31) * 86400e3; }
    await env.LICENCES.put(`key:${b.key}`, JSON.stringify(rec));
    return json({ ok: true, status: rec.status, renews: new Date(rec.renews).toISOString().slice(0, 10) });
  }
  return json({ error: "unknown" }, 404);
}

// ---------------------------------------------------------------- md5 (PayFast signatures; WebCrypto has no MD5)
export function md5(str) {
  const utf8 = new TextEncoder().encode(str);
  const n = ((utf8.length + 8) >>> 6) + 1, words = new Uint32Array(n * 16);
  for (let i = 0; i < utf8.length; i++) words[i >> 2] |= utf8[i] << ((i % 4) * 8);
  words[utf8.length >> 2] |= 0x80 << ((utf8.length % 4) * 8);
  words[n * 16 - 2] = utf8.length * 8;
  const K = new Uint32Array(64).map((_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32));
  const S = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
  let a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;
  for (let blk = 0; blk < n * 16; blk += 16) {
    let A = a0, B = b0, C = c0, D = d0;
    for (let i = 0; i < 64; i++) {
      let F, g;
      if (i < 16) { F = (B & C) | (~B & D); g = i; }
      else if (i < 32) { F = (D & B) | (~D & C); g = (5 * i + 1) % 16; }
      else if (i < 48) { F = B ^ C ^ D; g = (3 * i + 5) % 16; }
      else { F = C ^ (B | ~D); g = (7 * i) % 16; }
      const s = S[(i >> 4) * 4 + (i % 4)];
      const tmp = D; D = C; C = B;
      const x = (A + F + K[i] + words[blk + g]) >>> 0;
      B = (B + ((x << s) | (x >>> (32 - s)))) >>> 0;
      A = tmp;
    }
    a0 = (a0 + A) >>> 0; b0 = (b0 + B) >>> 0; c0 = (c0 + C) >>> 0; d0 = (d0 + D) >>> 0;
  }
  return [a0, b0, c0, d0].map(v => [0, 8, 16, 24].map(sh => ((v >>> sh) & 255).toString(16).padStart(2, "0")).join("")).join("");
}
export { pfSignature, pfEncode };
