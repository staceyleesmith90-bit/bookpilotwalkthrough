// Reel Studio · AI elements service (Cloudflare Worker + Workers AI, FLUX.1 schnell)
//
// Runs on the Reel Studio owner's Cloudflare account, so customers draw their reels' sticker sets with no
// account, key or setup of their own. The studio calls it with the customer's Reel Studio licence key.
//
//   POST /v1/elements   {"prompt": "...", "seed": 7, "size": 1024}
//   header  Authorization: Bearer <licence key>
//   → image/png  (headers: X-Elements-Left = sheets left today for this key)
//
// Limits: DAILY_LIMIT sheets per licence key per day (KV "USAGE"); keys are checked against LICENSES (KV),
// or the comma-separated secret LICENSE_KEYS for a quick start. Nothing is stored except the daily counter.

const MODEL = "@cf/black-forest-labs/flux-1-schnell";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

async function validKey(env, key) {
  if (!key || key.length < 12) return false;
  if (env.LICENSE_KEYS && env.LICENSE_KEYS.split(",").map((k) => k.trim()).includes(key)) return true;
  if (env.LICENSES) return (await env.LICENSES.get(key)) !== null;
  return false;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return json({ ok: true, model: MODEL });
    if (url.pathname !== "/v1/elements" || request.method !== "POST") return json({ error: "not found" }, 404);

    const key = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
    if (!(await validKey(env, key))) return json({ error: "Unknown Reel Studio licence key." }, 401);

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Send JSON: {\"prompt\": \"...\"}" }, 400);
    }
    const prompt = String(body.prompt || "").slice(0, 2000);
    if (prompt.length < 10) return json({ error: "The prompt is too short." }, 400);

    const limit = parseInt(env.DAILY_LIMIT || "20", 10);
    const day = new Date().toISOString().slice(0, 10);
    const counter = `${key}:${day}`;
    const used = env.USAGE ? parseInt((await env.USAGE.get(counter)) || "0", 10) : 0;
    if (used >= limit) return json({ error: `Today's ${limit} sticker sheets are used up — more tomorrow.` }, 429);

    const out = await env.AI.run(MODEL, {
      prompt,
      steps: 4,
      ...(Number.isInteger(body.seed) ? { seed: body.seed } : {}),
    });
    if (env.USAGE) await env.USAGE.put(counter, String(used + 1), { expirationTtl: 60 * 60 * 48 });

    const png = Uint8Array.from(atob(out.image), (c) => c.charCodeAt(0));
    return new Response(png, {
      headers: { "Content-Type": "image/jpeg", "X-Elements-Left": String(limit - used - 1) },
    });
  },
};
