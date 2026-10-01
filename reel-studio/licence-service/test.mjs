// node test.mjs — md5, signatures, and the validate/issue flow against an in-memory KV
import worker, { md5, pfSignature } from "./worker.js";
import { createHash } from "node:crypto";
const ok = (c, m) => { if (!c) { console.error("FAIL", m); process.exit(1); } else console.log("ok", m); };
for (const s of ["", "abc", "merchant_id=10000100&amount=449.00&item_name=Reel+Studio", "é ünïcödé 🎬".repeat(20)])
  ok(md5(s) === createHash("md5").update(s).digest("hex"), `md5(${s.slice(0, 20)})`);
const kv = new Map(); const env = { LICENCES: { get: async k => kv.get(k) ?? null, put: async (k, v) => kv.set(k, v) },
  ADMIN_TOKEN: "t0k", MAX_MACHINES: "2", PRICE_ZAR: "449.00", PUBLIC_URL: "https://x", PAYFAST_HOST: "sandbox.payfast.co.za",
  PAYFAST_MERCHANT_ID: "10000100", PAYFAST_MERCHANT_KEY: "46f0cd694581a", PAYFAST_PASSPHRASE: "jt7NOE43FZPn", PRODUCT: "Reel Studio monthly" };
const call = (path, body, auth) => worker.fetch(new Request("https://x" + path, { method: body ? "POST" : "GET",
  headers: { "content-type": "application/json", ...(auth ? { authorization: "Bearer " + auth } : {}) }, body: body && JSON.stringify(body) }), env);
ok((await call("/api/admin/issue", { email: "a@b.c" })).status === 401, "admin needs token");
const { key } = await (await call("/api/admin/issue", { email: "a@b.c", days: 31 }, "t0k")).json();
ok(/^RS-\w{4}-\w{4}-\w{4}$/.test(key), "key format " + key);
let v = await (await call("/api/licence/validate", { key, machine: "m1" })).json(); ok(v.valid, "valid on machine 1");
v = await (await call("/api/licence/validate", { key, machine: "m2" })).json(); ok(v.valid, "valid on machine 2");
v = await (await call("/api/licence/validate", { key, machine: "m3" })).json(); ok(!v.valid, "blocked on a 3rd machine");
v = await (await call("/api/licence/validate", { key: "RS-NOPE", machine: "m1" })).json(); ok(!v.valid, "unknown key rejected");
await call("/api/admin/revoke", { key }, "t0k");
v = await (await call("/api/licence/validate", { key, machine: "m1" })).json(); ok(!v.valid, "revoked key rejected");
const page = await (await call("/buy")).text(); ok(page.includes("sandbox.payfast.co.za/eng/process") && page.includes('name="signature"'), "checkout form");
console.log("all good");
