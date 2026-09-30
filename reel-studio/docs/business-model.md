# Making Reel Studio a monthly subscription

## The problem
Anything installed on a buyer's computer can be copied. Claude Code has no built-in way to
charge a monthly fee for someone's skills, so a pure "download and install" product ends up
one-off (like the competitor's $97), no matter what you call it.

## The fix: keep the valuable, always-fresh part on your side
Three models, from least to most control:

| Model | How it works | Monthly? | Costs you | Effort |
|---|---|---|---|---|
| 1. Licence key | Local app checks an active subscription key (Lemon Squeezy / Stripe) at start | Weak: Python source can be edited | ~0 | Low |
| **2. Hybrid "brain in the cloud"** (recommended) | Editing still runs on their computer; the brain lives on your server: templates, trend-sound feed, inspiration analysis, style library, sticker/sound/font packs, updates, review pages. Claude plugs in as a connector (remote MCP) they log into. Cancel → the brain switches off | Strong | Low (no video rendering on your server) | Medium |
| 3. Fully hosted web app | Upload in a browser (works on phones), your servers edit and render, Claude runs via your API account | Strongest | Server + Claude API per reel (plan cents per reel) | High |

## Recommended path
1. **Now – launch (model 2):** Reel Studio (local engine) + "Reel Studio Cloud" (your server):
   - Subscription + licence keys through **Lemon Squeezy** (handles global VAT/tax, subscriptions,
     licence-key API, cancellations) or Stripe.
   - The engine asks the cloud for: new templates and caption/sticker/sound packs (monthly drops),
     the weekly trending-sounds list, inspiration-link analysis, the branded review pages with
     feedback, and updates. Without an active subscription it still opens old projects, but gets
     nothing new — that's the reason to stay subscribed.
   - Claude connects to your cloud as a custom connector (remote MCP server with login), so
     "all of this knowledge" lives with you, not in the download.
2. **Later (model 3):** a hosted web version for people without a computer or Claude Code —
   higher price tier, because you pay for rendering and Claude usage per reel.

## Pricing ideas (vs the competitor's $97 once)
- Monthly: $19–29 · Yearly: $190–290 (two months free) · Founding members: lower price locked in.
- Include: monthly template + sticker/sound drops, trend-sound list, priority fixes, community
  or monthly live Q&A (her community is her real recurring income — copy the idea, not the product).

## What to build next for this
- A small cloud API: `/templates`, `/packs`, `/trends`, `/inspire`, `/review`, `/update`, auth by
  licence key; plus an MCP server wrapper so Claude can call it directly.
- A licence check in `setup-check` and a friendly "subscription ended" message.

## What the competitor actually does (seen on her checkout, Sept 2026)
- The engine: $97 one-off ($67 early), "lifetime" access, **Mac-first** (Windows "more hands-on").
- Straight after checkout, a one-click upsell: **"The Startup Moms Community" — $37/month**
  (normally $47, "yours stays $37 as long as you're a member"). Members get: every engine update
  first, "ask for it, I'll build it", a live hour each month, a walkthrough library, the community.
- So her real recurring income is the membership; the engine is the door opener.

## Our version (same proven shape, better product)
- **Reel Studio (one-off or first month)** + **Reel Studio Club (monthly)**: updates the moment
  they ship, new templates/sounds/effects each month, request-a-feature board, monthly live
  session, tutorials, community. Founding-member price locked while subscribed.
- Our edges to lead with: works on **Windows AND Mac**, works with **Claude AND ChatGPT Codex**,
  editable **CapCut export**, brand-agnostic (white-label for agencies), review page for clients.
- Keep the valuable, always-fresh parts (templates, sound packs, effects, trend lists, updates)
  flowing from the Club so the subscription keeps its value even though the engine runs locally.
