# Example: `reviews/impl-review.md`

An invoicing tool for small agencies. Change `invoice-late-fees`: an overdue invoice gets a
late fee of 1.5 % per started month, at least 5.00, shown on the invoice. Three phases:
1 the fee rule (TDD), 2 an hourly job that applies fees, 3 the fee on the invoice page and PDF.
The review ran interactively; the user decided one by one. This is the file as committed.

```markdown
# Implementation review: invoice-late-fees

Scope: full · Date: 2026-03-12 · Commits: 51e0a7c..c93b2d4 · Gates: typecheck ✓ lint ✓ test ✓ (594 tests, after fixes)

## Verdict
Ready after fixes. The rule, the job and the invoice view do what the plan asked, but the job
could charge a fee twice on a retry, and the rounding criterion was ticked without a test that
rounds; the test added for it found a real float-rounding bug. Both are fixed in 8d2e4f1 and
re-checked. One unplanned CSV column is kept at the owner's request; one missing index is deferred.

## Dimensions
| Dimension | Verdict | Findings |
|---|---|---|
| Plan adherence | PASS | |
| Scope | WARNING | F3 |
| Progress honesty | FAIL | F2 |
| Correctness | FAIL | F1 |
| Tests | PASS | F6 (suggestion only) |
| Data and migrations | WARNING | F5 |
| Security | PASS | |
| Architecture and patterns | WARNING | F4 |
| Lessons | PASS | L-004 (money in integer cents) respected after F2's fix |

## Plan coverage
| Phase | Commit | Delivered | Notes |
|---|---|---|---|
| 1 Late fee rule | 51e0a7c | yes | rounding wrong for half-cent amounts until F2 |
| 2 Hourly job applies fees | 7fa3e19 | yes | not idempotent until F1; scheduling pattern F4 |
| 3 Fee on invoice page and PDF | c93b2d4 | yes | also added a CSV column (F3) |

Files: planned and changed 9 · unplanned 1 (exports/invoices-csv.ts) · planned, not changed 0

## Findings

### F1 [CRITICAL] A rerun of the job charges the fee twice
**Impact:** MEDIUM (a real trade-off) · **Dimension:** Correctness · **Where:** invoices/apply-late-fee.ts:41
**What:** the job inserts a fee row for every overdue invoice without checking for an existing
row for the same day. The scheduler retries a failed run while the next hourly run may start.
**Why it matters:** customers are overcharged; the fee appears twice on the invoice and the PDF.
**Evidence:** two runs against the test database gave two fee rows for invoice 1042.
**Fix A (recommended):** unique constraint on (invoice_id, fee_date) and ON CONFLICT DO NOTHING
- Strength: enforced for every writer, including retries; payments use the same pattern
- Trade-off: one migration; existing duplicates had to be checked first (none)
- Confidence: HIGH, same pattern in payments/record-payment.ts
- Blind spot: none found
**Fix B:** look up an existing row in the job before inserting
- Strength: no migration
- Trade-off: two concurrent runs still race between the lookup and the insert
- Confidence: MEDIUM
- Blind spot: retry timing under load not measured
**Decision:** record as lesson + fix now (Fix A): migration 0019_late_fee_unique.sql and the
conflict clause; a test runs the job twice and expects one row (8d2e4f1)

### F2 [CRITICAL] Item 1.2 "rounds half-up to cents" ticked without a test that rounds
**Impact:** LOW (obvious, narrow fix) · **Dimension:** Progress honesty · **Where:** invoices/late-fee.test.ts:8
**What:** the only rounding test uses an amount of 1000.00, whose fee (15.00) never rounds.
**Why it matters:** the criterion was not proven. Adding the missing case showed the code
rounds on floats: 1.5 % of 1433.00 gave 21.49 instead of 21.50.
**Evidence:** new test "rounds a half cent up" failed before the fix, passes after.
**Fix:** compute in integer cents (L-004) and add half-cent and minimum-fee cases.
**Decision:** fix now: fee computed in cents, three cases added (8d2e4f1)

### F3 [WARNING] late_fee column added to the CSV export, not in the plan
**Impact:** LOW (obvious, narrow fix) · **Dimension:** Scope · **Where:** exports/invoices-csv.ts:22
**What:** phase 3 added a column to the export; neither plan.md nor change.md mentions it.
**Why it matters:** customers who import the CSV elsewhere see a new column without notice.
**Fix:** remove the column, or keep it and note it in plan.md.
**Decision:** accept: the owner asked for it during implementation; noted under Phase 3 in plan.md (accepted by owner)

### F4 [WARNING] Job scheduled with setInterval instead of the job registry
**Impact:** MEDIUM (a real trade-off) · **Dimension:** Architecture and patterns · **Where:** jobs/late-fees.ts:12
**What:** every other job registers in jobs/registry.ts, which adds locking and logging; this
one starts its own setInterval at import time.
**Why it matters:** with two app instances the job runs twice an hour, and failures are not logged.
**Fix:** register through jobs/registry.ts like jobs/send-reminders.ts.
**Decision:** fix now: registered in the registry, setInterval removed (8d2e4f1)

### F5 [WARNING] No index for the overdue scan
**Impact:** LOW (obvious, narrow fix) · **Dimension:** Data and migrations · **Where:** invoices/apply-late-fee.ts:18
**What:** the job filters on status and due_date; invoices has no index covering them.
**Why it matters:** a sequential scan every hour; 4 100 rows today, so no visible cost yet.
**Fix:** index on (status, due_date).
**Decision:** defer -> context/backlog/performance.md, revisit above 50 000 invoices

### F6 [SUGGESTION] Test names say "works"
**Impact:** LOW (obvious, narrow fix) · **Dimension:** Tests · **Where:** jobs/late-fees.test.ts:5, :19
**What:** "works" and "works for many" do not state the behaviour.
**Fix:** "applies one fee per overdue invoice", "skips invoices paid before the due date".
**Decision:** fix now: renamed (8d2e4f1)

## Progress audit
Before the review: 1.2 ticked without evidence (F2). After the fixes every ticked item has
evidence; 1.2 is backed by "rounds a half cent up". Open Manual items, not findings:
3.4 "PDF fee line matches the accountant's template" (owner).

## Triage summary
Fixed: F1 (Fix A), F2, F4, F6 · Lessons: F1 · Deferred: F5 (backlog/performance.md) ·
Accepted: F3 · Withdrawn: none. Fix commit 8d2e4f1; gates green after it.

## Lessons proposed
- A job that writes money is idempotent through a database constraint, not a check in code
  (from F1) -> softure-lesson --from invoice-late-fees#F1
```

What the run committed, in order:

1. `fix(invoice-late-fees): address impl review` (8d2e4f1): the code, the migration, the tests,
   the plan.md note for F3, and the Progress SHA edit left over from phase 3.
2. `docs(invoice-late-fees): impl review`: this report with 8d2e4f1 filled in, the backlog entry
   for F5, and change.md at `status: impl_reviewed`.

The backlog entry written for F5 (`context/backlog/performance.md`):

```markdown
- [ ] 2026-03-12 invoice-late-fees impl review F5: index invoices(status, due_date) for the hourly overdue scan (WARNING) context/archive/2026-03-09-invoice-late-fees/reviews/impl-review.md
```

The evidence path points at the archive location the change will have after `softure-archive`
(`<created>-<change-id>`); archive's link fix rewrites it if the date differs.
