---
name: softure-impl-review
description: >
  Review a finished implementation (or one finished phase) against its plan before it is
  archived or merged: drift from plan.md, correctness bugs, missing or weak tests, dishonest
  Progress (ticked but not done), unsafe migrations, security gaps and broken project
  patterns. Every finding gets a severity, an impact, a recommended fix and a decision, triaged
  with the user one by one or in a batch; accepted fixes are applied and committed. Writes
  context/changes/<change-id>/reviews/impl-review.md and sets change.md status to
  impl_reviewed. Use after softure-implement finishes the last phase, or when the user says
  "review the implementation", "impl review", "check it against the plan", "review what was
  done", "review phase N".
argument-hint: "<change-id> [phase N] [--triage] [--auto] [--no-fix]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - Agent
  - AskUserQuestion
---

# softure-impl-review: does the code do what the plan promised?

Contract: `WORKFLOW.md` §4 (change.md status), §6 (plan.md Progress), §8 (--auto), §9 (commits).
Project commands come from `context/workflow.json`. Never hard-code them. The report's headings
are fixed English; its prose follows `language` in workflow.json.

Read when needed:
- `references/rubric.md`: the dimensions and what to check in each, severity and impact scales,
  the finding format with fix options, verdict rules, briefs for review subagents. Read before
  grading.
- `references/triage.md`: the chat summary, the questions asked per finding, how each answer is
  handled, the lesson flow, resuming a saved triage. Read before talking to the user.
- `references/example-review.md`: a complete `reviews/impl-review.md` for an invoicing change.
  Read before writing the report.

## Scope

| Invocation | Reviews | Requires | Writes | Status |
|---|---|---|---|---|
| `<change-id>` | all phases | `status: implemented` | `reviews/impl-review.md` | → `impl_reviewed` |
| `<change-id> phase N` | phase N, plus whether it broke what earlier phases assumed | phase N's Automated items all ticked | `reviews/impl-review-p<N>.md` | unchanged |
| `<change-id> [phase N] --triage` | nothing new; resumes deciding a saved report | a report with `**Decision:** pending` | the same report | as for its scope, once nothing is pending |

- Full review on `implementing`: stop and name the first open `- [ ]` Automated item.
- A path under `context/archive/`: refuse; archived changes are not reviewed again.
- No argument, interactive: list changes with status `implementing` or `implemented`, recommend
  the most recently `updated`, and ask. `--auto`: the change-id is mandatory.
- The report already exists with pending decisions: interactive, ask "Resume triage"
  (recommended) or "Review again from scratch" (keep earlier decisions for findings that still
  apply); `--auto`, decide the pending ones by the `--auto` rules.

## Inputs

