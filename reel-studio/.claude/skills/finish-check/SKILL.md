---
name: finish-check
description: The last step of EVERY reel before showing the user — check the render like a pro editor and fix problems first, so the user reacts "wow" instead of asking "why". Always use after rendering a final.
---

# Finish check (never skip)

The engine already auto-fixes a lot (stabilising, face-framed zooms, push-ins on static stretches,
hook motion, stickers off faces, noise clean-up, colour/exposure correction, loudness). Your job is
the final eye:

1. Read the render output: "What I did", "Checks", and any **PROBLEMS** line. Fix PROBLEMS first.
2. Look at `projects/<p>/renders/check.jpg` (12 frames, one image). Check:
   - text readable (size, contrast), nothing cut off or under the app buttons
   - no sticker/text on a face; not more than 2 graphics at once; stickers match the brand look
   - title visible against the background; captions not covering the product
   - frames look corrected (no colour cast, not too dark), the look fits the vibe
3. Anything off → edit `timeline.json` (move/scale/remove items, add a zoom) → re-render → re-check.
4. Deliver it on the review page (never only as a raw file — some players, like the Claude
   desktop app, can't play the normal AAC audio): `python -m engine share <p> --options v<N>`,
   then publish `projects/<p>/renders/review/index.html` with its media files
   (`reel-opus.mp4`, `reel.mp4`, `soundtrack.mp3`) as a page with `capabilities: {db: {}}`
   (first time; later versions republish the same page) and give the user the link.
   Their timestamped notes land in the page's `feedback` collection: read them, make the
   changes, re-render, republish, and mark each note `status: "done"`.
5. Present it with a short "what I did" list in plain words (from the render output), e.g.
   "steadied the shaky footage · punched in on your face at every cut · cleaned the background
   noise · balanced the yellow light · highlighted your key words". Then offer 2 quick tweaks.
