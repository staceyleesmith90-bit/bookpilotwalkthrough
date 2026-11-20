// node test.mjs — md5, signatures, and the pay → instant download flow against an in-memory KV
import worker, { md5, pfSignature } from "./worker.js";
import { createHash } from "node:crypto";
const ok = (c, m) => { if (!c) { console.error("FAIL", m); process.exit(1); } else console.log("ok", m); };
for (const s of ["", "abc", "merchant_id=10000100&amount=449.00&item_name=Reel+Studio", "é ünïcödé 🎬".repeat(20)])
  ok(md5(s) === createHash("md5").update(s).digest("hex"), `md5(${s.slice(0, 20)})`);
const kv = new Map(); const env = { LICENCES: { get: async k => kv.get(k) ?? null, put: async (k, v) => kv.set(k, v) },
  ADMIN_TOKEN: "t0k", MAX_MACHINES: "2", PRICE_ZAR: "1000.00", PUBLIC_URL: "https://x", PAYFAST_HOST: "sandbox.payfast.co.za",
  PAYFAST_MERCHANT_ID: "10000100", PAYFAST_MERCHANT_KEY: "46f0cd694581a", PAYFAST_PASSPHRASE: "jt7NOE43FZPn", PRODUCT: "Reelmate", PRICE_USD: "59.00", PAYPAL_API: "api-m.sandbox.paypal.com", PAYPAL_CLIENT_ID: "cid", PAYPAL_SECRET: "sec" };
const call = (path, body, auth) => worker.fetch(new Request("https://x" + path, { method: body ? "POST" : "GET",
  headers: { "content-type": "application/json", ...(auth ? { authorization: "Bearer " + auth } : {}) }, body: body && JSON.stringify(body) }), env);
ok((await call("/api/admin/issue", { email: "a@b.c" })).status === 401, "admin needs token");
const { ref, welcome } = await (await call("/api/admin/issue", { email: "a@b.c" }, "t0k")).json();
ok(/^[a-f0-9]{32}$/.test(ref) && welcome.endsWith(ref), "issue gives a download link " + ref);
// no release yet: a friendly page, not an error
ok((await (await call(`/download/${ref}`)).text()).includes("Almost ready"), "no release yet → friendly page");
env.RELEASES = { get: async p => p === "releases/1.13.0.zip" ? { body: "ZIPDATA" } : null };
ok((await call("/api/admin/release", { version: "1.13.0", sha256: "a".repeat(64), notes: "New effects" })).status === 401, "release needs token");
await call("/api/admin/release", { version: "1.13.0", sha256: "a".repeat(64), notes: "New effects" }, "t0k");
const latest = await (await call("/api/update/latest")).json(); ok(latest.version === "1.13.0" && latest.notes === "New effects", "latest release");
// the welcome page starts the download and shows their own link; the zip downloads
const wpage = await (await call(`/welcome?ref=${ref}`)).text();
ok(wpage.includes(`/download/${ref}`) && wpage.includes("location.href") && wpage.includes(`welcome?ref=${ref}`), "welcome: auto download + own link");
ok(!/licen[cs]e key/i.test(wpage), "welcome page has no licence key");
const z = await call(`/download/${ref}`);
ok(z.status === 200 && z.headers.get("content-type") === "application/zip" && (await z.text()) === "ZIPDATA", "paid link downloads the zip");
ok(z.headers.get("content-disposition").includes("Reelmate-1.13.0.zip"), "zip has a nice name");
ok(JSON.parse(kv.get(`buy:${ref}`)).downloads === 1, "downloads are counted");
ok((await (await call(`/download/${"0".repeat(32)}`)).text()).includes("not found"), "unknown link → no zip");
ok((await (await call(`/download/abc%2F..`)).text()).includes("not found"), "bad link → no zip");
// updates use the saved download link
ok((await call("/api/update/download", { link: welcome })).status === 200, "update with the welcome link");
ok((await call("/api/update/download", { link: "nope" })).status === 403, "update without a link refused");
env.MAX_DOWNLOADS = "2"; await call(`/download/${ref}`);
ok((await (await call(`/download/${ref}`)).text()).includes("used a lot"), "download cap");
delete env.MAX_DOWNLOADS;
// refund: link switched off, and back on
await call("/api/admin/revoke", { ref }, "t0k");
ok((await call("/api/update/download", { link: welcome })).status === 403, "refunded: no updates");
ok((await (await call(`/welcome?ref=${ref}`)).text()).includes("refunded"), "refunded: welcome says so");
await call("/api/admin/restore", { ref }, "t0k");
ok((await call("/api/update/download", { link: welcome })).status === 200, "restored: updates again");
const page = await (await call("/buy/payfast")).text(); ok(page.includes("sandbox.payfast.co.za/eng/process") && page.includes('name="signature"'), "checkout form");
ok(!page.includes("subscription_type") && !page.includes('name="frequency"'), "checkout is once-off (no subscription)");
// no landing page here: /buy and / send people to your own landing page
env.LANDING_URL = "https://reelmate.example";
const lb = await call("/buy"); ok(lb.status === 302 && lb.headers.get("location").startsWith("https://reelmate.example"), "/buy → your landing page");
// PayPal: create order → approve → return → capture → forever key
let captured = 0;
globalThis.fetch = async (u, o = {}) => {
  const url = String(u);
  if (url.endsWith("/v1/oauth2/token")) return new Response(JSON.stringify({ access_token: "AT" }));
  if (url.endsWith("/v2/checkout/orders")) {
    const b = JSON.parse(o.body); ok(b.purchase_units[0].amount.value === "59.00" && b.purchase_units[0].amount.currency_code === "USD", "paypal order is $59");
    globalThis.__ref = b.purchase_units[0].reference_id;
    return new Response(JSON.stringify({ id: "ORDER123", links: [{ rel: "payer-action", href: "https://paypal.test/approve" }] }));
  }
  if (url.endsWith("/v2/checkout/orders/ORDER123/capture")) { captured++;
    return new Response(JSON.stringify({ status: "COMPLETED", payer: { email_address: "buyer@x.com" }, purchase_units: [{ reference_id: globalThis.__ref,
      payments: { captures: [{ status: "COMPLETED", amount: { currency_code: "USD", value: "59.00" } }] } }] })); }
  if (url.endsWith("/v2/checkout/orders/BADAMT/capture"))
    return new Response(JSON.stringify({ status: "COMPLETED", purchase_units: [{ reference_id: "r2", payments: { captures: [{ status: "COMPLETED", amount: { currency_code: "USD", value: "1.00" } }] } }] }));
  throw new Error("unexpected fetch " + url);
};
const go = await call("/buy/paypal"); ok(go.status === 302 && go.headers.get("location") === "https://paypal.test/approve", "paypal: to approval");
const back = await call("/paypal/return?token=ORDER123"); ok(back.status === 302 && back.headers.get("location").includes("/welcome?ref=" + globalThis.__ref), "paypal: captured → welcome");
const ppRec = JSON.parse(kv.get(`buy:${globalThis.__ref}`));
ok(ppRec.status === "active" && ppRec.source === "paypal" && ppRec.email === "buyer@x.com", "paypal: purchase saved");
const again = await call("/paypal/return?token=ORDER123"); ok(again.status === 302 && captured === 1, "paypal: refresh doesn't charge twice");
const wel = await (await call(`/welcome?ref=${globalThis.__ref}`)).text(); ok(wel.includes(`/download/${globalThis.__ref}`), "paypal: welcome page downloads");
const bad = await (await call("/paypal/return?token=BADAMT")).text(); ok(bad.includes("not finished"), "paypal: wrong amount → no download");
console.log("all good");
