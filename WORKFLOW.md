# SOFTURE workflow: the contract every `softure-*` skill follows

This file is the single source of truth for the delivery workflow. Every skill in `skills/`
reads and writes **only** the artifacts defined here, in the formats defined here. Orchestrators
(`softure-worktree`, `softure-worktree-manager`) and scripts parse these formats. Change the
format here first, then in every skill that touches it.

## 1. The chain

```
discovery (once per product / per roadmap)
  softure-init → softure-shape → softure-prd → softure-roadmap
                     ↑ softure-frame (challenge the problem at any point)

delivery (once per change)
  softure-new → softure-research → [softure-frame] → softure-plan → softure-plan-review
              → softure-implement (phase by phase) → softure-impl-review → softure-lesson? → softure-archive

orchestration
  softure-worktree          one change, end to end, in its own git worktree; merges on the owner's signal
  softure-worktree-manager  several changes in parallel, merging them one by one

hygiene (any time)
  softure-code-review   review a diff against the project conventions
  softure-rule-review   audit AI rule files (AGENTS.md, CLAUDE.md, skills) for drift and contradictions
  softure-lesson        turn a repeated mistake into a numbered rule
```

Each step produces a durable artifact the next step reads. A step never starts without its
upstream artifact. When the artifact is missing, the skill says which skill produces it and stops.

## 2. Project configuration: `context/workflow.json`

`softure-init` creates it. Every skill reads it. No skill hard-codes commands, branch names
or languages.

```jsonc
{
  "language": "en",                 // ISO code (e.g. "pl"): language of artifacts and reports (skills themselves are English)
  "mainBranch": "master",
  "gates": {                        // run before every implementation commit; all must pass
    "typecheck": "npx tsc --noEmit",
    "lint": "npm run lint",
    "test": "npm test"
  },
  "integration": {                  // optional: the slow, full suite
    "local": "npm run test:integration:full",
    "remote": null                  // e.g. a script that runs the suite on CI and waits: "bash scripts/ci-integration.sh"
  },
  "migrations": {                   // optional: lets orchestrators detect collisions between parallel changes
    "dir": "drizzle",
    "pattern": "^[0-9]{4}_.*\\.sql$",
    "regenerate": "npm run db:generate"
  },
  "worktree": {
    "setup": ["npm ci", "cp ../{repo}/.env .env"],   // run inside a fresh worktree
    "maxParallel": 4
  },
  "release": { "owner": true },     // releases and deploys are never done by skills when true
  "research": {                     // optional: extra knowledge sources softure-research should consult
    "sources": ["docs/", "context/foundation/prd.md"]
  }
}
```

## 3. Artifacts

```
context/
  workflow.json
  foundation/
    shape-notes.md      softure-shape     (frontmatter: session, status, created, updated; optional `## Frame` from softure-frame)
    prd.md              softure-prd       (frontmatter: version, status: draft | accepted, source, updated)
    roadmap.md          softure-roadmap   (§5)
    roadmaps/<YYYY-MM-DD>-<slug>.md      previous roadmaps, archived by softure-roadmap
    lessons.md          softure-lesson    (§7)
  changes/<change-id>/
    change.md           softure-new       (§4)
    research.md         softure-research
    frame.md            softure-frame     (optional)
    plan.md             softure-plan      (§6)
    reviews/
      plan-review.md    softure-plan-review
      impl-review.md    softure-impl-review
      code-review.md    softure-code-review (when run on a change)
  archive/<YYYY-MM-DD>-<change-id>/   softure-archive (date = change.md `created`)
  backlog/              ideas and deferred findings not on the roadmap yet:
                        <topic>.md (flat list, see below) or <group>/<id>/change.md (a prepared change;
                        when picked up it is moved to changes/<id>/backlog-input.md)
```

`change-id` is kebab-case, ASCII, at most 40 characters, unique across `changes/` and `archive/`.

**Headings are fixed English** in every artifact (`## Intent`, `## Progress`, `## Done`, `## Owner decisions and checks`, …),
regardless of `language`. Scripts and orchestrators find sections by these headings. Only the prose under them is
written in `language`.

