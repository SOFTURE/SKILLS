---
name: softure-code-review
description: >
  Review a diff, a pull request or a set of paths against the project's own conventions:
  the SOFTURE rules block in AGENTS.md, the project's AGENTS.md/CLAUDE.md, and the numbered
  rules in context/foundation/lessons.md. Grades findings Critical / Warning / Suggestion,
  cites the rule behind every finding, ends with one verdict (approve, request changes, needs
  discussion), and can apply the fixes after asking. Use when the user says "review this
  code", "code review", "check my changes", "review PR 42", "take a look at this PR".
argument-hint: "[<change-id> | <pr-number> | <branch> | <path>...] [--fix] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - AskUserQuestion
---

# softure-code-review: hold the code to the rules the project already wrote down

This skill does not invent a standard. Every finding points at a written rule, or at a
concrete defect (a bug, a security hole) that needs no rule to be wrong. Without either, a
finding can only be a Suggestion, and it says so.

Read `references/example-review.md` (a complete review of a team-wiki pull request, with the
fix round that followed) before writing your first report in a session, and whenever unsure how
to grade or word a finding.

## Scope resolution

| Argument | What gets reviewed |
|---|---|
| none | `git diff` (staged + unstaged); if empty, `git diff <mainBranch>...HEAD` |
| `<change-id>` | `git diff <mainBranch>...HEAD` on the change branch; report saved to `context/changes/<change-id>/reviews/code-review.md` |
| `<pr-number>` | `gh pr diff <n>` and `gh pr view <n>` |
| `<branch>` | `git diff <mainBranch>...<branch>` |
| paths | the files as they are now |

`mainBranch` comes from `context/workflow.json`. Default to `main` and then `master`,
whichever exists.

## Rule sources, in priority order

1. Project `AGENTS.md` / `CLAUDE.md`, outside the SOFTURE managed block. Project rules win.
2. The SOFTURE managed block (`<!-- softure-skills:begin … -->`).
3. `context/foundation/lessons.md`: cite as `L-NNN`.
4. Architecture tests and lint config in the repo. When a rule is already enforced by a test
   or linter, run it instead of eyeballing.

Read all of them before reading the code. Note which rules are relevant to the touched paths.

## Procedure

1. Resolve the scope and list the changed files. Skip generated files: lockfiles, migration
   snapshots, build output.
2. For each file, read enough surrounding code to judge the change in place. "Too long" and
   "impure" are only meaningful relative to what the function does and who calls it.
3. Walk the categories. A category with nothing to report is stated as clean.
   - **Language** (only when the managed block carries the `## Language` section; a project
     can leave it out through `workflow.json` → `install.rules`): any non-English code,
     identifier, comment, commit message or log text outside message dictionaries is a
     violation. Without that section, follow whatever language rule the project wrote, or skip
     the category.
   - **Correctness:** logic errors, unhandled states, off-by-one, time zones, async without
     error handling.
   - **Boundaries:** input validation, authorization, SQL parameterization, secrets, leaked
     internals in responses.
   - **Data:** migrations, invariants enforced in the database, transactions, N+1 queries.
   - **Types:** `any` without justification, unchecked casts of external data, optional-field
     soup instead of a discriminated union.
   - **Structure:** single responsibility, parameter count, nesting, dead code, duplication of
     something that already exists (search before flagging).
   - **Naming:** descriptive, verb-first functions, boolean prefixes, file named after its main export.
   - **Tests:** behaviour-named, isolated, specific assertions, edge and error paths.
   - **UI:** accessibility (labels, roles, focus), user-visible text through the project's
     message layer, design tokens instead of raw values.
   - **Reuse:** a SOFTURE module or an existing helper that already does this (WORKFLOW §10).
4. Grade each finding:
   - **Critical**: a bug, a security hole, data loss, or a broken contract (an API, a schema, a
     public type other code relies on). Must be fixed before merge. Cite the rule when there is
     one; a reproducible defect stands on its evidence.
   - **Warning**: breaks a cited rule (convention, lesson, architecture test) without an
     immediate defect. Should be fixed; does not block on its own.
   - **Suggestion**: an improvement without a rule behind it. Label it as taste.

   Critical and Warning together are the **violations**. When torn between Critical and Warning,
   ask what happens in production if nobody touches it.
