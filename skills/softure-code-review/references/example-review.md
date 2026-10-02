# Example: a code review and its fix round

A team wiki. The user runs `softure-code-review 57` on a pull request titled "Restore an older
page revision". The project carries the SOFTURE rules block in AGENTS.md (all sections) and
eleven lessons. Gates come from `context/workflow.json`.

## What the skill read first

- AGENTS.md: project sections ("Spaces and permissions", "Dates") and the softure block.
- `context/foundation/lessons.md`: L-001…L-011; relevant to the touched paths are L-006
  ("permission checks go through `assertCanEdit`, never an inline role comparison") and L-009
  ("dates are formatted only through `lib/dates.ts`").
- `eslint.config.mjs`: `no-floating-promises` is on, so floating promises are left to the linter.
- `gh pr view 57` and `gh pr diff 57`: six files, one of them a generated migration snapshot
  (skipped).

## The report

```markdown
# Code review: PR 57 "Restore an older page revision"

Rules read: AGENTS.md (project sections, softure block), lessons L-001…L-011, eslint config ·
Files: 5 reviewed, 1 skipped (drizzle/meta snapshot) · Gates: not run (review only)

**Verdict: REQUEST CHANGES** (the restore action can be called by anyone with a session, and it
interpolates an id into SQL)

## Critical
1. **pages/restore-revision.ts:14**: the server action checks that a session exists, but not
   that the user may edit the page's space; any signed-in reader can overwrite any page.
   Rule: softure block "Security" (authorization, not just a session), L-006.
   Fix: call `assertCanEdit(session.user, page.spaceId)` before the write, as
   `pages/update-page.ts:19` does.
2. **pages/restore-revision.ts:27**: `` sql.raw(`... WHERE id = ${revisionId}`) `` puts a value from
   the form into the query text. Rule: softure block "Data" (SQL is always parameterized).
   Fix: `db.select().from(revisions).where(eq(revisions.id, revisionId))`, or a bound parameter.

## Warnings
1. **pages/RestoreButton.tsx:22**: `aria-label="Restore this revision"` is inline text.
   Rule: softure block "React / Next.js" (user-visible text, including `aria-label`, goes
   through the message layer). Fix: add `revision.restoreLabel` to `messages/en.ts` and read it
   with `t()`.
2. **pages/RevisionList.tsx:9**: a local `formatRevisionDate` builds the date with
   `toLocaleString()`, which uses the server's time zone. Rule: L-009.
   Fix: use `formatDateTime(revision.createdAt, viewer.timeZone)` from `lib/dates.ts`.
3. **pages/restore-revision.test.ts:31**: "restore works" asserts `expect(result).toBeTruthy()`.
   Rule: softure block "Tests" (a name states the behaviour; assert exact values).
   Fix: "restores the body and title of the chosen revision", asserting both fields with
   `toEqual`, plus a case for a revision of another page (expects a refusal).

## Suggestions (taste)
1. **pages/RevisionList.tsx:40-88**: the inline diff view could be its own component; the file
   would read more easily. No rule behind it; take or leave.

## Clean categories
Language, Types, Naming, Structure, Reuse

## Summary
Fix the two Criticals before merging: together they let any signed-in user rewrite any page
through a query built from form input. The Warnings are small and local. Nothing here needs a
design discussion.
```

## Wording: the same finding, badly and well

- Bad: "Security could be improved in the restore action."
  No location, no mechanism, no rule, no fix.
- Bad: "**pages/restore-revision.ts:14**: consider adding a permission check." Advice, not a
  fix; the reader still has to work out which check and where it lives.
- Good: Critical 1 above. Location, what goes wrong, the rule and the lesson, and the exact call
  with a sibling that already does it.

## The fix round

Without `--fix`, the skill asks once: "Fix Critical and Warning findings" (recommended), "Fix
Critical only", "Let me pick", "Leave it as a report". The user takes the recommendation. Each
finding is fixed with a small edit; the suggestion is left alone. The skill runs the gates and
appends:

```markdown
## Fixes applied
| Finding | Change | Files |
|---|---|---|
| Critical 1 | `assertCanEdit` before the write; new test "refuses a reader of the space" | pages/restore-revision.ts, pages/restore-revision.test.ts |
| Critical 2 | query through the builder with `eq(revisions.id, revisionId)` | pages/restore-revision.ts |
| Warning 1 | `revision.restoreLabel` in messages/en.ts | pages/RestoreButton.tsx, messages/en.ts |
| Warning 2 | `formatDateTime` from lib/dates.ts | pages/RevisionList.tsx |
| Warning 3 | renamed, exact assertions, cross-page refusal case | pages/restore-revision.test.ts |

Left as is: Suggestion 1 (taste). Gates: typecheck ✓ lint ✓ test ✓ (1 204 tests).
Not committed and not pushed: the PR author commits.
```

## When the verdict is NEEDS DISCUSSION

Had the PR restored a revision by overwriting the page in place, while the PR description said
"restoring creates a new revision so nothing is lost", the code would match neither reading
cleanly. The report would then end with:

```markdown
**Verdict: NEEDS DISCUSSION** (should a restore create a new revision, as the PR description says,
or overwrite the current one, as the code does? The history view and the audit log depend on the answer.)
```

and the fix question would not be asked until that is settled. In `--auto` the safer reading
(create a new revision, nothing is lost) becomes the review's working assumption and is recorded
under `## Decisions (auto)`. The code change it implies is not mechanical, so it is reported,
not applied.
