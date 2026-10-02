---
name: softure-plan-review
description: >
  Adversarially review a plan before any code is written: check plan.md against
  change.md, research.md and the real codebase for missing phases, unverifiable criteria,
  unsafe migrations, test gaps, scope creep and ignored lessons. Every finding gets a
  decision; accepted fixes are applied to plan.md. Use after softure-plan, before
  softure-implement. Triggers: "review the plan", "plan review", "/softure-plan-review",
  "check the plan before implementation".
argument-hint: "<change-id> [--auto]"
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

# softure-plan-review: break the plan before it breaks the code

A plan fixed now costs minutes. The same flaw found during implementation costs a phase. This
skill assumes the plan is wrong somewhere and looks for where. It is not a style pass.

## Required inputs

- `context/changes/<id>/plan.md` and `change.md` with `status: planned`. If the status is not
  `planned`, run `softure-plan` first.
- `research.md` (and `frame.md` when present), `context/foundation/lessons.md`, and
  `context/workflow.json`.

## Procedure

1. **Check against reality, not only against the documents.** For every file, function, table
   and command the plan names, verify it exists and behaves as the plan assumes (Glob, Grep,
   Read). A plan built on a misread file is the most common critical defect. For a large plan,
   fan out read-only subagents per phase and give each the plan excerpt plus "find where this
   is wrong".

2. **Walk the review lenses.** Each lens gets either findings or the explicit line "no findings".
   - **Coverage:** does finishing all phases achieve change.md Intent? Is any roadmap Unknown or
     research risk left without a phase or a mitigation?
   - **Slicing:** does every phase leave the system green and deployable? Are there horizontal
     layers that only work together at the end?
   - **Verifiability:** can every Done-when criterion be checked by someone else? Flag "works",
     "looks good" and "handles errors" without a measure.
   - **Data and migrations:** migration order, locking on large tables, backfill, rollback or a
     justified forward-only, and a criterion that reads real rows. Check collisions with other
     in-flight changes (`context/changes/*/plan.md` mentioning the same migration folder or tables).
   - **Tests:** is the right discipline chosen (TDD for logic, money, parsing, security, state)?
     Are edge cases named (empty, null, boundaries, concurrency, error paths)? Does an e2e or
     integration test cover the user-visible outcome?
   - **Security:** authorisation on every new entry point, input validation at boundaries, no
     secrets in code, safe error messages.
   - **Scope:** work beyond change.md (creep), or Constraints violated, such as files owned by
     another change.
   - **Reuse:** a generic capability re-implemented although a SOFTURE module covers it
     (WORKFLOW.md §10). Duplication of existing helpers in the codebase.
   - **Lessons:** a lesson in `lessons.md` whose "Applies to" matches and the plan ignores.
   - **Progress format:** matches `softure-plan/references/progress-format.md` one-to-one with
     the phases.

3. **Grade every finding.**
   - **CRITICAL:** implementing as written fails the Intent, loses data, opens a security hole,
     or cannot be verified.
   - **WARNING:** likely rework, a fragile step, or a missing test or rollback.
   - **SUGGESTION:** a clear improvement that is cheap now.

4. **Decide every finding.** None stays pending.
   - **Fix now:** edit plan.md (phases, steps, criteria, Progress) and describe the edit.
   - **Accept risk:** state the risk, why it is acceptable, and who accepted it.
   - **Defer:** state where it goes (backlog, a follow-up change, a roadmap item).

   In interactive mode, present CRITICAL and WARNING findings to the user with your recommended
   decision first. Apply SUGGESTIONs you agree with directly.

5. **Apply the fixes to plan.md.** Keep `## Progress` consistent. Implementation has not started,
   so items may still be renumbered at this point.

6. **Write `reviews/plan-review.md`** using the template below, in the `workflow.json` language.

7. **Update `change.md`.** Set `status: plan_reviewed`, but only when no CRITICAL finding remains
   with a decision other than "Fix now (applied)". A CRITICAL finding that cannot be fixed inside
   the plan sends the change back to research: keep `status: planned` and report.

8. **Report** counts per severity, the decisions, and the next step.

## Output template

```markdown
# Plan review: <change-id>

Reviewed: plan.md @ <date>. Verdict: <ready | ready after fixes | back to research>.

## Findings

### C1 [CRITICAL] <title>
**Where:** Phase 2, step 3 (plan.md) · `src/x.ts:40`
**Problem:** <what is wrong, with evidence>
**Decision:** Fix now — <what changed in plan.md>

### W1 [WARNING] <title>
...
**Decision:** Accept risk — <why acceptable; accepted by owner|auto>

### S1 [SUGGESTION] <title>
...
**Decision:** Defer — <where it goes>

## Lenses with no findings
Coverage, Security, ...

## Decisions (auto)
<only in --auto>
```

## Status transitions

- `planned` → `plan_reviewed` when nothing CRITICAL remains open.
- Otherwise `status` stays `planned` and the report says why.

## `--auto`

- Do not ask. Decide each finding yourself:
  - CRITICAL and WARNING findings with a clear fix → **Fix now**;
  - SUGGESTION → Fix now when it is cheap, otherwise Defer;
  - **Accept risk** only when the fix would contradict change.md Constraints.
- Record each decision under `## Decisions (auto)`.
- Escalate when a CRITICAL finding needs an owner decision (scope, business rule, data deletion).

## Quality checklist

- [ ] Every named file, symbol, table and command was verified in the code.
- [ ] Every lens is covered, with findings or an explicit "no findings".
- [ ] Every finding has a severity, evidence, and a decision.
- [ ] Accepted fixes are actually applied to plan.md, and Progress is still consistent.
- [ ] No CRITICAL finding is open while the status is `plan_reviewed`.

## Anti-patterns

- Reviewing prose instead of checking the plan against the code.
- Leaving findings without decisions ("consider…", "might want to…").
- Inflating style nits to WARNING, or hiding a real risk as a SUGGESTION.
- Rewriting the whole plan. Fix the defects and keep the author's structure.
- Approving a plan whose criteria cannot be checked.

## Handoff

- Verdict ready: `softure-implement <change-id>`, starting at phase 1.
- Back to research: `softure-research <change-id>`, focused on the critical finding.
