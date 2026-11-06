---
name: script-this
description: "Script Kit. Use for 'script this', 'write a script for', or 'turn this into a reel script'. Writes a film-ready reel script in the user's voice from an idea, a hook, or a pasted ramble or voice-memo transcript: hook layers, word-for-word lines, beats, demo, one ask, filming direction. Writes the script only; never edits footage."
---

# Script this

First read `.claude/skills/script-kit-library/house-rules.md` and follow it the whole way through.

## 1. Start from what they gave

- **An idea** ("script this: my kids won't eat dinner"): use it.
- **A ramble or a transcript:** find the one idea worth a reel. Say it in one line, name the job it fits, and
  check that's the one they want (one question).
- **A reel from the week plan** ("reel 1", "the next one", "Tuesday's"): read `script-desk/week-plan.md` and use
  that row's script file. "The next one" is the first row in filming order without a script yet.
- **Nothing after "script this":** if `script-desk/week-plan.md` has a reel without a script yet, use the first
  one in filming order. Otherwise use the most recently changed file in `script-desk/scripts/` that has a hook
  sprint but no script yet. If there isn't one, use the newest idea in `script-desk/ideas.md`. Say which one. If
  there's nothing at all, ask for the idea in one line.
- If this idea already has a script file (from `hook sprint`), work in that file and use its chosen hook, unless
  their true story (step 3) changes what the reel is about. Then write a new Said line from their story, keep the
  sprint's hooks in the file, and say what changed in one line.

## 2. Read

- `script-desk/about-me.md` and `script-desk/voice-dna.md` (or the voice notes in `brand-kit.md`)
- `script-desk/my-reels.md` if it exists, to lean on what already works for them
- `.claude/skills/script-kit-library/method.md`, `levers.md`, `edit-words.md` and
  `templates/film-ready-script-template.md`
- `.claude/skills/script-kit-library/hook-library.md` only if there's no hook yet

## 3. Ask only what you have to

Read the script file's top line and the idea first. Then ask only what's still missing, in one message, each
question with your suggestion so they can just say "yes":

- The job, if the file doesn't say: reach, grow or convert? Suggest one with a one-line why.
- The register, if the file doesn't say: teaching or confessional? Suggest one.
- The story, when the script needs one told in first person and it isn't theirs yet (see "True stories only" in
  the house rules): "Has this happened to you? Tell me what really happened, in a line or two." Build the script
  from their answer, and save it: rewrite the file's Idea line in their words, and in `script-desk/ideas.md`
  replace a "(suggested)" line with theirs and drop "(suggested)". A no, or a skip: write it from the viewer's
  side, in "you".

Ask the format only if it isn't obvious. Yap is the default. The others are voiceover, b-roll reels and
animation. If they say "just write it", pick the best fit and say what you picked.

## 4. Write the film-ready script

Fill every section of the template:

- **Hook:** the three layers. Said (first sentence under 12 words, something concrete in it), shown (the first
  frame), read (the hook block from `method.md`: who it's for, then the tension, never a repeat of the spoken
  line). Stack two or three levers.
- **Script:** word for word, in their voice. Short lines, each readable in two seconds. Beats follow the shape
  (see `method.md`). Open a loop in line one and close it late, re-hook in the middle, land something new every
  few seconds, and put the biggest payoff near the end.
- **Edit notes** in brackets on the lines that need them, in the engine's words. Lean for confessional, the full
  set for teaching.
- **Beats:** a table with rough timings that fit the job's length.
- **The demo:** on a teaching reel, what the viewer sees that proves the point, and the line it lands on. On a
  confessional, write "none: the words carry it", or one quiet visual at most.
- **The ask:** one, after the payoff, with curiosity before any keyword. On a convert reel, use the offer and
  keyword from `about-me.md` that fit this reel's topic. No offer yet: use their "Until then" ask (follow,
  save, send, come back for the next part), and never invent an offer or a keyword.
- **Filming direction:** framing, setting, energy, the prop, the pause.
- **Caption first line:** a second hook for the feed.

Leave a bracket for any fact you don't have. Never invent numbers, results or stories, and only write "I" or
"me" for what's true of them. On a confessional reel, the story ends on the open question: no lesson and no
hopeful turn. The ask, if there is one, is one short line after it.

Fill the top line (job, register, format, length) and the Shape line.

Format changes the page: a voiceover gets the voice track plus a shot list, a b-roll reel gets its hook block
(5 to 8 seconds, one feeling, "Said: no voice") plus four more big lines to test, an animation gets a scene list
with one idea per scene.

## 5. Teach

Under the script in the chat (not in the file), three to five short lines: why this shape, which levers the hook
stacks, where the loop opens and closes, and why this ask.

## 6. Save

- Write the script file (create it, or update the existing one).
- In `script-desk/ideas.md`, add the idea if it's new, or add ` · script: script-desk/scripts/[file].md` to its
  line.

## 7. Next

One line: "Next: `check my script` to grade it, or film it."
