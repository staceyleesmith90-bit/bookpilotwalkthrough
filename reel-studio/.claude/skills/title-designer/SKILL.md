---
name: title-designer
description: Design beautiful layered titles and text moments — script over serif, tracked small caps, dates, pill tags, sparkles, typewriter lines, and big words BEHIND the person. Use for every reel's opening title, chapter titles, location lower-thirds, and whenever the user wants "prettier text", "aesthetic titles", "like CapCut", "text behind me", "typewriter text".
---

# Title designer

Read `docs/knowledge/title-design.md` once per session. Titles are what make reels look
designed — treat them like a graphic designer would, not like subtitles.

## Templates (`python -m engine titles`)
| template | Looks like | Best for |
|---|---|---|
| with-me | small tracked caps + big 2-line script + date | vlogs, "a day with me", soft/editorial |
| diary | tracked kicker + serif caps + script tucked under | lifestyle, routines |
| mini | serif word over a crossing script word | short 2-word titles |
| episode | oval badge + brush script + rotated "Eps #1" + location pin | series, daily vlogs |
| sparkle | chunky pop serif + glowing script + stars + pill tag | fun updates, announcements |
| headline | huge serif caps (+ `behind: true`) + script word | bold openers, "TODAY vlog" |
| slice | light serif lead-in + bold serif word | weekend / slice-of-life |
| typed | typewriter strips that type on with key clicks | POV, confessions, tips |
| location | pin + tracked place + line + date | travel, events (lower third) |
| chapter | outline number + kicker + script | multi-part reels, lists |

## In a plan
```json
{"line": 1, "do": ["title"], "title": {"template": "with-me", "title": "A Day With Me",
                                      "kicker": "mini vlog", "sub": "January 2026"}}
{"line": 1, "do": ["title"], "title": {"template": "headline", "title": "Today", "script": "vlog", "behind": true}}
{"line": 4, "do": ["title:typed:POV: you finally have a system"]}
{"line": 9, "do": ["title:location:Cape Town"]}
```
Optional fields per template: `kicker`, `sub` (date/subtitle), `tag` (pill or "Eps #1"),
`location`, `script` (the small script word), `number`, `size` (default 1.3), `y` (place it).

## Rules that make it look "elite"
- **Contrast of fonts**: one script + one serif/sans, never two scripts. Script big, caps small.
- **Overlap on purpose**: the script crosses the serif line. Rotate small accents −4° to −12°.
- **Tracking**: small caps get wide letter-spacing (the kicker); big words stay tight.
- **Hierarchy**: 1 hero word, 1 supporting line, 1 tiny detail (date, location, tag). Max 4 layers.
- **Stagger**: layers arrive one after another (0.15–0.5s apart) — done automatically.
- **Behind the person**: only on talking-head footage with a clear subject; placement is
  automatic (hairline height). Use one big word, 4–7 letters, uppercase serif.
- **Fonts come from the brand** (`title_fonts` in brand.json). Never force a font outside the pack.
- **Typewriter** for honest/POV lines; each character clicks (sound added automatically).
- Title on screen 2–4 seconds; captions hide while it's up (except location lower-thirds).
- Don't use the thought bubble for style moments; prefer `note:<text>` (handwritten aside +
  drawn arrow) or a `typed` title.
