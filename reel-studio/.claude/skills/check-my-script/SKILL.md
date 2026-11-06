---
name: check-my-script
description: "Script Kit. Use for 'check my script', 'grade my script', 'score this script', 'fix my script', or 'tighten this script'. Reviews a reel script against the 12-check scorecard, names what's already working and three optimizations to consider, offers one line to try, and makes the changes or trims it to a length when asked. Never shows a score."
---

# Check my script

First read `.claude/skills/script-kit-library/house-rules.md` and follow it the whole way through.

## 1. Find the script

- If they pasted a script, use it. If it isn't in a script file yet, save it as a new file in
  `script-desk/scripts/` (the film-ready template, their words under "Script") and say so in one line.
- If they named a file, use that file.
- Otherwise use the most recently changed file in `script-desk/scripts/` that has real lines under "Script", not
  the template's `[line one]` placeholders. Name it
  in your first line.
- If there's nothing to grade, ask them to paste the script, in one line, and stop.

## 2. Read what you need

- `.claude/skills/script-kit-library/scorecard.md`: the 12 checks and exactly how to report them (no score, no pass or fail)
- `.claude/skills/script-kit-library/method.md`: jobs, registers, hook layers, beats, retention, the ask
- `.claude/skills/script-kit-library/levers.md`
- `script-desk/voice-dna.md` for check 10. If it doesn't exist, judge the voice against `brand-kit.md` and add
  one line: "Run `build my voice DNA` and this check gets sharper."
- `script-desk/about-me.md` for who it's for (checks 2 and 11), if it exists.
- If the file has no Job line, work out the job from the script and say which one you assumed.

## 3. Grade it

First, look for any first-person story or detail you can't find on their desk or in the script file's Idea line
(see "True stories only" in the house rules). If this reel's line in `script-desk/ideas.md` still says
"(suggested)", its story isn't confirmed yet, whatever the Idea line says. If there is one, put one line at the top: 'Is this yours? "[the line]" It has to be true before you
film it.' It's a question, not a mark against the script.

Follow the reporting format in `scorecard.md` exactly: what's already working (quote their lines), three
optimizations to consider with the new line for each, and one line to try. The tone is a collaborator's: this
is good work, and here's how to take it further. Judge a confessional by the confessional contract: no lesson and
no hopeful turn is the contract kept, never something to change.

## 4. Save

Write the result into the script file's `## Check notes` section (a file from before calls it `## Score`: rename
it), replacing any older notes: today's date, what's working, the three optimizations, and the line to try. Don't
change the script itself yet.

## 5. Next

End with one line: "Want me to make these changes?" If they say yes, make them in the script file and keep
every other word of the script exactly as it was. Then refresh the Beats table and the Length line to match, and
say in one line what the changes added.

**"Fix it", "fix my script" or "tighten this script":** review it, then make the three optimizations right away
and say what they added. **"Trim it to [N] seconds":** cut to fit at about two and a half words a second, keeping the hook, the
payoff and the ask, then refresh the Beats and Length. Cut whole lines, not the words that sound like them.
