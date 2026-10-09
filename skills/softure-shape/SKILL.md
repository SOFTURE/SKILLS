---
name: softure-shape
description: >
  Turn a raw idea, feedback dump or business goal into `context/foundation/shape-notes.md`:
  the problem, who has it, what they do today, access, the appetite, the first flow and a
  rough solution sketch, the core rule, rabbit holes, no-gos, success signals and open
  questions. Detects greenfield vs brownfield and adapts the interview (brownfield adds the
  current system and preserved behaviour). Interviews one question at a time with a
  recommended answer, pushes back on solution-first thinking, saves after every phase and
  resumes an interrupted session. Use before writing a PRD, at the start of a product or of a
  new theme. Triggers: "shape this idea", "let's think this through", "I have an idea",
  "new project", "change to an existing system", "let's think it through before we start".
argument-hint: "[idea in one sentence | path to notes] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
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

The skill is a **facilitator**. Its value is the order and shape of the questions, not
answers it makes up. Nothing goes into the file that the user did not say or confirm, or
that the inputs do not support. Recommendations are proposals the user accepts or rejects.
The only exception is mechanical: headings, frontmatter, numbering.

## When to use, when not

- Use for a new product, a new theme, or a **meaningful** change to an existing system (a
  new module, a significant feature, a change of behaviour many users notice).
- A single bug, a small refactor or one well-understood feature does not need shaping: point
  to `softure-new` (or to `softure-frame` if the problem itself is in doubt) and stop.

## Inputs

- `context/workflow.json`. If missing, stop and point to `softure-init`.
- The idea: the argument, a file path, pasted notes or screenshots. With nothing at all, ask
  for the idea in one or two sentences, plus any notes or links worth reading, and nothing
  else.
- `context/foundation/shape-notes.md`, when it exists (see Resume and new sessions).
- `prd.md` and `roadmap.md` in `context/foundation/`, when present: the new theme must not
  silently contradict them.

## Greenfield or brownfield

Decide once per session and record it as `context_type` in the frontmatter. On resume, keep
the recorded value.

Signals, strongest first:
1. git history with commits beyond the initial scaffold (`git log --oneline | head`);
2. a lockfile (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `go.sum`,
   `Cargo.lock`, `Gemfile.lock`, `composer.lock`…);
3. source folders and framework config (`src/`, `app/`, a CI folder, a Dockerfile);
4. a manifest alone (`package.json`, `pyproject.toml`…) is **weak**: it may be a fresh init.

Any of 1 or 2 → propose **brownfield**. Only 3 or 4 → propose brownfield but say it might be
a fresh project. Nothing → **greenfield**. State the signals you found and confirm with one
question (recommended: the detected mode). `--auto`: take the detected mode and record the
signals under `## Decisions (auto)`.

Brownfield changes the interview: it starts from what exists, frames everything as a delta,
and asks what must be preserved. Skim the README, the entry points and existing
`context/foundation/*.md` first and summarise the current system in 5 to 10 lines. Do not
audit it.

## Resume and new sessions

When `shape-notes.md` exists, read it fully and decide:

- **`status: draft` with `_pending_` sections** → an interrupted session. Summarise each
  completed section in one line, then continue at the first `_pending_` section. Never
  re-ask what is already answered; the user's earlier decisions stand. Offer "restart" only
  as a second option; restarting moves the file to
  `context/foundation/archive/<YYYY-MM-DD>-shape-notes.md` (same day: `-2`, `-3`).
- **`status: accepted`** → a **new session** on a new theme. Increment `session`, collapse
  the old content into `## Previous sessions` (the key decisions, a few lines), and shape the
  new theme above it.

`--auto`: always resume a draft (never restart); with accepted notes and a new idea, start a
new session.

## Interview technique

- **One question per message.** Each comes with your recommended answer and why, so the user
  can just say "yes". Where the answer is a choice, offer 2 to 4 real options with their
  trade-offs, recommended first, and "Not decided yet" last (it goes to
  `## Open questions`).
- **Problem before solution.** If the user opens with a solution ("add a chat"), ask what
  happens today without it, how often, and what it costs. Do not drop the solution: park it
  under *Solution sketch* or `## Forward notes` and come back to it.
- **Concrete over general:** "last time this happened, what exactly did you do?" Challenge
  vague words ("everyone", "always", "a lot") and claims without evidence ("users want X":
  how do we know?).
- **Echo and lock.** After each phase, show a one-line summary per section and ask "Correct?"
  before writing.
- **Name anti-patterns specifically.** Never "this has issues": say which piece is too
  expensive, or that the core rule is missing, and offer concrete moves.
- **No stack decisions.** Do not ask about or recommend frameworks, databases, hosting or
  vendors. When the user volunteers them, record them under `## Forward notes`; they are
  inputs for later steps, not for the PRD.
- Write the user's own words verbatim in quotes where they are the evidence.
- Stop when every section can be written in your own words and the user agrees. In practice
  8 to 15 questions; many more means the idea is too big (propose splitting it).
- If the user wants to skip a phase ("just write the PRD"), say what the PRD will lack
  without it (for example "no core rule: the PRD will describe a plain list"), then let them
  skip. Skipped sections become open questions.

Per-phase questions, option sets, pushback prompts, the scope-cost and empty-CRUD scripts
and a sample exchange: read `references/question-bank.md` before the first question.

## Procedure

1. Read the inputs and decide greenfield or brownfield. State in two lines what you
   understood and the single biggest unknown.
