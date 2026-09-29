---
name: editing-lingo
description: Translate video-editing vocabulary into engine actions, and explain terms in plain words. Use whenever the user (or a style plan) mentions editing terms — b-roll, A-roll, jump cut, J-cut, L-cut, punch-in, transitions, whip, karaoke captions, lower third, takeover, hook, pattern interrupt, colour grade, LUT, SFX, riser, beat sync, safe zone, etc. — or asks "what does X mean?".
---

# Editing lingo

**Users should never need these words.** You pick treatments from the reel's idea
(`reel-recipes`). This skill is for understanding users who DO use jargon, explaining terms
kindly, and mapping any term to something the engine does.

Plan treatments (`do` in plan.json) cover most terms:
takeover · hook · punch-in · bubble · label · sticker · emoji · badge · broll · card · cta ·
reveal (riser→hit) · sfx. Captions/grade/pack are plan-level settings. Anything else
(J/L-cuts, speed ramps, masks) → edit the timeline or the engine code.

Users will use editor words loosely ("make it pop", "add some b-roll", "kareoke captions").
Map what they say to a concrete action from the glossary, do it, and — for non-editors —
explain the term in brackets the first time: "added a punch-in (a quick zoom for emphasis)".

Accept misspellings and synonyms: kareoke/karaoke, broll/b roll, transistion, sfx/sound fx.

Full glossary with the engine action for each term: `glossary.md` (same folder). Read it when a
term comes up that you're not sure how to execute.

## Most-used, at a glance
| They say | Means | Do |
|---|---|---|
| A-roll | The main footage (person talking) | Base track |
| B-roll | Extra footage laid over the talking | Cut in over the line it illustrates, audio stays A-roll |
| Jump cut | Cut out a pause inside one shot | Rough-cut silence removal |
| Punch-in / zoom cut | Sudden zoom (110–120%) on the same shot | Emphasis on key words; hides jump cuts |
| Hook | First 1–3s that stops the scroll | Hook banner text + fastest pacing |
| Takeover | Text fills the screen | `treatment: takeover`, main font |
| Karaoke captions | Words light up as spoken | Caption style `karaoke`, pop colour on active word |
| Single-word captions | One word at a time, centre | Caption style `single-word` |
| Lower third | Label in the bottom third (name/title) | Keep above the 440px bottom safe zone |
| Thought bubble | Inner-voice text | `treatment: bubble`, accent font, auto-fit |
| Pattern interrupt | Sudden change to re-grab attention | Punch-in, SFX, sticker or colour flash |
| Transition | How one shot changes to the next | Pick from glossary: cut, whip, zoom, flash, slide, blur |
| SFX | Sound effects | Pack `sfx` set; on text pops, stickers, transitions |
| Riser / hit | Build-up sound / impact sound | Before and on a reveal |
| Beat sync | Cuts land on music beats | Detect beats, snap cuts |
| Colour grade / filter / LUT | The overall colour look | Apply pack `grade` |
| Safe zone | Area not covered by app buttons | Enforced by `layout.SAFE_BOX` |
| Pacing | How fast things change | Tighter for hooks/lists; slower for emotional lines |
| Cover / thumbnail | Still image shown in the grid | Pick the best frame + hook text |
