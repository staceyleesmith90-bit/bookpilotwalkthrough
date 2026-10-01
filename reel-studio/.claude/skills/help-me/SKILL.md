---
name: help-me
description: Answer "how do I…" questions about Reel Studio with short, exact steps, and handle "set me up" and "update me". Use when the user asks how to do something in Reel Studio, is stuck, says "set me up", "update me", or "what can you do".
---

# Help

- **"set me up"** → `python -m engine setup-check` (fix anything missing) → brand-onboarding →
  voice-hub (optional) → offer the Studio. Keep each step one short message.
- **"update me"** → `python -m engine update` (keeps their brand, projects and inbox), then setup-check.
- **"how do I …"** → answer in ≤ 5 numbered steps using the Studio buttons first (Home ·
  Templates · Looks · Trending sounds · My brand · Edit), then the chat alternative. Examples:
  move/delete a sticker (Edit → click it → drag / Delete) · change font (My brand → Fonts) ·
  add a trending sound (Trending sounds tab) · change filter (Looks → Filters) · add my logo
  (My brand, or drop it in the chat) · batch reels (`broll-batch`).
- **"something's not working"** → fix it yourself first (read the error, setup-check, re-run). Still
  stuck → `python -m engine report` writes `out/problem-report.txt` (no footage, no keys, no brand);
  they add one line about what happened and email it to Systems Pilot support.
- **"show me the effects library"** → `python -m engine library`.
- **"what can you do"** → 6 bullets max, then "What are we making today?"
- Never answer "why didn't it zoom/…?" with an excuse: fix it (edit the timeline), re-render,
  and say what changed.
