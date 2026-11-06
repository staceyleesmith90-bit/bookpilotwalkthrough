# Script Kit house rules

Every Script Kit skill follows these rules. Read this file first, every time a Script Kit skill runs.

## In Reel Studio (read first — this maps the kit onto this studio)

- **brand-kit.md = this studio's brand files.** There is no brand-kit.md here: read the brand in use
  (`python -m engine brands`, then `brands/<name>/brand.json`) and `brand/voice.md` (how they talk) instead.
  "Not set up yet" means neither exists: offer `brand-onboarding` / `voice-hub` first, never block.
- **Python:** plain `python3` (no `scripts/ensure-python.sh` here).
- **Transcribing old reels** (Route B): `python -m engine transcribe-folder script-desk/old-reels` writes
  `script-desk/old-reels/transcript/words.json` in exactly the format `tools/reel-transcripts.py` reads.
  Add `--force` to redo all of them.
- **Engine skills the kit names:** `reference-reel` → Reel Studio's `inspiration-reels`; `pull-reels` → `broll-batch`;
  `set-me-up` → `help-me` ("set me up"); the kit's tutor skill is installed as `script-tutor` (Reel Studio's own
  `tutor-me` stays for editing lessons). Scripts end with a hand-off: "film it, drop it in, and say edit this".

## Where things live

- The working folder is the buyer's Reels Editing Engine folder, the one with `brand-kit.md` in it. Every path
  below starts there.
- Everything the kit makes goes in `script-desk/`. Never save anywhere else. Never edit `brand-kit.md` or any
  engine file. Read them only.
- The desk:

  | File | What it holds | Started by |
  |---|---|---|
  | `script-desk/about-me.md` | where they are, who they write for, their moments and words, topics, offer, proof | `set up my script desk` |
  | `script-desk/my-reels.md` | their reels (numbers, format, job, transcripts), plus their other posts and their interview answers | the lesson Connect your reels, `what's working for me`, `transcribe my old reels` |
  | `script-desk/reels-i-like.md` | reels they love from other creators: the shape of each, never the words | `what's working for me`, for anyone short on reels |
  | `script-desk/voice-dna.md` | how they talk, their labels, banned words and AI tells | `build my voice DNA` |
  | `script-desk/ideas.md` | ideas worth filming, one line each, tagged by job | any skill that finds an idea, including `tutor me` |
  | `script-desk/scripts/` | one file per reel, from the first hook to the posted numbers | `hook sprint`, `script this`, `break this down` |
  | `script-desk/week-plan.md` | this week's reels and the order to film them | `plan my week` |
  | `script-desk/old-reels/` | videos to transcribe, only on the no-Apify path | the buyer |

- Always write the full path, starting with `script-desk/`. The engine has its own `scripts/` folder for its
  code. Never write to it or change anything in it.
- The kit's reference files live in `.claude/skills/script-kit-library/`. Read them, never change them.
- **The kit's rules for the engine.** The engine reads the Script Kit's rules from `.claude/rules/script-kit.md`,
  a copy of `.claude/skills/script-kit-library/script-kit.md` made at install. Before anything else, check
  it's there and matches the library copy. If it's missing or different, copy the library file over it (create
  `.claude/rules/` if needed). It's the one file the kit writes outside `script-desk/`. Then check it's loaded:
  if your instructions for this session don't already include its heading, "The Script Kit, inside the Reels
  Editing Engine", it arrived after the session started. In either case, do the job, then add one line just
  before your reply's last line: "Close Claude Code and open it again once, so your engine picks up the Script
  Kit's rules."
- If `script-desk/` or `script-desk/scripts/` is missing, create it.
- File formats for every desk file are in `.claude/skills/script-kit-library/desk-files.md`. Match them exactly,
  so every skill can read what another skill wrote.

## Read before you ask

- Before asking the buyer anything, read what already exists: `brand-kit.md`, then `script-desk/about-me.md`,
  `script-desk/voice-dna.md`, `script-desk/my-reels.md`, `script-desk/reels-i-like.md` and
  `script-desk/ideas.md`. Never ask for something one of those files already holds.
- If a file is missing, work with what exists. At most once per reply, near the end, name the one missing file
  that would most improve THIS job and the command that adds it. Never stop the job because a file is missing.
- `about-me.md` says where they are. Someone just starting out has few reels, maybe no offer and no numbers.
  That's a stage, not a gap: follow "Just starting out" in `method.md`, and never make them feel behind.

## Teach as you work

- Give every choice one short line of why, like "Why: it names a moment, not a category." The buyer should learn
  what makes a script good, not just receive one.
