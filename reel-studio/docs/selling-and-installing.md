# Selling Reel Studio: how buyers get it and install it

## Does it work "on Claude"?
Yes, in **Claude Code** (part of the paid Claude Pro / Max plans), specifically the **Claude
desktop app → Code tab** or the Claude Code terminal app, running on the buyer's own Mac or
Windows computer. It does **not** run inside the normal Claude chat (claude.ai / phone app),
because it needs to run video tools (ffmpeg, transcription) on a computer.

| Where | Works? | Why |
|---|---|---|
| Claude desktop app, Code tab (Mac/Windows) | ✅ best | Runs the engine locally; free, private, fast |
| Claude Code in a terminal | ✅ | Same thing, for techy users |
| Claude Code on the web (cloud) | ⚠️ works for testing | Videos must be uploaded; the container resets |
| claude.ai chat / phone app | ❌ | Can't run video software |

What buyers need: a Claude Pro plan (or higher), a Mac (macOS 13+) or Windows 10/11, ~5 GB free.

## How buyers receive it (pick one)
1. **Private GitHub repo + "invite on purchase"** (best for updates). Sell on Stan Store / Gumroad
   / ThriveCart / Kajabi; after payment, an automation (Zapier/Make) invites their GitHub
   username as a read-only collaborator. They get every update with one click.
   Downside: buyers need a free GitHub account.
2. **Download link (zip)** (simplest for non-techy buyers). Deliver `reel-studio.zip` via the
   checkout page's download. Updates = email a new zip. No GitHub account needed.
3. **Both**: zip for everyone, GitHub access as a bonus for people who want auto-updates.

Recommendation: start with the **zip download** (easiest for creators), add GitHub later.

## Buyer install steps (put these on the thank-you page)
**Mac**
1. Download and unzip `reel-studio.zip` (double-click it). Move the folder to Documents.
2. Open the folder → `install` → double-click **install-mac.command**. (If macOS blocks it:
   right-click → Open → Open.) Wait until it says "All set".
3. Install the **Claude desktop app** (claude.ai/download) and sign in.
4. In Claude, open the **Code** tab → choose the `reel-studio` folder → say **"hi"**.
   Claude runs the brand interview. After that, double-click **Reel Studio.command** any time
   to open the Studio.

**Windows**
1. Download and unzip `reel-studio.zip` (right-click → Extract All). Move it to Documents.
2. Open the folder → `install` → right-click **install-windows.ps1** → **Run with PowerShell**.
   Wait until it says "All set".
3. Install the **Claude desktop app** and sign in.
4. Claude → **Code** tab → choose the `reel-studio` folder → say **"hi"**. Afterwards,
   double-click **Reel Studio.bat** to open the Studio.

## Before you sell (checklist)
- ☐ Test the installer once on a real Mac and a real Windows PC (I could only test on Linux).
- ☐ Add a licence/terms file (personal use, no resale), plus refund policy.
- ☐ Record a 3-minute "install + first reel" video for the thank-you page.
- ☐ Keep `docs/CREDITS.md` in the product (required by the open licences we use).
- ☐ Decide pricing (e.g. one-off price with 12 months of updates).
