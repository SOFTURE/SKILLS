# Worked examples: archiving a change

Read this before the first archive in a project, or when the roadmap or the working tree is in an
unusual state. The domain is invented: a team wiki, change `search-matches-page-titles`
(roadmap item `WK-8`, created 2026-10-02).

## 1. A normal close with one open Manual item

### Preconditions report (interactive)

```
Archive search-matches-page-titles: checks
  ok    nothing uncommitted in the change folder or in the 3 files it touched
  ok    nothing staged
  ok    status impl_reviewed; reviews/impl-review.md: 0 CRITICAL open
  ok    Progress: 0 open Automated items
  warn  Progress: 1 open Manual item: 2.4 "search feels instant on the 2k-page staging space"
  warn  Progress: 1 done row without a SHA: 3.1 "release note drafted" (phase had no code)
  ok    target context/archive/2026-10-02-search-matches-page-titles/ is free

1. Archive anyway (Recommended): the Manual item goes to the owner list, the SHA-less row is a docs-only phase
2. Resume implementation: softure-implement search-matches-page-titles
3. Stop
```

### change.md after the stamp

```markdown
status: archived
updated: 2026-10-06
archived_at: 2026-10-06
...
## Notes
- Placement: main roadmap, WK-8. ...
- Archived 2026-10-06: searching for a page's title now returns that page first in every readable space.
```

### Roadmap diff

```diff
-| **WK-8** | `search-matches-page-titles` | a title search finds the page first | — | autonomous | in_progress (archive, since 2026-10-06; worktree ../wiki-search-titles) |
+| **WK-8** | `search-matches-page-titles` | a title search finds the page first | — | autonomous | done_code (2026-10-06; waiting: owner check 2.4 on staging) |

 ### WK-8: Search matches page titles
 - **Change ID:** `search-matches-page-titles`
-- **Status:** in_progress (archive, since 2026-10-06; worktree ../wiki-search-titles)
+- **Status:** done_code (2026-10-06; waiting: owner check 2.4 on staging)

 ## Owner decisions and checks
+- [ ] **WK-8**: search feels instant on the 2k-page staging space (Manual 2.4). archive/2026-10-02-search-matches-page-titles/plan.md

 ## Done
+- **WK-8** `search-matches-page-titles`: a title search returns the page first; archived in `archive/2026-10-02-search-matches-page-titles/`
```

Only the last cell of the row changed. The archive folder carries the `created` date (10-02), not today.

### Final report

```
Archived search-matches-page-titles
  context/changes/search-matches-page-titles/ → context/archive/2026-10-02-search-matches-page-titles/
  change.md: status archived, archived_at 2026-10-06
  roadmap: WK-8 → done_code (waiting: owner check 2.4); ## Done +1; owner checks +1
  links fixed: 2 (context/foundation/roadmap.md, docs/search.md)
  commit: 5c81e0a chore(archive): close search-matches-page-titles
Not pushed. Next: softure-lesson for the lesson the review proposed (title weighting) and nobody recorded.
```

## 2. The roadmap has someone else's uncommitted edits

`git status --porcelain -- context/foundation/roadmap.md` prints ` M`, and `git diff` shows a new
item `WK-9` being drafted by the owner, not this change's row.

```
Archived search-matches-page-titles (commit 5c81e0a), with one exception:
  roadmap.md holds uncommitted edits that are not mine (a draft of WK-9).
  I closed WK-8 in the working tree (row, block, ## Done, owner check) but did not stage the file,
  so your draft is not committed by me. Commit roadmap.md together with your edits.
```

## 3. A hard stop

```
Cannot archive invoice-pdf-download:
  stop  Progress: 2 open Automated items: 2.2 "PDF totals match the invoice view", 2.3 "gates green"
  stop  staged but not part of this change: src/lib/tax.ts, src/lib/tax.test.ts
        (they would ride along in the archive commit; commit or unstage them yourself)
  warn  no reviews/impl-review.md
Nothing was changed. Next: softure-implement invoice-pdf-download.
```

All failing checks are reported at once, so a second run does not discover a new one.

## 4. A change without a plan

Change `pricing-page-copy`: the owner rewrote the copy by hand in commit `a1b2c3d`; no plan.

```markdown
## Notes
- Archived 2026-10-06 without a plan: delivered by a1b2c3d (copy in messages/en.ts), verified by
  the owner on the preview deploy. Open: legal check of the refund sentence → owner checks.
```

Roadmap: row `done`, `## Done` line, and under `## Owner decisions and checks`
`- [ ] **PR-2**: legal check of the refund sentence. archive/2026-09-30-pricing-page-copy/change.md`.
