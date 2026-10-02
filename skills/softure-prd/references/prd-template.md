# PRD templates and section rules

Read this when writing or revising `prd.md`. It holds both templates (greenfield and
brownfield), what each section must and must not contain, and the mapping from shape-notes
sections. Headings are fixed English; the prose is written in `workflow.json` → `language`.

## Frontmatter (both variants)

```yaml
---
project: "<name>"
version: 1
status: draft | accepted
context_type: greenfield | brownfield
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
source: shape-notes.md (session <n>)      # or: <path> (unshaped notes)
---
```

`context_type` comes from the shape-notes frontmatter. Without it (raw notes), detect it the
same way `softure-shape` does and confirm it.

## Greenfield template

```markdown
# PRD v<version>: <theme>

## Summary
- Problem: <the specific pain: who, in what moment, at what cost>
- Insight: <what we understand that today's alternatives miss>
- Who: <primary person>
- Outcome: <what is true for them after the release>
- Appetite: <fixed budget>; deadline: <date or none>
- Product: <web app | API | CLI | mobile | desktop | library | data pipeline | other>;
  expected scale: <a handful | dozens | thousands | more> of users
- Release boundary: <what this release includes, in one line>

## Goals
- G-1: <outcome with a number or a yes/no check>

## Non-goals
- <outcome or quality level we deliberately do not aim for> — <one-line reason>

## Users
- Primary: <role; context; the moment they reach for the product>
- Secondary: <short>
- Not for: <who, and why>

## Access control
<who can do what; roles; sign-up vs invitation; what an unauthenticated visitor sees>

## Primary flow
1. <step> (FR-1)
2. <step> (FR-2)

## Business rules
<Core rule: one declarative sentence.>
<Up to three short paragraphs: the inputs it uses (as the user supplies them), what it
produces, where the user meets it in the flow.>

## Functional requirements
| ID | Requirement (observable behaviour) | Priority | Goal | Module |
|---|---|---|---|---|
| FR-1 | When …, … can … | must | G-1 | @softure-ai/auth |

### FR-1: <short name>
Acceptance:
- Given …, when …, then …
Notes: edge cases, copy constraints, data rules.
Challenge: <strongest counter-argument> → <resolution>

## Non-functional requirements
- NFR-1: <property an outside observer can measure> — <target>

## Success metrics
| Metric | Baseline | Target | How measured | When checked |
|---|---|---|---|---|

### Guardrails
- <what must not get worse, with its current level>

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|

## Out of scope
- <capability not built in this release> — <reason; later | never>

## Open questions
- OQ-1: <question> → owner: <who> → needed by: <date or step> → blocking: yes | no

## Changelog
- v1 <YYYY-MM-DD>: first version from shape-notes session <n>.

## Decisions (auto)      (only in --auto)
```

## Brownfield template

Delta framing: every section describes **what changes** against the current system, not
the whole system. "Invoices can now be created from a schedule, alongside manual creation",
not "The system supports manual and scheduled invoices".

Differences from greenfield:

```markdown
## Summary                 (as greenfield, plus: "Current system: <one line>")

## Current system
- Purpose: <one sentence>
- Shape: <how it is built, at the level of "web app + public API + nightly job">
- Stack: <languages, frameworks, main services>   (the only section that may name them)
- Users today: <roles, rough scale>
- What it does today in the area of this change: <a few lines>

## Users                   (existing users whose experience changes; new users, if any)

## Access control          (changes only; or "No change: current model preserved.")

## Primary flow            (the changed flow; mark new steps "(new)")

## Business rules          (today: <current rule> → change: <new rule>;
                            or "No domain rule change: this is technical work.")

## Functional requirements
| ID | Requirement (observable behaviour) | Change | Priority | Goal | Module |
|---|---|---|---|---|---|
| FR-1 | When …, … can … | new | must | G-1 | — |
| FR-2 | … (was: …) | modified | must | G-1 | — |
| FR-3 | … keeps working exactly as today | preserved | must | G-2 | — |
| FR-4 | … is no longer offered | removed | should | G-1 | — |

## Compatibility and preserved behaviour
- Contracts that must keep working: <public API, exports, URLs, file formats, integrations>
- Existing data: <what happens to it, stated as an outcome: "old invoices keep their numbers">
- Rollout: <who sees the change first; whether the old path stays as a fallback>

### Guardrails             (under Success metrics: always includes the preserved FRs)
```

