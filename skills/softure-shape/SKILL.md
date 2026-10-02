---
name: softure-shape
description: >
  Turn a raw idea, feedback dump or business goal into `context/foundation/shape-notes.md`:
  the problem, who has it, what they do today, the appetite, a rough solution sketch,
  rabbit holes, no-gos and open questions. Interviews one question at a time and pushes
  back on solution-first thinking. Use before writing a PRD, at the start of a product or
  of a new theme. Triggers: "shape this idea", "let's think this through", "I have an idea",
  "let's think it through before we start".
argument-hint: "[idea in one sentence | path to notes] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - WebSearch
---

# softure-shape: from a raw idea to a shaped problem

## Purpose

Most wasted work starts with a solution nobody checked against a problem. This skill
produces a short, opinionated document that a PRD can be written from. It records the
problem worth solving and the boundaries of the solution. It does **not** produce a spec.

## Inputs

- `context/workflow.json`. If missing, stop and point to `softure-init`.
- The idea: the argument, a file path, pasted notes or screenshots. With no idea at all, ask
  for one sentence and nothing else.
- Brownfield: if the repo has code, skim the README, the entry points and the existing
  `context/foundation/*.md`, so you know the current system before discussing changes.
  Summarise it in 5 to 10 lines; do not audit it.
- If `shape-notes.md` already exists, this is a **new session**. Keep the old content under
  `## Previous sessions` (collapsed to the key decisions), then shape the new theme above it.

## Interview technique

- **One question per message.** Each question comes with your recommended answer and why,
  so the user can just say "yes".
- Ask about the **problem before the solution**. If the user opens with a solution
  ("add a chat"), ask what happens today without it, how often it happens and what it costs.
  Do not drop the solution: park it under *Solution sketch* and come back to it.
- Use concrete examples: "last time this happened, what exactly did you do?"
- Stop when every section below can be written in your own words and the user agrees with
  the summary. In practice that is 6 to 12 questions; more means the idea is too big
  (propose splitting it).
- Write the user's own words verbatim in quotes where they are the evidence.

## Procedure

1. Read the inputs. State in two lines what you understood, and the single biggest unknown.
2. Interview, in this order, skipping anything already answered by the inputs:
   1. **Problem**: what hurts, for whom, how often, and what evidence exists.
   2. **Who**: the primary person (role, context, skill level) and who is explicitly *not* targeted.
   3. **Today**: current alternatives and workarounds, including "do nothing".
   4. **Why now**: what changed, and what it costs to wait.
   5. **Appetite**: how much time this is worth (days/weeks), not how long it will take.
   6. **Solution sketch**: the smallest shape that solves the core problem, as bullet points
      or a fat-marker description, not screens.
   7. **Rabbit holes**: the parts that could explode in effort, with a decision for each.
   8. **No-gos**: what we deliberately will not do in this round.
   9. **Success**: how we will know it worked (an observable signal and a threshold).
3. Check for overlap with the SOFTURE module catalog (WORKFLOW §10). If part of the sketch
   is a generic capability (auth, mail, waitlist, billing…), note it under *Solution sketch*
   as "use `@softure-ai/<module>`".
4. Draft `shape-notes.md` using the template, then show a 10-line summary and ask:
   "Anything wrong or missing? (Recommended: accept)".
5. Apply corrections and write the file. Set `updated` in the frontmatter.

## Output: `context/foundation/shape-notes.md`

```markdown
---
project: "<name>"
session: 1
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
status: draft | accepted
---

# Shape notes: <theme in one line>

## Current system        (brownfield only; 5–10 lines)
## Problem               (who hurts, how often, evidence; quotes verbatim)
## Who it is for         (primary; secondary; explicitly not for)
## Today                 (alternatives and workarounds)
## Why now
## Appetite              (time budget, fixed; scope flexes, time does not)
## Solution sketch       (smallest shape; elements, not screens)
## Rabbit holes          (risk → decision)
## No-gos
## Success signals       (signal → threshold → how measured)
## Open questions        (owner → by when)
## Previous sessions     (only when re-shaping)
```

Write in `workflow.json` → `language`.

## `--auto`

Without a user to ask, shape only from the inputs. Every section the inputs do not support
gets `UNKNOWN: <what would answer it>` instead of an invented answer. Leave `status: draft`
and list the assumptions under `## Decisions (auto)`.

## Quality bar

- [ ] The problem is stated without naming the solution.
- [ ] There is at least one piece of evidence (a quote, a number or an incident), or an
      explicit note that none exists.
- [ ] The appetite is a time budget, not an estimate.
- [ ] Every rabbit hole has a decision.
- [ ] The success signals are observable by someone other than the author.
- [ ] Fits on about two screens. Longer usually means two themes.

## Do not

- Do not write requirements, user stories or tasks. That is `softure-prd`.
- Do not accept "users want X" without asking how we know.
- Do not run more than one question per message, and do not dump a questionnaire.

## Handoff

Accepted shape → `softure-prd`. If the user doubts whether this is the right thing at all →
`softure-frame`.
