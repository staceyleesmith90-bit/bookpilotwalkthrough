---
name: whats-working
description: "Script Kit. Use for 'what's working for me', 'transcribe my old reels', 'get my reels from Instagram', 'refresh my reels', or 'I don't have many reels yet'. Brings the user's own reels, other posts, reels they love or an interview onto the script desk, then reads what's working across their account. Not for cutting clips from a video, or for niche research."
---

# What's working for me

First read `.claude/skills/script-kit-library/house-rules.md` and follow it the whole way through. The formats for
`my-reels.md`, `reels-i-like.md` and `ideas.md` are in `.claude/skills/script-kit-library/desk-files.md`. Match
them exactly.

## 1. Which job is this?

- **"transcribe my old reels"** → Route B, then the short read (step 7).
- **"get my reels from Instagram"**, **"refresh my reels"**, or they ask you to use Apify on their reels → Route A,
  then the short read.
- **They pasted their reels** (captions, numbers, maybe what they said) → Route C, then the short read.
- **"I don't have many reels yet"**, or anything like it → Route D, then the starter read (step 8).
- **"what's working for me"** → the full read (step 9). If `script-desk/my-reels.md` is missing or has fewer
  than five reels, don't stall: say so in one line, then offer what fits. Route A if Apify is connected. Route B
  or C if they have reels. Route D if they're just starting, and in that case run the starter read instead. If
  the file has five or more reels and Apify is connected, offer a refresh first (Route A, "Refreshing"). A no is
  fine.

## 2. Route A · Their reels, from Instagram with Apify

1. **The handle.** Read it from `brand-kit.md` (the Handles line) or `script-desk/about-me.md`. Only ask if
   neither has it.
2. **Shares.** Share counts need a paid Apify plan. Unless `my-reels.md` already says "Shares: in my plan", ask
   once: "Are you on a paid Apify plan? Share counts need one." Anything but a clear yes means no.
3. **The cost, then wait.** Say it before running, and wait for a yes. Free-plan prices:
   - $0.0026 per reel, plus $0.001 to start the run.
   - Transcripts are most of the cost: about $0.05 for every started minute of each reel.
   - Share counts add $0.007 per reel.
   - Fifteen reels with transcripts usually comes to about a dollar, inside Apify's free $5 of monthly credit.
     Paid plans pay less per reel.
4. **Run** `apify/instagram-reel-scraper` with:
   `{"username": ["<handle>"], "resultsLimit": 15, "includeTranscript": true, "includeSharesCount": <true only on a paid plan>, "skipPinnedPosts": false}`.
   Use the number of reels they asked for if they named one.
5. **Read the full results** with `get-dataset-items` and the run's dataset id. The run's own preview cuts
   transcripts short. Page with `limit` and `offset` if needed.
