// Reelmate sales service (Cloudflare Worker). People pay ONCE on your landing page and download Reelmate straight
// away: a ZIP they unzip and install. No licence keys, no accounts, nothing paid inside the app. Updates included.
//
// Your landing page's buy buttons link to:
//   GET  /buy                      -> (optional) pick how to pay: PayFast (rand, South Africa) or PayPal (dollars, worldwide)
//   GET  /buy/payfast              -> PayFast once-off checkout (PRICE_ZAR)
//   GET  /buy/paypal               -> PayPal checkout (PRICE_USD), Orders API
// After paying:
//   POST /api/payfast/itn          -> PayFast tells us about the payment (verified)
//   GET  /paypal/return?token=…    -> PayPal sends the buyer back: we capture the payment
//   GET  /welcome?ref=…            -> "Thank you": the download starts by itself + how to install + their own download link
//   GET  /download/<ref>           -> the newest Reelmate ZIP (paid purchases only; MAX_DOWNLOADS per purchase)
// Updates (the app asks once a day; it uses the download link saved on the computer, never a key):
//   GET  /api/update/latest        -> the newest release {version, notes, sha256, size, min_extension}
//   POST /api/update/download      -> the release zip for a paid purchase {link}
// You (Bearer ADMIN_TOKEN):
//   POST /api/admin/release        -> publish a release (after uploading its zip to R2)
//   POST /api/admin/issue          -> a download link for an EFT buyer / a gift {email}
//   POST /api/admin/revoke|restore -> switch a purchase's link off (refund) or on again {ref}
//
// Storage (Workers KV, binding LICENCES): "buy:<REF>" -> {email, status, source, created, downloads};
//   "pp:<PAYPAL ORDER>" -> REF; "release:latest" -> {...}. Release zips live in R2 (binding RELEASES) at
//   "releases/<version>.zip" — the app only, never anyone's files.

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
      if (url.pathname.startsWith("/download/")) return await downloadZip(url.pathname.split("/")[2] || "", env, true);
      if (url.pathname === "/api/update/latest") return json(JSON.parse(await env.LICENCES.get("release:latest") || "{}"));
      if (url.pathname === "/api/update/download" && req.method === "POST") return await updateZip(req, env);
      if (url.pathname.startsWith("/api/admin/") && req.method === "POST") return await admin(req, env, url);
      return new Response("Reelmate", { status: 200 });
    } catch (e) {
      return json({ error: "server_error" }, 500);
    }
  },
};

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json" } });
const page = (title, body) => new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title><body style="font:16px/1.6 Nunito,system-ui,sans-serif;background:#FDF6EB;color:#17392B;display:grid;place-items:center;min-height:100vh;margin:0;padding:16px">
<main style="max-width:560px;background:#FFFDF8;border:1px solid #EADFCD;border-radius:22px;padding:28px">${body}</main></body>`, { headers: { "content-type": "text/html; charset=utf-8" } });

const newRef = () => crypto.randomUUID().replace(/-/g, "");
const refOk = ref => /^[a-f0-9]{32}$/.test(ref);
async function purchase(ref, env) {
  if (!refOk(ref)) return null;
  const raw = await env.LICENCES.get(`buy:${ref}`);
  return raw ? JSON.parse(raw) : null;
}
async function recordPurchase(ref, env, fields) {
  const rec = Object.assign({ status: "active", downloads: 0, created: new Date().toISOString().slice(0, 10) },
                            await purchase(ref, env) || {}, fields);
  await env.LICENCES.put(`buy:${ref}`, JSON.stringify(rec));
  return rec;
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
  const ref = newRef();
  const pairs = [
    ["merchant_id", env.PAYFAST_MERCHANT_ID], ["merchant_key", env.PAYFAST_MERCHANT_KEY],
    ["return_url", `${env.PUBLIC_URL}/welcome?ref=${ref}`], ["cancel_url", env.LANDING_URL || `${env.PUBLIC_URL}/buy`],
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
  if (!refOk(ref)) return new Response("bad ref", { status: 400 });
  if (data.payment_status === "COMPLETE") {
    if (Math.abs(parseFloat(data.amount_gross) - parseFloat(env.PRICE_ZAR)) > 0.01) return new Response("amount mismatch", { status: 400 });
    await recordPurchase(ref, env, { email: data.email_address || "", source: "payfast" });
  }
  return new Response("OK");
}

async function welcome(url, env) {
  const ref = url.searchParams.get("ref") || "";
  const rec = await purchase(ref, env);
  if (!rec) return page("Reelmate — almost there", `<h1 style="color:#104631">Thank you!</h1><p>We're confirming your payment. Your download starts on this page in a few seconds…</p><script>setTimeout(()=>location.reload(),4000)</script>`);
  if (!paid(rec)) return page("Reelmate", `<h1>This purchase was refunded</h1><p>Questions? Reply to your payment receipt.</p>`);
  const link = `${env.PUBLIC_URL}/download/${ref}`;
  const mine = `${env.PUBLIC_URL}/welcome?ref=${ref}`;
  return page("Welcome to Reelmate", `<h1 style="color:#104631;margin-top:0">You're in! 🎬</h1>
<p>Reelmate is yours forever, with every update. Your download is starting…</p>
<p><a href="${link}" style="display:inline-block;background:#E8541E;color:#fff;text-decoration:none;font-weight:800;border-radius:999px;padding:14px 26px;font-size:18px">Download Reelmate</a></p>
<h2 style="font-size:18px;color:#104631">Install it (about 10 minutes, once)</h2>
<ol><li>Open your <b>Downloads</b> folder and unzip <b>Reelmate.zip</b> (Windows: right-click → <i>Extract All</i>. Mac: double-click it).</li>
<li><b>Windows:</b> double-click <b>Install Reelmate</b>. <b>Mac:</b> double-click <b>Install Reelmate.command</b>. It installs everything it needs by itself.</li>
<li>Double-click <b>Reelmate</b> to open your studio. Done!</li></ol>
<p style="background:#E6F0EC;border-radius:14px;padding:12px 14px;font-size:14.5px"><b>Keep this page's link</b> (bookmark it): it's your personal download
link for a new computer, and Reelmate uses it for free updates.<br><span style="user-select:all;word-break:break-all;font-weight:700">${mine}</span></p>
<script>setTimeout(()=>{ location.href = ${JSON.stringify(link)}; }, 1500)</script>`);
}

