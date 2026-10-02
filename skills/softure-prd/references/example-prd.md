# Worked examples: PRD

Read this before drafting `prd.md`. Four examples: a complete greenfield PRD (written from
the Kilnbook shape notes in `softure-shape/references/example-shape-notes.md`), the
brownfield parts for a change to an existing invoicing tool, a revision, and bad
requirements with their fixes.

## 1. Good: greenfield, complete

```markdown
---
project: "Kilnbook"
version: 1
status: accepted
context_type: greenfield
created: 2026-03-05
updated: 2026-03-06
source: shape-notes.md (session 1)
---

# PRD v1: wheel booking for a members' pottery studio

## Summary
- Problem: the studio manager spends about four hours a week resolving double bookings of
  six wheels, made through a shared spreadsheet (23 in January).
- Insight: the conflict is not the calendar, it is the pass: members book sessions they no
  longer have, and nobody knows who is next when a slot frees up.
- Who: the studio manager; members on a monthly pass.
- Outcome: no double bookings, and a freed slot reaches the next waiting member without the
  manager.
- Appetite: three weeks of part-time work; deadline: 15 April (second room opens).
- Product: phone-friendly web app; expected scale: dozens of users (40, growing to 60).
- Release boundary: wheel booking with passes and a waitlist; the kiln stays manual.

## Goals
- G-1: zero double bookings per week in the first month after release.
- G-2: the manager spends under 30 minutes a week on the schedule.
- G-3: at least half of waitlist offers are accepted.

## Non-goals
- Offline use — members book from the studio or from home, both online.
- Availability beyond studio needs — an hour of downtime at night is acceptable.

## Users
- Primary: the studio manager; she keeps the schedule fair, answers complaints and decides
  whether the studio adopts a tool. She reaches for it every Sunday evening and whenever two
  members claim one wheel.
- Secondary: members on a monthly pass of 8 sessions, booking from their phones.
- Not for: drop-in visitors (handled at the desk), other studios.

## Access control
Members sign in with their own account, created by the manager's invitation; there is no
open sign-up. One manager role can see and change every booking and set pass balances.
Members see other bookings only as initials and never see another member's balance. A
visitor who is not signed in sees only the sign-in page.

## Primary flow
1. A member signs in and sees this week's wheel slots, free and taken (FR-1, FR-2).
2. They book a free slot; one session is taken from their pass (FR-3).
3. With no free slot, they join the waitlist for it (FR-4).
4. When someone cancels, the first member on the waitlist is offered the slot (FR-5, FR-6).

## Business rules
A booking is confirmed only while the member has an unused session in this month's pass;
otherwise it joins the waitlist, and a freed slot is offered to the waitlist in order, each
offer held for 2 hours before it moves to the next member.

The inputs are the member's pass balance (set by the manager) and the order in which members
joined a slot's waitlist. The result is either a confirmed booking or a waitlist position.
Members meet the rule when booking (a full pass means waitlist only) and when an offer
arrives.

## Functional requirements
| ID | Requirement (observable behaviour) | Priority | Goal | Module |
|---|---|---|---|---|
| FR-1 | When invited by the manager, a person can create an account and sign in | must | G-1 | @softure-ai/auth |
| FR-2 | When signed in, a member sees this week's slots for every wheel as free or taken | must | G-1 | — |
| FR-3 | When a member with an unused session books a free slot, the slot is theirs and their balance drops by one | must | G-1 | — |
| FR-4 | When a slot is taken or the pass is used up, a member can join that slot's waitlist | must | G-3 | — |
| FR-5 | When a booking is cancelled, the first member on the waitlist receives an offer by mail | must | G-3 | @softure-ai/mail |
| FR-6 | When an offer is not accepted within 2 hours, it moves to the next member on the waitlist | must | G-3 | — |
| FR-7 | The manager sees one day's bookings for all wheels on one screen and can move or cancel any of them | must | G-2 | — |
| FR-8 | The manager can set each member's monthly pass balance | must | G-2 | — |
| FR-9 | A member can book the same weekly slot for the next four weeks in one step | could | G-2 | — |

### FR-3: Booking with a pass
Acceptance:
- Given a member with 3 unused sessions and a free slot, when they book it, then the slot
  shows as taken for everyone and their balance shows 2.
- Given a member with 0 unused sessions, when they open a free slot, then they can only join
  the waitlist, and the screen says why.
- Given two members booking the last free slot at the same moment, then exactly one gets it
  and the other is offered the waitlist.
Notes: a cancelled booking returns the session to the pass (cancellation window: OQ-2).
Challenge: "Members will hoard slots as soon as the month opens" → kept; the pass limits
each member to 8 sessions, and the manager can see and cancel hoarded slots (FR-7).

### FR-6: Offer timeout
Acceptance:
- Given an offer sent at 10:00 and not accepted, when it is 12:00, then the next member on
  the waitlist receives the offer and the first one can no longer accept it.
- Given an empty waitlist, when a slot is cancelled, then the slot simply shows as free.
Challenge: "Two hours is too long for a slot that starts in one hour" → changed: the offer
lasts 2 hours or until 30 minutes before the slot starts, whichever comes first.

## Non-functional requirements
- NFR-1: a member can book a free slot on a phone in under 60 seconds from opening the page.
- NFR-2: the weekly view shows within 1 s for a studio with 60 members.
- NFR-3: works on the two latest major versions of the common mobile and desktop browsers.

## Success metrics
| Metric | Baseline | Target | How measured | When checked |
|---|---|---|---|---|
| Double bookings per week | about 6 (January) | 0 | manager's weekly count | weekly, first month |
| Manager's schedule time | about 4 h/week | under 30 min/week | manager's own log | after 4 weeks |
| Waitlist offers accepted | none today | at least 50% | counted by the product (FR-5, FR-6) | after 4 weeks |

### Guardrails
- Booking stays as fast as the spreadsheet: under 60 seconds on a phone (NFR-1).
- No member sees another member's pass balance.

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Members keep using the spreadsheet | medium | high | manager announces a switch date; the spreadsheet becomes read-only that day |
| Offer mails land in spam | medium | medium | members see open offers on the weekly view as well |
| Recurring booking (FR-9) eats the budget | medium | low | time-boxed to 2 days; dropped if it does not fit |

## Out of scope
- Kiln firing schedule — different rules; stays on the spreadsheet; later.
- Payments for passes — sold at the desk; later, maybe never.
- Native mobile app — a phone-friendly web page covers it; later if members ask.
- Support for other studios — never in this product line.

## Open questions
- OQ-1: Can a member hold two slots on the same day? → owner: studio manager → needed by:
  plan of FR-3 → blocking: no (default: yes).
- OQ-2: How long before a slot can a member cancel and keep the session? → owner: studio
  manager → needed by: plan of FR-3 → blocking: yes.

## Changelog
- v1 2026-03-05: first version from shape-notes session 1.
```