6. **Map the fields:** plays = `videoPlayCount` (fall back to `videoViewCount` only if it's missing), likes =
   `likesCount`, comments = `commentsCount`, shares = `sharesCount`, length = `videoDuration` (seconds), date =
   `timestamp`, link = `url`, words = `transcript`, caption = `caption`.
7. If the run fails or comes back empty, say what happened in one line (a private account and a mistyped
   handle are the usual reasons) and offer Routes B, C and D. Never fill a gap with a guess.

**Refreshing** (the file already exists): numbers keep climbing, so refresh them cheaply. Run the same actor with
`resultsLimit` set to the number of reels in the file plus a few, and `includeTranscript: false` (about 5 cents).
Update the numbers for reels already in the file. For reels that are new, run again with just their links and
`includeTranscript: true`, so only the new ones pay for transcripts. Give both costs before either run.

## 3. Route B · Their old reel videos, transcribed on this computer

The videos go in `script-desk/old-reels/`. The engine transcribes them locally, so nothing is uploaded and
nothing costs money.

1. If `script-desk/old-reels/` is missing or has no videos in it, make the folder and say: "Put your old reel
   videos in `script-desk/old-reels`, the same way you drop footage into your inbox for an edit. Put in every
   reel you want at once. Your originals from before the music went on work best. Then say
   `transcribe my old reels` again." Then stop.
2. See what's there, from the engine folder:
   `PY="$(bash scripts/ensure-python.sh)" && "$PY" .claude/skills/script-kit-library/tools/reel-transcripts.py script-desk/old-reels`
   It lists the videos, any videos still `missing` from the transcript, and any `skipped` files that aren't
   videos. Name the skipped files in one line.
3. Transcribe with the engine's own transcriber. Newer engines call it `word-timings.sh`, older ones
   `transcribe.sh`; this runs whichever one is there:
   `T=.claude/skills/rough-cut/scripts; S="$T/word-timings.sh"; [ -f "$S" ] || S="$T/transcribe.sh"; bash "$S" script-desk/old-reels`
   - When an earlier transcript exists and `missing` isn't empty, add `--force`. It transcribes the whole folder
     again, which is the only way to add new ones, so it takes longer.
   - Say it's working on their computer. With more than five videos, run it in the background and check back.
4. Run the helper from step 2 again. It prints each reel's length and words.
5. **Ask for the numbers**, in one message, only for videos not already in `my-reels.md` and not interview answers (step 7): list each by file
   name with a four-to-six word summary of what it says, so they can recognize it, and ask for its view count.
   The date posted, likes, comments and shares are welcome too, and "skip" is fine for any of them.
6. A video with no speech (music or on-screen text only) still counts. Save it with its numbers and "no speech"
   in place of the words.
7. A video that's an interview answer (they filmed themselves answering a `set up my script desk` question), not
   a posted reel: don't ask for its numbers. Save its words under `## In my own words`.

## 4. Route C · Reels they pasted

Save exactly what they gave you. Mark the source "pasted", and "Shares: typed in" if they gave share counts,
"Shares: not given" if they didn't. Anything they didn't give stays blank. Never guess a number, a date or what was said. Label each part of a
transcript (Said, On screen, Caption), as in `desk-files.md`. If a talking reel came without its words, say in one line that what they said is what
teaches Claude their voice, so adding it later is worth it. A reel that's only text on screen is complete as it
is.

## 5. Route D · Not many reels yet

Being new is a stage, not a problem. Say one line of hope first, like "Plenty to work with. Let's fill your desk
another way." Then offer three sources. They can do any, all, or one at a time. Suggest the order below.

1. **Reels they love** (up to 15). Ask for links to reels from other creators they'd love to make. For each one:
   the format, the job, the closest Hook Library pattern (see `hook-library.md`), the shape (see `method.md`),
   and in their words what they love about it. If their words quote the reel, keep the love and cut the quote.
   - With Apify connected, you can get each reel's words to judge it better. Cost first: about 5 cents a reel
     under a minute, using `apify/instagram-reel-scraper` with the links and `"includeTranscript": true`.
   - Without Apify, ask for what each one says first and what's on screen, a line each.
   - Save to `script-desk/reels-i-like.md`. Only the shape is saved. Never their words, captions, keywords or
     transcripts.
2. **Their other posts.** Carousels, photos and captions show how they write and what their people respond to.
   - With Apify connected: `apify/instagram-post-scraper` with `{"username": ["<handle>"], "resultsLimit": 20, "dataDetailLevel": "basicData"}`.
     Cost first: about $0.002 a post, so twenty posts is under 5 cents. Map type, `caption`, `likesCount`,
     `commentsCount`, `timestamp` and `url`.
   - Without Apify, or for another platform (a newsletter, a blog, TikTok, YouTube): they paste it in.
   - Save to `## My other posts` in `script-desk/my-reels.md`, captions word for word under `## Transcripts`.
3. **The voice interview.** Run it from `.claude/skills/script-kit-library/interview.md`. It's how Claude hears
   the way they talk, which is what their Voice DNA needs most. Save the answers under `## In my own words`.

Any reels of their own, even one or two, still go in first, through Route A, B or C.

## 6. Save to the desk

- `my-reels.md` in the exact format from `desk-files.md`: the Updated line with today's date, the source and
  whether shares are in their plan, the medians, the reels, other posts, transcripts and interview answers.
- Medians: the median plays for each format, with three or more reels in it. Outlier = plays divided by that
  format's median.
- When adding to an existing file, keep everything already there, update numbers that changed, and never add
  the same reel twice (match on the link, the file name for a video, or the date and first line for a pasted
  reel).

## 7. The short read (after Routes A, B and C)

Their most-watched reels, up to three, one line each: plays, format, what it is. One line of why: "These are
your real words and your real numbers. Every script from here learns from them." Last line, depending on the
count:
- five or more reels: "Next: say `what's working for me` and I'll tell you which job each reel was doing."
- fewer than five: "Next: add a few more reels, or say `I don't have many reels yet` and we'll fill your desk
  another way."

## 8. The starter read (after Route D)

- **What you're drawn to:** from `reels-i-like.md`, the patterns that show up in more than one reel they love
  (formats, hook patterns, registers, lengths). Write them to its "What I'm drawn to" section.
- **What your people respond to:** from their other posts, the two or three that got the most comments and likes,
  and what those have in common. Say plainly that a handful of posts is an early signal, not a verdict.
- **Your own reels:** if they have any, one line on which did best (plays, format, what it is). An early signal,
  not a verdict.
- **Your voice, so far:** two or three phrases from their interview or captions that sound most like them, quoted.
- **Three ideas** to film first, each a shape they love carrying their own topic. For someone just starting, two
  reach and one grow; with an offer, one per job. Add them to `script-desk/ideas.md` with
  `from: what's working (suggested)`, written as a moment or a topic, never as a story that happened to them.
- Last line: "Next: say `build my voice DNA`, then `hook sprint` on one of these ideas."

## 9. The full read ("what's working for me", five or more reels)

Read `.claude/skills/script-kit-library/method.md` (the three jobs, outliers) and
`.claude/skills/script-kit-library/levers.md` first.

1. **Tag each reel's job** in the Job column, using the three jobs in `method.md`:
   - reach: short on-screen lines over b-roll, built to be found by new people;
   - grow: a talking reel that names a tension, feeling or story their people live;
   - convert: teaches or shows something, then asks for an action (a comment keyword, a link, a DM).
   When it's a real toss-up, pick the closer one and say so in one line.
2. **Judge each job by its own number:**
   - reach by plays against its format's median (the outlier number);
   - grow by shares when they're in the file, otherwise by comments, and say that shares would make this read
     sharper;
   - convert by comments per 1,000 plays.
   A reel that looks weak on plays can still be the one doing its job. Say so when it happens.
3. **For each job, name the winner** and why it won, from its first line, its hook and its levers. Quote
   their own line.
4. **The pattern.** One to three things the winners share: a moment, a format, a length, a lever. Only patterns
   that show up in more than one reel. With fewer than ten reels, say the read will sharpen as they add more. If
   `reels-i-like.md` exists, say in one line whether what works for them matches what they love.
5. **Three ideas** to film next, one per job, each built from a winner's shape with a new concept from their
   topics. Write each as a moment or a topic, never as a story that happened to them. When a true story would
   carry it, ask it as a question: "Has your kid ever yelled 'race me' at the park?" Add them to
   `script-desk/ideas.md` (`from: what's working (suggested)`). Skip any idea that's already there.
6. Save the job tags to `my-reels.md`.

Reply format (full read):
- **Your reels by job:** the count per job, and each job's number.
- **What's working:** the winner in each job, one line of why, quoting their line.
- **The pattern:** one to three lines.
- **Next three to film:** the three ideas, tagged by job.
- Last line: "Next: say `hook sprint:` and paste one of these ideas."
