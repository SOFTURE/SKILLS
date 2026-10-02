---
name: softure-plan
description: >
  Turn research into an executable, phased plan: context/changes/<id>/plan.md with an
  explicit approach, key decisions, thin verifiable phases (each TDD or test-after, with
  files, intent and contract per step, and done-when criteria) and a canonical ## Progress
  section. Interviews the user one question at a time with a recommended answer, confirms
  the phase outline, and can refine or re-plan an existing plan. Use after softure-research
  (or softure-frame) and before implementation. Triggers: "plan the change", "write the
  plan", "/softure-plan", "break it into phases", "re-plan the remaining phases",
  "refine the plan".
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

The plan tells the implementer **what to change and why**, not how to type it. It is written
for someone who was not in the conversation: they must understand every choice from the file
alone.

## Required inputs

- `context/workflow.json`: if missing, run `softure-init` first.
- `context/changes/<id>/change.md` with `status: preparing`. If the status is `new`, run
  `softure-research` first. Other statuses: see "Existing plan" below.
- `context/changes/<id>/research.md`: if missing, run `softure-research` first. If research has
  an **escalated** open question that is still unanswered, stop and surface it.
- `frame.md`, when present. Its conclusions override change.md wording.
- `context/foundation/lessons.md`, when present.

## Resolve the input

- **No argument:** list `context/changes/*/change.md` with status `preparing` (and `planned`,
  for refining), newest `updated` first, and ask which one. In `--auto` an id is mandatory:
  stop and say so.
- **A path under `context/archive/`:** refuse. Say the change is archived and a new one is
  opened with `softure-new`.
- **Existing plan.md**, by change.md status:
  - `preparing`: an unfinished draft from an earlier session. Read it, continue where it
    stops, and do not re-ask what it already decides.
  - `planned` or `plan_reviewed`: **refine mode.** Read plan.md and `reviews/plan-review.md`
    (if any), change only what the request or the review asks for, keep the structure and the
    Progress numbering. Set the status back to `planned` so the change is reviewed again.
  - `implementing`: **re-plan mode** (sent here by softure-implement or plan-review). Done
    phases and their ticked Progress items stay untouched. Rewrite only the remaining phases.
    Follow the mid-flight rules in `references/progress-format.md` (new items take the next
    free number, obsolete items are marked dropped). Set the status to `planned`.
  - `implemented` or later: do not touch the plan. Point to softure-impl-review or a new change.

## Procedure

1. **Read everything yourself, fully, before asking or delegating.** change.md, research.md,
   frame.md, lessons.md, workflow.json, and any earlier plan in `context/changes/` or
   `context/archive/` that touched the same files. Research's current state and affected
   surface are your codebase baseline: do not re-search what it already mapped. Lessons whose
   "Applies to" matches are priors: they settle design pitfalls without a question.
   Use read-only subagents only for **gaps** research left (for example, the exact call sites
   of a function the plan will change). Give each a focused question with paths, ask for
   `path:line` evidence, and check surprising answers against the code yourself.

2. **Play back what you understood, then assess complexity.** In a few lines: what must be
   true at the end, the two or three discoveries that shape the plan (with `path:line`), and
   the edge cases you already see. Then state the complexity with its reasons (systems
   touched, data changes, integration points, unknowns, test surface):
   - `small`: 1 phase, a handful of files, follows an existing pattern;
   - `medium`: 2-3 phases, design decisions with real trade-offs;
   - `large`: 4+ phases, cross-cutting or data-heavy. This is a smell: propose splitting the
     change and say where the cut would go.

   Interactive: confirm in one question (Agree / It is bigger / It is smaller). `--auto`: take
   your own assessment and record it.

3. **Probe the gaps, one question at a time.** Ask only about ambiguities whose answer changes
   the plan. Each question offers 2-4 concrete options, the recommended one first and marked
   `(Recommended)`, each with one line of what it means, its strength and its trade-off. The
   recommendation is grounded in research or the code, never a guess. Stop as soon as answers
   stop changing the plan.
   - **Budget** (a ceiling, not a quota): research only: small 2-4, medium 4-7, large 6-10.
     Research plus frame: small 1-2, medium 2-4, large 4-6, and no questions about the
     problem itself, because frame settled it.
   - **Never ask** what change.md, research, frame or lessons already answer, implementation
     details you can read from the code (patterns, error handling, test setup), or
     preferences that do not change the plan.
   - **Push back.** When the user corrects a fact, verify it in the code before accepting it;
     if the code disagrees, show the evidence and ask again. When an answer contradicts
     change.md Constraints or grows the scope, say so and offer: keep the scope, or record
     the extension in change.md first. When the user picks a costlier option, state the cost
     once, then follow their choice.
   - Question categories, the budget table and worked examples:
     read `references/questioning.md` when preparing the questions.

   `--auto`: ask nothing. Take the recommended option for every question you would have asked
   and record each as `- <question> → <choice> (<reason>)` under `## Decisions (auto)`.

