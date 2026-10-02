# Pushback patterns

Read this when the request is solution-first, or when the user's preferred option differs
from your recommendation. Pushback is a service, not a contest: say it once, clearly, with the
evidence and the cost, then respect the decision and record it.

## Shape of a good pushback

1. Name what you heard: "You want F."
2. Name the gap: "The evidence shows G" or "Nothing shows the problem F solves yet."
3. Offer the cheaper move with its cost: "H would take a day instead of two weeks and tells us
   whether F is needed."
4. Recommend and ask once: "I recommend H. Go with H, or proceed with F?"

In `--auto` the same reasoning goes into the Decision paragraph and `## Decisions (auto)`;
nobody is asked.

## Patterns

| Signal in the request | Pushback | Usual cheaper framing |
| --- | --- | --- |
| A fix arrives with the bug report ("users get logged out, extend the session to 30 days") | Separate the observation (logouts) from the fix (longer session). Ask what evidence ties them. | Find why sessions end early; the expiry may be fine |
| One anecdote ("a customer asked for CSV export") | How many asked? What did they do with the data? | Shrink: one fixed report, or reuse an existing export |
| "Everyone needs X" | Who exactly, how often, and what do they do today instead? | Shrink to the one segment with evidence |
| Building generic infrastructure for one case ("a rules engine for discounts") | One rule exists today. What is the second, and when? | Hard-code the one rule behind a function; revisit at the second |
| A capability a SOFTURE module covers (roles, mail, feature switches) | WORKFLOW §10: module first | Reuse, and file the gap upstream if it almost fits |
| Scope grew during research ("while we're there…") | Which part delivers the Intent in change.md? | Shrink to that part; the rest goes to the backlog |
| "Make it faster" with no number | Faster from what to what, measured where? | Measure first; frame again with the number |
| A deadline drives a big build | What is the minimum that meets the date? | Shrink, with the rest explicitly deferred |
| The PRD already decided it | Do not reopen it | Only if research contradicts a named PRD line |

## When to stop pushing

- The user brings a fact you did not have: re-test the hypothesis it touches, then update the
  recommendation honestly, even if it flips.
- The user decides against your recommendation: record their choice and your recommendation
  side by side in the Decision paragraph, and move on. One round, not a negotiation.
- The cheaper option fails the Intent in change.md: it is not an option. Drop it from the table.