2. Interview phase by phase, skipping anything the inputs already answer. After each phase,
   write the file (`status: draft`, unfinished sections hold `_pending_`, `updated` set), so
   a broken session can resume.
   1. **Problem and who**: what hurts, for whom, in what moment, at what cost, with what
      evidence; the primary person and who is explicitly *not* targeted. Brownfield first:
      the current system and what must be preserved.
   2. **Today and why now**: current workarounds (including "do nothing"), what changed,
      what waiting costs.
   3. **Access**: how people get in, roles, who sees whose data. Even "single user, no
      sign-in" is an answer worth writing.
   4. **Appetite and the first flow**: a fixed time budget (not an estimate), hard deadline,
      full-time or side work; then the smallest end-to-end flow as numbered steps. Run the
      **scope-cost check** when the flow exceeds the appetite.
   5. **Solution sketch and core rule**: the few elements needed (not screens); the
      one-sentence rule the product applies that a spreadsheet would not. Run the
      **empty-CRUD check** when there is no rule. Brownfield: current rule → change, or "No
      domain rule change".
   6. **Rabbit holes, constraints, no-gos**: each rabbit hole with a decision (cut, fake,
      time-box, accept); brownfield constraints and preserved behaviour as outcomes; no-gos
      for both capabilities and quality levels, drawn from this domain.
   7. **Success signals**: signal → threshold → how measured, plus guardrails (what must not
      get worse); a rough expected scale.
3. Check for overlap with the SOFTURE module catalog (WORKFLOW §10). If part of the sketch
   is a generic capability (auth, mail, waitlist, billing…), note it under *Solution sketch*
   as "use `@softure-ai/<module>`".
4. **Cross-check (soft gate).** Run the quality bar below. Report each gap **by name with its
   consequence** ("Core rule: missing, so the PRD will describe a list with no logic"), never
   a generic "there are gaps". Offer: fill the gaps now (Recommended when more than one is
   missing) / accept and finish / go back to phase N. Accepted gaps go to `## Open questions`
   marked `(accepted gap)`, so `softure-prd` carries them over.
5. Show a 10-line summary and ask: "Anything wrong or missing? (Recommended: accept)".
   Apply corrections, set `status: accepted` and `updated`, write the file.

## Output: `context/foundation/shape-notes.md`

```markdown
---
project: "<name>"
session: 1
context_type: greenfield | brownfield
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
status: draft | accepted
---

# Shape notes: <theme in one line>

## Current system        (brownfield only; 5–10 lines)
## Problem               (who hurts, in what moment, how often, cost; evidence; quotes verbatim)
## Who it is for         (primary; secondary; explicitly not for)
## Access                (how people get in; roles; who sees whose data)
## Today                 (alternatives and workarounds, including doing nothing)
## Why now
## Appetite              (fixed time budget; deadline; full-time or side work; accepted overrun, if any)
## Solution sketch       (First flow as numbered steps; then elements, not screens; modules)
## Core rule             (one sentence; brownfield: today → change, or "No domain rule change")
## Rabbit holes          (risk → decision)
## Constraints and preserved behaviour   (brownfield only; outcomes, not mechanisms)
## No-gos                (capabilities and quality levels not pursued in this round)
## Success signals       (signal → threshold → how measured; guardrails)
## Open questions        (question → owner → by when; "(accepted gap)" where applicable)
## Forward notes         (optional: stack hints, implementation ideas, parked solutions)
## Frame                 (optional, written by softure-frame)
## Decisions (auto)      (only in --auto)
## Previous sessions     (only when re-shaping)
```

Headings stay in English. Write the prose in `workflow.json` → `language`. A complete
greenfield example, the brownfield differences and a bad example with what is wrong:
read `references/example-shape-notes.md` before drafting.

## `--auto`

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

Without a user to ask, shape only from the inputs:
- context type: the detected one; resume: always continue a draft;
- every section the inputs do not support gets `UNKNOWN: <what would answer it>` instead of
  an invented answer; a missing core rule is a **blocking** open question;
- scope-cost check: never grow the appetite; record the expensive pieces and the scope-down
  moves under `## Decisions (auto)` and add an open question for the owner;
- cross-check: write every gap to `## Open questions` as `(accepted gap)`;
- leave `status: draft` and list every assumption under `## Decisions (auto)`.

## Quality bar

- [ ] The problem is stated without naming the solution.
- [ ] There is at least one piece of evidence (a quote, a number or an incident), or an
      explicit note that none exists.
- [ ] The primary person is a role or a named person, not "users".
- [ ] Access is stated, even when it is "single user, no sign-in".
- [ ] The appetite is a time budget, not an estimate, and the first flow fits it (or the
      overrun is recorded as accepted).
- [ ] The core rule is one sentence a spreadsheet could not apply, or is a recorded gap.
- [ ] Every rabbit hole has a decision.
- [ ] Brownfield: preserved behaviour is named explicitly.
- [ ] No-gos are non-empty and specific to this domain.
- [ ] The success signals are observable by someone other than the author.
- [ ] No technology choice outside `## Current system` and `## Forward notes`.
- [ ] Fits on about two to three screens. Longer usually means two themes.

## Do not

- Do not write requirements, user stories, acceptance criteria or tasks. That is
  `softure-prd`.
- Do not accept "users want X" without asking how we know.
- Do not ask more than one question per message, and do not dump a questionnaire.
- Do not invent content to fill a section; ask, or mark it `UNKNOWN`.
- Do not run `softure-prd` yourself; the user decides when the notes are ready.

## Handoff

Report: the file path, context type, which sections are complete, the open questions (and
how many are blocking), and the forward notes that will matter later. Then: accepted shape →
`softure-prd`. If the user doubts whether this is the right thing at all → `softure-frame`.
