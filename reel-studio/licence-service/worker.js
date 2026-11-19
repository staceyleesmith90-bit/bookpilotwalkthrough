// Reelmate licence service (Cloudflare Worker). Reelmate is sold as ONE once-off payment and is theirs FOREVER,
// updates included. No trials, no subscriptions, nothing that runs out.
//
// It knows ONLY licence keys — never videos, brands or projects.
//   GET  /buy                      -> pick how to pay: PayFast (rand, South Africa) or PayPal (dollars, worldwide)
//   GET  /buy/payfast              -> PayFast once-off checkout (PRICE_ZAR)
//   POST /api/payfast/itn          -> PayFast tells us about the payment (verified)
//   GET  /buy/paypal               -> PayPal checkout (PRICE_USD), Orders API
//   GET  /paypal/return?token=…    -> PayPal sends the buyer back: we capture the payment, then show the key
//   GET  /welcome?ref=…            -> after paying: shows their licence key + how to install
//   POST /api/licence/validate     -> the extension checks a key {key, machine} -> {valid, renews, message}
//   POST /api/admin/issue|revoke   -> manual keys (EFT buyers, gifts) / switch a key off (refund, abuse), Bearer ADMIN_TOKEN
//   GET  /api/update/latest        -> the newest release {version, notes, sha256, size, min_extension}
//   POST /api/update/download      -> the release zip, for any paid (not revoked) key {key, machine}
//   POST /api/admin/release        -> publish a release (after uploading its zip to R2), Bearer ADMIN_TOKEN
//
// Storage (Workers KV): "key:<KEY>" -> {email, status, lifetime: true, machines[], ref, source}; "ref:<REF>" -> KEY;
//   "release:latest" -> {version, notes, sha256, size, min_extension}. Release zips live in R2 (binding RELEASES)
//   at "releases/<version>.zip" — the app only, never anyone's files.

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    try {
      if (url.pathname === "/buy") return choose(env);
      if (url.pathname === "/buy/payfast") return buy(url, env);
      if (url.pathname === "/buy/paypal") return await paypalBuy(env);
      if (url.pathname === "/paypal/return") return await paypalReturn(url, env);
      if (url.pathname === "/api/payfast/itn" && req.method === "POST") return await itn(req, env);
      if (url.pathname === "/welcome") return await welcome(url, env);
      if (url.pathname === "/api/licence/validate" && req.method === "POST") return await validate(req, env);
      if (url.pathname === "/api/update/latest") return json(JSON.parse(await env.LICENCES.get("release:latest") || "{}"));
      if (url.pathname === "/api/update/download" && req.method === "POST") return await download(req, env);
      if (url.pathname.startsWith("/api/admin/") && req.method === "POST") return await admin(req, env, url);
      return new Response("Reelmate licence service", { status: 200 });
    } catch (e) {
      return json({ error: "server_error" }, 500);
    }
  },
};

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json" } });
const page = (title, body) => new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title><body style="font:16px/1.6 Nunito,system-ui,sans-serif;background:#FDF6EB;color:#17392B;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px">
<main style="max-width:560px;background:#FFFDF8;border:1px solid #EADFCD;border-radius:22px;padding:28px">${body}</main></body>`, { headers: { "content-type": "text/html; charset=utf-8" } });

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
  ];                                                                       // once-off: no subscription fields
  const sig = pfSignature(pairs, env.PAYFAST_PASSPHRASE);
  const inputs = pairs.concat([["signature", sig]]).map(([k, v]) => `<input type="hidden" name="${k}" value="${String(v).replace(/"/g, "&quot;")}">`).join("");
  return page("Reelmate — checkout", `<h1 style="color:#104631">Reelmate</h1><p>Taking you to PayFast for your once-off payment…</p>
<form id="f" method="post" action="https://${env.PAYFAST_HOST}/eng/process">${inputs}<button style="padding:12px 20px;border-radius:999px;border:0;background:#E8541E;color:#fff;font-weight:700">Continue to PayFast</button></form>
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
    rec.status = "active";
    rec.lifetime = true;                                       // paid once: theirs forever, updates included
    rec.source = "payfast";
    await env.LICENCES.put(`key:${key}`, JSON.stringify(rec));
  }
  return new Response("OK");
}

async function welcome(url, env) {
  const ref = url.searchParams.get("ref") || "";
  const key = ref && await env.LICENCES.get(`ref:${ref}`);
  if (!key) return page("Reelmate — almost there", `<h1>Payment received?</h1><p>We're confirming it with PayFast — this page will show your licence key in a few seconds.</p><script>setTimeout(()=>location.reload(),4000)</script>`);
  return page("Welcome to Reelmate", `<h1 style="color:#104631">You're in 🎬</h1>
<p>Your licence key (yours forever):</p><p style="font:700 22px ui-monospace,monospace;background:#E6F0EC;padding:12px 16px;border-radius:12px;user-select:all">${key}</p>
<ol><li>Download <a style="color:#E8541E" href="${env.PUBLIC_URL}/download">Reelmate for Claude</a> (Windows or Mac).</li>
<li>Double-click the file — Claude opens and asks to install it. Click <b>Install</b>.</li>
<li>Paste your licence key when Claude asks. Done — say “edit my reel”.</li></ol>
<p style="color:#5E6B63">Keep this key safe. It works on up to ${env.MAX_MACHINES} computers.</p>`);
}

