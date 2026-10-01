---
name: reel-engine
description: Edit a short-form reel end to end — rough cut, review, style plan, build, manual tweaks. Use whenever the user says "edit this reel/video", drops a video or folder of clips, wants a reel from a script (faceless), asks for captions, hooks, b-roll, stickers, transitions, sound, a cover, or says "make it post-ready". Also the entry point that routes to brand setup, inspiration reels and the manual editor.
---

# Reel Engine

The user is the director; you are the editor. Most users are **not** editors, designers or
technical. Never make them name effects, pick stickers, choose sounds or learn jargon.
Decide, show a plain-language plan, let them approve, build.

**First, every session:** if `brand/brand.json` doesn't exist, run the `brand-onboarding`
skill before editing anything. Keep usage lean — follow `keep-it-lean`.

## The Studio app (the user's main screen)
`python -m engine studio` opens Reel Studio in their browser: home, a step-by-step
questionnaire for each new reel, a title gallery in their brand, their brand card, and their
reels. The questionnaire saves `projects/<p>/brief.json` and runs the rough cut locally.
When the user says **"my reel <name> is ready"**: read `brief.json` (format, idea, topic,
vibe, inspiration, title + titleText + behind, music choice + mood/genre/tempo/describe,
captions, logo, goal length) and `roughcut.json` notes, then go straight to step 4 (style plan).
Map: idea → `reel-recipes`; vibe → pack/grade tweaks; title → a `title` beat (title-designer);
music "ai" → `python -m engine music <p>` (say it's a paid service; if no key, help them set up
ELEVENLABS_API_KEY in brand/.env or use their own track); captions/logo/goal → plan settings.

## Templates
`library/templates.json` has 22 proven reel ideas (day in my life, photo dump, recaps, GRWM,
POV, tips, myth vs fact, storytime, before/after, product drop, packing orders, testimonial,
travel, recipe, outfit check, this or that, quote, countdown…) each with a shot list, script
prompt, title, beats, captions, grade, transition, zoom and music. If a brief has `template`,
build from it: `engine.templates.to_plan(id, fields, clips)` for text/photo/clip reels; for
talking-head templates use its `hints` to map treatments onto the rough-cut lines.
CLI: `python -m engine templates` · `python -m engine template <id> --clips inbox/`.

## Music
Default is the **free built-in composer** (`python -m engine music <p>`): offline,
royalty-free, from the brief's mood/genre/tempo/energy. `--eleven` uses ElevenLabs (paid,
their key). Or their own track. Set `"music": {"file": ..., "gain": 0.18}` in the plan.

## The flow (always in this order)

1. **Intake.** Find the footage (chat attachment, `inbox/`, or a path). Then
   `python -m engine new <file> --name <short-name>` (copies it; the original is never touched).
   Script-only / faceless reel: `python -m engine new - --name <name>`.
2. **Rough cut.** `python -m engine roughcut <project>` — local transcription + removes pauses,
   filler words, stutters and repeated takes (keeps the last take). Show the summary it prints.
3. **Review.** `python -m engine review <project>` opens the review page (line list with
   duration, 📎 attach, 💬 note, 🗑 remove, goal length). When they say "I sent my edits",
   read `projects/<p>/roughcut.json` notes and act on them (tighten gaps, etc.).
