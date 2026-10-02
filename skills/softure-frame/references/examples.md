# Example frames

Two complete frames in fictional projects, then a bad one. Use them for depth and tone, not
content.

## 1. Value shape: team wiki search

Change `wiki-full-text-search`. change.md Intent: "Find any page by its content." The
request in the roadmap: "Add Elasticsearch-backed full-text search."

```markdown
# Frame: wiki-full-text-search

## Request as stated
"Add Elasticsearch-backed full-text search" (roadmap WK-7, quoting a team lead in the feedback thread).

## Observation, premise, direction
- Observation: people say they "cannot find pages"; 14 messages in the feedback thread since July.
- Stated cause or premise: search only matches titles, so content is invisible.
- Proposed direction: run an Elasticsearch cluster and index every page.

## Premise check
- Do nothing for 3 months: people keep asking in chat; no data loss, no revenue impact.
- Evidence: search log (research.md, Data) shows 2,310 searches in 30 days, 41% with zero results; sampling 50 zero-result queries, 34 are words that appear in page bodies. The premise holds.
- Already solved elsewhere: Postgres is already the store; `tsvector` full-text search is available with no new service. No SOFTURE module covers search.
- Smallest proof: a body-text index on the existing `pages` table and the zero-result rate measured a week later.

## Framings
| Option | What we build | Cost vs as-asked | Risk |
|---|---|---|---|
| Proceed | Elasticsearch cluster, indexer, sync on edit | baseline (about 2 weeks + a service to run) | sync drift, new infrastructure |
| Shrink | Postgres full-text index on title + body, same search box | about 2 days, no new service | ranking less tunable |
| Reframe | Better titles via a required summary field | about 1 day | does not fix old pages |
| Kill | nothing | 0 | the 41% stays |

## Decision
Shrink -- because 34 of 50 failing queries are plain words in page bodies, which Postgres full-text search finds; nothing in the evidence needs fuzzy matching or facets. Confidence: HIGH.
Problem to plan around: search ignores page bodies.
Scope now: body text in the existing search, ranking by title match first. Out of scope now: typo tolerance, attachments, a separate search service.
What changes for the plan: no new infrastructure; success measure is the zero-result rate falling below 15%.
```

Why it is good: the premise is checked with numbers before options are drawn; the cheaper
option is not a hunch but follows from a sample; the out-of-scope list keeps the bigger ask
visible instead of silently dropping it.

## 2. Bug shape: double bookings

Change `prevent-double-bookings`, booking app for a physiotherapy clinic. Request: "Customers
double-click Book and we get two bookings. Disable the button after the first click."

```markdown
# Frame: prevent-double-bookings

## Request as stated
"Customers double-click Book and we get two bookings. Disable the button after the first click."

## Observation, premise, direction
- Observation: the same slot sometimes holds two bookings (11 cases in September, research.md Data).
- Stated cause or premise: customers double-click the Book button.
- Proposed direction: disable the button after the first click.

## Premise check
- Do nothing for 3 months: about 30 more conflicts; each costs a phone call and one upset customer.
- Evidence: 11 conflicts in 30 days out of 2,900 bookings.
- Already solved elsewhere: nothing; no SOFTURE module applies.
- Smallest proof: a query showing whether conflicting pairs share a customer.

## Hypotheses
| Where it could come from | Expected evidence | Found | Verdict |
|---|---|---|---|
| Double submit from the client <- stated | pairs share customer and are created within 1 s | 2 of 11 pairs share a customer, 0.3 s apart | WEAK |
| Server accepts two writes for one slot | no unique constraint on (therapist_id, starts_at); check-then-insert outside a transaction | `bookings` has no such constraint (src/db/schema.ts:40-58); `createBooking` reads availability then inserts in two statements (src/bookings/actions.ts:31-47) | STRONG |
| Calendar sync re-imports bookings | duplicates carry `source = 'sync'` | 0 of 22 rows have `source = 'sync'` | NONE |
Pressure test: blind search (observation only) also landed on actions.ts:31-47; prior occurrences: none in archive; inverse check: 9 of 11 pairs are different customers booking the same slot within 2 s, which a disabled button cannot prevent.

## Framings
| Option | What we build | Cost vs as-asked | Risk |
|---|---|---|---|
| Proceed | disable the button | same (hours) | fixes 2 of 11 |
| Reframe | the server refuses a second booking for a taken slot, the customer sees "slot just taken" | about 1 day | existing duplicates must be resolved first |
| Reframe + proceed | both | about 1 day | none beyond the above |
| Kill | nothing | 0 | conflicts continue |

## Decision
Reframe + proceed -- because 9 of 11 conflicts are two customers racing for one slot, which only the database can stop; the button change is cheap and removes the other 2. Confidence: HIGH.
Problem to plan around: the server lets two bookings take one slot.
Scope now: server-side refusal of a taken slot, conflict message, button disable. Out of scope now: waitlist for taken slots.
What changes for the plan: the plan starts with resolving the 11 existing conflicts, because any database-level guarantee fails while they exist; how to enforce it is the plan's choice.
```

Why it is good: the stated cause is kept and tested, not dismissed; it turns out partly right
(2 of 11), and the decision keeps it; the reframe rests on a query and two code locations; the
inverse check is what makes the confidence HIGH.

## Bad

```markdown
# Frame: prevent-double-bookings

## Decision
The real problem is probably a race condition, as is common in booking systems. We should
use optimistic locking with a version column and retry logic in the API. Confidence: HIGH.
```

What is wrong:
- Observation, premise and direction are not separated; the user's theory is discarded unread.
- "As is common in booking systems" is a prior, not evidence. No query, no `path:line`.
- It designs the solution (version column, retries); that is the plan's job.
- HIGH confidence without a single hypothesis tested or a pressure test.
- No options, no costs, no scope in / out.
