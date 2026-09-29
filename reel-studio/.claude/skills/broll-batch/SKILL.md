---
name: broll-batch
description: Turn long b-roll clips into many short clips and batch "trial reels" (hook on b-roll + caption map). Use when the user has long clips, wants to batch content, make trial reels, "chop my footage", or "make as many reels as possible".
---

# B-roll batch + trial reels

1. `python -m engine chop <file-or-folder> [--options 6]` → best 6 s clips in inbox/broll-cuts/
   (scored for sharpness, steadiness, exposure; never across a scene change) + a numbered
   contact sheet. Look at the sheet once; drop weak/duplicate clips.
2. Write hooks in their voice (`hooks-and-scripts`, brand/voice.md). Show the list as
   "clip 3 — POV: …" and let them approve/edit (one message, numbered).
3. Write `out/trial.json`: [{"clip": ..., "hook": ..., "caption": ...}] then
   `python -m engine trial out/trial.json` → out/trial-reels/*.mp4 + captions.md (file → caption,
   copy-paste ready). Long batch? Say it runs on their computer and they can leave it overnight.
4. Voiceover reels: when clips should follow a story (messy → clean, raw → finished), look at
   the contact sheet and order the b-roll to match the voiceover lines before planning.
