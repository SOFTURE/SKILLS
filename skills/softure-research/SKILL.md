---
name: softure-research
description: >
  Investigate the codebase for an open change and write context/changes/<id>/research.md:
  how things work today, which files, tests and data the change touches, risks, which
  SOFTURE modules already cover the need, and answers to every unknown. Use after
  softure-new and before planning. Triggers: "research the change", "investigate <id>",
  "/softure-research", "investigate the code before planning".
argument-hint: "<change-id> [--depth quick|normal|deep] [--focus \"area\"] [--auto]"
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

# softure-research: understand before deciding

Research turns "what we want" (change.md) into "what is actually there". The plan is only as
good as this document. Every claim here must point at evidence (`path:line`, a query result, a
command output), so a planner can trust it without re-reading the code.

## Required inputs

- `context/workflow.json`: if missing, run `softure-init` first. If it lists `research.sources`, read those too
  (docs, PRD, notes) before the codebase sweep, and cite them like code.
- `context/changes/<id>/change.md` with `status: new` or `preparing`: if missing, run
  `softure-new` first. If the status is later than `preparing`, warn that research is being
  redone and continue only when the user confirms (in `--auto`: continue and record it).
- If `roadmap_item` is set, read its block in `context/foundation/roadmap.md`. Its **Unknowns**
  are mandatory questions for this research.
- `context/foundation/lessons.md`, when present. Note the lessons whose "Applies to" overlaps
  this change.

## Procedure

1. **Frame the questions.** List what must be known to plan: the Intent, every roadmap
   Unknown, and the implicit questions (where is it implemented, who calls it, what data does it
   read and write, how is it tested, what breaks if it changes). Pick the depth:
   - `quick`: one area, under about 10 files.
   - `normal`: the default.
   - `deep`: money, data migrations, auth, concurrency, or anything irreversible.

2. **Fan out for breadth.** For independent questions, launch parallel **read-only** subagents
   (Explore-type, or general-purpose told not to edit). Each subagent gets:
   - one question or area;
   - the instruction to cite `path:line` for every claim;
   - a word limit;
   - the instruction to report facts, not proposals.

   Keep the synthesis yourself. Do not delegate conclusions.

3. **Go deep where it matters.** Read the central files yourself. Trace one real request or
   flow end to end, from entry point through logic and data to response or UI. When the change
   touches data, look at the schema and migrations, and at real data shape if a safe read-only
   path exists (a dev DB, fixtures). Never write to a database during research.

4. **Map the tests.** Find which tests cover the affected code (unit, integration, e2e), how to
   run them, and where coverage is missing. Note flaky or slow suites.

5. **Check SOFTURE modules first** (WORKFLOW.md §10). If the change needs a generic capability,
   check the `@softure-ai/*` catalog. Generic capabilities include auth, sessions, roles, feature
   switches, mail, unsubscribe, waitlist, MCP tokens, billing/trial, GDPR, consent, channel
   analytics, health and UI primitives. Record one of three outcomes:
   - **covered:** module and configuration needed;
   - **partially covered:** module plus the gap, to be filed as an issue in SOFTURE/AI;
   - **not applicable.**

6. **Assess risks.** Cover data loss, migrations and rollback, backwards compatibility,
   performance, security (authz, input validation, secrets), concurrency, and other in-flight
   changes touching the same files (check `context/changes/*/change.md` Constraints).

7. **Resolve open questions.** Each question ends in one of three states:
   - **answered**, with evidence;
   - **decided**, with the decision, the reason, and who decided (owner, or auto);
   - **escalated**, meaning it blocks planning, with the exact question and its options.

   A research document with unanswered questions and no escalation is unfinished.

8. **Write `research.md`** using the template below, in the `workflow.json` language.

9. **Update `change.md`.** Set `status: preparing` and update `updated`.

10. **Report** a five-line summary: key findings, risks, module verdict, escalations, next step.

## Output template

```markdown
# Research: <change-id>

Input: change.md[, roadmap <ID>]. Depth: <quick|normal|deep>.

## Summary
<5–8 lines a planner can act on>

## Current state
<how it works today, end to end, with path:line references>

## Affected surface
| Area | Files | Why |
| --- | --- | --- |

## Data
<tables, columns, migrations, real data shape, invariants — or "none">

## Tests
<what covers it, how to run, gaps>

## SOFTURE modules
<covered / partially covered (gap → issue) / not applicable — with reasoning>

## Risks
<each: what can go wrong, likelihood, mitigation idea>

## Relevant lessons
<L-NNN: why it applies>

## Answers to unknowns
<each roadmap unknown and implicit question → answer with evidence>

## Open questions
<each: answered / decided (by whom, why) / escalated (exact question + options)>

## Decisions (auto)
<only in --auto>
```

## Status transitions

- `new` (or `preparing`) → `preparing`.

## `--auto`

- Choose the depth from the risk profile. Use `deep` whenever money, data migration, auth or
  deletion is involved.
- Resolve questions by evidence first, then by the safer option. Record each choice under
  `## Decisions (auto)`.
- Escalate (stop, do not plan) only when a question changes the scope of change.md or requires
  an owner-only fact such as a business rule, credentials or legal text.

## Quality checklist

- [ ] Every factual claim has `path:line` or another concrete evidence pointer.
- [ ] Every roadmap Unknown is answered, decided or escalated.
- [ ] Tests that will prove the change are identified, with the command to run them.
- [ ] The SOFTURE module verdict is explicit.
- [ ] Collisions with other in-flight changes have been checked.
- [ ] The document contains no implementation plan, only options and facts.

## Anti-patterns

- Summarising file names without reading them ("`auth.ts` handles auth").
- Copying subagent output unverified. Spot-check every surprising claim yourself.
- Proposing the solution and calling it research.
- Writing to the database or changing code "to check something".
- Leaving an "Open questions" list with nothing marked as resolved or escalated.

## Handoff

- If the problem itself looks wrong or underspecified: `softure-frame <change-id>`.
- Otherwise: `softure-plan <change-id>`.
