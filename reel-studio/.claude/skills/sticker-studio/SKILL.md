---
name: sticker-studio
description: Choose, style and draw stickers, doodles, icons, emoji and badges for reels. Runs automatically on every reel — the user never has to ask. Use also when the user asks for a sticker, doodle, emoji, icon, arrow, label/badge, or "make it more fun/visual".
---

# Sticker Studio

## AI elements first: every reel gets its OWN set (what makes Reel Studio different)
Don't settle for generic emoji when the story has things in it. Read the story, pick 4–8 elements that are
*in it* (Liara's sandbox → sand bucket + spade, splash, baby bottle, tiny alarm clock, "mom on duty" badge),
one style for the whole set (`paper` · `clay` · `watercolour` · `doodle` · `retro` · `realistic` · `3d`;
suggest the one that fits the vibe in one line), in the reel's colours — ONE generation draws them all, so
they match. Show them on the storyboard before building.
1. Default (nothing set up): the free **hfspace** generator — no account, works from the user's own computer
   (small daily quota; if it says the quota is used up, fall back to 2 or 3). Or a connected one
   (`brand/ai.json` provider cloudflare / gemini / huggingface): 
   `python -m engine elements <p> --items "a; b; c" --style clay --story "one line"` → `projects/<p>/elements/*.png`.
2. Higgsfield connected in this chat: `python -m engine elements-prompts <p> --items ...` gives the exact prompt;
   generate it with the Higgsfield tool (1 sheet ≈ 1 credit; check the balance first), save the image to
   `projects/<p>/elements/inbox/`, then `python -m engine elements-cut <p> <image> --items "..."`.
3. Nothing connected: hand them the `elements-prompts` text for **Canva AI (Magic Media) / ChatGPT** —
   "paste this, download the picture, drop it in your elements inbox" — then `elements-cut` it.
   The free no-account generator (pollinations) is a last resort: quality is poor + watermarked; say so.
Use them as `{"image": "projects/<p>/elements/<name>.png", ...}` stickers (collage scenes, plan stickers).
Realistic props for object effects (a recipe box, a vintage printer) come from the same flow with `--style realistic`.
Setting up a free generator: Cloudflare (free daily allowance — account id in brand/ai.json, the API token
through the session's secure credential form for api.cloudflare.com) or a Google AI Studio key (host
generativelanguage.googleapis.com, header `x-goog-api-key`). Never ask for keys in the chat.

**Premium by default.** Read `docs/knowledge/premium-look.md`. Reels use the glass kit unless the
brand is deliberately playful (`"look": "playful"`): frosted glass chips (`badge:`), glass icons
(`icon:`), product **callouts** (`callout:ULTRA THIN|2mm core@540,1000` — dot at x,y on the
product), and serif words (`custom:`). Fewer, bigger, calmer: max 2 graphics on screen.

Non-creative users rely on you to make reels look designed. **Every reel gets stickers
that match what's being said, in the brand's style, without being asked.**
Read `docs/knowledge/sticker-design.md` once per session if you haven't.

## Sticker kinds (mix them)
| Kind | Plan syntax | Best for |
|---|---|---|
| Icon sticker (~1,500 concepts, Phosphor MIT) | `icon:<name>` (auto-found by word) | anything — rocket, baby, gym, suitcase… |
| Glossy 3D emoji (Fluent MIT) | `3d:<concept>` | premium, fun, product |
| Animated emoji (Noto, CC BY) | `anim:fire`, `anim:party`, `anim:love` | reactions, hooks |
| Rubber stamp | `stamp:new drop` | launches, "sold out", "limited" |

**Icon styles** (pack `sticker.style` or per item `"style"`): `cutout` (die-cut sticker),
`chip` (app-icon tile), `puffy` (3D vinyl with gloss), `holo` (holographic), `circle`
(badge disc), `duotone`, `retro` (hard shadow), `neon` (glow), `line`, `bold`, `thin`, `fill`.
Pair them with the pack: bold→cutout/retro · editorial→line/thin · sunny→puffy · playful→
retro/holo · minimal→line/chip · luxe→neon/thin · systems-pilot→chip.

## Drawn & emoji kinds
| Kind | Plan syntax | Best for |
|---|---|---|
| Line doodle / icon | `sticker:<name>` | hand-made, warm, editorial |
| Flat colour / retro / neon | same, style comes from the pack (or `style` in the timeline) | bold, playful, luxe |
| Emoji (Fluent MIT / Twemoji CC-BY) | `emoji:coffee`, `emoji:🔥` | casual, reactions, humour |
| Badge (text in a shape) | `badge:TIP #1`, `badge:$2,000`, `badge:NEW` | lists, prices, labels |
| Photo cut-out | overlay of their photo (see `overlays-and-logos`) | products, people, proof |

Sticker styles: `doodle` (line art), `flat` (solid colour + dark outline), `retro` (flat +
hard offset shadow), `neon` (glowing lines), `emoji`. The pack sets the default; you can
override one item in the timeline (`"style": "neon"`).

## Choosing (every reel)
1. The planner auto-adds obvious ones from spoken words (hours→clock, coffee, money, idea…),
   ~1 per 6 seconds, timed to the word.
2. You add **meaning** the auto-picker can't see: emotions (heart, eyes, sparkle), numbers
   (`badge:3 TIPS`), proof (`badge:$2,000`), jokes (`emoji:😅`).
3. Density: calm packs 2–4 per 30s; bold/playful 4–8 per 30s. Never two on screen fighting
   for attention; none in the first second of the hook.
4. Placement, sizing, collision-avoidance, safe zones and float/pop animation are automatic.

## Never "no sticker": Reel Studio makes its own
If a word isn't in the library, isn't an icon/emoji and isn't auto-detected, **the reel still
gets a sticker** — nobody is ever told "we don't have that one":
1. **Instantly (automatic, no credits):** `render("matcha", ...)` falls back to a *custom
   lettered sticker*: the word in the brand's script font, brand colours, sparkle, die-cut
   white edge + shadow (`custom:<words>` forces one, e.g. `custom:launch day`). The word is
   logged in `library/stickers/requests.json` (`python -m engine sticker-requests`).
2. **Next (you, at the start of a session or when asked):** read `requests.json`, draw an
   illustrated SVG for each requested concept (rules below), add tags to `index.json` and
   remove it from `requests.json`. From then on every user/reel gets the illustrated one.

## Sticker fonts (words on stickers match the brand, or the user's choice)
- **Automatic (default):** lettered stickers use the brand's script font; badges and stamps use
  the brand's headline font. So two brands never get the same-looking stickers.
- **User's choice for all stickers:** Studio → My brand → Fonts, or
  `python -m engine font-use "<font>" --role sticker` (lettering) / `--role sticker_label`
  (badges, stamps). `font-use auto --role sticker` goes back to automatic.
- **One sticker only:** add `"font": "<role or font name>"` to that item in timeline.json, e.g.
  `"font": "serif"` or `"font": "Pacifico"`. Pick a contrast to the title font, not a copy of it.
- Their **own font** (bought/custom, not on Google): `python -m engine font-add <file> --role sticker`
  or the upload button in My brand. `.ttf`/`.otf` only; remind them to check the licence
  allows video/social use.

## The library is open — draw what's missing
Search: `from engine import stickers; stickers.find("rocket")`. If `None` and no good emoji,
**draw it**: write `library/stickers/<name>.svg` and add tags to `library/stickers/index.json`.

SVG rules (so it recolours to any brand and matches the set):
- `viewBox="-10 -10 220 220"`, drawing within 0–200; a simple silhouette readable at 150px.
- `stroke-linecap="round" stroke-linejoin="round"`, `stroke-width="{stroke}"`.
- Colours only via placeholders: `{accent}` lines, `{pop}` one highlight detail, `{paper}`
  fill of closed shapes. No hard-coded colours, no text, no gradients.
- 2–6 paths, slightly imperfect curves (hand-made feel).
- Render once to check: `stickers.render("<name>", packs.load(), 300).save("out/check.png")`
  and look at it. Fix, then use it. It's now available to every future reel.

Tags should include synonyms people say ("rocket": launch, grow, fast, start, boost).

## Legal
Only our generators, SVGs drawn here, Fluent Emoji (MIT) and Twemoji (CC-BY 4.0, credited in
docs/CREDITS.md), and the user's own files. Never copy stickers out of CapCut, Canva, Giphy
or other apps — study the idea, draw our own version.
