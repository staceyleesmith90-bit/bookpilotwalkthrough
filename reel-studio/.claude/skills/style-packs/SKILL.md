---
name: style-packs
description: Choose or change the overall look of reels — fonts, colours, colour grade/filter, sticker style, caption style and sound set. Use for "make it look more calm/bold/luxury", "change the filter", "use another style", "try it in the playful look", or when comparing looks.
---

# Style packs

A pack = tokens only: fonts by role, colours, sticker style, sounds, grade, captions. Swap
the pack → the whole reel restyles. The user's own pack is `brand` (brand/brand.json, made by
`brand-onboarding`). Presets in `library/packs.json`:

| Pack | Feel | Fonts | Stickers | Grade | Captions |
|---|---|---|---|---|---|
| bold | loud, modern | Poppins ExtraBold + Caveat | doodle, die-cut | clean-bright | karaoke |
| editorial | calm, classic | Playfair + Playfair Italic | thin doodle | soft-matte | line |
| sunny | soft, warm | Nunito Black + Shadows Into Light | flat, die-cut | warm-film | karaoke |
| playful | bouncy, fun | Baloo 2 + Pacifico | retro | vivid | single-word |
| minimal | clean, quiet | Inter | thin line | clean-bright | line |
| luxe | rich, moody | Cormorant + DM Serif | neon | moody | line |
| systems-pilot | smart, modern (Systems Pilot brand) | Poppins + Inter | chip | clean-bright | highlight |

Try a look on one reel: set `"pack": "<name>"` in plan.json (or the editor's pack menu).
Preview any pack as a still: `python -m engine brand-preview <pack>`.

## Grades (filters) — `engine/grades.py` (29 looks, grouped in `GROUPS`)
Everyday: clean-bright, clean-girl, peachy, vivid, cool-crisp · Warm & soft: warm-film, latte,
golden-hour, creamy-pastel, soft-matte · Dreamy: soft-glow, dreamy-haze · Film: portrait-film,
green-film, disposable, vintage-fade, sepia-memory · Cinematic: cinematic, teal-orange, moody,
noir, bw-classic · Seasonal & retro: summer, winter, retro-80s, vhs, night-neon. Users can also drop a `.cube` LUT in `inbox/` and use
`"grade": "file.cube"`. Describe grades in plain words (see DESCRIPTIONS in grades.py).

## Caption styles (`engine/captions.py`, 14)
karaoke · single-word · line · box · highlight · bounce · outline · neon · build · two-tone ·
elegant · shadow · stacked · typewriter · off.

## Motion (`engine/fx.py`)
Pack keys `transition` and `zoom` set defaults. Transitions: flash, dip-black, dip-white, whip,
zoom-blur, glitch, light-leak, pixelate, spin, blur, shape-wipe (brand colour), rgb-split,
film-burn. Zooms: punch, push, pull, whip, shake, pulse, focus (towards the face), drift. Takeovers and cards hide captions automatically.

## Changing the brand
Edit brand/brand.json via Python (`packs.load("brand")` → change → `packs.save_brand`), run
`packs.check` for contrast, then `brand-preview`. Explain changes in plain words.
