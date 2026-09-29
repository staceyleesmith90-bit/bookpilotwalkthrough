# Studying CapCut / TikTok templates — and doing better

Sources: CapCut's public template pages and TikTok discovery pages for "trending CapCut
templates 2026" (links in sources.md), plus the vlog-title screenshots studied for
title-design.md. We study formats and techniques; we never copy template files or assets.

## What the popular templates are
| Type | What it does | Our template |
|---|---|---|
| Day in my life / mini vlog | script title + time stamps over cosy b-roll | day-in-my-life, morning-routine |
| Photo dump | 6–12 photos cut on the beat, flash transitions | photo-dump |
| Recap (week / month / year) | labels per period, nostalgic grade | week-recap, year-recap |
| Velocity / beat edits | speed ramps and hard cuts on music beats | photo-dump, outfit-check (pulse zooms on beats) |
| Aesthetic text / quote | one designed line over a calm clip | quote, pov |
| Trend formats (POV, this or that) | text prompts that invite comments | pov, this-or-that |
| Glow-up / before-after | reveal with flash + riser | before-after |
| Birthday / event | title, photos, sparkles | photo-dump + sparkle title |

## Why they work
1. **One strong title** in a pretty font pairing within the first second.
2. **Rhythm**: cuts land on beats; every change has a sound.
3. **A reason to keep watching**: numbers, days, labels, a reveal.
4. **Low effort to fill**: "add 8 photos" and done.

## Where CapCut templates fall short (our advantage)
- **They look like everyone else's.** Same fonts, same colours, same sticker on 300k videos.
  → Ours render in the user's brand (fonts, colours, sticker style, logo) automatically.
- **Fixed slot counts and timings.** 8 slots means 8 photos, cut to someone else's song.
  → Ours adapt to however many clips they have and their own voice/length.
- **No guidance on what to film.** → Every template has a shot list and a script prompt.
- **No voice / no captions of *their* words.** → Talking-head templates cut, caption and
  style their real voice.
- **Trending sounds may not be licensed for business use.** → Built-in royalty-free music.
- **Music and text are someone else's taste.** → Their inspiration reels and vibe steer it.

## How Claude uses this
- When the user describes an idea, check `library/templates.json` for a matching template
  and offer it: "This fits the Photo Dump template — want to use that?"
- New trend? Study 2–3 examples (inspiration-reels skill: one contact sheet each), write a new
  template entry (name, why, film, script, title, beats, captions, grade, transition, zoom,
  stickers, music) and add it to the library so every user gets it.
