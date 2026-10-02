# Triage: talking the findings through with the user

The user decides; the skill recommends. Every question puts the recommended answer first and
says why in a few words. In `--auto` none of this is asked: the `--auto` rules in SKILL.md pick
the decision, and each one is recorded under `## Decisions (auto)`.

## 1. Chat summary (before any question)

Plain text, short, readable without the report open. Each level is printed with its meaning.

```
Implementation review: invoice-late-fees (full, 3 phases, commits 51e0a7c..c93b2d4)
Gates: typecheck pass · lint pass · test pass (588 tests)

Plan adherence             PASS
Scope                      WARNING   1 finding
Progress honesty           FAIL      1 finding
Correctness                FAIL      1 finding
Tests                      PASS
Data and migrations        WARNING   1 finding
Security                   PASS
Architecture and patterns  WARNING   1 finding
Lessons                    PASS

Findings: 2 critical, 3 warnings, 1 suggestion

F1  CRITICAL    MEDIUM impact (a real trade-off)    a rerun of the job charges the fee twice
F2  CRITICAL    LOW impact (obvious, narrow fix)    1.2 "rounds half-up" ticked without a test that rounds
F3  WARNING     LOW impact (obvious, narrow fix)    late_fee column added to the CSV export, not in the plan
F4  WARNING     MEDIUM impact (a real trade-off)    job scheduled with setInterval instead of the job registry
F5  WARNING     LOW impact (obvious, narrow fix)    no index for the overdue scan
F6  SUGGESTION  LOW impact (obvious, narrow fix)    test names say "works"
```

Dimensions that pass appear only in the table, never as findings.

## 2. How to proceed

Ask once:
- **"Decide one by one"**: recommended when there is any CRITICAL or HIGH-impact finding.
- **"Take every recommendation"**: recommended when all findings are LOW or MEDIUM impact and
  none is CRITICAL. CRITICAL and HIGH-impact findings are still asked one by one; the rest are
  decided as recommended, then listed.
- **"Save and decide later"**: write the report with `**Decision:** pending (recommended: …)`,
  commit the report alone as `docs(<change-id>): impl review` so it survives the session, and
  print the path and `softure-impl-review <change-id> --triage`. Status stays as it was.

## 3. One question per finding

Order: CRITICAL first, then by impact. The question carries the whole finding, so the user does
not have to scroll:

```
F1 of 6: a rerun of the job charges the fee twice
CRITICAL · MEDIUM impact (a real trade-off) · Correctness · invoices/apply-late-fee.ts:41

The job inserts a fee row without checking for an existing one. It runs hourly and is retried
on failure, so a second run in the same day adds the fee again (reproduced on the test database:
two runs, two rows for invoice 1042).

Fix A (recommended): unique constraint on (invoice_id, fee_date) plus ON CONFLICT DO NOTHING
  Strength: the database enforces it for every writer, including the retry path
  Trade-off: one migration; existing duplicates must be checked first (query: none today)
  Confidence: HIGH, the payments table uses the same pattern
Fix B: check for an existing row in the job before inserting
  Strength: no migration
  Trade-off: two concurrent runs still race between the check and the insert
  Confidence: MEDIUM, the retry runs in parallel with the next hourly run
```

Options, with two fixes: "Apply Fix A (recommended)", "Apply Fix B", "Defer", "Record as lesson".
Options, with one fix: the recommended decision first (usually "Fix now"), then "Fix
differently", "Defer", "Record as lesson". "Accept" and "withdraw" come through the free-text
answer, which is always available.

## 4. Handling the answer

- **Fix now / Apply Fix A or B**: for MEDIUM or HIGH impact, show the exact before/after and
  ask "Apply this?"; for LOW impact, apply directly. Record `fix now: <what changed> (Fix A)`;
  the SHA is added after the fix commit.
- **Fix differently**: ask how, apply that, record it as the user's fix.
- **Defer**: ask where to (recommended: the backlog topic file that matches, or the roadmap's
  "Owner decisions and checks" when the owner must decide). Write the entry there and record
  the target.
- **Free text "accept" / "keep it"**: record `accept: <the user's reason> (accepted by owner)`.
  If the user gives no reason, ask once for one line.
- **Free text "that is not a bug" / "wrong"**: look at the argument. If it holds, record
  `withdrawn: <why>`. If it does not, say what evidence contradicts it once, then record what the
  user decides.
- **Skip without a decision**: there is no skip. Offer "Defer" or "Accept" instead.
- **Record as lesson**: draft the rule in one line from the finding (the mechanism, not the
  incident), show it, and hand off to `softure-lesson --from <change-id>#F<n>`. Then **always**
  ask "Also fix the code now?" (recommended: yes, unless the lesson is purely about process).
  Never decide that on the user's behalf, however small or large the fix looks. Record
  `record as lesson + fix now` or `record as lesson`.

Keep momentum: the user has read the summary, so do not repeat it between questions. After each
decision, update the report file if it is already written.

## 5. Triage summary

Printed at the end and written into `## Triage summary`:

```
Triage complete: invoice-late-fees

Fixed:      F1 (Fix A), F2, F4, F6       (4)
Lessons:    F1 (also fixed)              (1)
Deferred:   F5 -> context/backlog/performance.md   (1)
Accepted:   F3 (owner asked for the column)        (1)
Withdrawn:  none

Fix commit: 8d2e4f1 · Gates after fixes: typecheck pass · lint pass · test pass (594 tests)
Verdict: Ready after fixes
Next: softure-lesson (F1), then softure-archive invoice-late-fees
```

## 6. Resuming a saved triage

`--triage`, or a report found with pending decisions: read `reviews/impl-review.md` (or
`impl-review-p<N>.md`), collect the `### F` sections whose `**Decision:**` starts with `pending`,
and continue at step 3 with them. When none is pending, say "every finding is decided" and go to
the commit step. Before applying a deferred-then-resumed fix, re-read the code at its location:
it may have changed since the report was written.
