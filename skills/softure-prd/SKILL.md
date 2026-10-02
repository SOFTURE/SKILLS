---
name: softure-prd
description: >
  Write or revise `context/foundation/prd.md` from accepted shape notes (or, with a
  warning, from raw notes): summary and insight, goals and non-goals, users, access
  control, the primary flow, the core business rule, functional requirements with stable
  IDs (FR-1…) and testable acceptance, measurable non-functional requirements, success
  metrics with guardrails, risks, out-of-scope and open questions. Greenfield and
  brownfield variants (brownfield marks every requirement new / modified / preserved /
  removed). Challenges each must-have requirement, lints out implementation detail, never
  invents what the input lacks, and bumps the version with a changelog on every revision.
  Use after softure-shape, or when the product direction changes. Triggers: "write the PRD",
  "update the PRD", "turn the shape into requirements", "write down the requirements".
argument-hint: "[--revise] [--from <notes-path>] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - AskUserQuestion
---

# softure-prd: requirements a roadmap can be sliced from

## Purpose

The PRD is the contract between *why* (shape notes) and *in what order* (roadmap). It says
what must be true for users, with stable IDs that roadmap items, plans and reviews can cite.
It does not say how to implement.

The skill turns decisions already made into requirements. It **never invents** a business
rule, a goal, a priority, a target or a non-goal the input does not contain: a gap becomes
an open question, visibly, so the owner can close it. Its interactive part is narrow: close
the gaps that change a requirement, and challenge the requirements before they are locked.

## Inputs

- `context/workflow.json`. If missing, stop and point to `softure-init`.
- `context/foundation/shape-notes.md` with `status: accepted`. If it is missing, stop and
  point to `softure-shape`. If it is a draft, show what is unfinished and ask whether to
  accept it as is (Recommended: finish shaping first).
- `--from <path>`: raw notes instead of shape notes (a brief, a feedback dump). Allowed, but
  run the input check below and say plainly that a PRD from unshaped notes carries many
  gaps. Record `source: <path> (unshaped notes)`.
- An existing `prd.md` means **revise mode** (see Versioning).
- Brownfield: read the code paths the shape notes mention, so that requirements are stated
  relative to what exists. Do not audit the code.

## Input check

Before writing, score the input on six signals, one point each, and show the result:

```
Input check (6 signals):
  [x] Problem with evidence            <found | missing>
  [x] Primary person named (a role)    <found | missing>
  [ ] First flow as steps              <found | missing>
  [x] Core rule in one sentence        <found | missing>   (brownfield technical work: "No domain rule change" counts)
  [x] No-gos listed                    <found | missing>
  [ ] Success signal with a threshold  <found | missing>
  Score: 4/6
```

