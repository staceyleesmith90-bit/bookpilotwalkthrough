---
name: voice-dna
description: "Script Kit. Use for 'build my voice DNA', 'update my voice DNA', 'learn how I talk', 'make Claude sound like me', or 'never say [word] in my scripts'. Builds script-desk/voice-dna.md from the user's own words on the script desk (reel transcripts, interview answers, captions), quoting their real lines, so every script sounds like them."
---

# Build my Voice DNA

First read `.claude/skills/script-kit-library/house-rules.md` and follow it the whole way through.

A voice is a set of patterns you can write down. Once they're written down, Claude can match them.

**"Never say [word]" or "stop using [phrase]":** skip the build. Add it to "Words I never use" in
`script-desk/voice-dna.md` (create the file from the template if needed), confirm in one line, and stop.

## 1. Gather their words

Read `script-desk/my-reels.md`. Their words come in three strengths:

1. **Reel transcripts:** how they actually talk on camera. The strongest evidence.
2. **Interview answers** (`## In my own words`): how they talk when they're not performing. Strong.
3. **Captions and other posts:** how they write. Useful, but a written voice isn't a spoken one, so never let
   captions alone decide how their scripts sound.

- Five or more transcripts and interview answers together: build it.
- Fewer than five: say what's there in one line, then offer the voice interview from
  `.claude/skills/script-kit-library/interview.md` right now. It takes the place of the reels they haven't posted
  yet. If they'd rather not, and there are at least three sources, build a first pass and mark it "first pass" in
  the file.
- They can also paste samples straight into the chat (a voice note transcript, a newsletter). Use those too.

## 2. Read the rest

The voice notes and words to avoid in `brand-kit.md`, and `script-desk/about-me.md` if it exists.

## 3. Find the patterns

Study how they say things, not the numbers. For every pattern, quote their exact words and name where it came
from (the reel, the interview question, or the post). Keep a pattern only if it shows up at least twice (a phrase in
`brand-kit.md`'s voice notes counts as one of the two, but only for the same words or the same pattern, not a
similar idea), except stories and labels, which can come from one strong source. A section with no evidence yet
says "Not enough yet: this fills in as you post." Never fill it with a guess. Never invent or tidy a quote. Their typos and
fragments are the point.

## 4. Write the file

Save `script-desk/voice-dna.md` using `.claude/skills/script-kit-library/templates/voice-dna-template.md`.

- **Words I never use:** start from `brand-kit.md`. Anything you only suspect goes in marked "(check me)".
- **AI tells I ban:** the standard list from the template, plus any tell they say bothers them. A tell on the
  standard list that is truly theirs (in their own spoken words at least twice, like "Not smaller. Stronger.")
  stays theirs: note it under their rhythm with the proof and a limit ("once per reel"), not on the ban list.
- Say at the top what it was built from, like "Built from 4 reel transcripts, 6 interview answers and 12
  captions", so the next update knows what's new.

If `voice-dna.md` already exists, update it instead of replacing it: keep everything they edited or crossed out,
add new patterns from new sources, and change the Updated date.

## 5. Test it

Write three first lines for one of their topics using the Voice DNA. Label each with the pattern it uses. Any
fact or opinion they haven't given you stays a bracket or goes in "you". Put
them in the file's "Quick test" section and show them in the chat.

## 6. Check it with them

Ask them to read it out loud and tell you anything that isn't them. When they do, fix the file right away. If
their next message is something else, go with it: the file is saved, and they can come back to it.

## 7. Next

One line: "Every Script Kit skill writes with this now." Then, if a script file already has a hook sprint: "Try
`hook sprint` again with the same idea and hear the difference." If not: "Try `hook sprint` on your next idea."
