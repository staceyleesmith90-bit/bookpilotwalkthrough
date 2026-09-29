---
name: overlays-and-logos
description: Put the user's own logo, watermark, product photos, screenshots or other images onto reels, and let them move them. Use when the user attaches or drops files, or says "add my logo", "move my logo", "put this image here", "watermark", "add this product".
---

# Overlays and logos

## Where files come from
- Attached in chat → save a copy into `inbox/`.
- Dragged into the `inbox/` folder → `layout.inbox_files(ROOT)` lists them.
- PNG, JPG, WEBP, SVG accepted (animated GIF/MP4 → use as b-roll: `broll:inbox/x.mp4`).

## The brand logo
Set once in brand.json (`"logo": {"file", "position", "width"}`) during onboarding. The
planner puts it on **every** reel (fading in, whole reel, above everything, in a safe corner,
with a soft pill behind it if it would disappear on the background). Turn off for one reel
with `"logo": false` in plan.json, or override with `"logo": {"position": "bottom-right"}`.

**Moving it:** exact spot → set `"x"`/`"y"` in the plan's logo object, or the user drags it in
the manual editor (`manual-editor` skill). To make a new position the default for all future
reels, copy the x/y into brand.json's logo.

## Other images
| File | Default |
|---|---|
| Product photo | pop in when the product is mentioned; die-cut look |
| Screenshot | card near the line it supports |
| Photo of a person/place | cut-out with arrow sticker + short `label` |

Add them in the timeline as `{"type": "overlay", "file": "inbox/x.png", "start", "end", "x",
"y", "width", "anim": "pop"}` (or via the editor's ＋ Add → Your files). The user's 📎
attachments from the review page are in `roughcut.json` → place them on that line's time.

## Rules
- White-box JPG logos: `knock_out_white: true` (default for logos).
- Keep aspect ratio; never cover faces or captions (placement does this).
- Only use files the user owns or provided.