- Keep chat replies short and easy to scan. End with one line that says what to do next. When a skill spells out
  its own reply format, that format wins.

## Writing in the buyer's voice

Anything written for the buyer to say, show or post:

- **In their language.** Write in the language they write to you in, and reply in it too. If they chat in
  Spanish, their hooks and scripts come back in Spanish. If they switch, switch with them. The commands they type
  (`hook sprint`, `script this`) stay in English because that's all the skills know, so a command never counts as
  their language. Their reels, Voice DNA or brand kit may be in another language: carry their voice across, never
  translate their phrases word for word. Desk file headings and labels (`## Who it's for`, `Said:`, `Read:`) stay
  exactly as `desk-files.md` shows them, so every skill can still read them.
- **To the right person.** Every hook and script speaks to the person in "Who it's for" in `about-me.md`, read
  with its kind of account (see "Who the reel is for" in `method.md`). A product seller's reels speak to the
  customer, even a behind-the-scenes or maker story. A creator with nothing to sell speaks to the follower she's
  building.
- Sounds like them. Match `script-desk/voice-dna.md` when it exists. Otherwise use the voice notes in
  `brand-kit.md`.
- No em dashes. Use periods and short sentences.
- No AI tells: lists of three out of habit, "it's not X, it's Y" on repeat, words nobody says out loud, a warm-up
  line before the point, sentences that all sound the same, a tidy moral at the end. `voice-dna.md` may ban more.
- Seen, not diagnosed. Never make the viewer feel behind, late, lazy or failing.
- No hustle talk ("rise and grind", "boss babe") unless the buyer's Voice DNA says it is truly theirs.
- Their facts only. Never invent numbers, results, stories, clients or quotes. When a line needs a fact you
  don't have, leave a bracket for them to fill: `[your number]`.
- **True stories only.** A story, a moment or a detail is theirs only when their own words say so: their reels
  and posts, their interview answers, `about-me.md`, `brand-kit.md`, or what they've told you in this chat. An
  idea marked "(suggested)" in `ideas.md` is Claude's idea, not their memory, even when it says "your".
- First person only for what's theirs. A line with "I", "me" or "my kid" puts it in their mouth. A moment
  `about-me.md` lists as their person's stays their person's ("moms at 5am"). When a script needs a first-person
  story that isn't theirs yet, ask one question: "Has this happened to you? Tell me what really happened, in a
  line or two." Then build from their details, not yours. A no, or a skip: write it as the viewer's moment
  ("you") or as a question.
- Never put words in a real person's mouth: their kid, their partner, a client, a friend. Quote someone only when
  the buyer told you that person said it.
- Concrete first. A hook's first sentence holds something concrete: a time, a place, an object, an exact number or a named moment. A loop
  opener ("I have a puzzle I can't solve") can hand that job to the first frame, like a whiteboard with the
  puzzle on it. A category of people on its own ("moms", "coaches") doesn't count.
- Never reuse a line from the Hook Library or its bonus set, Meg's or a translation, even in the same niche. They show a pattern
  moving. Write fresh from the buyer's own moments and words. The same pattern carrying their own facts is the
  point: what's off limits is an example's wording and its made-up details. Their real numbers and stories are
  always theirs to use, even when an example looks close.
- Other creators' words never go on the desk. From their reels, only the shape is saved.
- Filming direction is a suggestion. A prop, an outfit or a place they haven't mentioned is offered, not assumed:
  "in your work clothes, if you film right after a shift", never "in scrubs" when they never said scrubs.

## Money and computers

- Apify runs cost money. Apify is connected when you can see Apify tools (like `call-actor` or
  `get-dataset-items`). Before any run, say what it will cost and wait for a yes. If Apify isn't connected, use
  what's already in `script-desk/` and mention the engine lesson "Connect Apify" in one line.
- Everything works the same on Mac and PC. Use plain file reads and writes. No Mac-only tools.
- When a Python file has to run, use the engine's own Python, from the engine folder:
  `PY="$(bash scripts/ensure-python.sh)" && "$PY" <file>`. Never a bare `python3` or `python`: a new Mac has
  only a placeholder, and Windows names it differently. This works the same on both.

## Script files

- Name: `script-desk/scripts/YYYY-MM-DD-short-title.md` (lowercase, hyphens, the date the file was started).
- Shape: the film-ready template in `.claude/skills/script-kit-library/templates/film-ready-script-template.md`.
  Every section keeps its placeholder line until a skill fills it.
- One reel per file. When a skill works on a reel that already has a file, update that file.
- Which file? If the buyer names one, use it. Otherwise use the most recently changed file in
  `script-desk/scripts/`, and name it near the top of the reply.
