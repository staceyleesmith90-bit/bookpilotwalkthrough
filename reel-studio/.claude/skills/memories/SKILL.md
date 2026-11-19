---
name: memories
description: Turn the day's photos and clips into a keepsake video for the camera roll — for moms with hundreds of photos of their kids and anyone who loves sharing without being an influencer. Use when the user drops a bunch of family/day photos, says "make a memory video", "our day", "save these memories", "photo dump of the kids", "holiday video", "birthday video", or picks Memories in the Studio.
---

# Memories (photos of the day → a keepsake video)

Warm, gentle, personal. Not a sales reel: no hook tricks, no call to action, no end card.

1. **Bring the photos in.** From a phone, big sets go best through a **Google Drive** folder link (or a shared
   album download) — `python -m engine memories <project> <link>`; or tick Uploads in the Studio.
2. **Ask once (tap answers + "type it"):** "What happened today? A few words or a voice note is perfect."
   Turn their words into 3–8 short, warm lines in THEIR voice ("she pulled the cat's tail", "boetie came to play",
   "my heart, full"). Their language (Afrikaans stays Afrikaans). Never invent events.
3. `python -m engine memories <project> --name "<title>" --story "line; line; line"` — it picks the keepers
   (time order, near-identical burst shots collapsed to the sharpest, blurry/dark ones skipped, max ~16),
   gives every photo a slow zoom/pan, mutes clip sound (usually mom talking — ask before keeping it), adds a
   date + title opener, a scrapbook page, a soft ending, calm piano and a cover.
4. Look at `renders/footage-sheet.jpg` or the storyboard and **move each story line onto the photo it's about**
   (plan beats → the collage label), e.g. "boetie came to play" on the photo with both kids. Faces stay clear.
5. Optional sweetness: an AI sticker set from the day (sticker-studio: clay or watercolour), moving stickers.
6. Storyboard → render → hand over the plays-in-Claude copy + say "saved for your camera roll".
Kids' names, ages and places stay in the project (private, never in git).
