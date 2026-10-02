# Example research.md

A fictional invoicing tool (Next.js, Postgres via drizzle, a nightly job runner). The change is
roadmap item **INV-4**: "Send a reminder e-mail when an invoice is 7 days overdue." Roadmap
Unknowns: *Do we already track when an invoice became overdue? Can we send mail today, and how?*

Use it for the level of detail, not for the content.

## Good

```markdown
# Research: overdue-invoice-reminders

Input: change.md, roadmap INV-4, research.sources (docs/billing.md). Depth: deep (customer-facing mail, money-adjacent).
Snapshot: 3f9c2e1 on main, 2026-10-02 10:14 Europe/Warsaw.

## Summary
- "Overdue" is not stored; it is computed on read from `due_date < today` (src/invoices/status.ts:12-31). There is no timestamp of when an invoice became overdue.
- "7 days overdue" can be computed from `due_date + 7` without a new column, but "send once" needs a record of sent reminders. Nothing like it exists.
- Mail already goes out through `@softure-ai/mail` for receipts (src/mail/send-receipt.ts:8); its template and unsubscribe handling cover reminders. Module verdict: covered.
- The nightly runner (jobs/nightly.ts:20) runs at 02:00 server time and already iterates invoices for the ageing report, so a reminder step fits there.
- Main risk: double sends when the job is retried. The runner retries on failure (jobs/runner.ts:44) and has no idempotency key.
- One escalation: whether partially paid invoices get a reminder (business rule).

## Current state
1. An invoice is created in `createInvoice` (src/invoices/actions.ts:40-88) with `due_date` = issue date + `payment_terms_days` (default 14, src/invoices/defaults.ts:3).
2. Status is derived, never stored: `getInvoiceStatus` returns `paid` when `paid_cents >= total_cents`, `overdue` when `due_date < today` and not paid, else `open` (src/invoices/status.ts:12-31). "today" is computed with `startOfDay(new Date())` in server time, not in the account's time zone (status.ts:14).
3. The ageing report job calls `listUnpaidInvoices()` (src/invoices/queries.ts:55) once per night (jobs/nightly.ts:20-37).
4. Receipts are sent with `sendMail({ template: "receipt", to, data })` from `@softure-ai/mail` (src/mail/send-receipt.ts:8-19); the unsubscribe link is added by the module.

## Affected surface
| Area | Files | Why |
| --- | --- | --- |
| Job | jobs/nightly.ts, jobs/runner.ts | new step; retry behaviour matters |
| Query | src/invoices/queries.ts | needs "unpaid and due_date = today - 7" |
| Mail | src/mail/, messages/en.ts | new template and copy |
| Schema | src/db/schema.ts, drizzle/ | record of sent reminders |

## Data
- `invoices`: `due_date date not null`, `total_cents int`, `paid_cents int default 0` (src/db/schema.ts:31-52). No status column.
- Dev DB, read-only query: 1,204 invoices, 87 unpaid past due, 9 with `paid_cents` between 1 and `total_cents - 1` (partially paid).
- No table records sent mail per invoice. `mail_log` exists but stores only template and recipient, no invoice id (schema.ts:90-98).

## Tests
- `src/invoices/status.test.ts` covers paid/open/overdue, but not the day boundary or time zone.
- `jobs/nightly.test.ts` runs the ageing step against PGlite; run with `npm test -- jobs/`.
- No test covers runner retries. Gap.

## Patterns to follow
- Jobs are plain async functions registered in `jobs/registry.ts:5-18`, each step wrapped in `withJobLog` (jobs/nightly.ts:22).
- Mail templates live in `src/mail/templates/<name>.tsx` with copy in `messages/en.ts` (example: receipt.tsx).

## Prior work
- `context/archive/2026-08-14-payment-terms/plan.md`: chose to derive status instead of storing it, "to avoid a backfill"; still true in code.
- `git log --follow jobs/runner.ts`: retries added in a1b2c3d after a timeout incident; no idempotency was added then.
- No earlier change touched reminders.

## SOFTURE modules
- Mail: **covered** by `@softure-ai/mail` (templates, unsubscribe, sending log). Configure a `reminder` template in `softure.config.ts`.
- Scheduling: not applicable (the project has its own runner).

## Risks
- Double send on job retry: likely (retries exist, no idempotency). Mitigation idea: a unique `(invoice_id, kind)` row written in the same transaction as the send decision.
- Day boundary in server time instead of account time zone: medium; reminders a day early or late for accounts far from the server. See L-012.
- Volume: 87 overdue today; no throttling needed at this size.

## Relevant lessons
- L-012 "Compute day boundaries in the account time zone": status.ts:14 violates it today; the reminder query would inherit the bug.

## Answers to unknowns
- *Do we track when an invoice became overdue?* No. It is derived from `due_date` (status.ts:12-31); "7 days overdue" = `due_date = today - 7` in the account zone.
- *Can we send mail today, and how?* Yes, `@softure-ai/mail` (send-receipt.ts:8-19), unsubscribe included.

## Open questions
- Should the reminder fire once or every 7 days? **Decided** by owner on 2026-10-02: once.
- Do partially paid invoices get a reminder? **Escalated**: business rule. Options: (a) yes, with the remaining amount; (b) no, only fully unpaid. 9 invoices today.
- Does the runner run exactly once per night? **Answered**: no, it retries up to 3 times (runner.ts:44).
```

Why it works: the snapshot pins what was read; every claim has a location; the data section
uses a real read-only query; absence ("no test covers retries", "no earlier change") is stated;
the risk names a mechanism, not a worry; the escalation gives options and their size.

## Bad

```markdown
## Summary
Invoices have statuses and there is a mail system. We should add a `reminded_at` column and a cron job.

## Current state
`status.ts` handles statuses. `mail/` sends e-mails.

## Risks
Possible edge cases with dates.

## Open questions
- What about partial payments?
```

What is wrong:
- It proposes a solution (`reminded_at`, a cron job) instead of describing what exists.
- "Has statuses" is false: status is derived, and the plan built on this would add a backfill.
- File names without line references or behaviour; nobody can verify them.
- "Edge cases with dates" names no mechanism; the real one (server-time day boundary, L-012) is missed.
- The open question has no state: not answered, decided or escalated.
- No module verdict, no tests, no prior work, no snapshot.