5. Pick the verdict, exactly one:
   - `APPROVE`: no Critical; the Warnings are minor or already acknowledged in the change.
   - `REQUEST CHANGES`: at least one Critical, or Warnings that together make the change unsafe
     to merge.
   - `NEEDS DISCUSSION`: the diff raises a design question it cannot settle by itself (two
     rules pull in opposite directions, the approach contradicts the plan or the PR description).
     Name the question.
6. Write the report and print it. Then fix (step 7) or stop.
7. **Fixes.**
   - With `--fix`: apply every violation with a local, mechanical fix.
   - Interactive, without `--fix`: ask once, recommended answer first: "Fix Critical and
     Warning findings" (recommended when there is anything to fix), "Fix Critical only", "Let me
     pick" (one question listing the findings), "Leave it as a report".
   - Apply in small edits, one finding at a time, without touching code no finding names. Run the
     gates from workflow.json and add a `## Fixes applied` section (finding, what changed, gates
     result). Never commit unless asked; inside a change, the caller commits. On a PR, never post
     comments or push unless the user asks.

## Output

```markdown
# Code review: <scope>

Rules read: AGENTS.md (project sections, softure block), lessons L-001…L-0NN, eslint config ·
Files: N reviewed, M skipped (generated) · Gates: ✓/✗ (when run)

**Verdict: REQUEST CHANGES** (one line why)

## Critical
1. **path:line**: <what is wrong, and the evidence>. Rule: <citation or "defect">. Fix: <concrete change>.

## Warnings
1. **path:line**: <what is wrong>. Rule: <citation>. Fix: <concrete change>.

## Suggestions (taste)
1. **path:line**: <idea>. No rule behind it; take or leave.

## Clean categories
Naming, Types, …

## Summary
One paragraph: the most important thing to fix and the overall risk.
```

Omit an empty severity section; list the category under "Clean categories" instead. Order
findings by impact within a section, and do not bury one real bug under twenty nits: when there
are more than about fifteen findings, merge those with one root cause and list every location.

**Citing a rule.** Name the source and the section, short enough to find: `AGENTS.md
"Security"`, `softure block "Data"`, `L-014`, `eslint no-floating-promises`,
`architecture test domain-has-no-ui-imports`. A citation the reader cannot find is not a citation.

**One finding, one fix.** The fix is a concrete edit ("pass `pageId` as a bound parameter"), not
advice ("consider improving the query"). When the right fix is a design choice, the finding is
NEEDS DISCUSSION material, and the verdict says so.

Print the report in the chat. When a change-id is given, also write it to `reviews/code-review.md`
(headings fixed English, prose in the workflow.json `language`).

## --auto

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

Behave as with `--fix`: apply every violation (Critical or Warning) that has a local, mechanical
fix, leave Suggestions unapplied, and record what was applied and what was left in `## Fixes
applied`. Ask nothing. A NEEDS DISCUSSION question is answered with the safer option and recorded
under `## Decisions (auto)` (WORKFLOW §8). Escalate only a security violation whose fix changes
behaviour visible to users.

## Checklist

- [ ] Every violation cites a rule or is a concrete correctness/security defect.
- [ ] Suggestions are labelled as such.
- [ ] Existing helpers and SOFTURE modules checked before flagging duplication.
- [ ] Every finding has a location, a severity and a concrete fix; the verdict is exactly one line.
- [ ] Gates run after any applied fix.

## Anti-patterns

- Inventing house style mid-review.
- Burying one real bug under twenty nits. Order findings by impact.
- Flagging code outside the diff, unless the change makes it wrong.
- Rewriting working code to the reviewer's taste under `--fix`.
- Grading a rule violation Critical to force a change, or a real bug Suggestion to stay polite.
- Advice instead of a fix: "consider", "might want to", "could be cleaner".

## Handoff

Patterns that keep coming back across reviews belong in `softure-lesson`. Rules that
contradict each other go to `softure-rule-review`.