4. **Choose the approach.** Write 2-3 viable options. For each give a one-line description, its
   cost, its risk and its reversibility. Recommend one and say why.
   - If a SOFTURE module covers the capability (research §SOFTURE modules), the module-based
     option is the default. Re-implementing a covered capability needs an explicit reason.
   - Interactive: ask only when the choice genuinely matters and the code does not decide it.
     When one option clearly wins, state it and why, and move on.
   - Record every decision that shapes the plan in the **Key decisions** table, with its
     source (change, research, frame, owner, plan), so a later reader sees what was settled
     upstream and what was decided here.

5. **Slice into phases and confirm the outline.** Each phase is a **thin, independently
   verifiable increment** that leaves the system working: green gates, deployable. Prefer
   vertical slices (data, logic and UI for one behaviour) over horizontal layers. Useful
   orders *inside* a slice:
   - data change: migration, data access, domain logic, entry point (route, action, job), UI;
   - new behaviour: the rule as a pure function under test first, then the wiring;
   - refactor: pin current behaviour with characterisation tests, change in small steps,
     keep old callers working, remove the old path last.

   Interactive: print the outline (one line per phase: what it delivers) and ask: Looks right
   (Recommended) / Adjust / Merge phases (too granular) / Split phases (too coarse). `--auto`:
   keep your outline.

6. **Write each phase.**
   - **Discipline:**
     - `TDD` for logic with clear inputs and outputs (calculations, money, parsing, state
       machines, migrations with invariants, security rules);
     - `test-after` for UI wiring, copy and layout.
   - **Files:** the paths to create or modify, taken from research.
   - **Steps:** concrete and ordered. Each step names its file and states its **intent** (what
     changes and why, in one or two sentences) and, when other steps depend on it, its
     **contract** (signature, schema column, route, event, invariant). Name the functions,
     components, tables and commands. **No code by default.** Add a short snippet only when the
     change is non-obvious: a tricky query, an unusual API call, an ordering that looks wrong
     but is not, a workaround for a known bug.
   - **Tests:** the named cases, including empty, boundary and failure paths.
   - **Done when:** criteria phrased so that someone else could check them, as plain bullets
     (checkboxes live only in `## Progress`). Split them into *Automated* (a command, a test,
     a query) and *Manual* (only a human can judge it, such as visual quality or tone).
   - The last automated criterion of every phase is "Gates green (typecheck, lint, test)", using
     the gates from `workflow.json`. Never write the commands themselves into the plan from
     memory: take them from `workflow.json`.

7. **Plan data safety.** For any schema or data change, include:
   - the migration (in the `workflow.json` migrations folder, when configured);
   - its rollback path, or an explicit "forward-only, because...";
   - a backfill when needed, restartable when the table is large;
   - a criterion that reads real rows. A rendered UI never proves data was written.

8. **Add critical details only when they exist.** Under `## Approach`, an optional
   **Critical details** block holds what the implementer must know before touching the code
   and cannot see from the paths: a non-obvious ordering or race, a time-zone or rounding rule,
   a performance budget with a number, a state change whose obvious order is wrong. One to
   three sentences each. No templated bullets: a plan without this block is not incomplete.

9. **Write risks and rollback.** List what can fail in production and how to undo each phase.

10. **Remove open questions.** Search your draft for "TBD", "maybe", "or", "?" and "decide
    later". Resolve each one, or move it back to research as an escalation and stop.

11. **Write the Progress section** exactly per `references/progress-format.md`: one
    `### Phase N:` per `## Phase N:`, and every Done-when criterion as a numbered checkbox.

12. **Write `plan.md`** in the `workflow.json` language, using the template below, then run the
    quality checklist against it. A complete worked example (and a bad one, with why):
    `references/plan-example.md`, read it before writing your first plan in a repo.

