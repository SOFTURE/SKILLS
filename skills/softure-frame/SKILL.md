---
name: softure-frame
description: >
  Challenge WHAT is being built before anyone plans HOW. Works on an idea (before the PRD)
  or on a change after research. Separates the observation from the stated cause and the
  problem from the proposed solution, tests the competing explanations against evidence,
  generates alternative framings, offers kill / shrink / reframe / reuse / proceed options,
  and records one decision in `frame.md` of the change, or in a section of shape-notes.
  "The framing was right" is a valid outcome. Use when the request smells like a solution in
  search of a problem, when a bug report arrives with its fix attached, when research found a
  cheaper path, or when scope keeps growing. Triggers: "is this the right thing to build",
  "challenge this", "frame it", "does this even make sense", "can we do this cheaper",
  "what is the root cause", "should we even".
argument-hint: "[change-id | idea] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Agent
  - AskUserQuestion
---

# softure-frame: challenge what to build

## Purpose

A good plan for the wrong thing is still waste. This skill spends a short, bounded effort
trying to make the work **smaller, different or unnecessary**, or to show that the stated
cause is not the real one, before planning locks it in. It ends with an explicit decision,
not a discussion. It never designs the implementation: that is `softure-plan`'s job.

## When to use, when to skip

Use it when the input has one of these shapes:
- **Bug shape:** "X is broken, let's do Y". An observation arrives welded to a cause and a fix.
- **Value shape:** "we need feature F". A solution arrives without the problem it solves.
- **Scope shape:** "split this in two", "is this even the right scope", or scope that keeps growing.
- **Assumption shape:** the plan rests on "users want…", "the slow part is…", unverified.

Skip it for mechanical work (rename, dependency bump), for a cause the user has already
verified ("I reproduced it, plan the fix"), or for a tightly scoped item with no premise to
test. When unsure, run it: on a solid request it costs two or three minutes and ends with
"framing confirmed".

## Inputs

One of two modes:
- **Change mode:** `context/changes/<change-id>/change.md` must exist, and should have
  `research.md`. Without research, say that framing is weaker without it and offer to run
  `softure-research` first (recommended), unless the user wants to frame now. An archived
  change is never framed; open a new one.
- **Idea mode:** an idea or `context/foundation/shape-notes.md`.

Also read `context/foundation/prd.md`, `roadmap.md` and `lessons.md` when present: the frame
must respect the PRD's goals, and lessons about earlier misframings are priors. Read every file
the user names, fully.

## Procedure

1. **Capture, separately.** Write three lines and keep them apart for the rest of the run:
   - **Observation:** what is literally seen or asked (a symptom, a metric, a request as quoted).
   - **Stated cause or premise:** what the requester believes explains it, or why they want it.
   - **Proposed direction:** what they want to build or change.

   Echo them back. The observation is fixed ground; the other two are hypotheses until
   evidence supports them. If the user pushes ("just plan the fix"), keep the separation: it
   is the whole point. If there is no stated cause ("something feels off"), say the frame is
   observation-driven. If you cannot separate problem from solution at all, that is the first
   finding.

2. **Test the premise.** Answer briefly, using evidence from research and the code:
   - What happens if we do nothing for three months?
   - Is the problem real and frequent, or a single anecdote? (count it: logs, data, tickets)
   - Does something in the codebase, a SOFTURE module (`@softure-ai/*`, WORKFLOW §10) or a
     configuration change already solve most of it?
   - What is the smallest change that would prove or disprove the value?

3. **Map where it could come from** (bug, scope and assumption shapes; skip for a clean value
   shape). Build a short map of the places the observation could originate, from what you
   read in *this* system: stages of a data flow, layers of a design, links in a chain of
   assumptions. Mark the node where the stated cause sits. Only list nodes that could
   plausibly produce this observation; two real candidates beat five padded ones.

4. **Test each hypothesis against expected evidence.** For each node ask: *if the problem
   were here, what would we see, and do we see it?* Grade STRONG / WEAK / NONE with `path:line`
   or data. When the surface is large, launch read-only subagents in parallel, one per
   hypothesis, at most five; brief template in `references/diagnostic-lens.md`. Then
   **pressure-test the leader**: a blind search that does not name it, prior occurrences in
   `context/archive/` and git history, and the inverse check (what should be absent if it is
   true). If the original framing still fits the evidence equally well, keep it.

5. **Narrow with questions** (interactive), only when evidence leaves two or more hypotheses
   standing. Ask **one question at a time**. Each one must be able to rule a hypothesis in or
   out; options describe what the user *sees or knows* (when it happens, for whom, since
   when), never fixes. Diagnostic questions always include "I have not checked": false
   certainty is the enemy here, and "not checked" tells you to verify instead of trusting.
   Stop as soon as the ranking stops moving; five questions is the ceiling. If evidence is
   already conclusive, say so and skip. `--auto`: no questions; answer them from data, logs
   and code, and grade what stays unknown as WEAK.

