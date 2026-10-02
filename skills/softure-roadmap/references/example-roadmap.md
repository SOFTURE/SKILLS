# Worked example: a booking app roadmap

Read this before writing your first roadmap in a project, or when unsure how the contract format
(WORKFLOW §5) holds the framing, baseline and lanes. The domain is invented: **Slotbook**, online
booking for one physiotherapy clinic.

## The input (PRD v2, excerpt)

- **G-1:** clients book without calling. Target: half of all bookings online within 8 weeks.
- **FR-1** (must): a visitor sees the free slots of a service for the next 14 days.
- **FR-2** (must): the clinic owner sets opening hours and staff shifts.
- **FR-3** (must): a visitor books a free slot and receives a confirmation email.
- **FR-4** (must): a client cancels through the link in the email.
- **FR-5** (must): cancellation is refused inside the clinic's cancellation window.
- **FR-6** (must): staff see the bookings of the day.
- **FR-7** (should): a reminder email goes out 24 hours before the visit.
- **FR-8** (could): a deposit is taken at booking.
- **NFR-1:** the free-slot page answers in under 500 ms at p95. **NFR-2:** no slot is ever booked twice.
- Open questions: how long is the cancellation window? Which payment provider?

Interview result: optimise for `speed` (summary: "live before the spring season"); first proof
`BK-2`; main risk `decisions` (the window question gates FR-5).

Baseline from the probes: UI and server present (one web app, staff login through
`@softure-ai/auth`), data present (Postgres, migrations in `drizzle/`), mail absent, CI present,
observability partial (logs only).

## The output: `context/foundation/roadmap.md`