async function validate(req, env) {
  const { key = "", machine = "" } = await req.json().catch(() => ({}));
  const raw = await env.LICENCES.get(`key:${String(key).trim().toUpperCase()}`);
  if (!raw) return json({ valid: false, message: "That licence key wasn't found. Check it on your Reelmate welcome page." });
  const rec = JSON.parse(raw);
  if (!paid(rec)) return json({ valid: false, message: "This Reelmate key was switched off. Contact support." });
  const machines = rec.machines || [];
  if (machine && !machines.includes(machine)) {
    if (machines.length >= parseInt(env.MAX_MACHINES || "2")) return json({ valid: false, message: `This key is already used on ${machines.length} computers. Contact support to move it.` });
    machines.push(machine); rec.machines = machines;
    await env.LICENCES.put(`key:${String(key).trim().toUpperCase()}`, JSON.stringify(rec));
  }
  return json({ valid: true, plan: "lifetime", message: "Reelmate is yours forever — updates included." });
}

function paid(rec) {                                           // bought once = forever, unless switched off (refund)
  return rec.status !== "revoked";
}

async function activeKey(key, machine, env) {
  const raw = await env.LICENCES.get(`key:${String(key).trim().toUpperCase()}`);
  if (!raw) return false;
  const rec = JSON.parse(raw);
  return paid(rec) && (!machine || (rec.machines || []).includes(machine));
}

