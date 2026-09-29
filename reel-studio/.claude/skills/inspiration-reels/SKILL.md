---
name: inspiration-reels
description: Make the user's reel feel like a reel they love. Use when the user pastes a TikTok/Instagram/YouTube link (or several), says "make it like this", "this is my style", or fills the optional inspiration link in the Studio.
---

# Match an inspiration reel (optional step — skip if they have none)

1. `python -m engine inspire <link> --name <short-name>` (downloads, measures cuts/min, sound
   events per second, speech speed, colour; writes brand/inspiration/<name>.json and a 12-frame
   contact sheet). Several links → run each; the style is what they share.
   TikTok profiles can't be listed automatically — ask for individual video links.
2. Look at the contact sheet ONCE and fill `claude_notes` in the json:
   `caption_style` (kinetic · duo · pop · popin · boxed · shadow · off), `text_treatments` (where text
   sits, how big, mixed fonts?), `format` (talking · framed · vlog · photo dump · motion-design — "vlog" switches on vlog mode: captions off, a held `tag` label, short clips), `energy`,
   `what_to_borrow` (3 bullets). Numbers miss animated text — trust your eyes over "cuts/min".
3. In plan.json set `"inspiration": "<name>"` — its settings (speed, captions, grade, sound kit,
   framed layouts) fill anything the plan doesn't set. Override freely.
4. Tell the user in 2 lines what you borrowed ("fast pace, key words big in script, framed
   moments, playful sounds") — never copy their words, footage, music or graphics.
Also: "speed it up" → `"speed": 1.1–1.25` in plan.json (voice pitch stays natural).