**Backlog** (`context/backlog/<topic>.md`) collects deferred review findings and ideas that are not roadmap items yet.
Append entries as `- [ ] <YYYY-MM-DD> <source change-id or review>: <finding> (<severity>) <evidence path>`.

## 4. `change.md`

```markdown
---
change_id: pending-states
title: "One sentence: the outcome, not the activity"
status: new
roadmap_item: FC-10          # or null
branch: null                 # set by softure-worktree: change branch / worktree path
created: 2026-10-01
updated: 2026-10-01
archived_at: null
---

## Intent
What must be true when this change is done, and for whom.

## Context
Where it comes from (roadmap item, feedback quoted verbatim, incident), what is known today.

## Constraints
Files this change owns exclusively, things it must not touch, deadlines.

## Notes
Free-form. Orchestrators append signals here.
```

**Status values (exact strings, in this order):**

| status | set by | meaning / resume point |
|---|---|---|
| `new` | softure-new | next: research |
| `preparing` | softure-research | research written; next: frame (optional) or plan |
| `planned` | softure-plan | next: plan review |
| `plan_reviewed` | softure-plan-review | next: implement phase 1 |
| `implementing` | softure-implement | resume at the first `- [ ]` in plan.md Progress |
| `implemented` | softure-implement | all phases done; next: impl review |
| `impl_reviewed` | softure-impl-review | next: triage, integration, archive |
| `archived` | softure-archive | folder moved to archive |

Every skill that changes `status` also sets `updated`.
`softure-frame` leaves the status unchanged (`preparing`). When `softure-plan-review` finds a CRITICAL issue the plan
cannot fix, the status stays `planned` and the finding names the step to redo (`research` or `plan`). Orchestrators
read that finding before re-running plan-review.

## 5. `roadmap.md`

```markdown
---
project: "Name"
roadmap: short-slug
version: 1
status: draft | ready | done
prd_version: 4
updated: 2026-10-01
---

# Roadmap <slug>: <theme>

> Run-wide orders, read by orchestrators (not parsed):
> - Push main branch: no | at the end
> - Parallelism: up to 4 at once

## At a glance

| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **FC-1** | `landing-hero-balance` | hero 50/50, chart readable without text | — | autonomous | ready |

## Order
Why this order; which items may run in parallel and which files each one owns.

## Items

### FC-1: Hero in balance
- **Change ID:** `landing-hero-balance`
- **Status:** ready
- **Outcome:** …
- **Prerequisites:** …
- **Unknowns:** questions research must answer
- **Risk:** …
- **Baseline:** how we measure before/after
- **PRD refs:** …

## Before the next release
- [ ] what must happen before the next release/deploy (env var, manual migration step, …) (**FC-1**)

## Owner decisions and checks
- [ ] **FC-1**: what waits for the owner (Manual 2.4). <evidence path>

## Done
- **FC-0** `some-change`: one line; archived in `archive/2026-09-30-some-change/`
```

`Mode` is `autonomous` (an orchestrator may run it end to end) or `owner` (needs the owner at the keyboard).
In `--auto`, decisions go to a `## Decisions (auto)` section at the end of roadmap.md.
`softure-archive` owns the transition to `done` / `done_code`: it rewrites the row and the item block and appends to
`## Done`. Orchestrators only write `in_progress` and `ready_to_merge`. They fall back to writing `done` themselves
only when the archive step did not.
Each item block may carry `- **Input:** <path>` (e.g. the change folder), which tells research where its brief lives.
`change.md` is defined **only** in §4. softure-roadmap `--open-changes` and softure-new write the same format.

Parsing rules (scripts depend on them):
- Item IDs match `[A-Z]+-\d+`. A table row starts with `| **<ID>** | \`<change-id>\` |`, and the
  **last cell is the status**. Exactly one row per change-id.
- **Status vocabulary:**
  - `proposed`: may be dropped.
  - `ready`
  - `blocked (<why>)`
  - `in_progress (<stage>, since <YYYY-MM-DD>; <where>)`
  - `ready_to_merge (since <YYYY-MM-DD>; <where>)`
  - `done`
  - `done_code (<YYYY-MM-DD>; waiting: <what>)`: merged, waits for a release or an owner check.
