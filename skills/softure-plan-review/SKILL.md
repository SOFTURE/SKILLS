---
name: softure-plan-review
description: >
  Adversarially review a plan before any code is written: check plan.md against itself,
  against change.md, research.md and lessons, and against the real codebase for missing
  phases, broken contracts between steps, unverifiable criteria, unsafe migrations, test
  gaps, pattern proliferation, scope creep and ignored lessons. Every finding gets a
  severity, a decision effort, evidence and a recommended fix; the user triages them one at
  a time (or saves the review and resumes later); accepted fixes are applied to plan.md.
  Use after softure-plan, before softure-implement. Triggers: "review the plan", "plan
  review", "/softure-plan-review", "check the plan before implementation", "is this plan
  good", "resume the plan review".
argument-hint: "<change-id> [--quick] [--auto]"
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
skill assumes the plan is wrong somewhere and looks for where. It is not a style pass, and it
does not manufacture findings: a sound plan gets a short review that says so.

Where softure-impl-review asks "did we build what we planned?", this asks "will this plan
work?"

## Required inputs

- `context/changes/<id>/plan.md` and `change.md` with `status: planned`. If the status is not
  `planned`, run `softure-plan` first.
- `research.md` (and `frame.md` when present), `context/foundation/lessons.md`, and
  `context/workflow.json`.

## Resolve the input

- **No argument:** list changes with status `planned`, newest `updated` first, and ask which
  one. In `--auto` an id is mandatory: stop and say so.
- **A path under `context/archive/`:** refuse. Archived plans are not reviewed.
- **`reviews/plan-review.md` exists with `**Decision:** pending` findings:** resume triage at
  the first pending finding (step 9). Re-check that plan.md has not changed in the meantime;
  if it has, re-verify those findings before asking about them.
- **`reviews/plan-review.md` exists, fully decided, and plan.md changed since** (refine or
  re-plan): run a fresh review and overwrite the file. Carry an earlier finding over, with its
  decision, only when it still applies.
- **`--quick`:** document-only review. Run steps 1-3 and 5-12, skip the deep verification
  (step 4), and say "quick" in the review header. Use it for small plans or a second pass after
  fixes, never as the only review of a plan with data changes.

## Procedure

1. **Load and extract.** Read plan.md fully, then change.md, research.md, frame.md and the
   lessons whose "Applies to" touch the plan's paths. Pull out: the goal and its measurable
   outcome, out of scope, the starting point, each phase (files, steps, contracts, tests,
   criteria), the key decisions, the risks, and `## Progress`.

2. **Check the plan against itself.** These scans are cheap and often find the most valuable
   defects: things the author discovered but did not follow through on.
   - **Contradiction:** the starting point or a critical detail names a limitation that a phase
     relies on anyway; an out-of-scope item reappears in a phase; a key decision says one thing
     and a step does another.
   - **Promise gap:** every capability in `## Goal` and every risk mitigation has a phase or a
     step that builds it.
   - **Contract breaks:** follow the data across steps and phases. If step B needs an id, a
     token, a column or an event from step A, does A produce it, in that shape? If the plan
     renames or reshapes anything other code or other clients consume (an API field, an
     event, a public route, a file format), is it flagged as breaking, with a migration path?
     Flag every place where the implementer would have to guess (which endpoint, which table,
     which time zone).
   - **Progress mechanics:** one `## Progress`, last; titles identical to the phases; one item
     per Done-when bullet; no checkboxes elsewhere; gates item last in each phase
     (`softure-plan/references/progress-format.md`). A defect is CRITICAL: softure-implement
     resumes from this section.

3. **Ground it in the repository.** For every file, function, table, column and command the
   plan names, verify it exists and behaves as the plan assumes (Glob, Grep, Read). Commands
   must match `workflow.json`. A plan built on a misread file is the most common critical
   defect. Record one grounding line for the review, for example
   `Grounding: 9/9 paths, 6/7 symbols (findInvoiceById missing), 3/3 commands`. A miss becomes
   a finding; a full match needs no more than the line.

4. **Verify the riskiest claims (deep mode).** Pick the 3-5 claims that would force the most
   rework if wrong (an assumed behaviour of a library or job runner, "nothing else calls this",
   "this table is small", "the module covers it"). Hand them to one read-only subagent, or one
   per phase for a large plan, with a focused brief: the claims, the paths, and three tasks:
   - confirm or contradict each claim with `path:line` evidence;
   - **blast radius:** find callers, importers and consumers of everything the plan modifies
     that the plan does not mention;
   - **existing patterns:** where the plan introduces a new pattern, find whether the touched
     area already solves it another way.

   A focused brief finds more than "review this plan". Check surprising answers yourself.

