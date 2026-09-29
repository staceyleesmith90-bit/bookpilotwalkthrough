# Sound design for short-form video

Sound is half of why app-edited reels feel "finished". The rules are simple; timing is everything.

## The core kit (all built into `engine/sfx.py`, royalty-free by construction)
| Sound | Job | When |
|---|---|---|
| **pop** | something appears | text pop-in, sticker, badge |
| **whoosh / swish** | movement | transitions, b-roll in, slides, whips |
| **hit** | impact | hook slam, full-screen takeover, smash cut |
| **riser → hit** | build + payoff | before a reveal, result, price |
| **ding** | positive / done | result, CTA, checkmark |
| **tick** | counting | numbered lists, count-ups, timers |
| **click** | UI / typing | typewriter text, screen recordings |
| **boing** | comedy | punchline, fail, silly moment |
| **shutter** | photo | photo cut-out appears, "snapshot" moments |
| **notify** | phone | DM/notification moments, CTA |

## Rules
1. **Sync to the frame.** The peak of the sound lands exactly on the visual change. A whoosh's
   loudest point = the cut; a riser peaks into the reveal.
2. **Less is more.** 2–3 well-placed sounds beat 10 random ones. Our planner keeps roughly
   ≤ 1 effect per 2 seconds; the hook and the reveal get the strongest ones.
3. **Voice first.** Effects sit under the voice (≈ 50–70% level for transitions). Music is
   ducked automatically whenever someone talks.
4. **One sound family per reel.** Match the pack: soft packs → click/swish/ding; bold →
   pop/hit/whoosh; playful → boing/pop; luxe → swish/riser/ding.
5. **Open strong, close positive.** A clean impact or notification on the hook grabs attention;
   a soft ding on the CTA makes the ask feel good.
6. **Don't repeat back to back.** Alternate pop / swish variants so it doesn't sound robotic.

## Music
- Background music at ~15–20% under speech, fading out over the last second.
- Users bring tracks they have rights to (drop in `inbox/`). For business accounts, platform
  "trending sounds" may not be licensed for commercial use — say so.
- Beat-synced edits: place cuts/pop-ins on the beat when a track is used (future: beat detection).

## Bringing their own library
Users with a subscription library (e.g. Epidemic Sound) can drop `.wav` files into
`library/sfx/` or `inbox/` and use them by file name: `sfx:my-whoosh.wav`, or set pack
`"sfx": {"transition": "my-whoosh.wav"}`.

## How pro short-form editors sound-design (studied from CapCut / Premiere tutorials, 2026)
Three passes, in order:
1. **Motion** — anything that moves gets a whoosh. Match the whoosh to the move: long soft whoosh
   for a slow push-in (stretch it to the move's length), short swish for a pop/slide, and put the
   whoosh's LOUDEST point on the frame with the most motion blur (the peak of the move).
   Two moves at once (pop + zoom) = small whoosh layered on a bigger one.
2. **Texture** — tactile sounds make graphics feel real and direct the eye: pop-ups = soft clicks,
   typewriter text = one key per letter (vary the keys, quieter on spaces, a ding at the end),
   slides/highlighter swipes = paper/card slides, glows = digital blips/bells, glass UI = glass taps,
   data/numbers = data blips. "Colour correction for audio."
3. **Lift & hit** — risers build anticipation into a reveal; a hit releases it. Big hits are
   LAYERED across frequencies (sub thump + mid punch + high shimmer) — one sound feels thin.
Rules: commit to ONE sound style per video (clean ≠ streetwear ≠ luxury); never reuse the
identical sample back-to-back; SFX sit under the voice; carve a pocket in the music around
1–4 kHz so the voice sits on top (don't just turn the music down); ease music in with a riser
and end on a hit or a reverb tail, never a hard stop.

In Reel Studio: `engine/sounddesign.py` does all of this automatically. Kits: clean · luxe
(premium look) · playful · digital (bold). Plan keys: `"sound_kit"`, `sfx:<name>` for one-offs.
Samples: Kenney CC0 packs (library/sfx/kenney) + synthesised whooshes/risers/hits.