6. **Generate 3 to 5 framings**, each as one line plus the cost difference:
   - *Proceed* as asked (or *Confirmed*, when the stated cause held up).
   - *Shrink*: the 20% that delivers 80%.
   - *Reframe*: solve the underlying problem differently (the real cause from step 4, process,
     copy, default value, existing feature).
   - *Reuse*: adopt an existing module or library instead of building.
   - *Kill or defer*, with the reason.

7. **Recommend one, then push back where it is due.** Give the deciding argument and a
   confidence (HIGH: strong evidence and a decisive signal; MEDIUM: evidence one way, signal
   weaker; LOW: inconclusive, name the verification step needed before planning). Ask a single
   decision question with the options, recommendation first. The decision question has no
   "I'm not sure" option: if the user is unsure, the recommendation stands. Pushback patterns
   and how to phrase them: `references/pushback.md`, read it **when the user's preferred option
   differs from yours or the request is solution-first**. If the user objects with a fact you
   did not have, re-test the affected hypothesis instead of defending the frame.

8. **Record** the decision (template below).
   - Change mode: write `frame.md` in the change folder and update `change.md` -> `## Intent`
     if the outcome changed. The status stays `preparing` (WORKFLOW §4); only `updated` changes.
   - Idea mode: add or replace a `## Frame` section in shape-notes.md with the same headings
     one level down.

9. **Route** (interactive: ask, recommendation first; `--auto`: take the route below):
   - Proceed / confirmed / shrink / reuse / reframe -> `softure-plan` (change mode) or
     `softure-prd` (idea mode).
   - LOW confidence -> verify first (reproduce, measure, read the missing data), then plan.
   - Kill / defer -> leave the change in `changes/` with a `## Notes` line "deferred by frame:
     <reason>", and ask whether to archive it.

## Output: `frame.md`

```markdown
# Frame: <change-id>

## Request as stated
## Observation, premise, direction
- Observation: …
- Stated cause or premise: …
- Proposed direction: …
## Premise check
- Do nothing for 3 months: …
- Evidence (frequency, data): …
- Already solved elsewhere: …
- Smallest proof: …
## Hypotheses                (bug / scope / assumption shapes; omit for a clean value shape)
| Where it could come from | Expected evidence | Found | Verdict |
|---|---|---|---|
Pressure test: blind search -> …; prior occurrences -> …; inverse check -> …
## Framings
| Option | What we build | Cost vs as-asked | Risk |
|---|---|---|---|
## Decision
<option> -- because <deciding argument>. Confidence: HIGH | MEDIUM | LOW.
Problem to plan around: <one sentence>. Scope now: … Out of scope now: …
What changes for the plan: <one or two sentences; for LOW, the verification step that comes first>
## Decisions (auto)        (only in --auto)
```

Keep it to one screen or two. Write in `workflow.json` -> `language`; headings stay English.
Two complete examples (a value-shape frame and a bug-shape frame) and a bad one with why:
read `references/examples.md` **before writing your first frame.md in a repo**.

## `--auto`

- No questions at any step. Narrowing questions are answered from evidence; the decision
  question takes the recommendation. Record each under `## Decisions (auto)`.
- Choose the smallest option that still meets change.md's `## Intent`.
- Never choose *kill* in `--auto`: if killing is the best option, record it as the
  recommendation, choose *shrink*, and add a `## Notes` line in change.md for the owner.
- LOW confidence: do not stop. Put the verification step into "What changes for the plan" as
  the plan's first phase, and record the choice.

## Quality bar

- [ ] Observation, premise and direction are written separately and never merged.
- [ ] Every hypothesis verdict cites evidence from this repo or its data, not a hunch.
- [ ] At least one option is materially cheaper than the request.
- [ ] Each option names its cost difference, not just its features.
- [ ] The decision is a single option with one deciding argument and a confidence.
- [ ] The scope after framing is explicit (in / out).

## Guardrails

- **"The framing was right" is a success.** Never manufacture a reframe the evidence does
  not carry; a clever wrong reframe costs more than none.
- **Evidence before pattern-matching.** Recognising a familiar shape from other systems is a
  source of hypotheses, never of verdicts.
- **No solution design.** Options are about *what* and *how much*, never phases, files or
  technical approaches.
- **No hypothesis padding**, and a time box: two rounds of investigation and at most five
  questions. Past that, the case needs reproduction or measurement, so recommend it and stop.
- Do not reopen decisions the PRD or roadmap made explicitly, unless research contradicts them.
  In that case, say exactly which line is contradicted and why.
- Do not touch code or data.

## Handoff

`softure-plan <change-id>` (change mode) or `softure-prd` (idea mode).
