---
name: trending-sounds
description: Suggest trending TikTok/Instagram sounds for a reel and prepare a version to add them to. Use when the user asks about trending sounds/songs/audio, "what's trending", "which song should I use", or wants to post with a popular sound.
---

# Trending sounds

**Honest setup:** TikTok has no public trending-sounds API and its songs are licensed for use
*inside* TikTok. Reel Studio never scrapes or downloads them. We **suggest**; the user adds the
sound in the app. Say this in one friendly sentence if they ask why.

## What to do
1. **Find what's trending** (only when asked, or once a week if they post often — keep it lean):
   - Send them to TikTok's own list (`python -m engine sounds` prints the Creative Center link;
     the Studio has an "Open TikTok's trending sounds" button). Business accounts: use the
     "Approved for business use" filter / Commercial Music Library.
   - Or, if you have web search, look for this week's public "trending TikTok sounds" round-ups
     (one search, not ten) and pick 3–5 that fit their brand's vibe.
2. **Save them** with moods so matching works:
   `python -m engine sounds-add "Song — Artist" --mood cosy,dreamy --tempo slow [--business] [--link URL]`
   (or the Studio → Trending sounds tab). Sounds older than 3 weeks drop off automatically.
3. **Suggest for a reel:** `python -m engine sounds-suggest <project> [--business]` ranks saved
   sounds by the reel's mood/tempo. Explain the pick in plain words ("playful, matches your
   upbeat tips").
4. **Render** as normal. Every final render also writes
   `renders/final-for-trending-sound.mp4`: voice + sound effects, **no background music**, so
   the trending sound doesn't clash. Tell them to post that file, then follow the steps
   printed by `sounds-suggest` (add sound → volume: added ~20%, original 100%).

## Rules
- Business/brand accounts: only suggest sounds marked business-safe; warn once that
  non-approved songs can get muted or removed on business accounts.
- Trends are about timing: a sound that's 3+ weeks old is usually past its peak.
- Never promise a sound "will go viral"; say it's popular right now.