- `change.md`, `plan.md`, `research.md`, and `frame.md` if it exists.
- The change's commits: `git log --oneline <mainBranch>..HEAD`, plus `git diff <mainBranch>...HEAD`
  (for a phase review: that phase's commit).
- `context/foundation/lessons.md`: existing rules the code must respect.
- The project's AGENTS.md / CLAUDE.md conventions.

## Procedure

1. **Map the plan to commits and files.** For each `## Phase N`, find its commit
   (`(<change-id>): … (pN)`). A phase without a commit, or a commit outside every phase (other
   than `fix`, `docs(<id>): progress` and review commits), is a finding. Then compare the files the
   plan names with the files the diff touches: in both (check the content matches the intent),
   only in the diff (unplanned: investigate), only in the plan (possibly missing).
2. **Audit Progress honesty.** For every `- [x]`, find the evidence: a test name, a file, a
   command output, a screenshot. Re-run the gates (`gates.*`) and every Automated criterion that
   names a command; do not trust earlier runs. A ticked box without evidence is **CRITICAL**.
   `(verified by agent: …)` must point at something that exists. Open Manual items are pending,
   not findings.
3. **Check drift.** Everything the code does that the plan did not ask for, everything the plan
   asked for that the code does not do. Intentional drift must be explained in plan.md
   (`## Decisions (auto)` or a phase note). Unexplained drift is a finding. A flaw in the plan
   itself (an insecure approach it prescribed) is a finding too.
4. **Read for correctness.** Read every changed file in full, not just the hunks: edge cases
   (empty, null, boundaries, time zones, money rounding), error paths (surfaced or swallowed?),
   concurrency (unconditional UPDATEs, read-then-write without locking), transaction boundaries,
   cache and revalidation after writes, performance (N+1 queries, unbounded loops or result sets),
   resource leaks.
5. **Check tests.** Does each new behaviour have a test that fails without the change? Are the
   assertions specific? For the riskiest behaviour, temporarily break it and confirm a test goes
   red (copy the file aside first, restore it from that copy). Record the result.
6. **Check migrations** (if `migrations.dir` changed): forward-only, rollback note, no destructive
   change without a data plan, indexes for new lookups, constraints enforce invariants in the
   database, numbering does not collide with the main branch.
7. **Check security:** authorization on every new action and route (not just a session), input
   validated at the boundary, parameterized SQL, no secrets in code or logs, no stack traces in
   responses, rate limits on anything public.
8. **Check patterns and lessons.** For each new module, compare with one or two siblings that do
   the same kind of job (registration, error handling, structure, tests). Report only substantive
   mismatches, scaled to the size of the diff. Cite any `lessons.md` rule the code breaks by ID.

   For a diff over about ten files, fan out read-only subagents with targeted briefs
   (`references/rubric.md`) instead of loading every file into the main context.
9. **Grade and recommend.** Each finding gets a severity, an impact, a dimension, a location,
   evidence and one recommended fix (two only for a genuine trade-off). Consolidate to at most
   ten findings; never merge away a CRITICAL. Set a verdict per dimension and overall.
10. **Triage.** Interactive: print the chat summary, then ask how to proceed and decide each
    finding (`references/triage.md`): CRITICAL and HIGH-impact findings one by one, the rest one
    by one or as a batch of recommended decisions. `--auto`: see below. `--no-fix`: decide, apply
    nothing.
11. **Apply the fixes** decided `fix now`: minimal edits, no refactoring around them. For a
    MEDIUM or HIGH impact fix, show the before/after first. Re-run the gates, re-check each fixed
    CRITICAL the way it was found, and commit `fix(<change-id>): address impl review`. That commit
    also carries any pending Progress SHA edit from implementation.
12. **Write and commit the report.** Write the fix SHA into each decision, set change.md
    `status: impl_reviewed` and `updated` (full review only, and only when no decision is
    pending), then commit the report and change.md as `docs(<change-id>): impl review` (phase
    review: `docs(<change-id>): impl review p<N>`). The report never rides in the fix commit,
    because it records that commit's SHA. Never amend.

## Severities, impact and decisions

| Severity | Meaning |
|---|---|
| CRITICAL | Wrong behaviour, data loss risk, security hole, or Progress claims something not done. Blocks archive and merge. |
| WARNING | Real defect or gap with limited blast radius: missing test, unclear error, drift without explanation, a broken pattern. |
| SUGGESTION | Better, but not wrong. Never blocks. |

Impact is how much thought the **decision** needs, not how bad the defect is: LOW (the fix is
obvious and narrow), MEDIUM (a real trade-off), HIGH (wide blast radius or no clear best path). A
CRITICAL can be LOW impact (one obvious line) and a WARNING HIGH (an architectural choice).

Each finding gets exactly one decision. Never leave one without it, except while a triage is
saved for later; `pending` is not a decision, and archive and merge treat it as open.
- `fix now`: applied in this run (record which option, and the SHA).
- `accept`: risk understood and kept; give the reason and who accepted. Only the owner accepts a CRITICAL.
- `defer`: goes to `context/backlog/<topic>.md` (WORKFLOW §3 entry format) or the roadmap
  "Owner decisions and checks" list; give the target.
- `withdrawn`: the finding was wrong; say why (keeps the audit trail honest).
- `record as lesson`: hand off to `softure-lesson --from <change-id>#F<n>` with a one-line rule
  draft. Combined with `fix now` unless the lesson is purely about process.

## Output: `reviews/impl-review.md`

Layout (full example in `references/example-review.md`):

```markdown
# Implementation review: <change-id>

Scope: full | phase N · Date: YYYY-MM-DD · Commits: <first>..<last> · Gates: typecheck ✓ lint ✓ test ✓ (N tests)

## Verdict
Ready / Ready after fixes / Not ready. One paragraph.

## Dimensions
| Dimension | Verdict | Findings |

## Plan coverage
| Phase | Commit | Delivered | Notes |
Files: planned and changed N · unplanned N (…) · planned, not changed N (…)

## Findings
### F1 [CRITICAL] <title>
**Impact:** LOW (obvious, narrow fix) · **Dimension:** … · **Where:** path:line
**What:** … **Why it matters:** … **Evidence:** …
**Fix:** … (or Fix A / Fix B with strength, trade-off, confidence, blind spot)
**Decision:** fix now: <what was changed> (<sha>)

## Progress audit
## Triage summary
## Lessons proposed
## Decisions (auto)        (only in --auto)
```

## --auto

- CRITICAL and WARNING findings that have a clear local fix: `fix now` (the recommended option).
- Fixes that need a product decision: `defer` to the roadmap "Owner decisions and checks"
  list, with the finding ID.
- SUGGESTIONs: `accept`, unless the fix is under about 10 lines and risk-free.
- A finding that matches a pattern already seen in lessons.md, or that repeats across changes:
  also `record as lesson`.
- No questions, no before/after confirmation. Each decision also goes under `## Decisions (auto)`.
- If a CRITICAL cannot be fixed without leaving the change's scope, stop and escalate
  (WORKFLOW §8.2).

`--no-fix` (either mode): write the report with recommended decisions as
`**Decision:** pending (recommended: …)`, apply nothing, leave the status unchanged. Resume with
`--triage`.

## Checklist

- [ ] Gates and command-based criteria re-run in this session, results in the report header.
- [ ] Every `- [x]` has evidence.
- [ ] Every changed file was read in full; planned, unplanned and missing files are accounted for.
- [ ] Every finding has severity, impact, location, evidence, a recommended fix and a decision.
- [ ] Fix commit references the change-id; the report records its SHA in a separate commit.
- [ ] Status is `impl_reviewed` (full review) and no decision is pending.

## Anti-patterns

- Reviewing only the diff hunks. Bugs live in the unchanged lines next to them.
- "Looks good" with zero findings on a non-trivial change. Look again at the error paths and tests.
- Vague findings ("there may be a security issue"). Name the file, the line and the mechanism.
- Inventing a second fix option to look thorough. One fix unless the trade-off is real.
- Style preferences graded as WARNING. If the code works and matches the plan, it is a SUGGESTION at most.
- Rewriting the feature during review. Fixes stay minimal; larger rework goes back to the plan.
- Unticking or rewording Progress items to make the review pass.
- Arguing with a user who skips a finding. Record the decision and move on.

## Handoff

- Lessons proposed: run `softure-lesson`.
- Phase review: back to `softure-implement <change-id> next`.
- Full review: `softure-archive <change-id>`. Inside a worktree run, `softure-worktree`
  continues with integration and archive. After fixing a CRITICAL, it re-runs this review.