5. **Walk the review lenses.** Each lens ends with PASS, WARN or FAIL, and findings only for real
   issues. The questions and a typical finding per lens are in `references/lenses.md`: read it
   during the first reviews in a repo and whenever a lens feels thin.
   - **Coverage and end state:** finishing all phases achieves change.md Intent; no criterion
     set that passes while the goal is unmet; no "last mile" left; every roadmap Unknown and
     research risk has a phase or a mitigation.
   - **Slicing:** every phase leaves the system green and deployable; no horizontal layers.
   - **Verifiability:** every criterion checkable by someone else; no unmeasured "works",
     "looks good", "handles errors".
   - **Data and migrations:** order, locking on large tables, restartable backfill, rollback or
     justified forward-only, a real-row criterion, collisions with other in-flight changes.
   - **Tests:** right discipline, named edge cases, the user-visible outcome covered end to end.
   - **Security:** authorisation on every new entry point, validated input, no secrets in code,
     safe error messages.
   - **Lean:** the removal test per phase and step; no premature abstraction or "while we are
     here" work.
   - **Fit:** no second way of doing what the codebase already does; sane dependency direction;
     shared utilities listed with their callers; no vague "update accordingly" steps.
   - **Cost and defaults:** paid calls, emails and compute at expected volume; changed defaults
     that silently alter behaviour.
   - **Scope:** nothing beyond change.md; Constraints and files owned by other changes respected.
   - **Reuse:** SOFTURE modules (WORKFLOW.md §10) and existing helpers used, not rebuilt.
   - **Lessons:** every matching lesson followed. A finding that repeats a known lesson weighs
     more, not less: the team has paid for it before.
   - **Progress format:** the result of the mechanics check in step 2.

6. **Grade every finding.**
   - **Severity** (how bad if ignored):
     - **CRITICAL:** implementing as written fails the Intent, loses data, opens a security
       hole, or cannot be verified.
     - **WARNING:** likely rework, a fragile step, or a missing test or rollback.
     - **SUGGESTION:** a clear improvement that is cheap now.
   - **Effort** (how much thought the decision needs, independent of severity): **low** (obvious,
     narrow fix), **medium** (a real trade-off or a non-trivial edit), **high** (wide blast
     radius or no clear best path). A CRITICAL with low effort is cheap; a WARNING with high
     effort deserves time.
   - **Fix:** default to one. Offer two only when each has an upside the other lacks (patch
     the symptom versus remove the class of problem); never invent a weak second option. For
     medium and high effort, give each option its strength, trade-off, confidence (high,
     medium or low, with why) and blind spot (what is not verified). Mark one `(Recommended)`.
   - Be specific (a path, a line, the consequence), and separate "will not work" (CRITICAL)
     from "could be better". Cap the review at about 10 findings by consolidating related ones.

7. **Set the verdict.**
   - **ready:** every lens PASS, or only SUGGESTIONs.
   - **ready after fixes:** findings exist and every CRITICAL and WARNING is decided, CRITICALs
     by an applied fix.
   - **back to plan:** the approach itself is wrong or most lenses FAIL; patching would rewrite
     the plan. Name the finding softure-plan must address.
   - **back to research:** the plan rests on a fact that turned out false or unknown. Name the
     question research must answer.

8. **Present the review.** Plain text, CRITICAL first, empty groups omitted, PASS lenses only in
   the lens table; each finding opens with its id and title alone, then labelled lines
   (severity as a word, effort, lens, where, problem, fix). Then ask: Triage now (Recommended) /
   Save and triage later. "Later" writes the review with `**Decision:** pending` on the open
   findings and keeps `status: planned`; a re-run resumes it.

9. **Triage, one finding at a time,** in severity order. Show the finding and offer:
   - **Apply the fix** (or Fix A / Fix B): show the exact plan edit, before and after, then
     apply it;
   - **Fix differently:** take the user's approach, apply it;
   - **Accept risk:** record the risk, why it is acceptable, and who accepted it;
   - **Defer:** record where it goes (backlog file, follow-up change, roadmap item);
   - **Dismiss:** not an issue; record the user's reason.

   Recommend one. Keep momentum: the user has read the review, so take the decision and move
   on. For a CRITICAL accepted or dismissed against your recommendation, state the consequence
   once in one sentence, then record the user's decision. Apply SUGGESTIONs you agree with
   directly and list them in the summary. Update the review file after every decision.

10. **Apply the fixes to plan.md.** Minimal, targeted edits: fix the defect, keep the author's
    structure. Keep `## Progress` consistent with the phases. Before implementation starts,
    items may still be renumbered; after a re-plan, done items stay untouched.

