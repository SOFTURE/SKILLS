---
name: softure-lesson
description: >
  Turn a mistake that happened (or keeps happening) into a numbered, durable rule in
  context/foundation/lessons.md, with the incident that justifies it and how to apply it.
  Interviews briefly, drafts the entry, shows it for approval, deduplicates against existing
  lessons and numbers safely across parallel worktrees. Use when the user says "record a
  lesson", "remember this rule", "add to lessons", "make sure this never happens again",
  "add a rule", or when a review finding is marked "record as lesson".
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
create it with the `# Lessons` header and one sentence saying what it is for; do not send the
user to `softure-init` for it. Research, frame, plan and the reviews read lessons as priors, so a
lesson earns its place only if it changes what one of them does next time.

## What qualifies

A lesson is a rule that would have prevented a **concrete** mistake in this repo, or would have
changed how earlier work was framed or fixed, and that a future agent would plausibly repeat.
It is not:
- general programming advice already in the conventions;
- a task or a TODO (those go to the roadmap or backlog);
- a fact about one file that the code itself makes obvious;
- a write-up of a one-off incident with no rule a reviewer could check.

If the input fails this test, say why and stop. Writing nothing is a valid outcome.

## Procedure

1. **Collect the incident.** Interactive: ask **one question at a time**, at most three, each
   with your draft answer when you have one (from the conversation, the diff or the review), so
   the user confirms or corrects instead of writing from scratch:
   - What happened, concretely (file, command, symptom)?
   - What did it cost (time, data, a wrong release)?
   - When should the rule fire next time (paths, areas, kinds of work, which skills)?

   With `--from <change-id>#F<n>`, read the finding in `reviews/impl-review.md` (or the review it
   names) and skip the questions it already answers.
2. **Deduplicate.** Search existing lessons for the same mechanism, not the same words: grep
   key terms, then read candidates. If one already covers it:
   - same rule: add the new incident as a second line under **Why:** (`Also: <date>, <change-id>: …`).
     Do not create a new number.
   - broader rule: generalize the existing lesson's title, keep its number, and note the widening.

   These are the only edits this skill makes to an old lesson; reversing or deleting one is an
   owner edit or a `softure-rule-review` finding.
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
4. **Draft the entry:**
   ```markdown
   ## L-042: <imperative rule in one line>
   **Why:** <the incident: what happened, where, what it cost>.
   **How to apply:** <the trigger and the concrete behaviour; include the check or command if there is one>.
   **Applies to:** <paths, areas, skills>.
   ```
   - **Title:** imperative and testable: a reviewer can paste it into a finding and point at a
     violating line. "Be careful with dates" is not a rule; "Compute day boundaries in the
     configured time zone, never in UTC" is.
   - **Why:** mechanism, not blame, with the change id or commit so it can be found.
   - **Applies to:** globs (`drizzle/*.sql`), activities ("any phase that adds a migration") and
     the skills that should weigh it (`plan`, `implement`, `impl-review`, `all`). Never "everywhere".
5. **Confirm** (interactive). Show the rendered entry and ask once: *Append* (recommended) /
   *Edit a field* / *Cancel*. On *Edit*, change only the named field and show it again.
   `--auto`: no confirmation.
6. **Write it** at the end of the file (or apply the dedupe edit from step 2). Then re-read the
   file and check: the new heading is the last `## L-` section, its number appears exactly once,
   and nothing above it changed.
7. **Enforce when possible.** If the rule can be a test, lint rule, database constraint or
   architecture check, propose it, and add it inside a change when you have one. Mention the
   enforcement in **How to apply**.
8. **Commit** only inside a change or when asked: `docs(lessons): L-042 <short title>`. Report
   the number and title, and stop. One invocation records one lesson; several candidates usually
   share one mechanism, so merge them, or run the skill once per rule.

Complete examples (a new lesson, a merged incident, a widened rule) and bad entries with what is
wrong: read `references/examples.md` **when drafting, if you are unsure the title is testable or
the Applies to is specific enough**.

## --auto

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

- No questions and no confirmation: take the facts from the review finding or the caller's draft.
- Skip writing when step "What qualifies" fails, and report the skip in one line.
- On a number collision found later (merge with another worktree), renumber the newer lesson,
  then `grep -rn "L-<old>"` and fix every reference in the same commit.

## Checklist

- [ ] Concrete incident in **Why**, with a findable reference (change id, commit, date).
- [ ] Testable, imperative title.
- [ ] **Applies to** names paths or activities and the skills that should weigh it.
- [ ] No duplicate of an existing lesson.
- [ ] Number = max across main and worktrees + 1.
- [ ] Re-read after writing; only the intended section changed.
- [ ] Enforcement proposed where possible.

## Anti-patterns

- Lessons that restate the conventions block.
- Recording blame instead of mechanism.
- Ten lessons from one change. Merge them into the one rule that matters.
- Editing an old lesson's number or meaning silently.
- Writing the user's wording for them without showing it (interactive): the team owns its rules.

## Handoff

Back to the caller (softure-impl-review, softure-worktree), or to `softure-rule-review` if the new
rule contradicts an existing one.
