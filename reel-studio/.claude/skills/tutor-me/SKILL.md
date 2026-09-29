---
name: tutor-me
description: Explain WHY a reel/post worked so the user can make their own original version — never a copy. Use when the user pastes a reel/TikTok/post link and asks "why did this go viral", "what makes this good", "teach me", "break this down", or "tutor me".
---

# Tutor me — learn from a great reel, then make your own

Integrity rule: we reverse-engineer the *principles*, never the content. No copying scripts,
footage, audio or on-screen text. The output is a lesson + an original idea in the user's voice.

1. Get it cheaply: `python -m engine inspire <url>` (pacing, cuts/min, colour, contact sheet).
   Transcript: yt-dlp captions, or the local transcription used by the `watch` skill.
   Look at the contact sheet once (1 image).
2. Teach in plain words, 5 short sections:
   - **Hook (0–3 s):** what they said/showed and which psychology it uses (curiosity gap, pattern
     interrupt, bold claim, relatable pain, "POV", visual contrast…).
   - **Retention:** how they kept people watching (open loop, list countdown, fast cuts, text
     changes every ~2 s, payoff delayed to the end, reveal).
   - **Visual style:** framing, text style, captions, colour, pace (numbers from `inspire`).
   - **Emotion + value:** what the viewer gets (laugh, learn, feel seen, save-worthy).
   - **CTA:** what action they asked for and why it works.
3. **Your version:** 3 original hook ideas for THEIR niche in THEIR voice (read brand/voice.md),
   plus which Reel Studio template/recipe fits (`python -m engine templates`).
4. Offer: "Want me to save this lesson?" → append a 5-line summary to brand/voice/lessons.md.
