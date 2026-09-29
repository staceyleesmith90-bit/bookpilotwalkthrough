# Motion, transitions, layout and pacing

## Entrance animations (`anim` on timeline items)
| anim | Feel | Use for |
|---|---|---|
| pop | bouncy scale-in (ease-back overshoot) | stickers, takeovers, badges — the default |
| fade | soft | logos, cards, calm packs |
| slide | rises into place | CTAs, lower thirds |
| type | letters appear left→right | labels, "typing" moments (pair with click) |
| drop | falls in from above with bounce | playful badges, reveals |
| none | instant | hard-cut energy, precise edits |
Exit is a quick fade (0.15s). Idle stickers float gently.

**Timing**: entrances 0.2–0.35s. Things appear *on the word* they belong to.

## Transitions (between shots / beats)
| Transition | Feel | Pair with |
|---|---|---|
| hard cut | default, energetic | nothing or a soft pop |
| jump cut | removes pauses in one shot | none (hide with punch-in) |
| punch-in (zoom cut) | emphasis, pattern interrupt | hit or nothing |
| whip / slide | fast change of topic | whoosh |
| flash | reveal, "and then…" | hit |
| fade / dip | emotional, time passing | soft swish or music only |
| b-roll insert | show, don't tell | whoosh on entry |
Rule: one transition style per reel + punch-ins; fancy transitions max 2–3 per reel.

## Layout (1080×1920)
- **Safe zone**: x 60–930, y 220–1480. App UI covers the rest (profile, caption, buttons).
- **Face zone** (talking head): roughly x 230–850, y 380–1180 — keep stickers out.
- **Caption line**: y ≈ 1245 (lower third, above the app caption).
- **Hook banner**: y ≈ 380, top of the safe zone.
- **Takeover**: centred, up to 4–5 lines, hides captions while on screen.
- **Stickers**: near the related text, top-right corner of a takeover is the classic spot.
- The engine enforces all of this (`layout.free_spot`, shrink-to-fit, collision boxes).

## Pacing & retention
- **Hook ≤ 2 seconds**: name the payoff or tension. Cut greetings.
- **Pattern interrupt every ~8–12 seconds**: takeover, punch-in, b-roll, card, sticker, sound.
- **Cuts per minute** (from inspiration reels): slow < 12, medium 12–30, fast > 30.
- **Line length**: lines over ~6s get flagged in review — viewers drift.
- **End on the CTA**, not on "bye".
