# Interviewing for a plan

Read this when preparing the questions in step 3 of softure-plan. The goal of the interview is
not to collect opinions. It is to make every decision that would otherwise be guessed during
implementation, and nothing more.

## Every artifact is a decision already made

Reading change.md, research.md and frame.md counts as listening to the user. A question whose
answer is already written down tells the user that their earlier work was ignored.

| Inputs | small | medium | large | What to skip |
| --- | --- | --- | --- | --- |
| research | 2-4 | 4-7 | 6-10 | anything research answers, with or without evidence |
| research + frame | 1-2 | 2-4 | 4-6 | also every problem question: frame owns the problem, you own the solution |

The numbers are a ceiling. Stop earlier when the answers stop changing the plan. Asking fewer
questions because the material is good is a success, not a shortcut.

When frame.md is present, take its problem statement as the task definition. If frame marks its
own confidence as low, put that in `## Risks and rollback` and spend one question on how to
proceed: verify first (a spike phase) or plan with the risk named.

## Problem questions and solution questions

Tag every candidate question before asking it:

- **[P] problem**: what is in or out, how success is judged from the user's side, what is a
  must-have versus a nice-to-have, how big the data or the audience is. Skip all of them when a
  frame exists.
- **[S] solution**: how the system should behave in a situation the requirements did not
  describe. Always allowed, because no upstream step decides them.

Categories worth checking, by complexity:

| Category | Tag | From |
| --- | --- | --- |
| Scope boundary (what is explicitly out) | P | small |
| Success as the user sees it | P | small |
| Priority: what gets cut first | P | small |
| Edge cases and failure modes (empty, duplicate, concurrent, partial) | S | small |
| Data model: columns, constraints, what existing rows get | S | medium |
| Error handling the user sees: message, retry, nothing | S | medium |
| Test depth: which cases deserve an e2e test | S | medium |
| Load and latency: expected volume, acceptable wait | S | medium |
| Architecture: sync or async, job or request, where state lives | S | large |
| Concurrency and conflicts: who wins, what the loser sees | S | large |
| Security model: who may call it, what they may see | S | large |
| Rollout and rollback: flag, staged migration, revert path | S | large |
| Observability: what tells us it broke in production | S | large |

Do not ask about implementation details the code already decides (the project's error type,
its test helpers, its folder layout). Find them and follow them.

## Shape of a question

- One question per message. Wait for the answer before the next one.
- 2-4 options. The recommended option comes first and carries `(Recommended)`.
- Each option: what it means, its strength, its trade-off, in one line. The recommendation
  cites the code, research or a lesson that justifies it.
- Options are mutually exclusive unless the question says "pick all that apply".
- The user may always answer in their own words.

## Worked examples

### 1. Booking app, medium, [S] concurrency

> Two people can open the same free slot at once. When both confirm, what should happen?
>
> 1. **Second confirmation fails with "this slot was just taken" (Recommended).** A unique
>    constraint on `(resource_id, starts_at)` rejects the second insert. Strength: no double
>    booking even under load, matches how `reservations` already guards rooms
>    (`src/db/schema.ts:88`). Trade-off: the loser re-picks a slot; we need one new message.
> 2. **Hold the slot for 5 minutes when it is opened.** Strength: the loser never fills in the
>    form for nothing. Trade-off: expiring holds need a job and a cleanup path; abandoned holds
>    hide free slots.
> 3. **Last confirmation wins.** Strength: no new code. Trade-off: one customer silently loses
>    a booking they were shown as confirmed. Acceptable only if double booking is harmless.

Why it is a good question: the requirements never described this case, each option changes
the plan (a constraint and a message, a job, or nothing), and the recommendation points at an
existing pattern in the code.

### 2. Invoicing tool, small, [P] scope (skip it when a frame exists)

> Reminders go out for overdue invoices. Should partially paid invoices get one too?
>
> 1. **Yes, for the remaining amount (Recommended).** Strength: matches the overdue filter on
>    the dashboard, which already counts partial payments as overdue (`src/invoices/status.ts:31`).
>    Trade-off: the email must show the remaining amount, not the total.
> 2. **No, only invoices with no payment at all.** Strength: simpler wording. Trade-off: the
>    dashboard and the reminders disagree about what "overdue" means.

### 3. Team wiki, large, [S] data for existing rows

> Pages get an owner. What do the 4,200 existing pages get?
>
> 1. **Their original author, backfilled in a separate, restartable step (Recommended).**
>    Strength: every page has a real owner from day one; the backfill can resume after a
>    failure. Trade-off: a second migration step after the column is added; pages whose author
>    left the team need a fallback owner (the space admin).
> 2. **No owner (nullable column), shown as "unowned".** Strength: one small migration.
>    Trade-off: the review reminders this change exists for skip most of the wiki.

## Bad questions, and why

- "Should we write tests?" There is one answer, and the skill already decides it (discipline).
- "Which folder should the new component go in?" The code decides; look at its neighbours.
- "Do you want reminders to be reliable?" Not a decision. Ask what happens on a failed send.
- "What is the scope?" Too open. Offer the two or three concrete boundaries that matter.
- Three questions in one message. The user answers the easiest one and the rest get lost.

## Playback before the questions

Before the first question, show that you understood. For example:

> We need overdue invoices to trigger one reminder email, three days after the due date,
> unless the client has reminders switched off.
>
> What shapes the plan:
> - invoices have no record of reminders today (`src/db/schema.ts:120`), so we need a column
>   to make "once" true;
> - the mail module is already configured for receipts (research §SOFTURE modules), so sending
>   is covered;
> - due dates are stored as dates without a time zone, so "three days after" needs a reference
>   zone.
>
> Complexity: medium. Data change, a scheduled job and one settings toggle; no new service.
> I expect 3 phases and about 4 questions. Does that match your view?

## Pushing back

- **A factual correction.** User: "The job runner already retries failed sends." Check before
  agreeing. If `src/jobs/runner.ts` has no retry, answer with the evidence: "I read
  `src/jobs/runner.ts:12-40`: a failed job is logged and dropped. Do you want retries added in
  this change, or is a failed reminder acceptable?"
- **Scope growth.** User: "While we are here, let us add SMS reminders." Answer: "SMS is not in
  change.md Intent and needs a new provider. Keep it out (I will add it to out of scope and the
  backlog), or extend change.md first?"
- **A costlier choice.** User picks the 5-minute hold. Say once: "That adds a job and a cleanup
  path, so one more phase." Then plan it.

## Confirming the outline

After the approach is clear, print the phases before writing them out:

> 1. Reminder state and eligibility rule: the column and a tested query that finds due invoices.
> 2. Sending job: the scheduled job sends once per invoice, safe to run twice.
> 3. Per-client switch: the settings toggle, respected by the job, with an e2e test.
>
> Looks right (Recommended) / Adjust / Merge phases / Split phases?

## `--auto`

No question is asked. For each question you would have asked, take the recommended option and
record it:

```markdown
## Decisions (auto)
- Partially paid invoices get a reminder? → yes, for the remaining amount (matches the dashboard overdue filter, src/invoices/status.ts:31)
- Reference time zone for "three days after due"? → the account's time zone (due dates are local business dates)
```
