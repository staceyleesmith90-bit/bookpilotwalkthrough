---
name: manual-editor
description: Open the drag-and-drop timeline editor so the user can move, resize, retime or restyle anything themselves (logo, text, stickers, images, b-roll, zooms, sound effects). Use when the user says "let me move it myself", "I want to adjust", "move my logo", "open the editor", or wants fine control.
---

# Manual editor

`python -m engine editor <project>` → opens http://localhost:8765 in their browser.
Runs locally, no credits. Tell them what they can do:

- **Move** anything by dragging it on the video (logo, text, stickers, bubbles, images).
- **Resize** with the pink dot; **rotate**, **animation**, **colour**, **sticker style** in the side panel.
- **Retime**: drag a bar on the timeline to move it, drag its edges to trim. Sound effects are
  the diamonds on the Sound FX row — drag them too.
- **Edit text** in the side panel (it re-fits automatically).
- **Add**: text, badge, thought bubble, any sticker or emoji (`emoji:🔥`, `emoji:coffee`), or a
  file from their `inbox/` (logos, product photos).
- **Pack switcher** restyles the whole reel instantly.
- **Quick preview** (half size, fast) and **Render final** — results play right in the page.
- Undo with Ctrl/Cmd+Z; arrow keys nudge; Space plays.

Everything saves to `projects/<p>/timeline.json`. If they come back to chat afterwards, read
only what you need from the timeline (e.g. the logo item) — their manual changes are final
unless they ask you to change them. Rebuilding from plan.json would overwrite manual
changes: warn before doing that.

To stop the editor: Ctrl+C in the terminal where it runs (or just close it later).
