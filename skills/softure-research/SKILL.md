---
name: softure-research
description: >
  Investigate the codebase for an open change and write context/changes/<id>/research.md:
  how things work today, which files, tests and data the change touches, what earlier
  changes decided, risks, which SOFTURE modules already cover the need, and answers to every
  unknown. Fans out read-only subagents with distinct roles and keeps the synthesis itself.
  Use after softure-new and before planning, and again for follow-up questions on the same
  change. Triggers: "research the change", "investigate <id>", "/softure-research",
  "investigate the code before planning", "how does X work today".
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
  `softure-new` first. If the folder sits under `context/archive/`, refuse: archived changes are
  history; open a new change instead. If the status is later than `preparing`, warn that research
  is being redone and continue only when the user confirms (in `--auto`: continue and record it).
- If `roadmap_item` is set, read its block in `context/foundation/roadmap.md`. Its **Unknowns**
  are mandatory questions for this research.
- `context/foundation/lessons.md`, when present. Note the lessons whose "Applies to" overlaps
  this change, and use them as priors: an accepted rule narrows what is worth re-investigating.
- Every file named in change.md or in the request (ticket, spec, JSON sample): read it **fully,
  yourself, before** fanning out. Subagents get a better brief when you already know the input.

## Procedure

1. **Frame the questions.** List what must be known to plan: the Intent, every roadmap
   Unknown, and the implicit questions (where is it implemented, who calls it, what data does it
   read and write, how is it tested, what breaks if it changes, what did earlier changes decide
   here). Pick the depth:
   - `quick`: one area, under about 10 files.
   - `normal`: the default.
   - `deep`: money, data migrations, auth, concurrency, or anything irreversible.

2. **Settle scope when it is ambiguous** (interactive only; skip when change.md and the
   Unknowns pin it). Ask **one question at a time**, at most two, each with 2 to 4 concrete
   options, a one-line consequence each, recommendation first: *Depth* (map of entry points /
   full flow with failure modes) and *Focus* (data and migrations / integration points / history
   of earlier decisions / performance). `--auto`: no question; depth from the risk profile, focus
   from the Intent and Unknowns, both recorded under `## Decisions (auto)`.

3. **Fan out for breadth.** Split the questions into 2 to 4 independent areas (never more than
   5) and launch read-only subagents for them **in one message**, so they run in parallel. Give
   each a distinct role: *locator* (where things live), *flow tracer* (one path end to end),
   *history miner* (earlier changes, archive, git log on the hot files), *data and test scout*.
   Each brief carries one area, the verbatim Intent, the `path:line` rule, a word limit and
   "facts only, no proposals". Roles and a brief template: read `references/fan-out.md` **when
   you launch subagents**. If the harness has a task list, add one task per area.

4. **Synthesize yourself.** Wait for **all** subagents. Live code beats historical documents
   (say so when they disagree); read disputed lines yourself; spot-check every surprise. Do not
   delegate conclusions.

5. **Go deep where it matters.** Read the central files yourself. Trace one real request or
   flow end to end, from entry point through logic and data to response or UI. When the change
   touches data, look at the schema and migrations, and at real data shape if a safe read-only
   path exists (a dev DB, fixtures). Never write to a database during research.

6. **Map the tests.** Find which tests cover the affected code (unit, integration, e2e), how to
   run them, and where coverage is missing. Note flaky or slow suites.

7. **Check SOFTURE modules first** (WORKFLOW.md §10). If the change needs a generic capability,
   check the `@softure-ai/*` catalog. Generic capabilities include auth, sessions, roles, feature
   switches, mail, unsubscribe, waitlist, MCP tokens, billing/trial, GDPR, consent, channel
   analytics, health and UI primitives. Record one of three outcomes:
   - **covered:** module and configuration needed;
   - **partially covered:** module plus the gap, to be filed as an issue in SOFTURE/AI;
   - **not applicable.**

8. **Assess risks.** Cover data loss, migrations and rollback, backwards compatibility,
   performance, security (authz, input validation, secrets), concurrency, and other in-flight
   changes touching the same files (check `context/changes/*/change.md` Constraints).

