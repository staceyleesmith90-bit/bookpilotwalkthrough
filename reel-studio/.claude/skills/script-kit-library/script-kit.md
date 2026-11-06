# The Script Kit, inside the Reels Editing Engine

This engine also has the Script Kit: ten script-writing skills in `.claude/skills/` (every description starts
"Script Kit.") and their shared `.claude/skills/script-kit-library/`. Their work lives in `script-desk/`. This
file comes with the kit, not with the engine, so no engine update ever changes it.

**Script work is in scope here.** CLAUDE.md says this engine edits, and only that. With the Script Kit installed,
writing the script before the shoot is in scope too, as its own lane before the edit. When she asks for hooks, a
script, her Voice DNA, what's working in her reels, a breakdown of a reel, or a week plan, run the matching
Script Kit skill and follow its house rules. That lane reads `brand-kit.md` but writes only inside
`script-desk/`. It never touches `projects/`, the edit pipeline or any engine file, and the engine's editing rules
apply to edits exactly as written.

| She says | Run this Script Kit skill |
|---|---|
| "set up my script desk", "update my script desk", "what can the Script Kit do" | `script-desk` |
| "hook sprint", "write hooks for ..." | `hook-sprint` |
| "script this", "write a script for ...", "turn this into a reel script" | `script-this` |
| "check my script", "fix my script", "tighten this script" | `check-my-script` |
| "find the demo", "how do I show this" | `find-the-demo` |
| "build my voice DNA", "never say [word] in my scripts" | `voice-dna` (not `learn`, which keeps editing preferences) |
| "what's working for me", "transcribe my old reels", "get my reels from Instagram", "I don't have many reels yet", her own reels pasted in, or why her reels aren't getting views | `whats-working` (not `pull-reels`, which clips a long video, and not `report-a-problem`, which is for broken tools) |
| "break this down" with a reel link or pasted words | `break-it-down` (not `reference-reel`, which studies a reel's editing) |
| "tutor me", "tutor me on this", "why did this go viral", several post links to study together | `script-tutor` |
| "plan my week", "what should I film this week" | `plan-my-week` |

- **"Set up my script desk" is not the engine's first run.** It runs `script-desk`. If `brand-kit.md` still has
  `<<` placeholders, the engine's own setup comes first, and the desk right after.
- **Reel links with no ask.** While she's filling her desk with reels she loves, the links go to `whats-working`.
  Otherwise ask one question: study its editing (`reference-reel`), find out why it worked (`break-it-down`, or `script-tutor` for several posts or a carousel), or
  save it as a reel she loves (`whats-working`).
- **Her scripted ask.** CLAUDE.md's rule that no caption or end screen carries a sales ask is about the edit: the
  engine adds no business or CTA logic of its own. A spoken ask she scripted and filmed (a comment keyword, a
  follow, a save, a send) is her own words: keep it in the cut like any other line. Put it on screen only when
  her script's edit notes ask for it.
- **Editing a reel she scripted.** When she points at a script in `script-desk/scripts/` or pastes one ("here's
  my script with edit notes, edit this reel"), read it before planning the edit. Its `(edit: ...)` notes are her
  direction, written in the engine's own words (`product/BUILD-VOCABULARY.md`): plan each one on its line. Its
  hook "Read" line is her hook block, still held to the engine's hook rules; if it breaks one, say which and
  offer a fix. Filming direction is context only. Plan first and get her approval, as on every job.
- **Hook copy.** The Script Kit writes the "Read" line to the engine's hook rules: one block at the top of the
  frame, a line that names who it's for, never a repeat of the spoken line. If the two ever differ, the engine's
  hook rules win for anything on screen.
- **Her language.** A script written in Spanish, or any language, gets its on-screen words in that same
  language. She talks to Claude in her language, and her reels come back in it.
- **Her Voice DNA.** When `script-desk/voice-dna.md` exists, read it before writing any on-screen words in an
  edit: hook blocks, thought bubbles, b-roll hook lines, graphics. It holds her real phrases and the words she
  bans. If it ever disagrees with `brand-kit.md`, the brand kit's hard rules win.
- **Whose folder it is.** `script-desk/` is her own, made by her Script Kit. Any skill that finds it, `homebase`
  included, calls it her Script Kit, never "another product".
