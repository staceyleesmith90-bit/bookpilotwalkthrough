# Competitor engine study (feature level only)

Studied a purchased copy of a competing product (proprietary licence: personal use; no resale or
redistribution of it or any part). Notes below are OUR summary of its features and approach — no code,
prompts, text, presets or assets were copied. Everything we add is written from scratch. Open-source
parts it builds on are used from their ORIGINAL upstream sources under their own licences.

## How it is put together
- Her workflow layer (playbooks + scripts) on top of open-source tools:
  - **HyperFrames** (HeyGen, Apache-2.0, github.com/heygen-com/hyperframes): HTML → video toolkit with
    ~26 authoring playbooks and a catalog of ~386 ready effects (captions, VFX, transitions, social,
    data, overlays), rendered with `npx hyperframes`. This is where most of the "premium" graphics and
    caption looks come from.
  - pyJianYingDraft / VectCutAPI (Apache-2.0) for CapCut drafts (same family as our pycapcut).
  - talking-head-recut (MIT, notedit/vtake-skills), WhisperX for word timing, YuNet face model (MIT).
- Mac-first (Windows is a separate "conversion" path), installed via shell scripts + course videos.
- Her own reels use her personal CapCut favourite sounds; buyers get an empty folder + a small Pixabay
  set, or their own Epidemic Sound subscription.

## Her flow
Inbox → job → rough cut (transcribe, cut, clean, level) → ⏸ style plan → graphics plan (beat by beat)
→ ⏸ one approval → one build pass → finish (CapCut or baked video) → export + phone check.
Two separate questions: how LOADED (teaching = heavy graphics, confessional = bare) and how DONE
(raw = editable CapCut text · medium = rendered animated layers inside CapCut · well-done = baked MP4 ·
hands-off = fully automatic after the rough cut).

## What she has that we don't (gaps to close — our own versions)
1. **Effects catalog**: hundreds of ready, high-end captions/transitions/overlays via HyperFrames, used
   by name ("use Pill Karaoke captions"); animated full-screen "breakaway" cards.
2. **Cut precision**: word alignment, cut points snapped to the real start/end of the sound, double-take
   and restart removal, J-cut audio crossfades, a steady loudness chain that doesn't "pump".
3. **Doneness choice**: editable CapCut text vs animated layers in CapCut vs baked video vs hands-off.
4. **CapCut finishing**: native Auto Captions recipe; text set in CapCut's own fonts by name; a new
   draft version per change (never overwrite a draft the user opened; CapCut closed while writing);
   "your turn" — read the user's hand-trimmed CapCut cut back in and rebuild on it; choose which
   element kinds get their own tracks.
5. **Placement measured, not guessed**: the speaker's head-to-chin box across the whole take → open
   zones; fixed platform-safe bands (top/bottom) checked for every placement; optional "chin lock".
6. **Fast revisions**: graphics rendered part by part and re-composited in seconds instead of a full
   re-render.
7. **Learning**: preferences the user teaches are stored and applied by the builders, with list/forget.
8. **Reusable recipe**: turn a finished reel into one paste-ready prompt.
9. **More formats**: pull many short clips from one long video; voiceover/faceless reels on b-roll.
10. **Effects library page** with live previews and copyable phrases; cover picker using face detection.
11. **Sound**: use the user's OWN CapCut favourites (read locally) or their own Epidemic Sound account.
12. **Usage thrift**: rich interactive review only the first time; lean table on re-cuts.

## Where we are already ahead
One-click Claude extension (no install scripts), Windows = Mac, Codex support, monthly licence model,
real recorded CC0 sound library bundled, measured noise check + neural voice cleaner, auto director
(stabilise, face-framed punch-ins), phone/computer review page with voice notes, CapCut project export,
brand end screen, inspiration links without paid keys.

## Build plan (priority)
- P1 quality you can see: HyperFrames effects + captions (used from upstream, Apache-2.0); animated
  breakaway cards; doneness choice incl. animated layers in CapCut; part-by-part fast revisions.
- P2 cut quality: word alignment, snap-to-sound cuts, restart removal, J-cuts, steady loudness;
  measured open zones + safe bands.
- P3 stickiness: learn preferences, CapCut round trip, reusable recipe, effects library page,
  use-my-CapCut-favourites sounds, pull-reels, voiceover reels.