9. **Resolve open questions.** Each question ends in one of three states:
   - **answered**, with evidence;
   - **decided**, with the decision, the reason, and who decided (owner, or auto);
   - **escalated**, meaning it blocks planning, with the exact question and its options.

   A research document with unanswered questions and no escalation is unfinished.

10. **Write `research.md`** using the template below, in the `workflow.json` language. Capture
    the snapshot first (`git rev-parse --short HEAD`, current branch, date in
    `workflow.json` → `timezone` when set). No placeholder values: a field you cannot fill is a
    finding, not a blank.

11. **Update `change.md`.** Set `status: preparing` and update `updated`.

12. **Report** a five-line summary: key findings, risks, module verdict, escalations, next step.

## Follow-up questions

Do not rewrite the document. Append `## Follow-up <YYYY-MM-DD>: <question>` with its own
evidence, fan out only for the new area, correct earlier sections only when the follow-up proved
them wrong (dated), and update `updated` in change.md.

## Output template

```markdown
# Research: <change-id>

Input: change.md[, roadmap <ID>][, research.sources]. Depth: <quick|normal|deep>.
Snapshot: <short sha> on <branch>, <YYYY-MM-DD HH:MM zone>.

## Summary
<5-8 lines a planner can act on>

## Current state
<how it works today, end to end, with path:line references>

## Affected surface
| Area | Files | Why |
| --- | --- | --- |

## Data
<tables, columns, migrations, real data shape, invariants, or "none">

## Tests
<what covers it, how to run, gaps>

## Patterns to follow
<conventions the code already uses here that the plan must match, with an example path:line>

## Prior work
<earlier changes, archived research or plans, commits that decided something here; path + one line each, or "none found">

## SOFTURE modules
<covered / partially covered (gap -> issue) / not applicable, with reasoning>

## Risks
<each: what can go wrong, likelihood, mitigation idea>

## Relevant lessons
<L-NNN: why it applies>

## Answers to unknowns
<each roadmap unknown and implicit question -> answer with evidence>

## Open questions
<each: answered / decided (by whom, why) / escalated (exact question + options)>

## Decisions (auto)
<only in --auto>
```

A complete realistic example, and a bad one with what is wrong with it: read
`references/example-research.md` **before writing your first research.md in a repo**, or when
unsure how much detail a section needs.

## Status transitions

- `new` (or `preparing`) -> `preparing`.

## `--auto`

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

- No scope question (step 2). Choose the depth from the risk profile. Use `deep` whenever money,
  data migration, auth or deletion is involved.
- Resolve questions by evidence first, then by the safer option. Record each choice under
  `## Decisions (auto)`.
- Escalate (stop, do not plan) only when a question changes the scope of change.md or requires
  an owner-only fact such as a business rule, credentials or legal text.

## Quality checklist

- [ ] Every factual claim has `path:line` or another concrete evidence pointer.
- [ ] Every roadmap Unknown is answered, decided or escalated.
- [ ] Tests that will prove the change are identified, with the command to run them.
- [ ] The SOFTURE module verdict is explicit.
- [ ] Prior work was searched (`context/changes/`, `context/archive/`, git log), even if nothing was found.
- [ ] Collisions with other in-flight changes have been checked.
- [ ] The snapshot line names a real commit; no placeholders anywhere.
- [ ] The document contains no implementation plan, only options and facts.

## Anti-patterns

- Summarising file names without reading them ("`auth.ts` handles auth").
- Copying subagent output unverified. Spot-check every surprising claim yourself.
- Subagents with overlapping roles, or synthesis started before all of them returned.
- Treating an archived plan as the current state. History explains, code decides.
- Proposing the solution and calling it research.
- Writing to the database or changing code "to check something".
- Leaving an "Open questions" list with nothing marked as resolved or escalated.

## Handoff

- If the problem itself looks wrong or underspecified: `softure-frame <change-id>`.
- Otherwise: `softure-plan <change-id>`.