Brownfield order: Summary, Current system, Goals, Non-goals, Users, Access control, Primary
flow, Business rules, Functional requirements, Non-functional requirements, Compatibility and
preserved behaviour, Success metrics (with Guardrails), Risks, Out of scope, Open questions,
Changelog, Decisions (auto). All other sections are the same as greenfield.

## Section rules

- **Summary.** Facts, not marketing. No "we believe", "we envision", "revolutionary". If the
  insight line cannot be filled, it is an open question, not a slogan.
- **Goals.** Each measurable (a number or a yes/no check). Every goal has at least one FR.
- **Non-goals vs Out of scope.** Non-goals are outcomes and quality levels we do not aim for
  ("no offline use", "no multi-region availability"). Out of scope lists capabilities not
  built in this release, including deferred `could` FRs. Technology avoids ("no PHP") belong
  in neither; they go to the handoff as forward notes. Scope avoids ("we will not build our
  own scheduling algorithm") are non-goals.
- **Users.** One primary person, described by role, context and the moment they reach for
  the product. The release serves the primary person first.
- **Access control.** Always present. For a single-user local tool, one line is enough:
  "Single user; no sign-in; data stays on the device."
- **Primary flow.** The first flow from the shape notes, each step pointing to the FR that
  makes it possible. A step without an FR is a missing requirement.
- **Business rules.** The core rule first, as one sentence. Do not name the component that
  applies the rule ("the model decides", "the database checks"); state the rule as if the
  implementation were unknown. No rule in the input → `TODO: core rule (OQ-n)` and a
  **blocking** open question. Never invent one, and never infer one from the nouns in the
  FRs.
- **Functional requirements.** One observable behaviour each: "When <trigger>, <actor>
  can/sees <result>". IDs `FR-<n>`, never zero-padded, never reused. Group detail blocks
  under `###` theme headings when there are more than about eight. Priorities: `must` (the
  release fails without it), `should`, `could`; roughly 60% of effort or less is `must`.
  Brownfield: every line of "preserved behaviour" from the shape notes becomes a `preserved`
  FR, never a non-goal.
- **Acceptance criteria.** Given/when/then or a short list a tester could run without asking
  the author. Include the empty case and the failure case where they exist.
- **Non-functional requirements.** Only where they matter, each with a target: prefer
  `< N unit` or `≥ N unit`; a binary commitment ("no uploaded file is kept after the
  request") also counts. State what is true at the product's outer boundary, never how it is
  achieved (see `leak-lint.md`).
- **Success metrics.** Metric → baseline → target → how measured → when checked. A metric
  that cannot be measured by something that exists or is planned in an FR is not a metric.
- **Open questions.** Numbered `OQ-<n>`, each with owner, needed-by and blocking flag. Mark
  `blocking: yes` when the answer changes a `must` FR or the core rule.

## What a PRD never contains

- Data model sections, table or column lists, entity diagrams. Entities show up as nouns in
  the FRs; their shape is decided in planning.
- Implementation decisions, architecture, testing strategy, deployment or CI plans.
- Technology choices, except in brownfield `## Current system` and in the `Module` column
  (the `@softure-ai/*` reuse marker, WORKFLOW §10).

When the shape notes carry such content (usually under `## Forward notes`), do not copy it
in. List it in the handoff under "forward notes" so nothing is silently lost.

## Mapping from shape notes

| Shape notes | PRD |
|---|---|
| Problem, Why now, insight from the interview | Summary (problem, insight) |
| Who it is for | Users |
| Access | Access control |
| Appetite | Summary (appetite, deadline) |
| Solution sketch → first flow | Primary flow |
| Solution sketch → elements, modules | Functional requirements (Module column) |
| Core rule | Business rules |
| Rabbit holes | Risks, plus Out of scope where the decision was "cut" |
| Constraints and preserved behaviour | Compatibility and preserved behaviour, `preserved` FRs, Guardrails |
| No-gos | Non-goals and Out of scope |
| Success signals | Goals, Success metrics, Guardrails |
| Open questions, `UNKNOWN`, `(accepted gap)` | Open questions (carried over word for word) |
| Forward notes | not in the PRD; listed in the handoff |

## Gap markers

Where the input has nothing for a required part, write `TODO: <what is missing> (OQ-<n>)`
in place and add the matching open question. Partial content: write what is there, then the
`TODO` line. The marker is greppable (`grep -n "TODO:" prd.md`), so later steps and reviews
can count unresolved gaps; a PRD with a blocking `TODO` must not be accepted.