13. **Update `change.md`.** Set `status: planned` and update `updated`.

14. **Report and iterate.** Give: the approach in one line, a phases-at-a-glance table
    (`| Phase | Delivers | Key risk |`), the decisions taken, the riskiest phase, and the next
    step. Interactive: ask what to adjust (phase scope, criteria precision, missing edge
    cases, scope items) and apply the changes until the user is satisfied. `--auto`: no
    iteration; report and hand off.

If the session gets long, write the draft to plan.md early (status stays `preparing`). A fresh
`softure-plan <id>` picks it up as a draft.

## Output template

```markdown
# Plan: <change-id>

Input: change.md, research.md[, frame.md]. Complexity: <small|medium|large>.

## Goal
<the outcome from change.md, made measurable: what a user can do, what is true in the data>

**Out of scope:** <what this change deliberately does not do, so phases cannot drift into it>

## Approach
**Starting point:** <how it works today, 2-4 lines from research, with path:line>

**Chosen:** <option> - <why>.
Rejected: <option> - <one line>; <option> - <one line>.

**Key decisions:**
| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| <area> | <choice> | <one sentence> | research / frame / owner / plan |

**Critical details:** <optional; only real constraints>

## Phase 1: <title>
**Discipline:** TDD | test-after. **Files:** `a.ts`, `b.tsx`, `migrations/00NN_x.sql`

1. `path/a.ts`: <intent>. Contract: <signature / column / route>.
2. `path/b.tsx`: <intent>.

**Tests:** <named cases>

**Done when:**
- Automated: <criterion>; Gates green (typecheck, lint, test).
- Manual: <criterion>.

## Phase 2: <title>
...

## Risks and rollback
<risk → mitigation; how to revert each phase>

## Decisions (auto)
<only in --auto>

## Progress
<per references/progress-format.md>
```

`## Goal`, `## Approach`, `## Phase N:`, `## Risks and rollback`, `## Decisions (auto)` and
`## Progress` are the fixed headings from WORKFLOW.md §6. Everything else is a bold label inside
them, never an extra `##` heading.

## Status transitions

- `preparing` → `planned` (new plan).
- `plan_reviewed` → `planned` (refine mode: the change is reviewed again).
- `implementing` → `planned` (re-plan mode: the remaining phases are reviewed before
  implementation resumes at the first open Automated item).

## `--auto`

- Skip every confirmation (complexity, approach, outline, final iteration). Take the
  recommended option for every probing question and record it under `## Decisions (auto)` as
  `- <question> → <choice> (<reason>)`.
- Prefer the smallest reversible approach. Prefer TDD whenever the discipline is in doubt.
- Never stop to ask for an id: without one, stop and report.
- Stop and escalate when the only viable approach contradicts change.md Constraints, requires a
  destructive data operation, or needs an owner-only decision.

## Quality checklist

- [ ] Every phase leaves the system green and deployable.
- [ ] Every criterion is checkable by someone who did not write it.
- [ ] Every phase states its discipline, lists its files and names its test cases.
- [ ] Every step names a file and an intent; contracts are stated where other steps depend on
      them; code appears only where it is non-obvious.
- [ ] Data changes have migration, rollback (or a justified forward-only) and a real-data check.
- [ ] The SOFTURE module verdict from research is honoured, or overridden with a reason.
- [ ] Every capability promised in `## Goal` has a phase that builds it, and nothing listed as
      out of scope appears in a phase.
- [ ] The Key decisions table names a source for every decision.
- [ ] The plan contains no open questions.
- [ ] Phase blocks have no checkboxes; `## Progress` matches the phases one-to-one and follows
      the reference format.

## Anti-patterns

- Horizontal phases ("Phase 1: all DB, Phase 2: all API, Phase 3: all UI"). Nothing works until
  the end.
- Criteria like "works correctly" or "looks good". Say what is measured and how.
- A plan that re-decides what research already established, or ignores a relevant lesson.
- Asking the user what the code, research or frame already answers; padding the interview to
  reach a number.
- Accepting a user's factual correction without checking the code.
- Hiding design work in a step ("figure out the caching strategy").
- Pre-writing the code: pages of snippets for routine edits that follow an existing pattern.
- A filled-in "Critical details" block full of generic advice ("use memoization").
- More than about 6 phases without proposing to split the change.

## Handoff

Next: `softure-plan-review <change-id>`.
