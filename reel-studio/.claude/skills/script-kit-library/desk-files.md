# Desk file formats

Every skill reads and writes these exact shapes, so one skill can always read what another wrote. Headings are
fixed. Keep them even when a section is empty.

## script-desk/about-me.md

```markdown
# About me

## Where I am
[just starting / growing / selling] · [one line: how many reels so far, and anything already working]

## What kind of account
[teaches / sells a product / creator] · [one line: what I teach, sell or share]

## Who it's for
[one line: the person, their situation, and what they want. Never a demographic label on its own]
Also watching: [only for a product seller whose reels also draw other makers or shop owners. Otherwise leave this line out]

## Their moments
- [a time, a room or a place] · [the thought they have right then, in their words]
- [a time, a room or a place] (mine) · [a moment that happened to the buyer, in their words]

## Their words
- "[a phrase they actually say or type, word for word: a comment, a DM, a question, a search]"

## My topics
- [three to five topics, each small enough for one reel]

## What I offer
- Offer: [what my reels lead to] · Keyword: [KEYWORD, or "none yet"]
- Until then: [the next step I want from a viewer when there's no offer yet: follow, save, send, come back]

## My proof
- [a real number or result, a credential, a true story, or what I've tried. Only things I'd say out loud]

## My person
[the full one-person profile, added in the lesson "Your person". Empty until then.]
```

- Their moments are their person's moments, written as the person's ("she", "you" or "moms at..."), unless the
  buyer said a moment is their own. Then add "(mine)" after the place, so every skill knows it's theirs to tell in
  first person.
- A moment with no thought they remember is saved without one. Never write the thought for them.
- "Who it's for" follows "What kind of account" (see "Who the reel is for" in `method.md`): the person they help,
  the customer who buys their product, or the follower a creator is building. For a product seller it's always the
  customer. Other makers who watch go on the "Also watching" line, and reels aren't written to them.
- A desk made before this field existed has no "What kind of account". Read it from the offer and the brand kit,
  and ask once only if it's still unclear.
- One "Offer" line per offer, main offer first, each with its own keyword. No offer yet: one line,
  "Offer: none yet · Keyword: none yet", plus the "Until then" line.
- A field they skipped says "not yet". Other skills work with what's there and never invent the rest.
- "Where I am" tells every skill how to plan: someone just starting gets reach and grow reels first, and asks
  that don't need an offer (see "Just starting out" in `method.md`).

## script-desk/my-reels.md

```markdown
# My reels

Updated: YYYY-MM-DD · Source: Apify / transcribed videos / pasted / interview · Shares: in my plan / not in my plan / typed in / not given

## Medians
- Short reels (under 15 seconds): [median plays, or "not enough reels yet"]
- Talking reels (15 seconds and up): [median plays, or "not enough reels yet"]

## The reels
| # | Date | Link | Format | Length | Plays | Likes | Comments | Shares | Job | Outlier | What it is |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | YYYY-MM-DD | [link or file name] | short / talking | 0:07 | 12,345 | 456 | 78 | 90 | reach / grow / convert / ? | 2.1x | [one line] |

## My other posts
| # | Date | Link | Type | Likes | Comments | What it is |
|---|---|---|---|---|---|---|
| P1 | YYYY-MM-DD | [link] | carousel / photo / other | 456 | 78 | [one line] |

## Transcripts
### 1 · [one-line summary]
Said: [the spoken words, word for word]
On screen: [any text on screen]
Caption: [the caption]

### P1 · [one-line summary]
[the caption, word for word]

## In my own words
### [the interview question]
[their answer, word for word]
```

- Format: short = under 15 seconds, talking = 15 seconds and up.
- Outlier = plays divided by the median for that format, one decimal, with an x. A format with fewer than three
  reels has no median yet, so its outliers stay blank.
- Date: YYYY-MM-DD when known. Only a month given: YYYY-MM, using the most recent one that has already passed,
  and say so in one line. A day and month with no year: the most recent year that puts it in the past, said in
  one line. Skipped: blank. Newest first, undated rows last.
- Transcripts: label each part you have (Said, On screen, Caption) and leave out the labels you don't. Said is
  how they talk. Captions and on-screen lines are how they write.
- Shares: the number when known. "n/a" when Apify can't get them on their plan. Blank when they skipped it.
  Never guess.
- Job stays "?" until `what's working for me` tags it.
- "What it is" is one plain line on what the reel says or shows. No pronouns, no judgment.
- The same reel never goes in twice. Match on the link, the file name for a video, or the date and first line
  for a pasted reel.
- Other posts have no plays, so they never count toward the medians. Their captions are written words: good
  evidence for how someone writes, weaker evidence for how they talk.
- Sections with nothing in them keep their heading and stay empty.

## script-desk/reels-i-like.md

Reels the buyer loves from other creators. Only the shape is saved here, never their words.

```markdown
# Reels I like

Updated: YYYY-MM-DD

## The reels
| # | Link | Creator | Format | Job | Hook pattern | Shape | What I love about it |
|---|---|---|---|---|---|---|---|
| 1 | [link] | [@handle] | talking / b-roll / on-screen text | reach / grow / convert | [a Hook Library pattern name] | [story / list / ...] | [the buyer's words] |

## What I'm drawn to
- [a pattern that shows up in more than one: a format, a hook pattern, a register, a length]
```

- "Hook pattern" names the closest Hook Library pattern. "Shape" uses the shapes in `method.md`.
- No quotes, captions or transcripts from these reels. No keywords or numbers of theirs, except the plays when
  known, which may go in "What I love about it".
- Format here is what the reel is (someone talking, b-roll, text on screen), not its length.
- "What I love about it" is in the buyer's words. If those words quote the reel, keep the love and cut the quote.
- A hook pattern guessed without the reel's first line says so: "(best guess)".

## script-desk/voice-dna.md

Use the template in `templates/voice-dna-template.md`.

## script-desk/ideas.md

```markdown
# Ideas

- [reach] [the idea in one line] · from: [where it came from] · YYYY-MM-DD
- [grow] ...
- [convert] ...
```

Newest at the bottom. When an idea gets a script file, add ` · script: script-desk/scripts/[file].md` to its line.
Common "from" values: their own, interview, break this down, tutor me, what's working, plan my week, hook sprint.

When Claude came up with the idea, add "(suggested)" after the from value: `from: what's working (suggested)`.
Write it as a moment or a topic, never as a story that happened to them. Whether it happened is theirs to say.
When they tell you what really happened, rewrite the line in their words and drop "(suggested)".

## script-desk/scripts/[date]-[short-title].md

Use the template in `templates/film-ready-script-template.md`.

## script-desk/week-plan.md

Use the template in `templates/week-plan-template.md`. "Week of" is the coming Monday. It is replaced each week. Before replacing it, copy any reel that
got filmed into its script file's "After posting" section if it's not there yet.