async function download(req, env) {
  const { key = "", machine = "" } = await req.json().catch(() => ({}));
  if (!(await activeKey(key, machine, env))) return json({ error: "Updates are for paid Reelmate keys." }, 403);
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
  if (url.pathname === "/api/admin/issue") {             // EFT buyers, gifts: always a forever key
    const key = newKey();
    await env.LICENCES.put(`key:${key}`, JSON.stringify({ email: b.email || "", status: "active", machines: [],
      lifetime: true, source: b.source || "manual" }));
    return json({ key });
  }
  if (url.pathname === "/api/admin/revoke" || url.pathname === "/api/admin/restore") {
    const raw = await env.LICENCES.get(`key:${b.key}`);
    if (!raw) return json({ error: "not_found" }, 404);
    const rec = JSON.parse(raw);
    rec.status = url.pathname.endsWith("revoke") ? "revoked" : "active";
    await env.LICENCES.put(`key:${b.key}`, JSON.stringify(rec));
    return json({ ok: true, status: rec.status });
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

// ---------------------------------------------------------------- choose how to pay
function choose(env) {
  const btn = (href, bg, label, sub) => `<a href="${href}" style="display:block;text-decoration:none;background:${bg};color:#fff;border-radius:18px;padding:16px 20px;margin:12px 0;font-weight:800;font-size:18px">${label}<span style="display:block;font-weight:600;font-size:14px;opacity:.9">${sub}</span></a>`;
  return page("Get Reelmate", `<h1 style="color:#104631;margin-top:0">Get Reelmate</h1>
<p>One payment. Yours forever, with every update. No subscription.</p>
${btn("/buy/payfast", "#E8541E", `R${Number(env.PRICE_ZAR).toFixed(0)} · South Africa`, "Card, EFT, SnapScan and more (PayFast)")}
${btn("/buy/paypal", "#104631", `$${Number(env.PRICE_USD).toFixed(0)} · Everywhere else`, "PayPal or card (PayPal)")}
<p style="color:#5E6B63;font-size:14px">Your key appears straight after paying. Works on ${env.MAX_MACHINES} computers.</p>`);
}

// ---------------------------------------------------------------- PayPal (Orders v2)
async function ppToken(env) {
  const r = await fetch(`https://${env.PAYPAL_API}/v1/oauth2/token`, { method: "POST",
    headers: { authorization: "Basic " + btoa(`${env.PAYPAL_CLIENT_ID}:${env.PAYPAL_SECRET}`), "content-type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials" });
  return (await r.json()).access_token;
}

async function paypalBuy(env) {
  const ref = crypto.randomUUID().replace(/-/g, "");
  const tok = await ppToken(env);
  const r = await fetch(`https://${env.PAYPAL_API}/v2/checkout/orders`, { method: "POST",
    headers: { authorization: `Bearer ${tok}`, "content-type": "application/json" },
    body: JSON.stringify({ intent: "CAPTURE",
      purchase_units: [{ reference_id: ref, custom_id: ref, description: env.PRODUCT,
                         amount: { currency_code: "USD", value: Number(env.PRICE_USD).toFixed(2) } }],
      application_context: { brand_name: "Reelmate", user_action: "PAY_NOW", shipping_preference: "NO_SHIPPING",
                             return_url: `${env.PUBLIC_URL}/paypal/return`, cancel_url: `${env.PUBLIC_URL}/buy` } }) });
  const order = await r.json();
  const approve = (order.links || []).find(l => l.rel === "approve" || l.rel === "payer-action");
  if (!approve) return page("Reelmate — PayPal", "<h1>PayPal is busy</h1><p>Please try again in a minute.</p>");
  return Response.redirect(approve.href, 302);
}

async function paypalReturn(url, env) {
  const id = url.searchParams.get("token") || "";
  if (!/^[A-Z0-9]{5,40}$/.test(id)) return page("Reelmate", "<h1>Something went wrong</h1><p>Start again at /buy.</p>");
  const done = await env.LICENCES.get(`pp:${id}`);              // refreshed the page: show the same key again
  if (done) return Response.redirect(`${env.PUBLIC_URL}/welcome?ref=${done}`, 302);
  const tok = await ppToken(env);
  const r = await fetch(`https://${env.PAYPAL_API}/v2/checkout/orders/${id}/capture`, { method: "POST",
    headers: { authorization: `Bearer ${tok}`, "content-type": "application/json" } });
  const cap = await r.json();
  const unit = (cap.purchase_units || [])[0] || {};
  const pay = ((unit.payments || {}).captures || [])[0] || {};
  if (cap.status !== "COMPLETED" || pay.status !== "COMPLETED" || pay.amount?.currency_code !== "USD"
      || Math.abs(parseFloat(pay.amount?.value) - parseFloat(env.PRICE_USD)) > 0.01)
    return page("Reelmate — payment not finished", "<h1>Payment not finished</h1><p>Nothing was charged. <a href='/buy'>Try again</a>.</p>");
  const ref = unit.reference_id || id;
  const key = newKey();
  await env.LICENCES.put(`key:${key}`, JSON.stringify({ email: cap.payer?.email_address || "", status: "active", lifetime: true,
    machines: [], ref, source: "paypal", paypal_order: id }));
  await env.LICENCES.put(`ref:${ref}`, key);
  await env.LICENCES.put(`pp:${id}`, ref);
  return Response.redirect(`${env.PUBLIC_URL}/welcome?ref=${ref}`, 302);
}