Below 4, name each missing signal with its consequence for the PRD ("no first flow: the
primary flow and its FRs will be open questions"), never a generic "the input is thin".
Offer: shape first (Recommended) / write the PRD anyway, with the gaps as open questions /
cancel. `--auto`: write anyway and record the score under `## Decisions (auto)`.

## Procedure

1. **Context type.** Take `context_type` from the shape notes. Without it, detect it as
   `softure-shape` does (git history, lockfiles, source folders) and confirm it with one
   question (`--auto`: take the detected value).
2. **Extract and map.** Map each shape-notes section to its PRD section (mapping table in
   `references/prd-template.md`). Keep the user's wording; change only the form the PRD
   requires (FR sentences, given/when/then, tables). Carry every open question, `UNKNOWN`
   and `(accepted gap)` over word for word. Where the input has nothing, write
   `TODO: <what is missing> (OQ-<n>)` and add the open question. A missing core rule is a
   **blocking** question; never infer a rule from the nouns in the sketch.
3. **Resolve open questions**, one per message, each with a recommended answer and why. Ask
   only those that change a `must` requirement or the core rule. Everything else stays in
   `## Open questions` with an owner.
4. **Write the requirements:**
   - Each FR is one **observable behaviour**: "When <trigger>, <actor> can/sees <result>".
     It never names an implementation ("use a queue", "add a table").
   - Each FR gets acceptance criteria someone else could test: given/when/then, or a short
     list. Cover the empty case and the failure case where they exist.
   - Priority: `must` (the release fails without it), `should`, `could`. Roughly 60% of
     effort or less should be `must`.
   - The primary flow lists the first flow's steps, each pointing at the FR behind it.
   - Brownfield: every FR carries `Change: new | modified | preserved | removed`, and every
     line of preserved behaviour in the shape notes becomes a `preserved` FR with its own
     acceptance, not a non-goal.
   - NFRs are measurable (response time a user perceives, availability, retention,
     accessibility level, supported browsers or locales), and only where they matter.
5. **Challenge the must FRs.** For each `must` FR, one message: the strongest
   counter-argument specific to this FR, as 2 or 3 options plus "It stands as written" last
   (so the challenge is considered before it is dismissed). Possible outcomes: keep, split,
   demote, drop. Record the outcome under the FR as `Challenge: <argument> → <resolution>`.
   With more than eight `must` FRs, challenge them in batches of up to four per message.
6. **Mark generic capabilities.** For FRs that a SOFTURE module covers (WORKFLOW §10), add
   `Module: @softure-ai/<name>` so the roadmap and plan reuse it instead of rebuilding it.
7. **Self-review before writing:**
   - *Structure:* every section of the template for this `context_type`, in order, with the
     frontmatter keys present; no data-model, architecture, testing or deployment section.
   - *Consistency:* every goal has at least one FR; every `must` FR traces to a problem in
     the shape notes; every primary-flow step has an FR; every success metric is measurable
     with something that exists or is planned in an FR; nothing in *Out of scope* or
     *Non-goals* contradicts an FR; every `TODO:` has its open question.
   - *Leak lint:* scan for vendors, data-model notation, runtime locations, enforcement
     mechanisms, protocols and components acting as the rule (`references/leak-lint.md`).
     Show each hit with a proposed outside-observable rewrite; never rewrite silently.
8. Show the summary, the FR table and the open questions (blocking first), and ask
   "Accept? (Recommended: accept)". A PRD with a blocking `TODO:` cannot be accepted:
   recommend keeping it as `draft` and say which questions block. Apply corrections, set
   `status` and `updated`, and write.

## Output: `context/foundation/prd.md`

Section order (greenfield): Summary, Goals, Non-goals, Users, Access control, Primary flow,
Business rules, Functional requirements, Non-functional requirements, Success metrics (with
Guardrails), Risks, Out of scope, Open questions, Changelog, Decisions (auto). Brownfield
adds `## Current system` after Summary and `## Compatibility and preserved behaviour` after
the non-functional requirements, and frames every section as a delta.

The full templates, the rules per section, what a PRD never contains and the shape-notes
mapping: read `references/prd-template.md` before drafting. A complete greenfield PRD, the
brownfield parts, a revision and bad requirements with fixes: read
`references/example-prd.md`.

Write in `workflow.json` → `language`. Headings and IDs (`G-`, `FR-`, `NFR-`, `OQ-`) stay in
this ASCII form whatever the language.

## Versioning

- A new PRD starts at `version: 1`. Every revise run increments `version` and adds a
  `## Changelog` line: what changed, why, and which roadmap items cite the changed FRs.
- Before revising an `accepted` PRD, copy it to
  `context/foundation/archive/<YYYY-MM-DD>-prd.md` (same day: `-2`, `-3`), so the accepted
  version stays readable next to the new draft. A new revision starts as `status: draft`.
- IDs are **never reused or renumbered**. A dropped FR stays, with its row struck through
  (`~~FR-7~~`) and a reason. New FRs take the next free number.
- Revise only what the new input changes; do not rephrase accepted FRs on the way through.
- If a roadmap exists with `prd_version` lower than the new version, say which items cite
  changed FRs and recommend running `softure-roadmap --revise`.

## `--auto`

Write only what the input supports, and never ask:
- draft shape notes or a low input-check score: proceed, record it under
  `## Decisions (auto)`;
- unsupported or ambiguous points go to `## Open questions` with `TODO:` markers; a missing
  core rule stays a blocking question;
- challenge round: write the strongest counter-argument under each `must` FR, but keep the
  FR as the input states it (never drop or demote without the owner), and record it;
- leak lint: apply the outside-observable rewrites, list the original phrases as forward
  notes in the handoff, and record each one;
- revise mode: archive the accepted version first, as above;
- leave `status: draft` and record each interpretation under `## Decisions (auto)`.

## Quality bar

- [ ] No FR or NFR names a technology, a vendor, a table or a mechanism (Module column and
      brownfield `## Current system` excepted).
- [ ] Every FR has acceptance criteria a tester could run without asking the author.
- [ ] Every primary-flow step has an FR, and every goal has at least one FR.
- [ ] The core rule is one sentence, or a blocking open question.
- [ ] Goals and success metrics have numbers or explicit yes/no checks; guardrails exist.
- [ ] Access control is stated, even for a single-user tool.
- [ ] Out of scope is non-empty. If nothing is excluded, the scope is not shaped yet.
- [ ] Brownfield: every preserved behaviour is a `preserved` FR with acceptance.
- [ ] Every `TODO:` has a matching `OQ-<n>`; nothing was invented to fill a gap.
- [ ] IDs are stable across versions.

## Do not

- Do not slice the work into milestones. That is `softure-roadmap`.
- Do not copy the shape notes wholesale. Link to them and keep the PRD about requirements.
- Do not silently change an accepted FR. Every change goes through the changelog.
- Do not write a data model, architecture, test strategy or deployment plan. Such content in
  the input is listed in the handoff as forward notes, never dropped silently.
- Do not run `softure-roadmap` yourself; the owner reviews the PRD first.

## Handoff

Report: the path and version, context type, sections complete vs with `TODO:`, the number of
open questions (blocking first), the challenges that changed an FR, and forward notes from
the input that are not in the PRD (stack hints, data-model ideas, implementation notes) so
the plan can pick them up. Then: accepted PRD → `softure-roadmap`.
