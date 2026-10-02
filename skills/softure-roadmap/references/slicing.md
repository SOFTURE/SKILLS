# Slicing, foundations, ordering and parallel lanes

Read this while doing steps 5 to 9 of the procedure, and whenever an item feels too big, too
small, or horizontal.

## The vertical test

Ask of every item: **after this merges alone, can someone do something they could not do before,
or did a number we measure move?** If the honest answer is "no, but the next item can build on it",
the item is horizontal. Either fold it into the first item that needs it, or make it a foundation
with a named `Unlocks` (below).

An item is the right size when:

- one plan of 1 to 4 phases covers it, each phase verifiable on its own;
- it adds at most one migration;
- it has one primary surface (a screen, an endpoint family, a job), not three;
- it has at most three unknowns; more means research would be a project of its own;
- it can merge without a feature flag, or the flag is part of the item.

Size is expressed by these signals, never in hours, days, points or t-shirt sizes. Agent execution
is not linear in calendar time, and an estimate in the roadmap gets read as a promise.

## When an item is too big: split patterns

| Pattern | Example (booking app) |
|---|---|
| by user path: happy path first, edge paths after | "book a slot" first; "reschedule" and "cancel" as their own items |
| by data subset | one service type with a fixed duration first; variable durations later |
| by role | the client's view before the staff view, or the reverse if that is the first proof |
| walking skeleton plus enhancements | a bare booking flow end to end, then reminders, then deposits |
| read before write | staff see bookings before they can edit them |
| manual before automated | the owner enters opening hours in a form before a calendar import exists |
| fixed before configurable | one hard-coded cancellation window, then a setting |

## When an item is too small: fold it

A copy change, a single toggle, or a config value with no outcome of its own belongs inside the
item whose outcome it serves. A roadmap of twenty one-line items hides the order instead of
showing it.

## Foundations: the only horizontal work allowed

A foundation has no user-visible outcome by itself. It earns a row only when its block names what
it **unlocks**: specific item IDs, a blocking unknown it resolves, or a verification path a later
item needs (a seeded test account, an email sandbox). Rules:

- mark the outcome `(foundation) …` so nobody mistakes it for a feature;
- never scaffold a layer the baseline reports as `present`; if the baseline is wrong, fix the
  baseline first;
- no generic "data layer", "API layer" or "auth system" items; name the concrete capability
  ("(foundation) staff shifts stored and queryable");
- if it unlocks a single small item, fold it into that item instead.

## Every item traces to a source

Each item cites at least one PRD ID (`FR-n`, `NFR-n`, `G-n`) or, with `--from-feedback`, the
feedback point it answers. Something that surfaced in the interview but is in neither ("we should
also do offline mode") is **not** an item: it becomes an owner question under
`## Owner decisions and checks` if it is a real gap, or an entry in `context/backlog/<topic>.md`
if the owner chose to defer it. The roadmap orders what the PRD declares; it does not grow it.

## Ordering

1. Build the dependency graph: each item's prerequisites are other item IDs plus concrete external
   state ("clinic's SMTP account verified", "seed list of services"), never vague ("backend ready").
2. Sort topologically. No item may depend on one listed after it; no cycles.
3. Place the north star as early as its prerequisites allow. Do not delay it for symmetry.
4. Break the remaining ties by the goal from the interview:

| Goal | Tie-break |
|---|---|
| `feedback` | the item that exposes the riskiest assumption first, even if it demos worse |
| `quality` | foundations for observability and access control early, not after features |
| `simplicity` | the smallest viable item first; defer liberally |
| `speed` | strict `must` path; anything else is deferred, not queued at the end |
| `learning` | the item that touches the unfamiliar part first |

5. If an open owner question decides the order ("clients first or staff first?"), do not pick an
   order that prejudges it. The affected items are `blocked (<question>)` until it is answered.
6. Put a "finish" item last when the theme needs a measurement or review across items (for
   example, an end-to-end check of the whole booking flow on production data).

## Unknowns and blockers

- **Unknowns** are questions research can answer or the owner must decide:
  `- <question> (owner: research | <person>; blocks: yes | no)`. One with `blocks: yes` makes the
  row `blocked (<the question, short>)`.
- **External blockers** (a vendor, an account, a legal text, a design asset) go into
  Prerequisites as external state. If the team can resolve it alone, it is an unknown instead.
- Cross-cutting questions that gate several items go to `## Owner decisions and checks`, each
  naming the IDs it gates.

## Parallel lanes

A lane is one chain of prerequisites. Two items may run at the same time only if:

- their estimated file sets are disjoint (say "estimate": it comes from a quick search, not a plan);
- at most one of them adds a migration (`workflow.json` → `migrations`);
- neither changes a shared primitive (a layout, a design token file, an auth helper, a schema the
  other reads).

Give each hot file exactly one owner and write that down. Under `## Order`, show the lanes as a
small table `| Lane | Chain | Owns | Note |` with chains written as `BK-1 → BK-2 → BK-3`. Two to five
lanes; fewer than two means the order already reads as one line and the table is noise; more than
five usually means the graph is over-split. Every item appears in exactly one lane. When the main
risk is `capacity`, look harder for parallel lanes: they are the owner's best lever.

## Good and bad items

| Bad item | Why | Better |
|---|---|---|
| "Database schema for invoices" | horizontal; nothing observable after merge | "A freelancer creates an invoice and downloads it as PDF" (schema is inside) |
| "Invoicing module" | too big: create, send, remind, pay, export | split by path: create + PDF, then send by email, then reminders |
| "Change the button colour on the invoice page" | too small, no outcome | fold into the item whose screen it is |
| "Set up the API layer" | generic foundation, no `Unlocks` | "(foundation) invoice numbering is gap-free per year; unlocks IN-2, IN-4" |
| "Add analytics dashboard" (not in PRD) | invented scope | owner question or backlog entry |
| "Wiki search (2 days, M)" | estimate and size label | drop the estimate; split by data subset if it is big |
