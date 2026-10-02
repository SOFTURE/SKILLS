---
name: softure-impl-review
description: >
  Review a finished implementation against its plan before it is archived or merged: drift
  from plan.md, correctness bugs, missing or weak tests, dishonest Progress (ticked but not
  done), unsafe migrations and security gaps. Every finding gets a severity and a decision;
  accepted fixes are applied and committed. Writes context/changes/<change-id>/reviews/impl-review.md
  and sets change.md status to impl_reviewed. Use after softure-implement finishes the last
  phase, or when the user says "review the implementation", "impl review", "check it against
  the plan", "review what was done".
argument-hint: "<change-id> [--auto] [--no-fix]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - AskUserQuestion
---

# softure-impl-review: does the code do what the plan promised?

Contract: `WORKFLOW.md` §4 (change.md status), §6 (plan.md Progress), §8 (--auto), §9 (commits).
Project commands come from `context/workflow.json`. Never hard-code them.

## Inputs

- `context/changes/<change-id>/change.md`. Status must be `implemented`. If it is
  `implementing`, stop and name the first open `- [ ]` item: the plan is not finished.
- `plan.md`, `research.md`, and `frame.md` if it exists.
- The change's commits: `git log --oneline <mainBranch>..HEAD`, plus the full diff
  `git diff <mainBranch>...HEAD`.
- `context/foundation/lessons.md`: existing rules the code must respect.

## Procedure

1. **Map the plan to commits.** For each `## Phase N`, find its commit
   (`(<change-id>): … (pN)`) and the files it touched. Any phase without a commit, or any
   commit outside every phase, is a finding.
2. **Audit Progress honesty.** For every `- [x]` item, find the evidence: a test name, a file,
   a command output, a screenshot path. A ticked box without evidence is a **CRITICAL**
   finding. Re-run the gates (`gates.*` in workflow.json) and record the result. Do not trust
   earlier runs.
3. **Check drift.** List everything the code does that the plan did not ask for, and everything
   the plan asked for that the code does not do. Intentional drift must be explained in
   plan.md (`## Decisions (auto)` or a phase note). Unexplained drift is a finding.
4. **Read for correctness.** Read every changed file in full, not just the hunks. Check:
   - edge cases (empty, null, boundaries, time zones, money rounding);
   - error paths: is each one surfaced or swallowed?
   - concurrency: unconditional UPDATEs, read-then-write without locking;
   - transaction boundaries;
   - cache and revalidation after writes.
5. **Check tests.** Does each new behaviour have a test that fails without the change? Assertions
   should be specific (`toEqual` over `toBeTruthy`). For the riskiest behaviour, temporarily
   break it and confirm a test goes red. Revert the break before continuing.
6. **Check migrations** (if `migrations.dir` changed):
   - forward-only;
   - rollback note present;
   - no destructive change without a data plan;
   - indexes for new lookups;
   - constraints enforce invariants in the database, not only in code;
   - numbering does not collide with the main branch.
7. **Check security:**
   - authorization on every new action and route, not just authentication;
   - input validated at the boundary;
   - parameterized SQL only;
   - no secrets in code or logs;
   - no stack traces in responses;
   - rate limits on anything public.
8. **Check lessons.** Is any rule in lessons.md violated? Cite the lesson ID.
9. **Write the report** (template below). Then decide each finding:
   - interactive: one AskUserQuestion per CRITICAL, batched for the rest;
   - `--auto`: see below.
10. **Apply the fixes** marked `fix now`. Re-run the gates, then commit
    `fix(<change-id>): address impl review`. Add the fix commit SHA to the report.
11. Set change.md `status: impl_reviewed` and update `updated`. Commit the report together
    with the fixes, or alone with `docs(<change-id>): impl review` if nothing was fixed.

## Severities and decisions

| Severity | Meaning |
|---|---|
| CRITICAL | Wrong behaviour, data loss risk, security hole, or Progress claims something not done. Blocks archive and merge. |
| WARNING | Real defect or gap with limited blast radius: missing test, unclear error, drift without explanation. |
| SUGGESTION | Better, but not wrong. Never blocks. |

Each finding gets exactly one decision. Never leave a finding without one.
- `fix now`: applied in this run.
- `accept`: risk understood and kept; give the reason.
- `defer`: goes to `context/backlog/` or the roadmap "Owner decisions and checks" list; give the target.
- `record as lesson`: hand off to softure-lesson with a one-line rule draft. This can be combined
  with `fix now`.

## Output: `reviews/impl-review.md`

```markdown
# Implementation review: <change-id>

Date: YYYY-MM-DD · Commits: <first>..<last> · Gates: typecheck ✓ lint ✓ test ✓ (N tests)

## Verdict
Ready / Ready after fixes / Not ready. One paragraph.

## Plan coverage
| Phase | Commit | Delivered | Notes |

## Findings
### F1 [CRITICAL] <title>
**Where:** path:line · **What:** … · **Why it matters:** … · **Evidence:** …
**Decision:** fix now: <what was changed> (<sha>)

## Progress audit
Items ticked without evidence (should be none after fixes).

## Lessons proposed
- <rule draft> → softure-lesson
```

## --auto

- CRITICAL and WARNING findings that have a clear local fix: `fix now`.
- Fixes that need a product decision: `defer` to the roadmap "Owner decisions and checks"
  list, with the finding ID.
- SUGGESTIONs: `accept`, unless the fix is under about 10 lines and risk-free.
- A finding that matches a pattern already seen in lessons.md, or that repeats across changes:
  also `record as lesson`.
- If a CRITICAL cannot be fixed without leaving the change's scope, stop and escalate
  (WORKFLOW §8.2).

## Checklist

- [ ] Gates re-run in this session, results in the report header.
- [ ] Every `- [x]` has evidence.
- [ ] Every finding has a decision.
- [ ] Fix commit references the change-id.
- [ ] Status is `impl_reviewed`.

## Anti-patterns

- Reviewing only the diff hunks. Bugs live in the unchanged lines next to them.
- "Looks good" with zero findings on a non-trivial change. Look again at the error paths and tests.
- Rewriting the feature during review. Fixes stay minimal; larger rework goes back to the plan.
- Unticking or rewording Progress items to make the review pass.

## Handoff

- Lessons proposed: run `softure-lesson`.
- Then `softure-archive <change-id>`. Inside a worktree run, `softure-worktree` continues with
  integration and archive.