```markdown
---
project: "Slotbook"
roadmap: booking-mvp
version: 1
status: ready
prd_version: 2
updated: 2026-10-01
---

# Roadmap booking-mvp: clients book and manage visits online

> Run-wide orders, read by orchestrators (not parsed):
> - Push main branch: no
> - Archive roadmap: at the end
> - Parallelism: up to 2 at once
> - Owner at the keyboard: BK-6 (payment provider account)

## At a glance

| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **BK-1** | `clinic-availability-model` | (foundation) hours, shifts and bookings stored; free slots computable | — | autonomous | ready |
| **BK-2** | `visitor-books-free-slot` | a visitor books a free slot and gets a confirmation email | BK-1 | autonomous | ready |
| **BK-3** | `client-cancels-by-link` | a client cancels from the email link, outside the window | BK-2 | autonomous | blocked (cancellation window not decided) |
| **BK-4** | `staff-day-view` | staff see the day's bookings on one screen | BK-1 | autonomous | ready |
| **BK-5** | `visit-reminder-email` | clients get a reminder 24 hours before the visit | BK-2 | autonomous | ready |
| **BK-6** | `deposit-at-booking` | a deposit is taken when a visitor books | BK-2 | owner | proposed |
| **BK-7** | `booking-flow-check` | the online share of bookings is measured against G-1 | BK-2, BK-3, BK-4 | autonomous | ready |

## Order

**Optimising for:** speed (owner, interview 2026-10-01; PRD summary "live before the spring season").
**First proof:** BK-2, the first item that shows a visitor can book without calling (G-1).
**Main risk:** decisions. The cancellation window is open and gates BK-3; see owner decisions.
**Depth:** data (NFR-2 forbids double booking); UI and infrastructure stay simple.

BK-1 comes first because both the public flow and the staff view read the same availability
rules; building them twice would let the two disagree. BK-2 follows at once as the first proof.
BK-4 runs next to BK-2. BK-5 waits for BK-2 because both edit the mail templates. BK-6 is
`proposed` (FR-8 is a `could` and needs the owner's payment account). BK-7 closes the theme.

### Starting point (codebase, 2026-10-01)
- UI: present (`app/`, one Next.js app). Server: present (route handlers in `app/api/`).
- Data: present (Postgres, `drizzle/`, 12 migrations). Auth: present (`@softure-ai/auth`, staff only).
- Mail: absent. BK-2 adopts `@softure-ai/mail` instead of building a sender.
- CI: present (`.github/workflows/tests.yml`). Observability: partial (request logs, no error tracking).

### Lanes
| Lane | Chain | Owns (estimate) | Note |
| --- | --- | --- | --- |
| A | BK-1 → BK-2 → BK-3 → BK-5 | `lib/availability/**`, `app/(public)/book/**`, `mail/templates/**`, the only migrations | the must path |
| B | BK-4 | `app/(staff)/day/**` | parallel with BK-2 once BK-1 is merged; reads bookings, no migration |
| C | BK-6 → BK-7 | `app/(public)/book/deposit/**`, `scripts/booking-share.mts` | BK-6 only after the owner's decision |

Deferred: SMS reminders (raised in the interview, not in the PRD) → `context/backlog/booking.md`.

## Items

### BK-1: Availability model
- **Change ID:** `clinic-availability-model`
- **Status:** ready
- **Outcome:** (foundation) opening hours, staff shifts and bookings are stored; the free slots of
  a service for any day can be computed by one function.
- **Unlocks:** BK-2 (public slots), BK-4 (staff view); NFR-2 is enforced here by a unique constraint.
- **Prerequisites:** —
- **Touches (estimate):** `lib/availability/**`, `drizzle/` (one migration), owner settings form.
- **Unknowns:**
  - Do shifts repeat weekly or per date? (owner: research, from FR-2 acceptance; blocks: no)
- **Risk:** first because two items read it; a wrong slot rule here would surface in both.
- **Baseline:** no availability data; after: a test computes the free slots of a seeded week.
- **PRD refs:** FR-2, NFR-2

### BK-2: A visitor books a free slot
- **Change ID:** `visitor-books-free-slot`
- **Status:** ready
- **Outcome:** a visitor picks a service, sees free slots for 14 days, books one and receives a
  confirmation email.
- **Prerequisites:** BK-1; a sending domain verified for the clinic (external).
- **Touches (estimate):** `app/(public)/book/**`, `mail/templates/confirmation.*`, `softure.config.ts`.
- **Unknowns:**
  - Two visitors pick the same slot at once: which one wins, and what does the other see?
    (owner: research; blocks: no)
- **Risk:** the first proof; it goes as early as BK-1 allows.
- **Baseline:** 0 online bookings; after: a test books a slot and finds the email in the sandbox;
  slot page p95 measured against NFR-1.
- **PRD refs:** FR-1, FR-3, NFR-1, NFR-2, G-1

### BK-3: A client cancels from the email
- **Change ID:** `client-cancels-by-link`
- **Status:** blocked (cancellation window not decided)
- **Outcome:** a client cancels from the link in the confirmation email; inside the window the
  page says why it cannot.
- **Prerequisites:** BK-2; the owner's answer on the window.
- **Touches (estimate):** `app/(public)/cancel/**`, `lib/availability/cancel.ts`.
- **Unknowns:**
  - How long is the cancellation window? (owner: clinic owner; blocks: yes)
- **Risk:** small code, but building it before the answer means building it twice.
- **Baseline:** cancellations by phone only; after: a test cancels outside and inside the window.
- **PRD refs:** FR-4, FR-5

(BK-4 to BK-7 follow the same shape.)

## Before the next release
- [ ] Set `MAIL_FROM` and the mail provider key in production (**BK-2**)

## Owner decisions and checks
- [ ] **BK-3**: decide the cancellation window (hours before the visit). Gates BK-3.
- [ ] **BK-6**: choose the payment provider and open the account. Gates BK-6.

## Done
```

What makes it good:

- every `must` FR appears in a `PRD refs` line; FR-7 and FR-8 are covered or explicitly `proposed`;
- the one foundation names what it unlocks and does not scaffold anything the baseline reports present;
- the north star sits right after its only prerequisite; the order paragraph says why;
- the open question became a `blocked` row plus an owner line, not a guess;
- lanes have disjoint file sets and all migrations sit in lane A;
- mail is adopted from a module rather than built;
- no estimates, no dates other than the framing date, no implementation steps.

## A bad version of the same roadmap

```markdown
| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **BK-1** | `database` | All tables | — | autonomous | ready |
| **BK-2** | `backend-api` | API for bookings (3 days) | BK-1 | autonomous | ready |
| **BK-3** | `frontend` | Booking UI | BK-2 | autonomous | ready |
| **BK-4** | `sms-reminders` | SMS reminders | BK-3 | autonomous | ready |
| **BK-5** | `cancel` | Cancel | BK-6 | autonomous | ready |
```

Why each row fails the self-review:

- BK-1 to BK-3 are layers. Nothing is usable until all three merge, and they cannot run in parallel.
- "(3 days)" is an estimate; the roadmap orders work, it does not schedule it.
- BK-4 is not in the PRD (SMS appeared in a conversation); it should be a backlog entry.
- BK-5 depends on BK-6, which does not exist, and is `ready` although the window is undecided.
- `database`, `cancel`: change ids that name an activity or a layer, not an outcome.
- There are no item blocks, so the table cannot be checked against them.

## Handoff message after writing

```
Roadmap written: context/foundation/roadmap.md (booking-mvp, v1)
Optimising for speed; first proof BK-2; main risk: decisions.
Items: 7 (ready 5, blocked 1, proposed 1). PRD coverage: 6/6 must FRs. Owner decisions: 2.

Next: softure-new clinic-availability-model (BK-1). It is the only prerequisite of the first
proof BK-2 and of BK-4, so it opens both lanes.
Then: BK-2 and BK-4 in parallel, then BK-5.
Waiting on you: the cancellation window (unblocks BK-3), the payment provider (BK-6).
```

## The `## Summary` appended by `--close`

```markdown
## Summary

| ID | Item | What changed | Merge |
| --- | --- | --- | --- |
| BK-1 | Availability model | hours, shifts and bookings stored; slot function with tests | 4f2a9c1 |
| BK-2 | Visitor books a free slot | public booking with confirmation email (`@softure-ai/mail`) | 9b03e77 |
| BK-3 | Client cancels by link | cancellation up to 24 h before the visit | c1d5a20 |
| BK-4 | Staff day view | one screen with the day's bookings | 77e0b4d |
| BK-5 | Visit reminder | reminder email 24 h before | 2aa61f8 |
| BK-7 | Booking flow check | online share 41% after 3 weeks (target 50% at 8) | e9f1c03 |

Carried over: BK-6 (owner: payment provider) → `roadmaps/roadmap-payments.md`.
Integration: green 212/212 on e9f1c03.
```
