---
name: brand-onboarding
description: Interview a new user and set up their brand (colours, fonts, logo, voice, sticker style, captions) so every reel is on-brand. Use on first run (no brand/brand.json), when the user says "set up my brand", "change my brand/colours/fonts/logo", "I don't have a brand yet", or shares a website, logo or mood board for their brand.
---

# Brand onboarding (the setup interview)

Goal: `brand/brand.json` + `brand/logo.*` + a preview they love, in about 10 minutes.
Friendly, one question at a time, always with examples. Never ask for hex codes without
offering the easier routes. Point them to `START-HERE.md` for what to have ready.

## Step 0 — Welcome (say this, in your own words)
"Let's set up your look once so every reel comes out on-brand. I'll ask about 6 quick
things. If you have a website or logo I can pull most of it for you. No brand yet? I'll
suggest a few looks."

## Step 1 — Pick a route (ask which fits)
**A. "I have a website"** → `python -m engine brand-site <url>`. It returns colours (most
used first), fonts and logo candidates. Show the colours as a short list, confirm which are
really theirs. Download the logo they confirm (`brand.download_logo(url)`), or ask them to
drop their logo file in `inbox/`. If the site blocks reading (403), ask for a screenshot of
their homepage and use route B on it.

**B. "I have a logo / photo / mood board"** → save it in `inbox/`, then
`python -m engine brand-image inbox/<file>` for a palette + suggested roles. Look at the
image once (one Read) to name the vibe.

**C. "I don't have a brand yet"** → ask for 3 vibe words (examples: warm, bold, calm,
playful, luxe, clean, retro, natural). `python -m engine brand-starters "<words>"` makes 3
complete looks with preview images in `brand/previews/`. Show them (one Read of each is fine,
or a single combined look). Let them pick or mix ("look 1 colours with look 3 fonts").

**D. "I know my hex codes / fonts"** → take them directly.

**E. "I designed my style in Canva"** (or Figma/any design tool) → ask them to export the style
guide / brand-kit page / a few designs they love as PNG (or PDF) and drop them in the chat or
inbox/. Run `python -m engine brand-image <file>` for the exact colours; look at the image once to
read the font names, title styles, and sticker/graphic vibe (glass, editorial, playful…). Google
fonts → `brand.google_font`; Canva-only/bought fonts → they upload the .ttf/.otf (My brand → Fonts).
Mirror their design choices in the pack (title fonts, caption style, sticker look, colours).

## Step 2 — The 6 questions (skip any already answered by the route)
1. **Vibe** — three words for how your content should feel.
2. **Colours** — main brand colour(s), plus light or dark background preference.
3. **Fonts** — any fonts you use? (If it's a Google Font, `brand.google_font("Name")`
   downloads it legally. If it's a paid/custom font they own (not on Google), they upload the
   .ttf/.otf in Studio → My brand → Fonts, or drop it in `inbox/` and you run
   `python -m engine font-add inbox/<file> --role headline` (roles: headline, accent, caption,
   script, serif, sans, sticker, sticker_label). Never copy fonts from apps like CapCut/Canva.) Otherwise pick for them from
   the pairings in `docs/knowledge/typography.md`.
4. **Text energy** — loud & bold, or soft & minimal on screen?
5. **Stickers** — none / a few / lots, and which style: doodle, flat colour, retro, neon,
   emoji (show `library` examples or render `brand-preview` with each if unsure).
6. **Logo** — on every reel? Where (corner) and how big? (Default: small, top-left.)

Also capture (for scripts and captions): who they talk to, 3 words they'd never use, and
their sign-off / CTA style. Save these under `"voice"` in brand.json.

## Step 3 — Build, check, preview
```python
from engine import brand, packs
p = brand.build_pack("Their Name", colors, main_font, accent_font, caption_font,
                     prefer="light", sticker_style="flat", vibe="warm, honest, fun",
                     logo="brand/logo.png", captions="karaoke")
p["voice"] = {...}
print(packs.check(p))   # fix any contrast warnings before saving
packs.save_brand(p)
```
Then `python -m engine brand-preview` and show the image. Adjust from feedback until
they say yes. Tell them they can change it any time ("change my brand colours").

## Rules
- Contrast must pass `packs.check` (text readable). Fix silently by adjusting roles.
- Sticker lettering follows the brand script font automatically; ask "want your stickers in a
  specific font?" only if they care (`font-use "<font>" --role sticker`).
- One loud font only. Pair opposites (see typography doc).
- Keep it short. If they seem tired, finish with sensible defaults and move on to editing.

## Where they'll watch their edits (ask once, at the end)
"Where will you usually watch your edits — on your phone, your computer, or both?" Save it as
`"review_device": "phone" | "computer" | "both"` in brand/brand.json. The review page opens in that
mode (phones get the iPhone/Android-safe video, a sound check and "Save video to my phone";
computers get the browser player). They can switch any time with the Phone/Computer buttons.
