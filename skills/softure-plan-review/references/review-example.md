# Worked example: a plan review

Read this before writing your first review in a repo, or when unsure how specific a finding
should be. It reviews the first draft of the `overdue-invoice-reminders` plan; the plan after
these fixes is `softure-plan/references/plan-example.md`. Paths are illustrative.

## The draft, in short

- Phase 1: migration adding `invoices.reminder_sent_at` and `clients.reminders_enabled`; a
  query `findInvoicesDueForReminder` comparing `due_on + 3` with `current_date`.
- Phase 2: a job that sends the email for each selected invoice, then sets
  `reminder_sent_at = now()`. A `NotificationChannel` interface "so SMS can be added later".
  Criterion 2.2: "Reminders work."
- Phase 3: a client settings toggle and a `setRemindersEnabled(clientId, enabled)` action.

## The saved review: `reviews/plan-review.md`

```markdown
# Plan review: overdue-invoice-reminders

Reviewed: plan.md @ 2026-10-02. Mode: deep. Verdict: ready after fixes.
Findings: 2 critical, 2 warning, 1 suggestion.
Grounding: 11/11 paths, 5/6 symbols (getAccountTimeZone does not exist), 3/3 commands

## Lenses
| Lens | Result |
| --- | --- |
| Coverage and end state | WARN (W1) |
| Slicing | PASS |
| Verifiability | WARN (W2) |
| Data and migrations | FAIL (C1) |
| Tests | WARN (W1) |
| Security | FAIL (C2) |
| Lean | WARN (S1) |
| Fit | PASS |
| Cost and defaults | PASS |
| Scope | PASS |
| Reuse | PASS |
| Lessons | PASS |
| Progress format | PASS |

## Findings

### C1 [CRITICAL] Overlapping job runs send the same reminder twice
**Effort:** medium. **Lens:** Data and migrations. **Where:** Phase 2, step 1 (plan.md) · `src/jobs/registry.ts:8`
**Problem:** The job sends first and marks `reminder_sent_at` afterwards. Research §Risks
records that the scheduler starts a new instance before the old one stops during deploys, so
two runs can select the same invoice and both send. The Goal promises exactly one reminder.
**Fix A (Recommended):** claim each invoice with `UPDATE ... SET reminder_sent_at = now() WHERE
id = $1 AND reminder_sent_at IS NULL RETURNING id`, send only when a row is returned, release
the claim on a failed send. Strength: one statement, correct across any number of instances,
same pattern as `claimPayout` in `src/payouts/claim.ts:20`. Trade-off: a crash between claim
and send loses that reminder. Confidence: high, the pattern already runs in production. Blind
spot: crash frequency of the job runner is unmeasured.
**Fix B:** wrap the whole job in a database advisory lock. Strength: no change to the send
logic. Trade-off: a stuck run blocks all reminders until the lock is released. Confidence:
medium, the project has no advisory-lock helper yet. Blind spot: lock behaviour with the
connection pooler is unverified.
**Decision:** Fix now (applied, Fix A) - phase 2 step 1 rewritten as claim, send, release;
test "two concurrent runs send one email" added; Critical details added under Approach.

### C2 [CRITICAL] The new action does not check that the user owns the client
**Effort:** low. **Lens:** Security. **Where:** Phase 3, step 1
**Problem:** `setRemindersEnabled(clientId, enabled)` takes the id from the form. Any signed-in
user could switch reminders off for another account's client.
**Fix:** check ownership the way `updateClientAction` does (`src/app/clients/[id]/actions.ts:31`)
and add criterion 3.2 "rejects a client the user does not own".
**Decision:** Fix now (applied)

### W1 [WARNING] "Three days after the due date" is computed in UTC
**Effort:** low. **Lens:** Tests. **Where:** Phase 1, step 3 · grounding miss
**Problem:** The query compares with `current_date`, which is the database's UTC date. Accounts
east of UTC get the reminder up to a day late, accounts west of UTC up to a day early. The plan
cites `getAccountTimeZone`, which does not exist; the zone is the column `accounts.time_zone`
(`src/db/schema.ts:64`).
**Fix:** compute the local date of `now` from `accounts.time_zone` in the query; add the test
"account where now is still the previous day: not selected".
**Decision:** Fix now (applied)

### W2 [WARNING] Criterion 2.2 "Reminders work" cannot be checked
**Effort:** low. **Lens:** Verifiability. **Where:** Phase 2, Done when; Progress 2.2
**Problem:** Nobody can tell when it is true, and it does not read any data.
**Fix:** replace with "after one run on the dev database, the reminded count equals the
eligible count taken before the run; a second run sends 0".
**Decision:** Fix now (applied)

### S1 [SUGGESTION] Drop the NotificationChannel interface
**Effort:** low. **Lens:** Lean. **Where:** Phase 2, step 2
**Problem:** The interface has one implementation; SMS is out of scope in the plan's own Goal.
**Fix:** call the mail module directly; introduce an abstraction when a second channel exists.
**Decision:** Fix now (applied)

## Triage summary
Fixed: C1 (Fix A), C2, W1, W2, S1. Accepted: -. Deferred: -. Dismissed: -.
Verdict before triage: not ready (2 critical open; the fixes are local, so not back to plan). After: ready after fixes.
```

