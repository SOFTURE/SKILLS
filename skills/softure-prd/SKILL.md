---
name: softure-prd
description: >
  Write or revise `context/foundation/prd.md` from accepted shape notes: goals and
  non-goals, users, functional requirements with stable IDs (FR-1…), non-functional
  requirements, success metrics, risks and out-of-scope, with a version that is bumped on
  every edit. Use after softure-shape, or when the product direction changes. Triggers:
  "write the PRD", "update the PRD", "turn the shape into requirements",
  "write down the requirements".
argument-hint: "[--revise] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
---

# softure-prd: requirements a roadmap can be sliced from

## Purpose

The PRD is the contract between *why* (shape notes) and *in what order* (roadmap). It says
what must be true for users, with stable IDs that roadmap items, plans and reviews can cite.
It does not say how to implement.

## Inputs

- `context/foundation/shape-notes.md` with `status: accepted`. If it is missing or still a
  draft, stop and point to `softure-shape` (or ask the user to accept the draft).
- An existing `prd.md` means **revise mode**: keep the IDs, bump `version`, and log the change
  (see Versioning).
- For brownfield work, read the code paths the shape notes mention, so that requirements are
  stated relative to what exists.

## Procedure

1. **Extract.** From the shape notes, list the candidate goals, users, capabilities and
   constraints. Mark anything the notes do not support as an open question. Do not fill gaps
   by invention.
2. **Resolve open questions**, one per message, each with a recommended answer. Ask only those
   that change a requirement. Everything else goes to `## Open questions` with an owner.
3. **Write the requirements:**
   - Each FR is one **observable behaviour**: "When <trigger>, <actor> can/sees <result>".
     It never names an implementation ("use Redis", "add a table").
   - Each FR gets acceptance criteria someone else could test: given/when/then, or a short
     bullet list.
   - Priority: `must` (the release fails without it), `should`, `could`. Roughly 60% of
     effort or less should be `must`.
   - NFRs are measurable (latency p95, availability, data retention, accessibility level,
     supported locales), and only where they matter.
4. **Mark generic capabilities.** For FRs that a SOFTURE module covers (WORKFLOW §10), add
   `Module: @softure-ai/<name>` so the roadmap and plan reuse it instead of rebuilding it.
5. **Check consistency:**
   - every goal has at least one FR;
   - every `must` FR traces to a problem in the shape notes;
   - every success metric is measurable with something that exists or is planned in an FR;
   - nothing in *Out of scope* contradicts an FR.
6. Show the FR table, ask "Accept? (Recommended: accept)", then apply corrections and write.

## Output: `context/foundation/prd.md`

```markdown
---
project: "<name>"
version: 1
status: draft | accepted
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
source: shape-notes.md (session <n>)
---

# PRD v<version>: <theme>

## Summary              (5 lines: problem, who, outcome, appetite, release boundary)
## Goals                (G-1…, each measurable)
## Non-goals
## Users                (primary / secondary / not for; link to shape notes)
## Current system       (brownfield: what stays as is, explicitly)
## Functional requirements
| ID | Requirement (observable behaviour) | Priority | Goal | Module |
|---|---|---|---|---|
| FR-1 | When …, … can … | must | G-1 | @softure-ai/auth |

### FR-1: <short name>
Acceptance:
- Given …, when …, then …
Notes: edge cases, copy constraints, data rules.

## Non-functional requirements   (NFR-1…, each with a number)
## Success metrics               (metric → baseline → target → how measured → when checked)
## Risks                         (risk → likelihood → impact → mitigation)
## Out of scope
## Open questions                (question → owner → needed by)
## Changelog                     (v<n> <date>: what changed and why)
```

Write in `workflow.json` → `language`. IDs stay in this ASCII form whatever the language.

## Versioning

- A new PRD starts at `version: 1`. Every revise run increments `version` and adds a
  `## Changelog` line.
- IDs are **never reused or renumbered**. A dropped FR stays, with its row struck through
  (`~~FR-7~~`) and a reason. New FRs take the next free number.
- If a roadmap exists with `prd_version` lower than the new version, say which items cite
  changed FRs and recommend running `softure-roadmap --revise`.

## `--auto`

Write only what the shape notes support. Unsupported or ambiguous points go to
`## Open questions`. Leave `status: draft` and record each interpretation under
`## Decisions (auto)`.

## Quality bar

- [ ] No FR names a technology or a table.
- [ ] Every FR has acceptance criteria a tester could run without asking the author.
- [ ] Goals and success metrics have numbers or explicit yes/no checks.
- [ ] Out of scope is non-empty. If nothing is excluded, the scope is not shaped yet.
- [ ] IDs are stable across versions.

## Do not

- Do not slice the work into milestones. That is `softure-roadmap`.
- Do not copy the shape notes wholesale. Link to them and keep the PRD about requirements.
- Do not silently change an accepted FR. Every change goes through the changelog.

## Handoff

Accepted PRD → `softure-roadmap`.
