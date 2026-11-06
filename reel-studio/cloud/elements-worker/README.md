# Reel Studio AI elements service

Lets every Reel Studio customer generate their reel's custom sticker sets with **no account or key of their
own**: the studio calls this small service on the Reel Studio owner's Cloudflare account, which runs
FLUX.1 schnell (Apache 2.0, commercial use OK) on Workers AI.

**Cost:** 10,000 free neurons a day, then about $0.011 per 1,000 neurons. One sticker sheet (1024 px, 4 steps)
is roughly 40–60 neurons, so well under 1 US cent a sheet (about 170–230 free sheets a day).

## Switch it on (once, about 10 minutes)
1. Free Cloudflare account → install Node.js → in this folder: `npx wrangler login`.
2. `npx wrangler kv namespace create USAGE` → paste the id into `wrangler.toml` (uncomment that block).
3. Quick start keys: `npx wrangler secret put LICENSE_KEYS` → paste comma-separated licence keys.
   (Later: a `LICENSES` KV namespace, one entry per customer key, filled by the subscription system.)
4. `npx wrangler deploy` → it prints the URL, e.g. `https://reelstudio-elements.<you>.workers.dev`.
5. In the studio: `brand/ai.json` → `{"provider": "reelstudio", "url": "<that URL>", "key": "<licence key>"}`
   (shipped builds fill these in from the customer's licence automatically).

Check: `curl https://<url>/health`.
