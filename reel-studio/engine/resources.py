"""Free places to get more: effects ideas, sounds, music, b-roll, photos, filters, GIFs and animations.

Shown in the Studio (Free resources tab). Each entry says what it's good for and the one licence
rule that matters. Two kinds:
  "yours"  — free for the user to download and use in their own reels (drop files in the inbox).
             Their licences do NOT allow us to bundle or bulk-download them into Reel Studio.
  "open"   — CC0 / public domain or open licence: fine to bundle (some are already in Reel Studio).
Checked October 2026 — licences change; the link is always the source of truth.
"""

RESOURCES = [
    ("Effects & design ideas", [
        ("HyperFrames", "https://www.hyperframes.dev", "open",
         "Hundreds of animated effects and 13 brand designs (many already built in). Pick a design, change its colours, download its FRAME.md and add it under Brands → From a design file."),
        ("HyperFrames on GitHub", "https://github.com/heygen-com/hyperframes", "open",
         "The open-source home of HyperFrames (Apache-2.0)."),
        ("LottieFiles", "https://lottiefiles.com/free-animations", "yours",
         "Free animated icons and stickers. Fine to use in your reels; not allowed: collecting them into another library."),
    ]),
    ("Sound effects", [
        ("Freesound (filter: Creative Commons 0)", "https://freesound.org/search/?f=license:%22Creative+Commons+0%22", "open",
         "700,000+ sounds; about half are CC0 (free for anything, no credit). Tick the Creative Commons 0 filter."),
        ("Pixabay sound effects", "https://pixabay.com/sound-effects/", "yours",
         "Huge free library, no credit needed. Download what you like into inbox/sound-effects. Bulk downloading isn't allowed."),
        ("Mixkit sound effects", "https://mixkit.co/free-sound-effects/", "yours",
         "Clean, well-made free effects (clicks, whooshes, pops). For your own videos."),
        ("Kenney audio packs", "https://kenney.nl/assets/category:Audio", "open",
         "CC0 interface and impact sounds (some already built in)."),
        ("Sonniss GDC bundles", "https://gdc.sonniss.com/", "yours",
         "Many gigabytes of pro sound effects, free each year. Use in your productions; not allowed: sharing them as a library."),
    ]),
    ("Music", [
        ("Pixabay music", "https://pixabay.com/music/", "yours", "Free music, no credit needed for most tracks."),
        ("Mixkit music", "https://mixkit.co/free-stock-music/", "yours", "Free tracks for your videos."),
        ("YouTube Audio Library", "https://www.youtube.com/audiolibrary", "yours",
         "Free music from YouTube (check each track's credit rule)."),
        ("Free Music Archive", "https://freemusicarchive.org/", "yours", "Creative Commons music; check each track's licence."),
    ]),
    ("B-roll video", [
        ("Pexels videos", "https://www.pexels.com/videos/", "yours", "Free vertical and landscape clips, no credit needed."),
        ("Pixabay videos", "https://pixabay.com/videos/", "yours", "Free clips, many vertical."),
        ("Mixkit stock video", "https://mixkit.co/free-stock-video/", "yours", "Polished free clips."),
        ("Coverr", "https://coverr.co/", "yours", "Free lifestyle and business clips."),
    ]),
    ("Photos", [
        ("Unsplash", "https://unsplash.com/", "yours", "Beautiful free photos. Not allowed: building a competing photo library."),
        ("Pexels photos", "https://www.pexels.com/", "yours", "Free photos, no credit needed."),
        ("Pixabay images", "https://pixabay.com/images/", "yours", "Free photos and illustrations."),
    ]),
    ("Filters (LUTs)", [
        ("FreeVisuals LUTs", "https://www.freevisuals.net/free-luts", "yours",
         "Free .cube cinematic filters, personal and commercial use. Upload the .cube files under Looks → Your own filters."),
        ("Editor Hub LUTs", "https://editor-hub.com/assets/luts", "yours", "50 free .cube filters with live previews."),
        ("Free For Video LUTs", "https://freeforvideo.com/200-free-cinematic-luts", "yours", "200+ free cinematic .cube filters."),
    ]),
    ("GIFs", [
        ("GIPHY", "https://giphy.com/", "yours", "Find GIFs and stickers. Download as MP4/GIF and drop into your inbox."),
        ("GIPHY GIF Maker", "https://giphy.com/create/gifmaker", "yours", "Turn your own clip or photos into a GIF or sticker."),
        ("ezgif", "https://ezgif.com/", "yours", "Free online GIF maker: video to GIF, crop, resize, remove background."),
    ]),
]

KINDS = {"yours": "Free for your reels", "open": "Open licence"}


def all_resources():
    return [{"group": g, "items": [{"name": n, "url": u, "kind": k, "kind_label": KINDS[k], "about": a}
                                    for n, u, k, a in items]} for g, items in RESOURCES]