- **Stages** (first token inside the parentheses of `in_progress`): `research`, `frame`, `plan`,
  `plan-review`, `implement N/M`, `impl-review`, `integration`, `archive`.
- The item block mirrors the row status in `- **Status:** …` directly under `- **Change ID:**`.

## 6. `plan.md`

```markdown
# Plan: <change-id>

Input: change.md, research.md[, frame.md]

## Goal
## Approach            (chosen option and why; rejected options in one line each)
## Phase 1: <title>
**Discipline:** TDD | test-after. **Files:** …
Steps, then "Done when" criteria.
## Phase 2: …
## Risks and rollback
## Decisions (auto)    (only when produced in autonomous mode)

## Progress

> `- [ ]` pending, `- [x]` done. A phase ends with ` — <commit sha>` on its done items. Never rename items.

### Phase 1: <title>

#### Automated
- [ ] 1.1 <criterion a machine can check>
- [ ] 1.2 Gates green (typecheck, lint, test)

#### Manual
- [ ] 1.3 <criterion only a human can check>
```

Rules:
- `## Progress` is the **only** execution state. No sidecar files.
- It is the last section of the file, with one `### Phase N:` per `## Phase N:`.
- Only `softure-implement` ticks boxes.
- **The resume point is the first `- [ ]` under an `#### Automated` heading.** Open Manual items never block resuming.
  They are carried to the roadmap's `## Owner decisions and checks` at archive time.
- Notation:
  - done: `- [x] N.M text — <sha>`;
  - a Manual item the agent verified itself: `- [x] N.M text — <sha> (verified by agent: <how>)`;
  - dropped mid-flight: `- [x] ~~N.M text~~ — dropped: <reason>`.
- SHA: the phase commit is created first, then the SHA is written into Progress by amending that commit before
  anything is pushed. If the commit is already pushed, record it in a separate `docs(<change-id>): progress p<N>` commit.
- A plan has **no open questions**. Unresolved ones go back to research or to the owner.

## 7. `lessons.md`

```markdown
# Lessons

## L-001: <the rule, imperative, one line>
**Why:** the concrete incident (what happened, what it cost).
**How to apply:** when it applies, and what to do differently.
**Applies to:** paths / areas / skills.
```

Numbers are never reused. Under parallel work, the next number is the maximum over the main
branch and all worktrees, plus one.

## 8. Autonomous mode

Every interactive skill accepts `--auto` (orchestrators always pass it). In `--auto`:
- never ask the user;
- take the recommended option;
- choose the safer option when risk is unclear;
- record each decision under `## Decisions (auto)` in the artifact being written:
  `- <question> → <choice> (<one-line reason>)`;
- stop and escalate only for:
  1. destructive or irreversible actions (data loss, force-push, production);
  2. scope that contradicts change.md;
  3. a missing secret or access the agent cannot obtain.

## 9. Commits

- Implementation: `<type>(<change-id>): <phase title> (p<N>)`. Type is `feat`, `fix`, `refactor`,
  `test`, `docs` or `chore`.
- Review fixes: `fix(<change-id>): address impl review`.
- Progress bookkeeping (only when amending is impossible): `docs(<change-id>): progress p<N>`.
- Archive: `chore(archive): close <change-id>`.
- Roadmap stage updates: `docs(roadmap): <ID> <stage>`.
- Lessons: `docs(lessons): L-<NNN> <title>`. Rule-file edits: `docs(rules): <what>`.
- Merge of a worktree branch: `Merge <change-id> (<ID>): <outcome>`.

## 10. SOFTURE modules first

Before planning any generic capability, `softure-research` and `softure-plan` check the
**SOFTURE AI module catalog** (`@softure-ai/*`, https://github.com/SOFTURE/AI). Generic
capabilities include auth, sessions, roles, feature switches, mail, unsubscribe, waitlist,
MCP access tokens, billing/trial, GDPR export/delete, consent, channel analytics, health
checks and UI primitives. If a module covers the need, the plan uses the module, configured
through `softure.config.ts`. If a module almost covers it, the plan records the gap as an
issue for SOFTURE/AI instead of re-implementing it locally.
