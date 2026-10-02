# Worked example: a two-phase run

A booking app for a climbing gym. Change `cancellation-window`: customers may cancel a class
booking until 24 hours before it starts; after that the button is disabled and says why.
`context/workflow.json` defines three gates (`typecheck`, `lint`, `test`); the run uses them by
name and never assumes their commands.

## Start

The user runs `softure-implement cancellation-window`. change.md says `plan_reviewed`, the tree
is clean. Progress at the start:

```markdown
### Phase 1: Cancellation rule on the server

#### Automated
- [ ] 1.1 `cancelBooking` returns `{ kind: "cancelled" }` when the class starts in more than 24 h
- [ ] 1.2 `cancelBooking` returns `{ kind: "too_late", startsAt }` at 24 h or less, and changes no row
- [ ] 1.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 1.4 Front desk confirms the 24 h rule also applies to private lessons

### Phase 2: Cancel button shows the window

#### Automated
- [ ] 2.1 Button is enabled with "Cancel (until Tue 18:00)" inside the window
- [ ] 2.2 Button is disabled with the reason text outside the window (component test)
- [ ] 2.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 2.4 Disabled state is visibly disabled in light and dark themes at 390 px
- [ ] 2.5 The reason text is clear to a customer
```

The skill sets `status: implementing`, starts the touched-file set with the change folder's
uncommitted artifacts plus `plan.md`, and reads lessons. L-007 ("a write that depends on a read
uses a conditional UPDATE") applies to `bookings/`, so it shapes phase 1.

## Phase 1: reconcile, then TDD

Reconciling finds a difference:

```
Mismatch in phase 1, step 2
Plan says:      set bookings.status to 'cancelled'
Code has:       no status column; a booking is cancelled when canceled_at is set
                (db/schema/bookings.ts:31, read by bookings/queries.ts:12)
Why it matters: writing a status column fails the migration check and nothing reads it
Recommendation: adapt (set canceled_at = now()), because the meaning is identical and
                every reader already uses canceled_at
```

Asked with "Adapt and continue" (recommended), "Drop this step" and "Stop and re-plan", the user
picks the first. A note goes under Phase 1 in plan.md and into the commit body.

The test for 1.2 is written first and run:

```
FAIL bookings/cancel-booking.test.ts > returns too_late at exactly 24 hours
  expected { kind: 'too_late', startsAt: 2026-03-03T18:00:00.000Z }
  received { kind: 'cancelled' }
```

Red for the right reason (the rule is missing, not an import error). The implementation uses
`UPDATE bookings SET canceled_at = now() WHERE id = $1 AND canceled_at IS NULL AND starts_at > now() + interval '24 hours'`,
so a double click cannot cancel twice (L-007). Tests go green, all three gates pass, 1.1 to 1.3
are ticked. Item 1.4 needs a person at the front desk, so it stays open; it does not hold up the
commit, and there is no gate message because nobody can check it right now.

Staging: the set is `bookings/cancel-booking.ts`, its test, `bookings/actions.ts`, and the
change folder files. `git status --porcelain` shows nothing else. The proposed message:

```
feat(cancellation-window): Cancellation rule on the server (p1)

cancelBooking refuses at 24 h or less and returns the start time so the
UI can explain. The plan said to write bookings.status; the schema marks
cancellation with canceled_at, so the action sets that (noted in plan.md).
The UPDATE is conditional, so a repeated request cannot cancel twice.

Files: bookings/cancel-booking.ts, bookings/cancel-booking.test.ts,
bookings/actions.ts, context/changes/cancellation-window/*
```

The user approves. `git log -1 --format='%h %s'` shows `3b9d2f4 feat(cancellation-window):
Cancellation rule on the server (p1)`, so the SHA is written:

```markdown
- [x] 1.1 `cancelBooking` returns `{ kind: "cancelled" }` when the class starts in more than 24 h — 3b9d2f4
- [x] 1.2 `cancelBooking` returns `{ kind: "too_late", startsAt }` at 24 h or less, and changes no row — 3b9d2f4
- [x] 1.3 Gates green (typecheck, lint, test) — 3b9d2f4
```

That edit stays uncommitted. The skill reports and asks:

```
Phase 1 of 2 committed (3b9d2f4). Progress 3/8.
Open for the owner: 1.4 Front desk confirms the 24 h rule also applies to private lessons.
```

Options: "Continue to phase 2" (recommended), "Stop here, resume later", "Review this phase
first". The user continues.

## Phase 2: the manual gate and a hook failure

Test-after: the button and its component tests first, then 2.1 and 2.2 pass and the gates are
green. For 2.4 the skill starts the dev server, opens a booking 20 hours out at 390 px in both
themes, takes two screenshots into `reviews/`, and looks at them: the button is greyed out and
the cursor is not a pointer. 2.4 is ticked `(verified by agent: screenshots in reviews/p2-*.png)`.
2.5 is a judgement about wording, so the gate opens:

```
Phase 2 of 2 is ready to commit: Cancel button shows the window

Passed automatically:
- 2.1 enabled with "Cancel (until Tue 18:00)" inside the window (test "shows the deadline")
- 2.2 disabled with the reason outside the window (test "explains why it is disabled")
- 2.3 Gates green: typecheck, lint, test (236 tests)

Verified by me:
- 2.4 visibly disabled in light and dark at 390 px (reviews/p2-light.png, reviews/p2-dark.png)

Please check:
- 2.5 the reason text is clear to a customer (open any booking within 24 h on /bookings)

Still waiting from earlier phases:
- 1.4 Front desk confirms the 24 h rule also applies to private lessons
```

Recommended: "Commit now, check later" (no later phase builds on the wording). The user picks
"Found a problem": with 1 hour left the text reads "Cancellation closed 1 hours before class".
The skill fixes the plural through the message layer, adds a test for the one-hour case, re-runs
the gates and shows the gate again. This time the user answers "Checked, all good", and 2.5 is
ticked without a note.

The commit is refused by the lint hook (an unused import left by the fix). HEAD is still
`3b9d2f4`, so amending would rewrite phase 1. The skill removes the import, re-runs `lint`,
re-stages the file, and commits again as a new commit:

```
feat(cancellation-window): Cancel button shows the window (p2)

The button shows the deadline inside the window and the reason outside it;
plural forms come from the message layer. Carries the phase 1 Progress SHA.

Files: bookings/CancelButton.tsx, bookings/CancelButton.test.tsx,
messages/en.ts, context/changes/cancellation-window/plan.md, reviews/p2-*.png
```

HEAD now reads `a61c07e feat(cancellation-window): Cancel button shows the window (p2)`.

## Finish

Re-scan: no open Automated item; open Manual item 1.4. The skill writes `a61c07e` into 2.1 to
2.5, sets `status: implemented`, and commits plan.md and change.md as
`docs(cancellation-window): progress p2`. Final Progress:

```markdown
### Phase 1: Cancellation rule on the server

#### Automated
- [x] 1.1 `cancelBooking` returns `{ kind: "cancelled" }` when the class starts in more than 24 h — 3b9d2f4
- [x] 1.2 `cancelBooking` returns `{ kind: "too_late", startsAt }` at 24 h or less, and changes no row — 3b9d2f4
- [x] 1.3 Gates green (typecheck, lint, test) — 3b9d2f4

#### Manual
- [ ] 1.4 Front desk confirms the 24 h rule also applies to private lessons

### Phase 2: Cancel button shows the window

#### Automated
- [x] 2.1 Button is enabled with "Cancel (until Tue 18:00)" inside the window — a61c07e
- [x] 2.2 Button is disabled with the reason text outside the window (component test) — a61c07e
- [x] 2.3 Gates green (typecheck, lint, test) — a61c07e

#### Manual
- [x] 2.4 Disabled state is visibly disabled in light and dark themes at 390 px — a61c07e (verified by agent: screenshots in reviews/p2-*.png)
- [x] 2.5 The reason text is clear to a customer — a61c07e
```

Completion summary:

```
cancellation-window implemented: 2 phases (p1 3b9d2f4, p2 a61c07e), progress 7/8.
Key files: bookings/cancel-booking.ts, bookings/actions.ts, bookings/CancelButton.tsx, messages/en.ts
Decisions: phase 1 writes canceled_at instead of a status column (plan.md, phase 1 note)
Open for the owner: 1.4 Front desk confirms the 24 h rule also applies to private lessons
Next: softure-impl-review cancellation-window
```

Asked "Run the implementation review now?", the user can take it (recommended) or leave it.

## The same run with `--auto`

- The mismatch is adapted without a question and recorded under `## Decisions (auto)`:
  `- plan writes bookings.status, schema uses canceled_at → set canceled_at (same meaning, every reader uses it)`.
- No question between phases, no gate. 2.4 is still verified by screenshots; 2.5 stays `- [ ]`
  and joins 1.4 in the summary for the owner.
- The hook failure is fixed the same way. Had the hook failed on a file outside the change, the
  run would stop and report instead.
