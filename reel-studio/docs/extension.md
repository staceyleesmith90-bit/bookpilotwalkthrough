# Reel Studio as a one-click Claude extension (and for Codex)

**The customer's experience**
1. Subscribe (PayFast monthly) → the welcome page shows their licence key + the download.
2. Double-click `reel-studio-<version>.mcpb` → Claude Desktop (Windows or Mac) asks to install → **Install**.
3. Paste the licence key when asked. Done. In any Claude chat: "edit my reel", "interview me", "make it like this link".

**What stays where**
- Videos, brand, projects and finished reels: on their computer, in `Documents/Reel Studio`
  (Inbox for new videos). Nothing is uploaded; we store no files.
- Thinking: their own Claude plan. We pay no AI costs.
- Our server: only the licence service (keys + subscription status) — `licence-service/`, a free
  Cloudflare Worker fed by PayFast. Cancel → the key stops working at the end of the paid month.
- First run downloads the editing tools once (Python packages, ffmpeg, the animation browser) —
  a few minutes, automatic.

**Build the file:** `python scripts/build_extension.py` → `dist/reel-studio-<version>.mcpb`

**Codex (ChatGPT's coding agent, Windows/Mac/Linux):** unzip the .mcpb somewhere, then
```
codex mcp add reel-studio --env REEL_LICENSE_KEY=RS-XXXX-XXXX-XXXX -- uv --directory /path/to/reel-studio-ext run src/server.py
```
(or the same as a `[mcp_servers.reel-studio]` table in `~/.codex/config.toml`). Same tools, same
playbooks, their own ChatGPT plan pays for the thinking.

**ChatGPT app (chat.openai.com / desktop):** only connects to tools hosted online, so it can't run
the local editor without uploading videos to a server. Not offered (keeps the "nothing stored" promise).

**Licence service — go live checklist (Gert / Stacey-Lee)**
1. Free Cloudflare account → `cd licence-service && npx wrangler kv namespace create LICENCES` → paste id in wrangler.toml.
2. `npx wrangler secret put PAYFAST_MERCHANT_ID` (and PAYFAST_MERCHANT_KEY, PAYFAST_PASSPHRASE, ADMIN_TOKEN).
3. `npx wrangler deploy`, point reelstudio.systemspilot.co.za at it (Cloudflare custom domain).
4. Test with PAYFAST_HOST = sandbox.payfast.co.za first, then switch to www.payfast.co.za.
5. PayPal / founders / testers: issue keys with `POST /api/admin/issue` (Bearer ADMIN_TOKEN).
Tests: `node licence-service/test.mjs`.
