# Reelmate as a one-click Claude extension (and for Codex)

**The customer's experience**
1. Pay once on the landing page (PayFast R1000 or PayPal $59, no subscription) → the welcome page starts the
   download straight away (the Reelmate ZIP) and gives them their own download link (for a new computer + updates).
2. Unzip → double-click **Install Reelmate** (Windows) / **Install Reelmate.command** (Mac). No licence key, ever.
3. Optional: `reel-studio-<version>.mcpb` → Claude Desktop asks to install → **Install**. In any Claude chat:
   "edit my reel", "interview me", "make it like this link".

**What stays where**
- Videos, brand, projects and finished reels: on their computer, in `Documents/Reelmate`
  (Inbox for new videos). Nothing is uploaded; we store no files.
- Thinking: their own Claude plan. We pay no AI costs.
- Our server: only the sales service — `licence-service/`, a free Cloudflare Worker fed by PayFast (rand) and
  PayPal (dollars). It records who paid and hands out the ZIP (and updates). No keys, no trials, no accounts.
- First run downloads the editing tools once (Python packages, ffmpeg, the animation browser) —
  a few minutes, automatic.

**Build the file:** `python scripts/build_extension.py` → `dist/reel-studio-<version>.mcpb`

**Codex (ChatGPT's coding agent, Windows/Mac/Linux):** unzip the .mcpb somewhere, then
```
codex mcp add reel-studio -- uv --directory /path/to/reel-studio-ext run src/server.py
```
(or the same as a `[mcp_servers.reel-studio]` table in `~/.codex/config.toml`). Same tools, same
playbooks, their own ChatGPT plan pays for the thinking.

**ChatGPT app (chat.openai.com / desktop):** only connects to tools hosted online, so it can't run
the local editor without uploading videos to a server. Not offered (keeps the "nothing stored" promise).

**Sales service — go live checklist (Gert / Stacey-Lee)**
1. Free Cloudflare account → `cd licence-service && npx wrangler kv namespace create LICENCES` → paste id in wrangler.toml.
2. `npx wrangler secret put PAYFAST_MERCHANT_ID` (and PAYFAST_MERCHANT_KEY, PAYFAST_PASSPHRASE, ADMIN_TOKEN).
3. `npx wrangler deploy`, point reelstudio.systemspilot.co.za at it (Cloudflare custom domain).
   On your landing page, the buy buttons link to `https://reelstudio.systemspilot.co.za/buy/payfast` (rand) and
   `/buy/paypal` (dollars), or one button to `/buy` (it asks which). Set LANDING_URL in wrangler.toml.
   Upload the ZIP: `npx wrangler r2 object put reel-releases/releases/<version>.zip --file Reelmate.zip`, then
   `POST /api/admin/release {version, sha256}` (Bearer ADMIN_TOKEN). The newest release is what buyers download.
4. Test with PAYFAST_HOST = sandbox.payfast.co.za first, then switch to www.payfast.co.za.
5. EFT buyers or gifts: `POST /api/admin/issue {email}` (Bearer ADMIN_TOKEN) → their welcome/download link.
   Refund: `/api/admin/revoke {ref}` switches that link off.
6. Prices: PRICE_ZAR / PRICE_USD in licence-service/wrangler.toml. PayPal: `npx wrangler secret put PAYPAL_CLIENT_ID` and `PAYPAL_SECRET` (developer.paypal.com → Apps); test with PAYPAL_API = api-m.sandbox.paypal.com first.
Tests: `node licence-service/test.mjs`.
