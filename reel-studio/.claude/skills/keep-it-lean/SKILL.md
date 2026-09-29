---
name: keep-it-lean
description: Keep Claude usage (plan limits / credits) low while editing reels. Applies to every reel session; also use when the user asks about credits, limits, cost, or "how many reels can I make".
---

# Keep it lean

Heavy work runs on the user's computer and costs **no** Claude usage: transcription,
rough cut, layout, stickers, rendering, the review page and the manual editor. Claude usage
comes from what you read and write in the conversation. Keep it small:

## Do
- Read **summaries**, not raw data: the roughcut summary, `plan.summary`, the job status.
  Don't open transcript.json, timeline.json or roughcut.json in full unless fixing a bug —
  use `jq`/Python to pull the one field you need.
- Write **short plans** (plan.json is ~10–30 lines). Let the planner do layout and timing.
- Look at images **only when judgement is needed**, and one at a time: a contact sheet for
  inspiration, a brand preview, one frame to check a problem. Never read every frame.
- Use `--preview` renders while iterating; one final render at the end.
- Batch similar reels: one plan pattern, reused.
- For tweaks, edit the one timeline item (by id) with a small Python/jq command, or send the
  user to the manual editor (free).

## Don't
- Don't run the `watch` skill on long videos unless asked (many frames = expensive).
- Don't re-transcribe; transcripts are cached.
- Don't paste long files back into the chat.

## If the user asks "will this use a lot of credits?"
Say: most of the work runs on your computer. A typical reel is a short conversation: a few
messages to plan and a couple of small tweaks. What uses more: long back-and-forth
redesigns, studying lots of reference videos in detail, and starting over repeatedly. If
they hit a limit, the editor still works without Claude; they can make manual tweaks and
render there. Be honest that exact numbers depend on their plan and how much they change.
