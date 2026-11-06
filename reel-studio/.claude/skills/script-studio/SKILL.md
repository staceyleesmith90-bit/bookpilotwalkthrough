---
name: script-studio
description: Reel Studio's Script Studio — everything BEFORE the camera rolls: ideas, hooks, scripts, a week of reels. Use for "what can Script Studio do", "help me plan what to film", "I don't know what to post", or whenever another script skill needs the shared rules (where files live, the story bank, how scripts hand over to the edit). Routes to story-bank, hook-lab, write-my-script, script-check and content-week.
---

# Script Studio

Reel Studio edits what they film. Script Studio makes sure what they film is worth editing. It thinks like
a director, not a copywriter: every script already knows what the studio will put on screen (effects,
AI elements, b-roll, the cover), so the edit is half-planned before they press record.

## The five tools (say them in plain words, never as commands they must type)
| They say | Run | What they get |
|---|---|---|
| "set up my story bank", first time using scripts | `story-bank` | `my-scripts/story-bank.md`: who they talk to, their real moments, topics, offer, proof |
| "hooks for…", "how do I start this reel" | `hook-lab` | 8 hooks in their voice, 2 marked to test |
| "write a script", "script this", a voice-memo ramble | `write-my-script` | a script card: spoken lines + what's on screen + filming notes |
| "check my script", "is this good" | `script-check` | traffic lights on 8 checks + the one fix that matters most |
| "plan my week", "what should I film" | `content-week` | 5 reels (reach / trust / sell), filming order, one batch day |
Studying someone else's reel → `tutor-me`. How they talk → `voice-hub` (`brand/voice.md`). Their old reels as
text → `python -m engine transcribe-folder <folder>`.

## Shared rules (every script skill follows these)
1. **Read first, ask second.** Before any question read: `brand/voice.md`, the brand in use
   (`python -m engine brands` → `brands/<name>/brand.json`), `my-scripts/story-bank.md` and recent
   `my-scripts/*.md`. Never ask what's already written down.
2. **One question at a time, with 2–4 tap answers.** Short answers are fine; ask one follow-up only when an
   answer is too vague to write from ("busy mums" → "busy with what, at what time of day?").
3. **Their words, not ours.** Lines come from `brand/voice.md` and things they actually said. Banned:
   "game-changer", "unlock", "level up", "dive in", "journey", "elevate", "in today's video", em-dash
   sentences, three-adjective lists, rhetorical "Here's the thing:". Read every line out loud in your head:
   if they wouldn't say it at the school gate, rewrite it.
4. **Specific beats clever.** A number, a name, a time of day, a real object. "3 a.m. feed" not "late nights".
5. **Every reel has one job:** *reach* (new people), *trust* (people who know them), or *sell* (people ready to
   buy). Label it. One reel, one job, one ask.
6. **Show, don't only tell.** Every script names at least one "show-me moment": something the camera sees that
   proves the point (the messy desk, the before photo, the receipt, the baby's face when mom looks).
7. **Files live in `my-scripts/`** (personal, never in git). One file per reel: `my-scripts/<yyyy-mm-dd>-<slug>.md`,
   plus `story-bank.md`, `ideas.md` (one line per idea + its job), `week.md`.
8. **Hand-off to the edit.** Every script card ends with a *Studio plan* block (see write-my-script): the beats,
   which effect/element fits each, the cover line. When they've filmed it: "drop the clips in (or paste a
   Google Drive link) and say *edit this*" → reel-engine reads that block instead of starting from zero.

## Library (read when the skill says so)
- `hook-shapes.md` — our 12 hook shapes, each with when to use it and a fill-in line.
- `reel-shapes.md` — 8 reel structures (beat by beat, with timings) and which job each suits.
