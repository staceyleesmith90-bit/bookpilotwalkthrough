---
name: brand-reels
description: Reels for brands where nobody has to talk — products and services — for social media managers running one or many client brands. Use when the user manages brands/clients, sells products or services, says "make a reel for my product/service/client", "product video", "promo", "sale post", "how it works", "testimonials", "FAQ reel", "add my products", or picks Brand reel in the Studio.
---

# Brand reels (products + services, no talking)

**Who it's for:** social media managers with several client brands, and small businesses — online shops,
salons, coaches, trades, studios. Most of their content has no talking head: the product or service is the star.

## 1. The right brand first
`python -m engine brands` → `brand-use "<client>"` (or `brand-new` + **brand-onboarding** for a new client:
logo, colours, fonts, voice). Everything below is per brand and moves with it when switching.

## 2. The catalogue (once per brand, then reuse forever)
`brand/catalog.json` — ask one thing at a time (tap answers), and fill it yourself:
- **What they sell:** products, services or both; one line about the business; their call to action
  ("Shop now · link in bio", "Book via WhatsApp", "DM 'BOOK'").
- **Products:** name, price (and old price on sale), 3 short benefits (≤ 4 words each: "25 km range"),
  a clean product photo (any background — Reelmate cuts it out), optional badge (NEW, SALE, BESTSELLER).
- **Services:** name, price, 3 steps (what happens, in the client's words), optional detail per step
  (time, what's included), a photo of the work; before + after photos when it's a results service.
- **Reviews:** real ones only, with first name + town; **FAQs:** the 3 questions customers really ask.
No product photo? Offer a `--style realistic` AI product shot (aielements) only as a mock-up, never as the
real product, or ask for 1 phone photo on a plain table near a window.
Overview: `python -m engine brand-reels`. Studio: Home → **Brand reel** (pick item + recipe, add items there).

## 3. Pick the recipe from the goal (say why in one line)
| Goal | Product | Service |
|---|---|---|
| New people (reach) | `reasons`, `new-drop` | `faq`, `results` |
| Trust | `reviews` | `reviews`, `how-it-works` |
| Sell now | `offer`, `showcase` | `how-it-works` + offer line, `results` |
`python -m engine brand-reel <recipe> --name "<item>" [--clips <folder of their footage>]` → plan.json.
Their own clips (product in use, the salon, packing orders) slot in between with labels — always ask for 2–3.

## 4. Make it theirs, then storyboard
Adjust the plan: hook line on the first beat, the brand's real words (voice.md), an AI element set for the
story (props, not the product), music feel. Then `timeline` + `storyboard` → Storyboard page → build.
Batch for managers: one brand, a week of reels = 5 recipes × their items (`content-week` for the plan).

## Never
- Invent prices, reviews, stats or claims. Missing → ask, or leave it out.
- Put AI-made pictures where the real product must be shown.
- Mix brands: check `python -m engine brands` before every new client reel.
