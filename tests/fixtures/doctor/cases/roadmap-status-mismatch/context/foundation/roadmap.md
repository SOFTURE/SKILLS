---
project: "Example clinic"
roadmap: search
version: 2
status: done
prd_version: 3
updated: 2026-11-10
---

# Roadmap search: visitors find what they look for

> Run-wide orders, read by orchestrators (not parsed):
> - Archive roadmap: at the end
> - Release: at the end

## At a glance

| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **SR-1** | `search-index` | (foundation) pages are indexed | — | autonomous | done |
| **SR-2** | `search-titles` | a title search finds the page | SR-1 | autonomous | **in_progress** (implement 2/3, since 2026-11-08; cloud session, branch `claude/x` — do not take in another session) |
| **SR-3** | `search-filters` | results filter by service | SR-2 | autonomous | ready |
| **SR-4** | `search-synonyms` | synonyms find the page | SR-1 | autonomous | done_code (2026-11-09; waiting: release) |
| **SR-5** | `search-paid-api` | paid ranking improves results | SR-2 | owner | blocked (provider account) |

## Order
SR-1 first.

## Items

### SR-1: Index
- **Change ID:** `search-index`
- **Status:** done

### SR-2: Titles
- **Change ID:** `search-titles`
- **Status:** in_progress (implement 2/3, since 2026-11-08; cloud session, branch `claude/x` — do not take in another session)

## Before the next release
- [ ] Set `SEARCH_INDEX_URL` in production (**SR-1**)
- [x] Run the reindex once (**SR-1**)

## Owner decisions and checks
- [ ] **SR-5**: choose the ranking provider and open the account. Gates SR-5.
- [ ] **SR-4**: owner step: add the provider api key to the deploy settings (secret only the owner has). archive/2026-11-09-search-synonyms/change.md
- [x] **SR-1**: decided the index engine.

## Done
- **SR-1** `search-index`: pages are indexed; archived in `archive/2026-11-01-search-index/`