Why this is good:
- Every FR is something a person can observe; none names a table, a vendor or a mechanism.
  The only product names are in the `Module` column, as reuse markers.
- The primary flow points at FRs, so a missing requirement would show as a step without one.
- The core rule is one sentence, and FR-3, FR-4 and FR-6 implement exactly that rule.
- Acceptance includes the empty case (empty waitlist), the failure case (no sessions left)
  and the race (two members, one slot).
- The challenge on FR-6 changed the requirement; the challenge on FR-3 was answered and kept.
- An open question is marked blocking because it changes a `must` FR.
- Nothing was invented: the NFR numbers the shape notes left vague ("without a noticeable
  wait" became NFR-2's 1 s, browser support became NFR-3) were proposed in step 3 with a
  recommended value and confirmed by the owner before they were written.

## 2. Good: brownfield, the parts that differ

Billdesk, an invoicing tool for small agencies, adds recurring invoices (shape notes:
`softure-shape/references/example-shape-notes.md`, section 2).

```markdown
## Current system
- Purpose: issue, export and send one-off invoices for small agencies.
- Shape: web app, public API for invoice creation, nightly mail digest.
- Stack: TypeScript web app on a relational database; PDF rendering service.
- Users today: about 300 agencies; 40 of them create invoices through the API.
- Today in this area: retainer invoices are made by copying last month's invoice by hand.

## Business rules
Today: an invoice gets the next free number of the year when it is issued.
Change: a schedule produces a draft on its due date; the draft gets a number only when a
person issues it, so drafts never use up numbers and the sequence stays gapless.

## Functional requirements
| ID | Requirement (observable behaviour) | Change | Priority | Goal | Module |
|---|---|---|---|---|---|
| FR-1 | When a user sets a schedule on an invoice (monthly, on day N), a draft copy appears on each due date | new | must | G-1 | — |
| FR-2 | When a scheduled draft is waiting, the user is reminded by mail on its due date | new | must | G-1 | @softure-ai/mail |
| FR-3 | The invoice list shows which invoices came from a schedule (was: no source shown) | modified | should | G-2 | — |
| FR-4 | Invoice numbers stay gapless per year, whether issued by hand or from a schedule | preserved | must | G-2 | — |
| FR-5 | Creating an invoice through the public API works exactly as before for existing integrations | preserved | must | G-2 | — |
| FR-6 | Customers who never set a schedule see no new step in creating an invoice | preserved | must | G-2 | — |

## Compatibility and preserved behaviour
- Contracts: the public invoice-creation API keeps its requests and responses unchanged;
  PDF layout and numbering format are unchanged.
- Existing data: invoices issued before the change keep their numbers, PDFs and history.
- Rollout: schedules are offered to all customers at once; nothing changes until a customer
  sets one, so there is no fallback path to keep.

## Success metrics
### Guardrails
- Zero gaps in invoice numbering across all customers (checked weekly for the first month).
- No change in API error rate for the 40 integrations in the first two weeks.
```

What makes it brownfield: the current system is the baseline, the business rule shows today
before the change, and everything that must not break is a `preserved` FR with acceptance
criteria of its own, not a line in non-goals.

## 3. A revision (v1 → v2)

The studio decides the kiln cannot wait. The PRD is revised, not rewritten:

```markdown
| ~~FR-9~~ | ~~A member can book the same weekly slot for the next four weeks in one step~~ | could | G-2 | — |
| FR-10 | When signed in, a member can reserve a shelf in the next kiln firing | must | G-4 | — |

### ~~FR-9~~: dropped in v2
Reason: no member asked for it during the first month; budget moved to the kiln (FR-10).

## Changelog
- v2 2026-04-20: added G-4 and FR-10 (kiln shelves) after the owner moved the kiln into
  scope; dropped FR-9 (no demand). Roadmap items citing FR-9: KB-6.
- v1 2026-03-05: first version from shape-notes session 1.
```

IDs are not renumbered: FR-9 stays, struck through, and the new requirement takes FR-10. The
previous accepted version was archived to `foundation/archive/2026-04-20-prd.md` first.

## 4. Bad requirements and their fixes

| Bad | What is wrong | Better |
|---|---|---|
| FR: The system should be user-friendly. | Not observable, not testable. | NFR: a new member books their first slot without help in under 2 minutes (checked with 3 members). |
| FR: Add a bookings table and an API endpoint for it. | Implementation, not behaviour. | FR: When a member books a free slot, it shows as taken for everyone. |
| FR: Members can manage bookings. | "Manage" hides four behaviours, each with its own rules. | Separate FRs for book, cancel, join the waitlist, accept an offer. |
| FR: Use AI to suggest the best slot. | Names a mechanism; the rule is missing. | Rule first: "a member is offered the earliest free slot on their usual weekday"; the FR states what they see. |
| Goal: Improve the booking experience. | No number, no yes/no check. | G-1: zero double bookings per week in the first month. |
| Out of scope: (empty) | Nothing excluded means the scope is not shaped. | Name what was cut in shaping: kiln, payments, native app. |
| Business rules: Users can create, edit and delete bookings. | Plain CRUD; no rule the product applies. | `TODO: core rule (OQ-3)` with a blocking question, until the owner states the rule. |