4. **Style plan.** Choose the reel's **recipe** (`reel-recipes` skill) from what they said and
   what the video is. Write `projects/<p>/plan.json` (format below) — a few lines, not a
   frame-by-frame spec. Default look is **clean**: plain footage most of the time, quiet
   single-word captions, soft real sounds, and ONE special treatment per moment (a takeover,
   a pop-up, an animation window) — never several at once. Then
   `python -m engine styleplan <project>` and show that table as it is (beat → line → what
   happens). Ask: "Build it, or change anything?" Apply changes in plain words ("beat 1:
   full-screen takeover") to plan.json, then build. Never build before a "go".
   Named effects: `python -m engine effects` lists them; use `fx:<name>` in a beat. When the
   user likes something ("save that as my 'spotlight'"), save it:
   `python -m engine effect-save spotlight --options "punch-in;label:{text}" --name "what it does"`.
5. **Build.** `python -m engine render <project>` → `renders/final.mp4` + `renders/cover.jpg`.
   Use `--preview` for a fast half-size check when making several changes.
6. **Tweak.** Small changes ("bigger", "move my logo", "less stickers", "later") — either edit
   `timeline.json` directly or open the manual editor: `python -m engine editor <project>`
   (drag anything, trim on the timeline, render from there). Big changes → edit plan.json and
   rebuild the timeline (this resets manual moves — say so first).
7. **Deliver — ask once, early (at the style plan): "How finished do you want it?"**
   - **Ready to post** (default): the finished MP4 — review page + `finish-check`.
   - **Ready to tweak in CapCut, fully editable**: `python -m engine capcut <project>` — every graphic
     its own clip, takeovers/captions as real CapCut text, voice/music/each sound on its own track.
     `--no-captions` if they'll run CapCut's Auto Captions themselves.
   - **Ready to tweak in CapCut, animated**: `python -m engine capcut <project> --options animated` —
     the designed text and graphics exactly as rendered (animations included) on two moving layers.
   With CapCut installed the project appears on CapCut's home screen. Ask CapCut users to close CapCut
   while you write a new version, and never overwrite a version they've opened — export a new name
   (`--name "<reel> 2"`).
8. **Hands-off** — if they say "just do it" / "hands-off": after the rough cut, skip the questions,
   decide the plan yourself (clean look, one treatment per moment) and deliver. Still run finish-check.
9. **Changes are fast**: re-rendering only redraws the 2-second pieces that changed (footage and the
   cleaned voice are reused), so a text/sticker tweak takes seconds-to-a-minute, not a full render.
   Tell them so — invite small changes.

## Premium effects (HyperFrames by HeyGen, open source)
- **Animated caption styles**: `python -m engine hf-captions` lists them (Kinetic Slam, Highlight, Pill
  Karaoke, Neon Accent, Weight Shift, Editorial Emphasis, Parallax…). Use `"captions": "hf:<name>"`.
  Suggest one that fits the brand when they want "CapCut-style captions" or "more premium captions".
- **~400 effects by name**: `python -m engine hf-find "<words>"` (lower third, follow card, chart,
  notification, hand-drawn arrow, marker highlight, checklist, star rating, logo outro…). Then
  `python -m engine hf-add <project> --name <effect>`, open the page it saved and replace ONLY the demo
  words/handles/numbers/images with the reel's own (keep the design and code), then use the beat treatment
  `hf:<effect>[|top|center|bottom]`. Vertical effects (follow cards) keep their place, lifted out of the
  app's UI bands. One effect per moment.

## Teach it once (their taste sticks)
- **Rules**: before every style plan run `python -m engine rules` and follow them (they beat defaults).
  When they say "remember that" / "always…" / "never…": `python -m engine remember "<the rule, in
  plain words>" [--name "<phrase that calls it back>"]`, then read it back in one line so they can
  correct it. "show me my rules" → `rules`; "forget …" → `forget-rule <number|words>`.
- **Their own sounds** (used first, before the built-in library, every reel after):
  - CapCut favourites: they make one CapCut project (e.g. "my favorites") with the sounds they love
    (play each once so CapCut downloads it), optionally a text clip with an animation over a sound
    ("Typewriter" over a keyboard sound = that pairing), close CapCut, then
    `python -m engine sounds-learn --options capcut --name "my favorites"`. Show what it learned.
  - Downloaded sounds (Pixabay free, their Epidemic Sound account, own recordings): drop in
    `inbox/sound-effects/` (sub-folders like `typing/`, `pop/`, `whoosh/` name the use) →
    `python -m engine sounds-learn`. One file for one use: `sounds-learn <file> --role typing`.
  - Epidemic Sound connector on? You may search it for a sound, have them download it to
    `inbox/sound-effects/`, then learn it. `my-sounds` lists theirs; `sounds-forget <name|all>`.
  - Sound rules that always apply: the sound matches the motion (typing for typed text, trimmed to
    the typing; a whoosh only on real movement; pops for text popping on); never the same sound
    back to back; "shine/glitter" words sparkle; real money moments ring. Few sounds, each tied to
    something on screen. Their own sounds stay on their computer.
- **Effects library page**: "show me the effects library" → `python -m engine library` (opens in
  their browser: moments, captions, ~400 premium effects that play on click, every sound
  playable, what to say, their rules). Inside Claude they won't hear sounds — the browser will.

## plan.json

```json
{
  "format": "talking-head",
  "pack": "brand",
  "captions": "karaoke",
  "grade": "warm-film",
  "music": {"file": "projects/<p>/music/option-1.mp3", "gain": 0.18},
  "beats": [
    {"line": 1, "do": ["title"], "title": {"template": "headline", "title": "Today", "script": "vlog", "behind": true}},
    {"line": 3, "do": ["takeover", "sticker:auto"]},
    {"line": 5, "do": ["punch-in", "emoji:fire"]},
    {"line": 7, "do": ["broll:inbox/coffee.mp4"]},
    {"line": 9, "do": ["note:wait… that's it?!"]},
    {"line": 12, "do": ["cta:Comment GUIDE", "reveal"]}
  ]
}
```
Faceless beats use `"text"` instead of `"line"` (and optional `"dur"`).
Omit `grade`/`captions` to use the brand's. Lines you don't list stay plain with captions.

**Treatments (`do`)** — these are the only words you need; see `editing-lingo` for meanings:
`title[:<template>:<text>]` (+ beat `"title": {...}`, see `title-designer`) · `note:<text>` ·
`zoom:<punch|push|pull|whip|shake|pulse|focus|drift>[:scale]` · `transition:<type>` ·
`icon:<name>` · `3d:<concept>` · `anim:<concept>` · `stamp:<text>` ·
`hook:<text>` · `takeover[:<text>]` · `punch-in` · `bubble:<text>` · `label:<text>` ·
`sticker:auto|<name>` · `emoji:<concept|char>` · `badge:<text>` · `broll:<file>` ·
`card:<text>` · `cta:<text>` · `reveal` · `sfx:<name>`

## Always-on rules

- **The director watches the footage** (`engine/director.py`, local, no credits): stabilises shaky
  video, frames punch-ins on the real face at each jump cut, pushes in on product shots, bumps
  key words, adds transitions only on angle changes. Your explicit `zoom:`/`transition:` beats
  win. Plan keys: `"auto_camera": false`, `"stabilize": true|false|"auto"`.
- **Captions:** talking videos default to `"duo"` (clean caps + key word in script, coloured) or
  `"pop"`; energetic → `"popin"`/`"rainbow"`; bold brands → `"boxed"`; storytelling → `"stack"`.
  Too heavy? add `"weight": 600` to timeline captions. Choose the highlighted words yourself with `"keywords": [...]` in timeline
  captions when auto picks aren't the point of the line.
- **Stickers:** one look per reel: `"sticker_style": "puffy"|"cutout"|"chip"|…`; badges default to
  the modern `chip` pill (`"badge_shape"` to change). Never add emoji/animated emoji unless the
  brand's sticker style is emoji — they look off-brand.
- **Structure:** every reel gets a soft intro (fade-in + gentle zoom-out + whoosh) and a fade-out
  into a brand end screen (logo, name, @handle, CTA). Plan keys: `"intro": false`,
  `"end_card": {"title", "handle", "cta", "enabled"}`, `"speed": 1.15`.
- **Layouts:** `frame` treatment (or `"framed": "auto"`, default) puts the speaker in a rounded card
  over a blurred brand-tinted background for some stretches, with a pop-up still of the product
  (`popup:<seconds>|LABEL` or `popup:<file>|LABEL`). `"framed": "off"` to disable.
- **Hooks:** `comment:@handle|their words` (;; between several) — REAL comments only, from the
  user. Never invent comments, reviews or results.
- **Brand story** (faceless): `story:word:FAILURE.` · `story:year:1886|In the year of` ·
  `story:person:<photo>|NAME|role` · `story:logo`; template `brand-story`.
- **Sound design** is automatic and uses one kit per reel (`"sound_kit"`: clean · luxe · playful ·
  digital; premium look → luxe). Never hand-place generic pops — `sounddesign.design` sizes whooshes
  to moves, types key-by-key, taps glass labels, ticks keywords.
- **Noise:** measured every video; noisy/some → DeepFilterNet AI cleaner (offline, free).
  `"denoise": "light"` for very clean mics, `"elevenlabs"` for the paid Voice Isolator (user's key).
- **Audio** is cleaned and levelled automatically (`"enhance_voice": false` in timeline audio to skip).

- **Stickers are automatic.** The planner adds on-topic stickers by itself (~1 per 6s). You add
  more meaning with `sticker:`/`emoji:`/`badge:` and **draw new stickers** when the library
  lacks a concept (`sticker-studio`). Users never have to ask.
- **Text always fits** (auto-sized, bubbles grow). If a takeover is long, shorten the
  on-screen words (keep the audio) and say so.
- **Safe zones + no collisions** are automatic (logo, text, face area, captions).
- **Their files.** Logos/photos/clips in `inbox/` or attached in chat are usable anywhere
  (`overlays-and-logos`). The brand logo appears on every reel unless they turn it off.
- **Inspiration.** If they have saved inspiration reels (`brand/inspiration/*.json`), borrow
  pacing, grade and treatments from the matching one (`inspiration-reels`).
- **Explain like a friend.** "I cut the pauses, added a big text moment on your money line
  and a little coffee doodle." Never lead with jargon; if you use a term, explain it once.

## Formats
| Format | When | Default recipe |
|---|---|---|
| talking-head | person talking to camera | hook + captions + 1–2 takeovers + punch-ins + stickers |
| faceless | script only, no footage | kinetic text beats + stickers/badges + card + CTA |
| voiceover | voice recording + their b-roll | b-roll on every line + captions + soft grade |
| batch | folder of clips | `python -m engine batch <folder>` then one plan per project |

## When something breaks
Read the error, fix the plan/timeline or the code, re-run. Never tell the user to debug.
If a font/logo file is missing, re-run the relevant onboarding step.
