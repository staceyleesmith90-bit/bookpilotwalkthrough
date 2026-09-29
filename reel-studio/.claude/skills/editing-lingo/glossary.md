# Editing glossary → engine actions

In plan.json terms: takeover = `takeover`, hook banner = `hook:`, punch-in = `punch-in`,
b-roll = `broll:<file>`, callout/label = `label:`, badge = `badge:`, title card = `card:`,
reveal = `reveal`, CTA = `cta:`, any SFX = `sfx:<pop|whoosh|swish|click|ding|hit|riser|tick|boing|shutter|notify>`.

Plain meaning first, then what the engine does. Grouped so Claude can scan quickly.

## Footage & structure
- **A-roll** — main footage, usually the person talking. → Base video + audio track.
- **B-roll** — supporting clips over the A-roll audio (hands typing, coffee, kids playing). → Insert over the line it illustrates; A-roll audio continues underneath.
- **Cutaway** — a brief b-roll shot, 1–2s. → Short b-roll insert.
- **Insert** — close-up detail (product, screen). → B-roll insert, often with punch-in.
- **Talking head / yap** — person speaking to camera. → Talking-head format.
- **Faceless** — no person on screen (text, b-roll, voiceover). → Faceless/text format.
- **Voiceover (VO)** — narration recorded separately. → Voiceover format; cut b-roll to the words.
- **Rough cut** — first assembly: best takes, silences removed. → Step 2 of the flow.
- **Fine cut / final cut** — polished version. → After review + style build.
- **Take** — one attempt at a line. → Keep the warmest/clearest take.
- **Beat** — one idea/line in the reel. → One row in the style plan.
- **Hook** — first 1–3 seconds. → Hook banner, fastest pacing, no stickers in first second.
- **CTA (call to action)** — "comment X", "follow for more". → End card or caption line, pop colour.
- **Loop** — ending flows back into the start. → Match last frame/line to the first.

## Cuts
- **Hard cut** — instant change. → Default cut.
- **Jump cut** — removes a pause within one shot. → Silence/false-start removal.
- **J-cut** — next clip's audio starts before its picture. → Lead audio 0.2–0.5s.
- **L-cut** — current audio continues over the next picture. → Trail audio 0.2–0.5s.
- **Match cut** — cut between two shots with matching shape/motion. → Align on the similar frame.
- **Smash cut** — abrupt cut for comedy/shock, often with a sound hit. → Hard cut + hit SFX.
- **Punch-in / zoom cut** — jump to 110–120% scale on the same shot. → Scale step on key words.
- **Speed ramp** — speed up/slow down smoothly. → Ramp playback rate.
- **Freeze frame** — hold one frame. → Hold + optional label/sticker.

## Transitions
- **Whip / swipe** — fast slide with motion blur. → Slide out/in + whoosh.
- **Zoom transition** — zoom through into the next shot. → Scale + blur + whoosh.
- **Flash / dip to white** — quick white frame. → 2–4 frames white + hit.
- **Dip to black / fade** — calm, emotional change. → 6–12 frame fade.
- **Crossfade / dissolve** — one image melts into the next. → Opacity blend.
- **Glitch** — digital distortion for 3–6 frames. → RGB split + offset slices.
- **Shape wipe** — circle/star/brand-shape reveals next shot. → Mask wipe in pack colour.
- **Blur transition** — blur out, blur in. → Gaussian ramp.
- **Spin** — rotate out/in. → Rotation + blur.

## Text & captions
- **Captions / subtitles** — spoken words on screen. → Caption style from pack.
- **Karaoke captions** — words highlight as they're spoken. → Active word in `pop` colour.
- **Single-word captions** — one word at a time. → Centre, main or caption font, pop-in.
- **Line captions** — a short line at a time. → 2–5 words per line.
- **Kinetic typography** — animated text as the main visual. → Faceless format, takeovers.
- **Full-screen takeover** — text fills the screen. → `treatment: takeover`.
- **Hook banner / hook card** — persistent title at the top. → Top of safe zone, first beats.
- **Lower third** — label in the lower third. → Above bottom safe zone.
- **Callout** — label + arrow pointing at something. → Accent font + arrow sticker.
- **Text pop / text in** — text arrives with a bounce. → Ease-back scale + pop SFX.
- **Typewriter** — letters type on. → Reveal left to right + click SFX.
- **Highlight / marker** — coloured block behind a word. → Pop-colour rectangle, hand-drawn edge.
- **Stat pop / count-up** — number counts up. → Animate number + tick SFX.
- **Numbered steps** — "1, 2, 3" headers. → Step badge + takeover.
- **Designed moment / title card** — full-frame designed card. → Card in pack colours.

## Graphics & overlays
- **Sticker** — small graphic (doodle, icon). → `sticker-studio` (automatic).
- **Doodle** — hand-drawn style line art. → Sticker style with wobble.
- **Die-cut** — white outline like a real sticker. → Pack `sticker.die_cut`.
- **Cut-out** — subject removed from its background. → Background removal + die-cut outline.
- **PiP (picture in picture)** — small video/image over the main one. → Rounded card overlay.
- **Watermark** — logo in a corner. → `overlays-and-logos`.
- **Emoji pop** — emoji appearing on a word. → Sticker or emoji at the word time.
- **Progress bar** — shows how far through the reel. → Thin pack-colour bar at top.

## Sound
- **SFX** — sound effects. → Pack `sfx` mapping.
- **Pop / click / whoosh / ding** — basic SFX. → Built-in synthesised set.
- **Riser** — rising build-up before a reveal. → Filtered noise sweep up.
- **Hit / impact / boom** — punch on a reveal. → Low thump.
- **Sting** — short musical accent. → Short chord/ding.
- **Music bed** — background music. → User track or generated (licence-checked); keep under voice.
- **Ducking** — music dips while someone talks. → Sidechain volume under speech.
- **Room tone** — quiet background sound to hide cuts. → Fill gaps at low level.
- **Beat sync** — cuts on music beats. → Beat detection, snap cut points.

## Colour & look
- **Colour grade / filter / LUT** — overall colour look. → Pack `grade` (.cube file).
- **Warm / cool** — more orange / more blue. → White-balance shift.
- **Film / vintage** — faded blacks, grain, warm. → Lifted blacks + grain + warm.
- **Matte** — soft, low-contrast. → Lifted blacks, reduced contrast.
- **Clean / bright** — crisp, true colour. → Exposure + slight contrast + saturation.
- **Grain** — film texture. → Subtle noise overlay.
- **Vignette** — darker edges. → Radial darken.
- **Exposure / contrast / saturation** — brightness / punch / colour strength. → Grade params.

## Framing & format
- **9:16** — vertical reel format (1080×1920). → Default canvas.
- **Safe zone** — area not covered by app UI. → `layout.SAFE_BOX`.
- **Reframe / crop** — move the frame to keep the subject in shot. → Face-tracked crop.
- **Ken Burns** — slow zoom/pan on a still photo. → Scale + move over time.
- **Pacing** — rhythm of changes. → Beat duration; tighter for lists, slower for emotion.
- **Cover / thumbnail** — grid image. → Best frame + hook text in main font.
