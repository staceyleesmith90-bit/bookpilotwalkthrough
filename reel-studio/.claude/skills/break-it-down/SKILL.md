---
name: break-it-down
description: "Script Kit. Use for 'break this down' with a reel link or pasted words, 'why did this reel work', or 'steal the shape of this'. Breaks down why one reel works (job, hook layers, levers, beats, loops, ask, demo), separates the format to borrow from the concept to leave, and turns it into a fill-in template for a new script. Not for editing footage."
---

# Break this down

First read `.claude/skills/script-kit-library/house-rules.md` and follow it the whole way through. Then read
`.claude/skills/script-kit-library/method.md`, `.claude/skills/script-kit-library/levers.md` and
`.claude/skills/script-kit-library/hook-library.md`.

Be honest about one thing up front: you can't watch a video or open an Instagram link. You work from the words,
the caption, the numbers, and what the user tells you is on screen.

## 1. Get the reel

- **One of their own reels** already in `script-desk/my-reels.md` (match the link): use its words and numbers.
  No cost.
- **A link, with Apify connected:** say the cost first and wait for a yes. One reel under a minute is about 5
  cents. Then run `apify/instagram-reel-scraper` with
  `{"username": ["<the reel link>"], "includeTranscript": true}` and read the full result with
  `get-dataset-items` (the run's own preview cuts the words short).
- **No Apify, a TikTok or YouTube link, or the run failed:** ask them to paste what's said (the first few lines
  they remember is enough to start), the caption, and one line on what's on screen. A screenshot of the first
  frame helps most.

What's on screen stays "not shown to me" unless they describe it or send a screenshot. Never describe a video
you haven't been given.

## 2. The breakdown

Every point gets one line of why, quoting the reel's own words.

1. **Job and register.** Reach, grow or convert, and teaching or confessional (see `method.md`).
2. **The hook.** Said, Shown and Read. Its pattern from the Hook Library, by name. The levers it pulls (see
   `levers.md`). Whether something concrete lands first, in the first sentence or the first frame.
3. **The beats.** Its shape (story, list, contrarian take, confessional, comparison, series episode) and each
   beat in order, with rough times when you know the length. Run the "but and so" test on the beats.
4. **The loops.** Where a question opens, any re-hook in the middle, and where it closes.
5. **The ask.** What it asks for and where, and whether curiosity comes before any keyword.
6. **The demo.** What proves the point on screen, or "not shown to me".

## 3. Format and concept

Two short lists:
- **The format (borrow this):** the hook pattern, the shape and beats, the pacing, where the ask sits, what's
  on screen.
- **The concept (never borrow this):** the topic, the examples, the story, the proof.

## 4. The fill-in template

Write the format as a skeleton with a [blank] for every piece of their own concept, one line per beat, each
marked with what it has to do: `[a moment your person lives at night] (Said, under 12 words)`.

- None of the original reel's sentences survive in the template. Borrow the shape, never the words.
- The test: if the original creator saw the finished reel, they'd recognize the format but not the idea.

## 5. Offer the script

Ask once, as the last line of the reply: "Want to film this shape? Give me your idea." Add "or say `use one from
my ideas`" only when `script-desk/ideas.md` has ideas in it.

When they give an idea:
- **The job:** take it from the source's shape. If the shape is convert and their `about-me.md` has no offer yet,
  say so in one line and offer two ways: keep the shape and end on their "Until then" ask (follow, save, send),
  or switch it to a grow reel.
- **Same point, different story:** if their idea lands on the same point as the source reel, say so kindly and
  help them find their own angle: their own story, their own flip, their own proof. Borrow the shape, not the
  point.
- Start a script file in `script-desk/scripts/` from the film-ready template. Fill in the top line (job,
  register, format, length), the Idea line, and the Shape line with the borrowed shape. Put the fill-in template
  in the Beats section, with the blanks you can fill from their desk files and `brand-kit.md` already filled.
  Every other section keeps its placeholder for `script this`.
- Add the idea to `script-desk/ideas.md` (`from: break this down`, with the script path).
- Never save another creator's words anywhere on the desk. Only the shape goes in. A warning about a phrase to
  avoid stays in the chat, since writing it down would put their words on the desk.

## Reply format

- **Job and register:** one line.
- **The hook:** Said / Shown / Read, the pattern, the levers.
- **The beats:** the shape, then each beat.
- **Loops, the ask, the demo:** a line each.
- **Borrow / never borrow:** the two short lists.
- **Your fill-in template:** the skeleton.
- Last line: the question from step 5.
