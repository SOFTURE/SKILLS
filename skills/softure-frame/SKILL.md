---
name: softure-frame
description: >
  Challenge WHAT is being built before anyone plans HOW. Works on an idea (before the PRD)
  or on a change after research: restates the problem, generates alternative framings,
  offers kill / shrink / reframe / proceed options, and records the decision in `frame.md`
  of the change, or in a section of shape-notes. Use when the request smells like a
  solution in search of a problem, when research found a cheaper path, or when scope keeps
  growing. Triggers: "is this the right thing to build", "challenge this", "frame it",
  "does this even make sense", "can we do this cheaper".
argument-hint: "[change-id | idea] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
---

# softure-frame: challenge what to build

## Purpose

A good plan for the wrong thing is still waste. This skill spends a few minutes trying to
make the work **smaller, different or unnecessary** before planning locks it in. It ends
with an explicit decision, not a discussion.

## Inputs

One of two modes:
- **Change mode:** `context/changes/<change-id>/change.md` must exist, and should have
  `research.md`. Without research, say that framing is weaker without it and offer to run
  `softure-research` first (recommended), unless the user wants to frame now.
- **Idea mode:** an idea or `context/foundation/shape-notes.md`.

Also read `context/foundation/prd.md` and `roadmap.md` when present, because the frame must
respect their goals.

## Procedure

1. **Restate.** Write the request as *problem → desired outcome → proposed solution*, in
   three lines. If you cannot separate problem from solution, that is the first finding.
2. **Test the premise.** Answer briefly, using evidence from research and the code:
   - What happens if we do nothing for three months?
   - Is the problem real and frequent, or a single anecdote?
   - Does something in the codebase, a SOFTURE module (`@softure-ai/*`, WORKFLOW §10) or a
     configuration change already solve most of it?
   - What is the smallest change that would prove or disprove the value?
3. **Generate 3 to 5 framings**, each as one line plus the cost difference:
   - *Proceed* as asked.
   - *Shrink*: the 20% that delivers 80%.
   - *Reframe*: solve the underlying problem differently (process, copy, default value,
     existing feature).
   - *Reuse*: adopt an existing module or library instead of building.
   - *Kill or defer*, with the reason.
4. **Recommend one** and give the deciding argument, then ask a single question with the
   options. Never offer "I'm not sure" as an option; if the user is unsure, the recommendation
   stands.
5. **Record** the decision (template below).
   - Change mode: write `frame.md` in the change folder and update `change.md` → `## Intent`
     if the outcome changed.
   - Idea mode: add or replace a `## Frame` section in shape-notes.md.
6. **Route:**
   - Proceed / shrink / reuse → `softure-plan` (change mode) or `softure-prd` (idea mode).
   - Kill / defer → leave the change in `changes/` with a `## Notes` line "deferred by frame:
     <reason>", and ask whether to archive it.

## Output: `frame.md`

```markdown
# Frame: <change-id>

## Request as stated
## Problem → outcome → proposed solution   (three lines)
## Premise check
- Do nothing for 3 months: …
- Evidence: …
- Already solved elsewhere: …
- Smallest proof: …
## Framings
| Option | What we build | Cost vs as-asked | Risk |
|---|---|---|---|
## Decision
<option> — because <deciding argument>. Scope now: … Out of scope now: …
## Decisions (auto)        (only in --auto)
```

Write in `workflow.json` → `language`.

## `--auto`

Choose the smallest option that still meets change.md's `## Intent`. Never choose *kill*
in `--auto`: if killing is the best option, record it as the recommendation, choose *shrink*,
and add a `## Notes` line in change.md for the owner. Do not ask anything.

## Quality bar

- [ ] At least one option is materially cheaper than the request.
- [ ] Each option names its cost difference, not just its features.
- [ ] The decision is a single option with one deciding argument.
- [ ] The scope after framing is explicit (in / out).

## Do not

- Do not plan, estimate tasks or touch code.
- Do not reopen decisions the PRD or roadmap made explicitly, unless research contradicts them.
  In that case, say exactly which line is contradicted and why.
- Do not spend more than one round of questions. Framing is fast by design.

## Handoff

`softure-plan <change-id>` (change mode) or `softure-prd` (idea mode).
