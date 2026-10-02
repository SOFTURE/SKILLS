# Worked examples: shape notes

Read this before drafting `shape-notes.md`, and when unsure how much detail a section needs.
Three examples: a complete greenfield file, the sections a brownfield file adds or changes,
and a bad file with what is wrong with it.

## 1. Good: greenfield, complete

```markdown
---
project: "Kilnbook"
session: 1
context_type: greenfield
created: 2026-03-02
updated: 2026-03-04
status: accepted
---

# Shape notes: wheel and kiln booking for a members' pottery studio

## Problem
Members of a 40-person community pottery studio book the six wheels and the shared kiln
through a spreadsheet and a chat group. Double bookings happen about twice a week; the
studio manager, Ola, resolves each one by hand.
> "Every Sunday evening I spend an hour untangling who actually has wheel 3 on Tuesday."
> (Ola, studio manager)
Evidence: 23 double bookings counted in the chat history for January; one member cancelled
her pass in February and named the bookings as the reason.

## Who it is for
- Primary: the studio manager, who keeps the schedule fair and answers every complaint.
- Secondary: members on a monthly pass (8 sessions per month), booking from their phones.
- Not for: drop-in visitors who pay per visit (handled at the front desk), other studios.

## Access
Members sign in with an account the manager invites them to; there is no public sign-up.
The manager has one admin role. Members see who booked a wheel only as initials; they never
see another member's pass balance. Without signing in, nothing is visible.

## Today
A shared spreadsheet that anyone can edit, plus a chat group for swaps. When two names land
in one cell, the manager messages both and decides. Doing nothing costs her about four hours
a week and costs the studio members' trust.

## Why now
The studio grows from 40 to 60 members in April, when the second room opens. The
spreadsheet already breaks at 40.

## Appetite
Three weeks of part-time work (evenings), fixed. No hard deadline beyond "before the second
room opens on 15 April". The scope flexes, the time does not.

## Solution sketch
First flow:
1. A member signs in and sees this week's wheel slots, free and taken.
2. They book a free slot; one session is taken from their pass.
3. If no slot is free, they join the waitlist for that slot.
4. When someone cancels, the first person on the waitlist gets the slot offered.

Elements: weekly slot grid; booking with a pass balance; waitlist per slot; manager's view
of the day; mail when a waitlist slot opens (use `@softure-ai/mail`); sign-in (use
`@softure-ai/auth`).

## Core rule
A booking is confirmed only while the member has an unused session in this month's pass;
otherwise it joins the waitlist, and a freed slot is offered to the waitlist in order, each
offer held for 2 hours before it moves to the next member. (Shape: allocation.)

## Rabbit holes
- Kiln firing schedule: different rules (shelf space, temperature) → cut from round one;
  the kiln stays on the spreadsheet.
- Payments for passes → cut; passes are sold at the desk, the manager enters the balance.
- Recurring weekly bookings → time-box to 2 days; if it does not fit, drop it.

## No-gos
- No payments or invoicing in this round.
- No native mobile app; a phone-friendly web page is enough.
- No offline use.
- No support for other studios.

## Success signals
- Double bookings → 0 per week in the first month → manager's own weekly count.
- Manager's schedule time → under 30 minutes per week → she logs it for four weeks.
- Waitlist offers accepted → at least half → counted by the product.
- Guardrail: a member books a slot in under a minute on a phone, as today with the
  spreadsheet; the week's view opens without a noticeable wait.

## Open questions
- Can a member hold two slots on the same day? → Ola → before planning.
- How long before a session can a member cancel without losing it? → Ola → before planning.

## Forward notes
- Ola asked for "push notifications"; parked: mail covers the waitlist offer in round one.
- The studio already pays for a calendar subscription; nobody wants it integrated now.
```

Why this is good:
- The problem is stated without naming the solution, and it carries evidence (a quote, a
  count, a lost customer).
- The core rule is one sentence a spreadsheet cannot apply; it is what makes the product
  worth building.
- Every rabbit hole ends in a decision, and the appetite is a fixed budget.
- The user's solution ("push notifications") was not dropped: it is parked under
  `## Forward notes` with the reason.
- Success signals can be checked by someone other than the author.

## 2. Good: brownfield, the sections that differ

An invoicing tool for small agencies, adding recurring invoices. Only the sections that a
brownfield file adds or frames differently are shown.

```markdown
---
project: "Billdesk"
session: 3
context_type: brownfield
created: 2026-05-10
updated: 2026-05-12
status: accepted
---

# Shape notes: recurring invoices

## Current system
Billdesk is a web app used by about 300 small agencies to issue one-off invoices. Invoices
are numbered per year without gaps (a legal requirement for most customers), exported as PDF,
and sent by mail. A public API lets 40 customers create invoices from their own tools.
Retainer clients (the same amount every month) are invoiced by copying last month's invoice.

## Problem
Agencies with retainer clients copy an invoice every month and forget about one in ten.
> "We found three months of unbilled retainer in our yearly review." (support ticket #4182)
Evidence: 61 support tickets mentioning "copy invoice" or "repeat" in the last quarter.

## Core rule
Today: an invoice number is assigned when the invoice is issued, the next free number of the
year. Change: a schedule creates a draft on its date; the number is still assigned only when
the draft is issued, so drafts never consume numbers.

## Constraints and preserved behaviour
- Invoice numbers stay gapless per year, including invoices created from schedules.
- Existing invoices, their PDFs and their numbers do not change.
- The public API for creating invoices keeps working for the 40 existing integrations
  without any change on their side.
- Customers who never use schedules see no difference.

## No-gos
- No change to how one-off invoices are created or numbered.
- No automatic sending without a person issuing the draft (round one).
- No proration or usage-based amounts.
```

What makes it brownfield-shaped: the current system is described first and briefly; the
core rule states today's rule before the change; preserved behaviour is explicit, so the PRD
can turn each line into a `preserved` requirement.

## 3. Bad: solution first, nothing to build a PRD from

```markdown
# Shape notes: booking app

## Problem
Users need a modern booking app with a calendar, push notifications and payments.

## Who it is for
Everyone who does pottery.

## Solution sketch
React Native app, Firebase backend, Stripe for payments, Google Calendar sync, admin
dashboard with charts.

## Appetite
About 2 months, maybe more.

## Success signals
Users love it.
```

What is wrong, section by section:
- **Problem** names the solution (calendar, notifications, payments) and no pain, person,
  moment or cost. There is no evidence.
- **Who** is "everyone": there is no primary person to design the first flow for.
- **Solution sketch** is a technology list. Stack choices belong under `## Forward notes`;
  the sketch should be elements and a first flow.
- **Appetite** is an estimate ("about, maybe more"), not a budget, and it far exceeds what
  the problem justifies, because the problem was never stated.
- **Success signals** cannot be observed or measured.
- **Missing entirely:** today's workaround, why now, access, the core rule (as written, this
  is a calendar, which a spreadsheet already is), rabbit holes and no-gos.

The right response to this draft is not to polish it but to restart at phase 1 with the
question: "The last time a booking went wrong, what happened and who fixed it?"