## The same review, presented in the terminal

```text
PLAN REVIEW: overdue-invoice-reminders   (deep, 2026-10-02)
Findings: 2 critical, 2 warning, 1 suggestion
Grounding: 11/11 paths, 5/6 symbols, 3/3 commands

  Data and migrations   FAIL  (C1)
  Security              FAIL  (C2)
  Tests                 WARN  (W1)
  Verifiability         WARN  (W2)
  Lean                  WARN  (S1)
  8 other lenses        PASS
  Verdict: ready after fixes, if C1 and C2 are fixed

CRITICAL
  C1  Overlapping job runs send the same reminder twice
      Severity: CRITICAL
      Effort:   medium (a real trade-off between two fixes)
      Lens:     Data and migrations
      Where:    Phase 2, step 1
      Problem:  sends first, marks afterwards; the scheduler overlaps during deploys
      Fix A (Recommended): claim with a conditional UPDATE, send, release on failure
      Fix B: advisory lock around the job
  ...

Triage now (Recommended) / Save and triage later?
```

## A triage exchange

> **C1 of 5 - Overlapping job runs send the same reminder twice.** (details as above)
>
> 1. Apply Fix A (Recommended)
> 2. Apply Fix B
> 3. Fix differently
> 4. Accept risk
> 5. Defer
> 6. Dismiss

User: "Accept risk, deploys are rare."

Reviewer: "Understood. The consequence: every deploy that overlaps the 15-minute run can send a
duplicate to every invoice due that day, which is what the Goal rules out. Recording it as
accepted by you." Then the reviewer writes `**Decision:** Accept risk - duplicates possible
during deploys; accepted by owner`, keeps C1 open as a CRITICAL that is not fixed, and therefore
leaves the status at `planned` with the reason in the report. (In the saved review above, the
owner chose Fix A instead.)

Before applying a fix, the reviewer shows the edit:

```text
Phase 2, step 1
- before: For each selected invoice, send the reminder, then set reminder_sent_at = now().
+ after:  For each selected invoice, claim it with UPDATE ... WHERE reminder_sent_at IS NULL
+         RETURNING id; send only when a row came back; on a failed send, set it back to null.
```

## Good and bad findings

| Bad | Why | Good |
| --- | --- | --- |
| "Consider concurrency." | no evidence, no decision possible | "Two runs can select the same invoice (scheduler overlap, research §Risks); C1 with two fixes." |
| "Security could be improved." | which entry point, which hole? | "`setRemindersEnabled` trusts `clientId` from the form; any user can change another account's client." |
| "Tests might be insufficient." | which case is missing? | "No test for an account whose local date is still yesterday; the query uses the UTC date." |
| WARNING: "Rename `rem` to `reminder`." | a naming nit inflated to a warning | leave it out, or one SUGGESTION at most |
| SUGGESTION: "Maybe add a rollback." | a real risk hidden as a nicety | WARNING or CRITICAL with the rollback path as the fix |

## A sound plan

When nothing is wrong, the review is short:

```markdown
# Plan review: invoice-pdf-footer

Reviewed: plan.md @ 2026-10-02. Mode: quick. Verdict: ready.
Findings: 0 critical, 0 warning, 0 suggestion.
Grounding: 3/3 paths, 2/2 symbols, 3/3 commands

## Lenses
| Lens | Result |
| --- | --- |
| all 13 lenses | PASS |

## Findings
None. One phase, test-after, criteria read the generated PDF text.
```
