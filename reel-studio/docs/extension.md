# Reelmate as a one-click Claude extension (and for Codex)

**The customer's experience**
1. Buy once on the Reelmate website (payment and the download page live there, not in this project) → download the
   Reelmate ZIP straight away. Their download link also gives free updates (pasted once in Studio → Updates).
2. Unzip → double-click **Install Reelmate** (Windows) / **Install Reelmate.command** (Mac). No licence key, ever.
3. Optional: `reel-studio-<version>.mcpb` → Claude Desktop asks to install → **Install**. In any Claude chat:
   "edit my reel", "interview me", "make it like this link".

**What stays where**
- Videos, brand, projects and finished reels: on their computer, in `Documents/Reelmate`
  (Inbox for new videos). Nothing is uploaded; we store no files.
- Thinking: their own Claude plan. We pay no AI costs.
- Payment and downloads: on the Reelmate website (separate from this project). No keys, no trials, no accounts.
  Updates: `library/update.json` → `"feed"` is the website's update address (`<feed>/latest` gives
  {version, notes, sha256}; `<feed>/download` takes {"link"} and returns the ZIP).
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
