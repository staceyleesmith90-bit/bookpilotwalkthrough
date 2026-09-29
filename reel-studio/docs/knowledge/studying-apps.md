# How to study CapCut (and other apps) — legally — and turn it into our own effects

CapCut, Canva, Instagram and TikTok have great design, pairings and sounds. Their **files**
(stickers, templates, fonts, filters, sounds) are licensed only for use inside their apps, so
we never extract or copy them. What we copy is **understanding**: techniques and principles,
which nobody owns. Then we build our own version.

## The loop (repeat for every effect worth having)
1. **Capture** a short screen recording or public reel that uses the effect. Save to `inbox/`.
2. **Break it down** with the `watch` skill focused on 2–3 seconds (`--start/--end`):
   what moves, how fast, what easing, what sound, where on screen, what colours, how it exits.
3. **Write a one-line spec** in plain words, e.g.
   "Word slams in at 115% → settles to 100% in 0.25s, white with dark outline, hit sound on land."
4. **Build** it from our parts: an `anim` preset, a sticker/badge, a grade recipe, an SFX.
   If a new part is needed, add it to the engine (a new `anim`, sticker generator, grade,
   sound function) — our code, our drawing.
5. **Test** on two packs (light + dark), check it reads on a phone.
6. **Name and log it** in `docs/knowledge/effects-log.md` (name, spec, what inspired it in
   general terms, where it lives in the code).

## What to look for when studying
- **Pairings**: which font goes with which sticker style and which sound. Apps sell *sets* —
  that's why they look coherent. Our packs do the same.
- **Micro-timing**: overshoot on pop-ins, 2–4 frame flashes, sounds landing on the frame.
- **Restraint**: how few elements are on screen at once.
- **Motion curves**: ease-out for arrivals, ease-in for exits, overshoot for playful.
- **Layering**: shadow/outline for text over busy footage; die-cut outlines for stickers.

## Red lines
- No ripping assets, fonts, LUTs or sounds from apps or templates.
- No recreating a specific branded template 1:1 (e.g. an app's named template); take the idea
  and make it ours.
- No copying a creator's reel content, script or look wholesale — learn the style, apply the
  user's own brand.