function paid(rec) {                                           // bought once = forever, unless switched off (refund)
  return rec && rec.status !== "revoked";
}

async function downloadZip(ref, env, count) {
  const rec = await purchase(ref, env);
  if (!paid(rec)) return page("Reelmate", "<h1>Download link not found</h1><p>Use the link on your Reelmate welcome page, or reply to your payment receipt.</p>");
  if (count && (rec.downloads || 0) >= parseInt(env.MAX_DOWNLOADS || "25"))
    return page("Reelmate", "<h1>This link was used a lot</h1><p>Reply to your payment receipt and we'll send you a fresh one.</p>");
  const rel = JSON.parse(await env.LICENCES.get("release:latest") || "{}");
  if (!rel.version || !env.RELEASES) return page("Reelmate", "<h1>Almost ready</h1><p>The download is being prepared. Try again in a few minutes.</p>");
  const obj = await env.RELEASES.get(`releases/${rel.version}.zip`);
  if (!obj) return page("Reelmate", "<h1>Almost ready</h1><p>The download is being prepared. Try again in a few minutes.</p>");
  if (count) await recordPurchase(ref, env, { downloads: (rec.downloads || 0) + 1 });
  return new Response(obj.body, { headers: { "content-type": "application/zip", "x-version": rel.version,
    "content-disposition": `attachment; filename="Reelmate-${rel.version}.zip"` } });
}

async function updateZip(req, env) {                           // the app's daily update: {link} = their own download link
  const { link = "" } = await req.json().catch(() => ({}));
  const ref = (String(link).match(/[a-f0-9]{32}/) || [""])[0];
  if (!paid(await purchase(ref, env))) return json({ error: "Updates use the download link from your welcome page." }, 403);
  return downloadZip(ref, env, false);
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
  if (url.pathname === "/api/admin/issue") {             // EFT buyers, gifts: a download link that is theirs forever
    const ref = newRef();
    await recordPurchase(ref, env, { email: b.email || "", source: b.source || "manual" });
    return json({ ref, welcome: `${env.PUBLIC_URL}/welcome?ref=${ref}` });
  }
  if (url.pathname === "/api/admin/revoke" || url.pathname === "/api/admin/restore") {
    const rec = await purchase(b.ref || "", env);
    if (!rec) return json({ error: "not_found" }, 404);
    const out = await recordPurchase(b.ref, env, { status: url.pathname.endsWith("revoke") ? "revoked" : "active" });
    return json({ ok: true, status: out.status });
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
<p style="color:#5E6B63;font-size:14px">Your download starts straight after paying. Windows or Mac.</p>`);
}

// ---------------------------------------------------------------- PayPal (Orders v2)
async function ppToken(env) {
  const r = await fetch(`https://${env.PAYPAL_API}/v1/oauth2/token`, { method: "POST",
    headers: { authorization: "Basic " + btoa(`${env.PAYPAL_CLIENT_ID}:${env.PAYPAL_SECRET}`), "content-type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials" });
  return (await r.json()).access_token;
}

async function paypalBuy(env) {
  const ref = newRef();
  const tok = await ppToken(env);
  const r = await fetch(`https://${env.PAYPAL_API}/v2/checkout/orders`, { method: "POST",
    headers: { authorization: `Bearer ${tok}`, "content-type": "application/json" },
    body: JSON.stringify({ intent: "CAPTURE",
      purchase_units: [{ reference_id: ref, custom_id: ref, description: env.PRODUCT,
                         amount: { currency_code: "USD", value: Number(env.PRICE_USD).toFixed(2) } }],
      application_context: { brand_name: "Reelmate", user_action: "PAY_NOW", shipping_preference: "NO_SHIPPING",
                             return_url: `${env.PUBLIC_URL}/paypal/return`, cancel_url: env.LANDING_URL || `${env.PUBLIC_URL}/buy` } }) });
  const order = await r.json();
  const approve = (order.links || []).find(l => l.rel === "approve" || l.rel === "payer-action");
  if (!approve) return page("Reelmate — PayPal", "<h1>PayPal is busy</h1><p>Please try again in a minute.</p>");
  return Response.redirect(approve.href, 302);
}

async function paypalReturn(url, env) {
  const id = url.searchParams.get("token") || "";
  if (!/^[A-Z0-9]{5,40}$/.test(id)) return page("Reelmate", "<h1>Something went wrong</h1><p>Start again at /buy.</p>");
  const done = await env.LICENCES.get(`pp:${id}`);              // refreshed the page: same welcome page again
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
  const ref = refOk(unit.reference_id || "") ? unit.reference_id : newRef();
  await recordPurchase(ref, env, { email: cap.payer?.email_address || "", source: "paypal", paypal_order: id });
  await env.LICENCES.put(`pp:${id}`, ref);
  return Response.redirect(`${env.PUBLIC_URL}/welcome?ref=${ref}`, 302);
}
