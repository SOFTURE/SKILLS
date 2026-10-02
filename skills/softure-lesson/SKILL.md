---
name: softure-lesson
description: >
  Turn a mistake that happened (or keeps happening) into a numbered, durable rule in
  context/foundation/lessons.md, with the incident that justifies it and how to apply it.
  Deduplicates against existing lessons and numbers safely across parallel worktrees. Use
  when the user says "record a lesson", "remember this rule", "add to lessons", "make sure
  this never happens again", "add a rule", or when a review finding is marked "record as lesson".
argument-hint: "[\"<one-line rule draft>\"] [--from <change-id>#<finding>] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - AskUserQuestion
---

# softure-lesson: one incident, one rule, one number

Contract: `WORKFLOW.md` §7. The file is `context/foundation/lessons.md`. If it does not exist,
create it with the `# Lessons` header and one sentence saying what it is for.

## What qualifies

A lesson is a rule that would have prevented a **concrete** mistake in this repo, and that a
future agent would plausibly repeat. It is not:
- general programming advice already in the conventions;
- a task or a TODO (those go to the roadmap or backlog);
- a fact about one file that the code itself makes obvious.

If the input fails this test, say why and stop. Writing nothing is a valid outcome.

## Procedure

1. **Collect the incident.** Interactive: ask at most three questions.
   - What happened, concretely (file, command, symptom)?
   - What did it cost (time, data, a wrong release)?
   - When should the rule fire next time (paths, areas, kinds of work)?

   With `--from <change-id>#F<n>`, read the finding in `reviews/impl-review.md` and skip the
   questions it already answers.
2. **Deduplicate.** Search existing lessons for the same mechanism, not the same words: grep
   key terms, then read candidates. If one already covers it:
   - same rule: add the new incident as a second line under **Why:** (`Also: <date>, <change-id>: …`).
     Do not create a new number.
   - broader rule: generalize the existing lesson's title, keep its number, and note the widening.
3. **Pick the number.** Next number = max(`L-NNN` on the main branch, in the working tree, and in
   every worktree) + 1:
   ```bash
   main=$(jq -r .mainBranch context/workflow.json 2>/dev/null || echo main)
   { git show "$main:context/foundation/lessons.md" 2>/dev/null
     for wt in $(git worktree list --porcelain | sed -n 's/^worktree //p'); do
       cat "$wt/context/foundation/lessons.md" 2>/dev/null; done; } \
     | grep -oE '^#+ *L-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1
   ```
   Zero-pad to three digits. Numbers are never reused, even if a lesson is deleted.
4. **Write it** at the end of the file:
   ```markdown
   ## L-042: <imperative rule in one line>
   **Why:** <the incident: what happened, where, what it cost>.
   **How to apply:** <the trigger and the concrete behaviour; include the check or command if there is one>.
   **Applies to:** <paths, areas, skills>.
   ```
   The title must be testable. "Be careful with dates" is not a rule; "Compute day boundaries
   in the configured time zone, never in UTC" is.
5. **Enforce when possible.** If the rule can be a test, lint rule, database constraint or
   architecture check, propose it, and add it inside a change when you have one. Mention the
   enforcement in **How to apply**.
6. **Commit** only when running inside a change or when asked:
   `docs(lessons): L-042 <short title>`.

## --auto

- No questions: take the facts from the review finding or the caller's draft.
- Skip writing when step "What qualifies" fails, and report the skip in one line.
- On a number collision found later (merge with another worktree), renumber the newer lesson,
  then `grep -rn "L-<old>"` and fix every reference in the same commit.

## Checklist

- [ ] Concrete incident in **Why**.
- [ ] Testable, imperative title.
- [ ] No duplicate of an existing lesson.
- [ ] Number = max across main and worktrees + 1.
- [ ] Enforcement proposed where possible.

## Anti-patterns

- Lessons that restate the conventions block.
- Recording blame instead of mechanism.
- Ten lessons from one change. Merge them into the one rule that matters.
- Editing an old lesson's number or meaning silently.

## Handoff

Back to the caller (softure-impl-review, softure-worktree), or to `softure-rule-review` if the new
rule contradicts an existing one.
