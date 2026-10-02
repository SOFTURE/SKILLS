---
name: softure-code-review
description: >
  Review a diff, a pull request or a set of paths against the project's own conventions:
  the SOFTURE rules block in AGENTS.md, the project's AGENTS.md/CLAUDE.md, and the numbered
  rules in context/foundation/lessons.md. Separates hard violations from taste-level
  suggestions, cites the rule behind every finding, and can apply the fixes. Use when the
  user says "review this code", "code review", "check my changes", "review PR 42",
  "take a look at this PR".
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

This skill does not invent a standard. Every finding points at a written rule. Without a
rule behind it, a finding can only be a Suggestion, and it says so.

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
   - **Language:** any non-English code, identifier, comment, commit message or log text
     outside message dictionaries is a violation (the mandatory language rule in AGENTS.md).
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
4. Classify each finding:
   - **Violation**: breaks a cited rule, or is a correctness or security defect.
   - **Suggestion**: an improvement without a rule behind it. Label it as taste.
5. Write the report. With `--fix` (or the user's approval), apply violations in small edits,
   run the gates from workflow.json, and report what changed. Never commit unless asked. Inside
   a change, the caller commits.

## Output

```markdown
# Code review: <scope>

Rules read: AGENTS.md, softure block, lessons L-001…L-0NN · Files: N · Gates: ✓/✗ (when run)

## Violations
1. **path:line**: <what is wrong>. Rule: <AGENTS.md "Security" / L-014>. Fix: <concrete change>.

## Suggestions (taste)
1. **path:line**: <idea>. No rule behind it; take or leave.

## Clean categories
Naming, Types, …

## Summary
One paragraph: the most important thing to fix and the overall risk.
```

Print the report in the chat. When a change-id is given, also write it to `reviews/code-review.md`.

## --auto

Apply every violation that has a local, mechanical fix. Leave suggestions unapplied. Record
what was applied and what was left. Ask nothing. Escalate only a security violation whose fix
changes behaviour visible to users.

## Checklist

- [ ] Every violation cites a rule or is a concrete correctness/security defect.
- [ ] Suggestions are labelled as such.
- [ ] Existing helpers and SOFTURE modules checked before flagging duplication.
- [ ] Gates run after any applied fix.

## Anti-patterns

- Inventing house style mid-review.
- Burying one real bug under twenty nits. Order findings by impact.
- Flagging code outside the diff, unless the change makes it wrong.
- Rewriting working code to the reviewer's taste under `--fix`.

## Handoff

Patterns that keep coming back across reviews belong in `softure-lesson`. Rules that
contradict each other go to `softure-rule-review`.
