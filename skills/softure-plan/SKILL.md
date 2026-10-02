---
name: softure-plan
description: >
  Turn research into an executable, phased plan: context/changes/<id>/plan.md with an
  explicit approach, thin verifiable phases (each TDD or test-after, with files, steps
  and done-when criteria) and a canonical ## Progress section. Use after softure-research
  (or softure-frame) and before implementation. Triggers: "plan the change", "write the
  plan", "/softure-plan", "break it into phases".
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

# softure-plan: decide once, execute without guessing

A plan answers *how*. After this step, implementation is execution: no design decisions, no
open questions, no "figure it out later". If a phase cannot be described concretely, research
is not finished.

## Required inputs

- `context/workflow.json`: if missing, run `softure-init` first.
- `context/changes/<id>/change.md` with `status: preparing`. If the status is `new`, run
  `softure-research` first.
- `context/changes/<id>/research.md`: if missing, run `softure-research` first. If research has
  an **escalated** open question that is still unanswered, stop and surface it.
- `frame.md`, when present. Its conclusions override change.md wording.
- `context/foundation/lessons.md`, when present.

## Procedure

1. **Assess complexity.** Base it on research: affected surface, data changes, risk.
   State it as `small` (1 phase), `medium` (2–3) or `large` (4+). Large plans are a smell, so
   consider splitting the change and say so. In interactive mode, confirm the assessment in one
   question.

2. **Probe the gaps.** Ask about ambiguities that change the plan. Ask **one question at a time**,
   at most about 10, and stop as soon as answers stop changing the plan. Each question offers 2–4
   options with the recommended one first, marked `(Recommended)`, and a one-line trade-off for
   each. Never ask what the code or research already answers.

3. **Choose the approach.** Write 2–3 viable options. For each give a one-line description, its
   cost, its risk and its reversibility. Recommend one and say why.
   - If a SOFTURE module covers the capability (research §SOFTURE modules), the module-based
     option is the default.
   - Re-implementing a covered capability needs an explicit reason.

4. **Slice into phases.** Each phase is a **thin, independently verifiable increment** that
   leaves the system working: green gates, deployable. Prefer vertical slices (data → logic →
   UI for one behaviour) over horizontal layers. For each phase write:
   - **Discipline:**
     - `TDD` for logic with clear inputs and outputs (calculations, money, parsing, state
       machines, migrations with invariants, security rules);
     - `test-after` for UI wiring, copy and layout.
   - **Files:** the paths to create or modify, taken from research.
   - **Steps:** concrete and ordered. Name the functions, components, tables and commands.
   - **Done when:** criteria phrased so that someone else could check them. Split them into
     *Automated* (a command, a test, a query) and *Manual* (only a human can judge it, such as
     visual quality or tone).
   - The last automated criterion of every phase is "Gates green (typecheck, lint, test)", using
     the gates from `workflow.json`.

5. **Plan data safety.** For any schema or data change, include:
   - the migration;
   - its rollback path, or an explicit "forward-only, because…";
   - a backfill when needed;
   - a criterion that reads real rows. A rendered UI never proves data was written.

6. **Write risks and rollback.** List what can fail in production and how to undo each phase.

7. **Remove open questions.** Search your draft for "TBD", "maybe", "or", "?" and "decide later".
   Resolve each one, or move it back to research as an escalation and stop.

8. **Write the Progress section** exactly per `references/progress-format.md`: one
   `### Phase N:` per `## Phase N:`, and every Done-when criterion as a numbered checkbox.

9. **Write `plan.md`** in the `workflow.json` language, using the template below.

10. **Update `change.md`.** Set `status: planned` and update `updated`.

11. **Report** the approach in one line, the number of phases, the riskiest phase, and the next
    step.

## Output template

```markdown
# Plan: <change-id>

Input: change.md, research.md[, frame.md]. Complexity: <small|medium|large>.

## Goal
<the outcome from change.md, made measurable>

## Approach
**Chosen:** <option> — <why>.
Rejected: <option> — <one line>; <option> — <one line>.

## Phase 1: <title>
**Discipline:** TDD | test-after. **Files:** `a.ts`, `b.tsx`, `migrations/00NN_x.sql`
1. <step>
2. <step>
**Done when:** <criteria, automated then manual>

## Phase 2: <title>
...

## Risks and rollback
<risk → mitigation; how to revert each phase>

## Decisions (auto)
<only in --auto>

## Progress
<per references/progress-format.md>
```

## Status transitions

- `preparing` → `planned`.

## `--auto`

- Skip confirmations. Take the recommended option for every probing question and record it under
  `## Decisions (auto)` as `- <question> → <choice> (<reason>)`.
- Prefer the smallest reversible approach. Prefer TDD whenever the discipline is in doubt.
- Stop and escalate when the only viable approach contradicts change.md Constraints, requires a
  destructive data operation, or needs an owner-only decision.

## Quality checklist

- [ ] Every phase leaves the system green and deployable.
- [ ] Every criterion is checkable by someone who did not write it.
- [ ] Every phase states its discipline and lists its files.
- [ ] Data changes have migration, rollback (or a justified forward-only) and a real-data check.
- [ ] The SOFTURE module verdict from research is honoured, or overridden with a reason.
- [ ] The plan contains no open questions.
- [ ] `## Progress` matches the phases one-to-one and follows the reference format.

## Anti-patterns

- Horizontal phases ("Phase 1: all DB, Phase 2: all API, Phase 3: all UI"). Nothing works until
  the end.
- Criteria like "works correctly" or "looks good". Say what is measured and how.
- A plan that re-decides what research already established, or ignores a relevant lesson.
- Hiding design work in a step ("figure out the caching strategy").
- More than about 6 phases without proposing to split the change.

## Handoff

Next: `softure-plan-review <change-id>`.
