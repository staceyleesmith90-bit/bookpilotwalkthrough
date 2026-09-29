"""Trending sounds assistant (TikTok / Instagram).

TikTok doesn't offer a public API for trending sounds, and trending songs can't be downloaded
into a reel — they're licensed to be used *inside* TikTok. So Reel Studio does the legal thing:
  1. keeps a short list of trending sounds (brand/trending-sounds.json) — added by the user from
     TikTok's Creative Center, or by Claude from public "trending sounds this week" articles;
  2. suggests the best match for each reel (mood, tempo, business-safe);
  3. exports a version of the reel WITHOUT background music, so the user adds the sound in the
     TikTok/Instagram app (their voice and sound effects stay in).

    python -m engine sounds                 list + where to find trending sounds
    python -m engine sounds-add "Title — Artist" [--mood cosy,calm] [--business]
    python -m engine sounds-suggest <project>
"""
import json, os, re, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "brand", "trending-sounds.json")

# TikTok's official, public pages (open in the user's own browser)
CREATIVE_CENTER = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en"
COMMERCIAL_LIBRARY = "https://ads.tiktok.com/business/creativecenter/music/pc/en"

HOW_TO = {
    "tiktok": ["Open TikTok → ＋ → Upload → pick your exported reel (the 'for-trending-sound' version).",
               "Tap 'Add sound' (or 'Sounds') → search the song name → select it.",
               "Tap 'Volume': set 'Added sound' to about 15–25% and 'Original sound' to 100% so your voice stays clear.",
               "Business account? Only sounds marked 'Approved for business use' (Commercial Music Library) are allowed."],
    "instagram": ["Open Instagram → ＋ → Reel → pick your exported reel.",
                  "Tap the music note → search the song → choose the part you want.",
                  "Tap 'Mix audio': music ~20%, camera audio 100%.",
                  "Business/creator accounts sometimes only see royalty-free tracks — that's Instagram's licensing, not a bug."],
}

MOOD_WORDS = ["cosy", "dreamy", "uplifting", "confident", "calm", "playful", "romantic", "nostalgic",
              "motivational", "chic", "mysterious", "sunny", "emotional", "energetic", "funny", "sad", "hype"]


def load():
    return json.load(open(FILE)) if os.path.exists(FILE) else []


def save(items):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    json.dump(items, open(FILE, "w"), indent=1)


def add(text, mood=None, tempo=None, business=False, link=None, source="user"):
    """text like 'Espresso — Sabrina Carpenter' or 'original sound - @creator'."""
    parts = re.split(r"\s+[—–-]\s+", text.strip(), maxsplit=1)
    title, artist = parts[0], (parts[1] if len(parts) > 1 else "")
    items = [i for i in load() if i["title"].lower() != title.lower()]
    items.insert(0, {"title": title, "artist": artist, "link": link, "mood": mood or [], "tempo": tempo,
                     "business_ok": bool(business), "added": time.strftime("%Y-%m-%d"), "source": source})
    save(items[:60])
    return items[0]


def fresh(items, days=21):
    """Trends fade fast: keep only sounds added in the last few weeks."""
    cutoff = time.time() - days * 86400
    out = []
    for i in items:
        try:
            if time.mktime(time.strptime(i["added"], "%Y-%m-%d")) >= cutoff:
                out.append(i)
        except (KeyError, ValueError):
            pass
    return out


def suggest(brief, business=False, n=3):
    """Rank saved trending sounds for a reel brief (mood/tempo match, business-safe first)."""
    want = set((brief.get("mood") or []) + (brief.get("vibe") or []))
    tempo = brief.get("tempo")
    scored = []
    for i in fresh(load()):
        if business and not i.get("business_ok"):
            continue
        s = 2 * len(want & set(i.get("mood") or []))
        s += 1 if tempo and i.get("tempo") == tempo else 0
        s += 0.5 if i.get("business_ok") else 0
        scored.append((s, i))
    scored.sort(key=lambda x: -x[0])
    return [i for _, i in scored[:n]]


def summary():
    items = fresh(load())
    lines = [f"{len(items)} trending sounds saved (last 3 weeks)."]
    for i in items[:15]:
        tag = " ✅ business-safe" if i.get("business_ok") else ""
        mood = f" · {', '.join(i['mood'])}" if i.get("mood") else ""
        lines.append(f"• {i['title']}{' — ' + i['artist'] if i.get('artist') else ''}{mood}{tag}")
    lines.append(f"Find more: {CREATIVE_CENTER}")
    lines.append(f"Business-safe library: {COMMERCIAL_LIBRARY}")
    return "\n".join(lines)
