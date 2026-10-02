# Leak lint: keeping implementation out of the PRD

Read this before the self-review step. A PRD that names how something is built has made a
design decision nobody reviewed, and it ties the roadmap and the plan to that decision.
Scan every section except brownfield `## Current system`, the `Module` column, and
verbatim quotes inside `## Open questions`.

## Categories

| Category | Typical tokens | Rewrite as |
|---|---|---|
| Vendor or hosted service | any product or company name for payments, hosting, auth, AI, mail, analytics | the capability: "members can pay by card", "a sign-in link arrives by mail" |
| Framework, library, database | a framework, an ORM, a database, a queue | nothing in the PRD; to forward notes |
| Data model notation | table or column names, `(FK)`, `nullable`, `_id` or `_at` field lists, cascade, soft delete | the rule the user meets: "a deleted project stays restorable for 30 days" |
| Data operations | migration, backfill, schema change | the outcome for existing data: "invoices issued before the change keep their numbers" |
| Where it runs | client-side, server-side, at the edge, in a worker, in the cache | the observable property: "results appear within 1 s" |
| Enforcement mechanism | per IP, token bucket, rate limit per key, lock, retry with backoff | what an attacker or a user experiences: "a script guessing passwords is stopped; a person who mistypes three times is not" |
| UI affordance stated as a quality | spinner, progress bar, modal, toast, streaming | the quality: "any wait over 2 s shows visible progress" (an affordance is fine inside an FR's acceptance when it *is* the behaviour) |
| Transport or protocol | REST endpoint, GraphQL, WebSocket, webhook, SSE, gRPC | the information flow: "the manager's view updates without a reload when a member books" |
| Component as actor | "the model decides", "the cron job sends", "the database checks" | the rule with the product as actor: "a freed slot is offered to the next member on the waitlist" |

## Before and after

| Leaky | Outside-observable |
|---|---|
| FR: Store bookings in a `bookings` table with `member_id (FK)` and `slot_at`. | FR: When a member books a free slot, the slot shows as taken for everyone. |
| NFR: Cache the weekly grid server-side. | NFR: The weekly grid shows within 1 s for a studio with 60 members. |
| NFR: Rate-limit sign-in per IP to 5/min. | NFR: Automated password guessing is stopped before it can try 100 passwords against one account; a member who mistypes three times can still sign in. |
| FR: Send a webhook to the accounting tool on every invoice. | FR: When an invoice is issued, the customer's connected accounting tool shows it within 5 minutes. |
| Rule: The scheduler job creates drafts at midnight. | Rule: A schedule produces a draft on its due date; the draft gets a number only when issued. |
| Compatibility: Backfill `schedule_id` on old invoices. | Compatibility: Invoices issued before the change look and export exactly as before. |

## When the lint finds something

- Interactive: list each hit as `<section>: "<phrase>" — <category>`, propose the
  outside-observable rewrite, and ask once for all of them (Recommended: accept the
  rewrites). Never rewrite silently. The original wording goes to the handoff as a forward
  note when it carries a real preference ("the team wants to keep the current database").
- `--auto`: apply the rewrites, move the original phrases to the handoff's forward notes,
  and record each one under `## Decisions (auto)`.
- A hit you cannot rewrite without losing meaning is a sign the requirement is really a
  design decision: move it to forward notes and, if a requirement is left behind, state what
  the user observes.
