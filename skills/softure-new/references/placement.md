# Placing a change in a roadmap

Read this when a change arrives without a roadmap item (step 4 of the procedure). A change outside
every roadmap is invisible to the orchestrators and to whoever reads the roadmap as the board.

## Now or later

Decide from the material before offering options:

| Destination | Signals | Folder | Registered in |
|---|---|---|---|
| **now** | the request is for work in this session; it fits the main roadmap's theme; the invoker runs it now (`softure-worktree`, `softure-worktree-manager`) | `context/changes/<id>/` | `context/foundation/roadmap.md` |
| **later** | `--backlog <slug>`; "later", "park it", "not now", "some day", "when we have users"; a theme outside the main roadmap's | `context/backlog/roadmap-<slug>/<id>/` | `context/foundation/roadmaps/roadmap-<slug>.md` |

When the request is genuinely split, choose **later**. Taking an entry out of the backlog is one
`git mv`; undoing a half-started folder in `changes/` means deciding what to do with its research.

## The options, recommended first

- **work now** → a new row and item block in the main `roadmap.md`: next free number of the
  closest prefix, status `ready`, `- **Input:** context/changes/<id>/change.md` in the block. If
  the invoker already wrote the row (an orchestrator queues items before calling this skill),
  only check that it points at this folder.
- **later** → three writes, nothing in `changes/`:
  1. `context/backlog/roadmap-<slug>/<id>/change.md` with `status: backlog`;
  2. a row in the queued roadmap's table (`proposed`, `ready` or `blocked (…)`) and an item block
     with `- **Input:** ../../backlog/roadmap-<slug>/<id>/change.md`;
  3. a row in `context/backlog/roadmap-<slug>/README.md`
     (`| ID | Entry | Title | Condition | Kind |`).
- **new theme** → only when no queued roadmap fits: run `softure-roadmap --queue <slug>` first,
  then place the change there.
- **unlinked** → a one-off with `roadmap_item: null`. Allowed unless the project's rules say every
  change belongs to a roadmap.

## Choosing the queued roadmap

1. List `context/foundation/roadmaps/roadmap-*.md` (and an index such as
   `context/foundation/roadmaps/README.md` when the project keeps one). For each, read the title,
   the `trigger` and the `## Order` section.
2. Pick the one whose **reason for existing** covers the change: why its items wait (traffic, a
   provider account, a legal decision). A shared file or keyword is not a fit; the same reason is,
   even when the topic looks different.
3. Prefer an existing roadmap. A weak fit on the reason beats a new roadmap with one item.
4. A new theme gets an English slug named after the reason (`roadmap-payments`,
   `roadmap-compliance`), never after a page (`roadmap-landing` becomes a bin for every later edit
   of that page).

## Free IDs

```bash
grep -ho '\*\*[A-Z]\+-[0-9]\+' context/foundation/roadmap.md context/foundation/roadmaps/*.md | sort -u
```

A new row takes the next number of its roadmap's prefix. A new roadmap takes a prefix no other
roadmap uses.

## Record the decision

Under `## Notes`: `- Placement: <roadmap and ID, or unlinked>. <one-line reason>.` In `--auto`, the
same line, prefixed `Decision (auto):`.
