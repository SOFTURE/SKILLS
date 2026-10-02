# Worked example: a plan, good and bad

Read this before writing a plan in a repo for the first time, or when unsure how concrete a
step or a criterion should be. The domain is a small invoicing tool (TypeScript, Postgres, a
job scheduler, server actions). Paths and names are illustrative. The commands come from
`context/workflow.json`; the plan never spells them out itself.

The plan below is the version *after* softure-plan-review. The review that produced it is in
`softure-plan-review/references/review-example.md`.

## Good: `overdue-invoice-reminders`

```markdown
# Plan: overdue-invoice-reminders

Input: change.md, research.md. Complexity: medium.

## Goal
Every unpaid or partially paid invoice receives exactly one reminder email three days after
its due date, unless its client has reminders switched off. "Exactly one" holds when the job
runs twice, runs late, or two instances run at once.

**Out of scope:** second and later reminders; SMS; reminder wording per client; a reminder
history screen (backlog: `context/backlog/invoicing.md`).

## Approach
**Starting point:** invoices carry `due_on date` and `paid_cents` (`src/db/schema.ts:120-141`);
nothing records a reminder. The scheduler runs `src/jobs/*.ts` every 15 minutes
(`src/jobs/registry.ts:8`). Receipts already go through the SOFTURE mail module
(`softure.config.ts:22`).

**Chosen:** a scheduled job that selects eligible invoices and claims each one with a
conditional update before sending - one row, one claim, one email.
Rejected: send on invoice view (no view, no reminder); a queue per invoice created at issue
time (needs a queue we do not run, and re-dating an invoice would leave stale entries).

**Key decisions:**
| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Partially paid invoices | included, remaining amount shown | dashboard already treats them as overdue | owner |
| Reference time zone | the account's `time_zone` | due dates are local business dates | research |
| Duplicate protection | `UPDATE ... WHERE reminder_sent_at IS NULL RETURNING id` | works across instances without a lock table | plan |
| Mail | SOFTURE mail module | covered, already configured | research |
| Failed send | release the claim, retry on the next run | a lost reminder is worse than a late one | owner |

**Critical details:** claim first, send second, release on failure. Sending first and marking
afterwards double-sends whenever two instances overlap, and the scheduler does overlap during
deploys (research §Risks).

## Phase 1: Reminder state and eligibility rule
**Discipline:** TDD. **Files:** `drizzle/0042_invoice_reminders.sql`, `src/db/schema.ts`,
`src/invoices/reminders.ts`, `src/invoices/reminders.test.ts`

1. `drizzle/0042_invoice_reminders.sql`: add `invoices.reminder_sent_at timestamptz null` and
   `clients.reminders_enabled boolean not null default true`. Forward-only, because both are
   additive; rollback is dropping the two columns, no data depends on them yet.
2. `src/db/schema.ts`: mirror both columns.
3. `src/invoices/reminders.ts`: `findInvoicesDueForReminder(db, now): Promise<InvoiceId[]>`.
   Intent: one query that is the single definition of "due for a reminder". Contract: returns
   ids where `due_on + 3 days <= local date of now in the account's zone`, remaining amount
   > 0, `reminder_sent_at is null`, client `reminders_enabled`.

**Tests:** due exactly 3 days ago (selected); 2 days ago (not); fully paid (not); partially
paid (selected); already reminded (not); client switched off (not); account in a zone where
`now` is still the previous day (not); no invoices (empty list).

**Done when:**
- Automated: the eight cases above pass in `src/invoices/reminders.test.ts`; the migration
  applies on a copy of the dev database and both columns exist with the stated defaults;
  Gates green (typecheck, lint, test).

## Phase 2: Sending job, safe to run twice
**Discipline:** TDD. **Files:** `src/jobs/send-invoice-reminders.ts`,
`src/jobs/send-invoice-reminders.test.ts`, `src/jobs/registry.ts`,
`src/mail/templates/invoice-reminder.ts`, `messages/en.ts`

1. `src/jobs/send-invoice-reminders.ts`: for each id from `findInvoicesDueForReminder`, claim
   with `UPDATE invoices SET reminder_sent_at = now() WHERE id = $1 AND reminder_sent_at IS
   NULL RETURNING id`; send only when a row came back; on a send failure, set
   `reminder_sent_at` back to null and log the invoice id and the error.
2. `src/mail/templates/invoice-reminder.ts`: subject and body with invoice number, remaining
   amount and payment link; copy lives in `messages/en.ts`.
3. `src/jobs/registry.ts`: register the job on the existing 15-minute schedule.

**Tests:** two concurrent runs over the same invoice send one email; a failed send leaves
`reminder_sent_at` null and the next run sends; an empty selection sends nothing.

**Done when:**
- Automated: the three cases above pass; after one run against the dev database,
  `select count(*) from invoices where reminder_sent_at is not null` equals the eligible
  count taken before the run, and a second run sends 0; Gates green (typecheck, lint, test).
- Manual: the reminder email reads correctly in a real inbox, amount and link included.

## Phase 3: Per-client switch
**Discipline:** test-after. **Files:** `src/app/clients/[id]/settings-form.tsx`,
`src/app/clients/[id]/actions.ts`, `messages/en.ts`, `e2e/client-reminders.spec.ts`

1. `src/app/clients/[id]/actions.ts`: `setRemindersEnabled` server action; checks the user
   owns the client, not just that a session exists.
2. `src/app/clients/[id]/settings-form.tsx`: a labelled toggle bound to the action, with the
   pending state of the existing form controls.

**Tests:** e2e: switching off reminders for a client, then running the job, sends nothing for
that client's overdue invoice; a user without access to the client gets 403 from the action.

**Done when:**
- Automated: the e2e spec passes; the action rejects a foreign client id; Gates green
  (typecheck, lint, test).
- Manual: the toggle reads clearly in the settings screen at phone width.

## Risks and rollback
- Mail provider outage → claims are released, reminders go out on the next run; nothing lost.
- A bug in the eligibility rule mass-sends → the job is gated by its registry entry: removing
  it (one-line revert of phase 2) stops sending immediately; `reminder_sent_at` shows who got
  one.
- Revert per phase: phase 3 and 2 by reverting their commits; phase 1 by a down migration that
  drops the two columns.

## Progress

> `- [ ]` pending, `- [x]` done. A phase ends with ` — <commit sha>` on its done items. Never rename items.

### Phase 1: Reminder state and eligibility rule

#### Automated
- [ ] 1.1 Eight eligibility cases pass in `src/invoices/reminders.test.ts`
- [ ] 1.2 Migration 0042 applies on a dev copy; both columns exist with their defaults
- [ ] 1.3 Gates green (typecheck, lint, test)

### Phase 2: Sending job, safe to run twice

#### Automated
- [ ] 2.1 Concurrent runs send one email; failed send releases the claim; empty selection sends nothing
- [ ] 2.2 Dev run: reminded count equals the eligible count before the run; second run sends 0
- [ ] 2.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 2.4 Reminder email reads correctly in a real inbox, amount and link included

### Phase 3: Per-client switch

#### Automated
- [ ] 3.1 E2E: switched-off client gets no reminder after a job run
- [ ] 3.2 `setRemindersEnabled` rejects a client the user does not own
- [ ] 3.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 3.4 Toggle reads clearly in client settings at phone width
```

What makes it good:

- The goal is measurable and names the hard case ("exactly one", even under overlap).
- Every key decision has a source; the owner's two answers are visible without the transcript.
- Each phase is a working slice: after phase 1 nothing is sent yet, but the rule is proven and
  the data is ready; after phase 2 reminders work for everyone; phase 3 adds the opt-out.
- The one piece of SQL in the plan is there because its exact shape is the whole safety
  argument. Everything else is intent and contract.
- Criteria read real rows, not the UI.

## Bad: the same change, planned badly

```markdown
# Plan: overdue-invoice-reminders

## Goal
Add invoice reminders.

## Approach
We will add reminders using a job. Email provider: TBD (maybe the mail module or SMTP).

## Phase 1: Database
- [ ] Add the needed columns.

## Phase 2: Backend
- [ ] Implement the reminder logic and handle errors properly.
  ```ts
  export async function sendReminders() {
    const invoices = await db.select().from(invoicesTable);
    for (const invoice of invoices) { ... 60 more lines ... }
  }
  ```

## Phase 3: Frontend
- [ ] Add a toggle. Make sure it looks good.

## Progress
- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3
```

Why it is bad:

- **Goal is an activity**, not an outcome. Nobody can tell when it is done, and "exactly once"
  is never stated, so the double-send race is never planned for.
- **An open question** ("TBD", "maybe") moves a design decision into implementation, and ignores
  the module research found.
- **Horizontal phases**: after phase 1 and phase 2 nothing a user can see works, and the
  pieces meet for the first time in phase 3.
- **Unverifiable criteria**: "needed columns", "handle errors properly", "looks good".
- **Code dump** for a routine loop, while the one thing that needed precision (the claim
  query) is missing.
- **No files, no discipline, no tests, no data safety, no rollback.**
- **Checkboxes in phase blocks** and a Progress section that does not follow the format, so
  softure-implement cannot find a resume point.
