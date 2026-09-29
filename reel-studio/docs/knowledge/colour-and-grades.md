# Colour, filters and grades

## Brand colour roles
`bg` background (faceless reels, cards) · `ink` main text · `pop` highlight (karaoke word,
badges, one sticker colour) · `accent` second sticker/label colour · `paper` bubble & sticker
fill · `bubble_text`. `packs.check()` enforces readable contrast (text ≥ 4.5:1).

Palette rules: one dominant brand colour + one accent + neutrals. Highlight colours (yellow,
blush) can be low-contrast on light backgrounds — use them for shapes/badges, and outline them
when used as text.

## Our grades (filters) — `engine/grades.py`
| Grade | Look | Good for |
|---|---|---|
| clean-bright | true colour, slightly brighter/crisper | business, tutorials |
| warm-film | warm, lifted blacks, light grain | lifestyle, family, cosy |
| soft-matte | faded, gentle | calm, editorial |
| vivid | punchy saturation/contrast | playful, food, travel |
| moody | deep shadows, cool tint, vignette | luxe, beauty, night |
| cool-crisp | cool and sharp | tech, minimal |
| vintage-fade | faded retro colour + grain | nostalgic, retro |
| bw-classic | black & white + grain | dramatic, quotes |
| golden-hour | warm glow | outdoors, lifestyle |

How grades are made: white balance (colorbalance), tone curve (curves: lifting blacks = film
/matte look), saturation/contrast (eq), texture (noise = grain), vignette. To add a new grade,
combine those, name it by feel, add a one-line description.

Users can also bring `.cube` LUT files they own (drop in `inbox/`, `"grade": "name.cube"`).
Inspiration reels suggest a grade automatically from measured brightness/contrast/saturation/warmth.

Never copy filters out of other apps; describe the look, then build it from these parts.
