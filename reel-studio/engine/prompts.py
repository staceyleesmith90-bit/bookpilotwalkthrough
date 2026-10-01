"""The prompt library — every useful thing to say, ready to tap or copy, sorted by the moment you need it.

Nobody should have to learn how to prompt. The Studio shows these as cards with a Copy button; Claude
also offers them as tap answers. Placeholders in [brackets] are the only part to change.
Written for Reel Studio (our own words).
"""

LIBRARY = [
    ("Start a reel", "🎬", [
        ("Edit my newest video", "Edit the newest video in my inbox."),
        ("Just tidy it up", "Edit my newest video, but keep it simple: cut the pauses, add captions, nothing extra."),
        ("Add b-roll for me", "Edit my newest video and use the clips in my inbox as b-roll where they fit what I'm saying."),
        ("Full designed reel", "Make my newest video a fully designed reel: b-roll, graphics and effects where they help."),
        ("Voiceover reel", "Make a voiceover reel: my voice recording is in the inbox, use my clips folder for the visuals."),
        ("Text-only reel", "Make a text-only reel from these lines, no camera: [paste your lines]"),
        ("A batch from my clips", "Turn the clips in my inbox into as many short reels as make sense, each with a hook."),
        ("Do it all for me", "Edit my newest video hands-off. Decide everything yourself and show me the finished reel."),
    ]),
    ("Before I film", "📱", [
        ("Make me one like this", "I love this reel: [paste link]. Tell me exactly what to film so I can make my own version."),
        ("Shot list", "I want to make a reel about [topic]. Give me a shot list: one talking clip and the b-roll shots, a line each."),
        ("Write my script", "Write me a 30-second script about [topic] that sounds like me. Strong hook first."),
        ("Ten hook ideas", "Give me 10 hooks for a reel about [topic], in my voice. Number them so I can pick."),
        ("What should I post?", "Give me 5 reel ideas for this week for my brand, with a hook for each."),
    ]),
    ("Brands", "🏷️", [
        ("Which brand am I on?", "Which brand am I using right now? Show me all my brands."),
        ("Add a new brand", "Set up a new brand called [name]. Walk me through it with choices."),
        ("Switch brand", "Switch to my [name] brand."),
        ("Look from my video", "I don't have a brand yet. Make three looks from the colours in my video."),
        ("Use a ready-made design", "Show me the ready-made designs and help me pick one for [brand]."),
        ("My Canva design", "I styled my brand in Canva. Read it and make it my look."),
        ("Change my colours", "Make my accent colour [colour] and keep everything else."),
        ("Change my fonts", "Use [font name] for my headlines."),
    ]),
    ("It doesn't look like me", "🎨", [
        ("Too busy", "This feels too busy. Keep only the one or two best moments and make the rest clean."),
        ("Too plain", "This feels too plain. Add a few moments that make people stop: a takeover, a pop-up or a sticker."),
        ("Calmer", "Make the whole reel calmer: softer text, fewer effects, gentler sounds."),
        ("More energy", "Give this more energy: faster cuts, bolder text, punchier sounds."),
        ("More premium", "Make this look more premium and expensive."),
        ("Match this reel", "Make it feel like this reel I love: [paste link]. Keep my brand and my words."),
        ("Different filter", "Try a warmer filter on the whole video."),
        ("Black and white b-roll", "Make all the b-roll black and white."),
    ]),
    ("Text and captions", "🔤", [
        ("Bigger hook", "Make the hook at the start bigger and keep it on screen a bit longer."),
        ("It's on my face", "The text is covering my face. Move it to a clear spot."),
        ("Different caption style", "Show me three other caption styles on my video and let me pick."),
        ("Highlight key words", "Highlight the key words in my captions in my accent colour."),
        ("No captions", "Leave the captions out of this one."),
        ("Fix a word", "In the captions, change '[wrong]' to '[right]'."),
        ("Change a line", "Change the text '[old text]' to '[new text]'."),
    ]),
    ("The cut", "✂️", [
        ("Tighter", "Cut it tighter: shorter pauses and no repeated words."),
        ("Room to breathe", "It's cut too tight. Give my sentences a little room to breathe."),
        ("Remove a line", "Remove the line where I say '[words]'."),
        ("Shorter reel", "Get this under [30] seconds without losing the point."),
        ("Better hook", "Start with my strongest line instead."),
        ("Rewrite a line", "Line [number] is weak. Give me two better versions in my voice."),
    ]),
    ("Sounds and music", "🔊", [
        ("Fewer sounds", "There are too many sound effects. Keep only the ones that match something on screen."),
        ("Match the motion", "Make every sound match what's moving: typing for typed text, a whoosh only when something moves."),
        ("Use my CapCut sounds", "Learn my sounds from my CapCut project called [my favorites]."),
        ("Use my downloaded sounds", "Use the sound effects in my inbox."),
        ("Music options", "Give me three background music options that fit this reel."),
        ("For a trending sound", "Make a version without music so I can add a trending sound in TikTok."),
        ("Louder voice", "My voice is too quiet against the music. Fix the balance."),
    ]),
    ("Effects", "✨", [
        ("Show me effects", "Show me the effects library."),
        ("Count-up number", "When I say [number], show it counting up."),
        ("Follow card at the end", "End with an animated follow card with my handle."),
        ("Full-screen moment", "Make the line '[words]' a full-screen moment."),
        ("Product pop-up", "When I mention the product, pop up a picture of it."),
        ("Premium captions", "Use the Highlight captions from the premium styles."),
    ]),
    ("Teach it once", "🧠", [
        ("Remember that", "Remember that. Do it this way in every reel from now on."),
        ("Never again", "Never do [this] again in my reels."),
        ("Show my rules", "Show me everything you've learned about my style."),
        ("Forget a rule", "Forget the rule about [topic]."),
        ("Save an effect", "Save that as my [name] effect so I can ask for it by name."),
        ("Learn my voice", "Learn how I talk from my last reels: [profile link]."),
    ]),
    ("Finish", "✅", [
        ("Looks great", "This looks great. Give me the finished video."),
        ("Let me move things", "Open the editor so I can move things myself."),
        ("CapCut version", "Give me a CapCut version I can tweak."),
        ("Write my caption", "Write the post caption and hashtags for this reel."),
        ("Pick a cover", "Pick the best cover frame and put my hook on it."),
    ]),
    ("Help", "🛟", [
        ("What can you do?", "What can you do? Show me with buttons."),
        ("Something's wrong", "Something isn't working: [what happened]. Fix it."),
        ("Update", "Check for an update."),
    ]),
]


def all_prompts():
    return [{"group": g, "icon": ic, "items": [{"title": t, "say": s} for t, s in items]} for g, ic, items in LIBRARY]


def count():
    return sum(len(items) for _, _, items in LIBRARY)
