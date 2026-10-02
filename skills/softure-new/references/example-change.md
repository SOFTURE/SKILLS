# Worked examples: change.md

Read this before writing a change.md when unsure how much goes into each section, or when the
input is raw feedback rather than a roadmap item. Domains are invented.

## 1. From a roadmap item (invoicing tool)

Input: `softure-new IN-3`. The roadmap block reads:

```markdown
### IN-3: Overdue reminders
- **Change ID:** `overdue-invoice-reminders`
- **Status:** ready
- **Outcome:** a client whose invoice is 7 days overdue gets one reminder email; the freelancer
  sees on the invoice that it was sent.
- **Prerequisites:** IN-2 (invoices are sent by email)
- **Touches (estimate):** `jobs/reminders/**`, `mail/templates/reminder.*`, invoice detail page
- **Unknowns:**
  - Is "overdue" counted from the due date in the client's time zone or ours? (owner: research; blocks: no)
- **Risk:** a job that sends mail; a bug spams real clients.
- **Baseline:** reminders sent by hand; after: a test advances the clock and finds one email.
- **PRD refs:** FR-9, NFR-3
```

Result, `context/changes/overdue-invoice-reminders/change.md`:

```markdown
---
change_id: overdue-invoice-reminders
title: "A client with an invoice 7 days overdue gets exactly one reminder"
status: new
roadmap_item: IN-3
branch: null
created: 2026-10-02
updated: 2026-10-02
archived_at: null
---

## Intent
When an invoice is 7 days past its due date and still unpaid, its client receives one reminder
email, never more than one per invoice, and the freelancer sees on the invoice when it went out.

## Context
Roadmap item IN-3 (`context/foundation/roadmap.md`):

> - **Outcome:** a client whose invoice is 7 days overdue gets one reminder email; the freelancer
>   sees on the invoice that it was sent.
> - **Prerequisites:** IN-2 (invoices are sent by email)
> - **Unknowns:** Is "overdue" counted from the due date in the client's time zone or ours?
>   (owner: research; blocks: no)
> - **Risk:** a job that sends mail; a bug spams real clients.
> - **PRD refs:** FR-9, NFR-3

Known today: invoices carry `dueDate` and `paidAt` (`db/schema/invoices.ts`); mail goes through
`@softure-ai/mail` since IN-2.

## Constraints
- Owns exclusively: `jobs/reminders/**`, `mail/templates/reminder.*`.
- Must not touch the invoice numbering (`lib/numbering.ts`), owned by IN-4 running in parallel.
- Owner decision (PRD v3): one reminder only; no escalation series in this change.

## Notes
- Depends on IN-2 being merged (it is: `done` since 2026-09-28).
```

Why it works: the intent is observable ("exactly one", "sees when"), the item block is quoted, not
retold, the constraint names the parallel neighbour and its file, and nothing says *how* (no job
scheduler, no table design).

## 2. From raw feedback, not on the roadmap (team wiki)

Input: `softure-new "search ignores page titles, people complain"` plus a pasted message.

Questions asked (interactive), one at a time, recommendation first:

1. "Is the outcome 'a search for a page title finds that page first', or a wider search
   overhaul? (Recommended: title match first; the complaint is only about titles.)" → accepted.
2. "Work now (a row in the main roadmap, next ID WK-8) or later (roadmap-search, queued)?
   (Recommended: now; two teams are blocked by it.)" → accepted.

Result:

```markdown
---
change_id: search-matches-page-titles
title: "Searching for a page's title returns that page as the first result"
status: new
roadmap_item: WK-8
branch: null
created: 2026-10-02
updated: 2026-10-02
archived_at: null
---

## Intent
A member who types the exact or partial title of a page sees that page as the first search
result, in every space they can read.

## Context
> "I searched for 'Onboarding checklist' and got twelve pages that mention onboarding, but not the
> checklist itself. Had to find it through the sidebar again."
> (Dana, support lead, team chat, 2026-09-30)

Two more reports of the same kind in the feedback channel this week. Today search ranks by body
text only (`lib/search/query.ts`); titles are stored but not weighted.

## Constraints
- Must not change permissions filtering in search (`lib/search/acl.ts`).
- No new search service; this stays inside the current database (owner, 2026-10-01).

## Notes
- Placement: main roadmap, WK-8. Two teams are blocked now; the queued search roadmap is about
  a full-text overhaul, which this is not.
- Original request: "search ignores page titles, people complain".
```

## 3. A bad change.md for the same request

```markdown
---
change_id: fix-search
title: "Improve search"
status: new
roadmap_item: null
---

## Intent
Add a title boost of 3.0 to the search query and rebuild the index.

## Context
Users say search is bad.
```

What is wrong:

- `fix-search` names an activity, not the outcome; `improve` is not verifiable.
- The intent is a solution (a boost factor) and closes the door on research.
- The feedback is paraphrased; "search is bad" lost the actual case (titles) and the author.
- Missing `branch`, `created`, `updated`, `archived_at`, `## Constraints` and `## Notes`.
- Not placed: no roadmap row and no recorded decision to leave it unlinked, so orchestrators
  never see it.

## 4. Placed in the backlog instead

Input: `softure-new export-space-as-pdf --backlog docs-export`. The result lives at
`context/backlog/roadmap-docs-export/export-space-as-pdf/change.md` with `status: backlog`, the same
four sections, and one row each in `context/foundation/roadmaps/roadmap-docs-export.md` (status
`proposed`, its item block with `- **Input:** ../../backlog/roadmap-docs-export/export-space-as-pdf/change.md`)
and in `context/backlog/roadmap-docs-export/README.md`. Nothing is created under `context/changes/`.