11. **Write `reviews/plan-review.md`** using the template below, in the `workflow.json` language.
    A complete worked review, a triage exchange and good versus bad findings:
    `references/review-example.md`.

12. **Update `change.md`.** Set `status: plan_reviewed`, but only when no finding is pending and
    no CRITICAL finding remains with a decision other than "Fix now (applied)". With verdict
    `back to plan` or `back to research`, keep `status: planned` and name the step to redo.

13. **Report:** counts per severity, the decisions (fixed, accepted, deferred, dismissed), the
    verdict before and after triage, and the next step.

## Output template

```markdown
# Plan review: <change-id>

Reviewed: plan.md @ <date>. Mode: <deep | quick>. Verdict: <ready | ready after fixes | back to plan | back to research>.
Findings: <n> critical, <n> warning, <n> suggestion.
Grounding: <n/n paths, n/n symbols, n/n commands>

## Lenses
| Lens | Result |
| --- | --- |
| Coverage and end state | PASS |
| Data and migrations | FAIL (C1) |
| ... | ... |

## Findings

### C1 [CRITICAL] <title>
**Effort:** high. **Lens:** Data and migrations. **Where:** Phase 2, step 3 (plan.md) · `src/x.ts:40`
**Problem:** <what is wrong, with evidence>
**Fix A (Recommended):** <approach>. Strength: ... Trade-off: ... Confidence: high, <why>. Blind spot: ...
**Fix B:** <approach>. Strength: ... Trade-off: ... Confidence: medium, <why>. Blind spot: ...
**Decision:** Fix now (applied, Fix A) - <what changed in plan.md>

### W1 [WARNING] <title>
**Effort:** low. **Lens:** ... **Where:** ...
**Problem:** ...
**Fix:** <one line>
**Decision:** Accept risk - <why acceptable; accepted by owner|auto>

### S1 [SUGGESTION] <title>
...
**Decision:** Defer - <where it goes>

## Triage summary
Fixed: C1, S1. Accepted: W1. Deferred: -. Dismissed: -. Verdict after triage: ready after fixes.

## Decisions (auto)
<only in --auto>
```

Allowed decisions: `Fix now (applied[, Fix A|B])`, `Accept risk`, `Defer`, `Dismiss`, and
`pending` only in a review saved for later.

## Status transitions

- `planned` → `plan_reviewed` when nothing is pending and nothing CRITICAL remains open.
- Otherwise `status` stays `planned` and the report says why and which step comes next.

## `--auto`

- Do not ask; never save for later. Decide each finding yourself:
  - CRITICAL and WARNING findings with a clear fix → **Fix now**; with two fixes, the
    recommended one;
  - SUGGESTION → Fix now when it is cheap, otherwise Defer;
  - **Accept risk** only when the fix would contradict change.md Constraints;
  - **Dismiss** only when the deep verification produced evidence that the finding is a false
    positive; cite it.
- Record each decision under `## Decisions (auto)` as `- <finding id> <title> → <decision>
  (<reason>)`.
- `--quick` is ignored in `--auto`: autonomous runs always do the deep verification.
- Escalate when a CRITICAL finding needs an owner decision (scope, business rule, data
  deletion). With verdict `back to plan` or `back to research`, stop with status `planned`
  and name the step to redo; the orchestrator reads that finding before re-running.

## Quality checklist

- [ ] The internal consistency scans (contradiction, promise gap, contract breaks, Progress
      mechanics) were run.
- [ ] Every named file, symbol, table and command was verified in the code; the grounding line
      is in the review.
- [ ] In deep mode, the riskiest claims, the blast radius and existing patterns were checked.
- [ ] Every lens has a result; findings exist only for real issues.
- [ ] Every finding has a severity, an effort, evidence, a fix and a decision.
- [ ] Accepted fixes are actually applied to plan.md, and Progress is still consistent.
- [ ] No CRITICAL finding is open and nothing is pending while the status is `plan_reviewed`.

## Anti-patterns

- Reviewing prose instead of checking the plan against the code.
- Leaving findings without decisions ("consider...", "might want to...").
- Inflating style nits to WARNING, or hiding a real risk as a SUGGESTION.
- Manufacturing findings, or a second fix option, to look thorough.
- Arguing with the user after they decided. State the consequence once, then record.
- Rewriting the whole plan. Fix the defects and keep the author's structure.
- Approving a plan whose criteria cannot be checked.

## Handoff

- Verdict ready or ready after fixes: `softure-implement <change-id>`, starting at phase 1 (or
  at the first open Automated item after a re-plan).
- Back to plan: `softure-plan <change-id>`, focused on the named finding.
- Back to research: `softure-research <change-id>`, focused on the named question.
- Review saved for later: `softure-plan-review <change-id>` resumes the triage.
