# README templates written by softure-init

Each file is written only when absent. Write them in English or in `workflow.json` ->
`language`; the skill names, paths and headings stay as shown.

## `context/foundation/README.md`

```markdown
# Foundation

Documents that outlive any single change: shape notes, PRD, the active roadmap, queued roadmaps
and lessons. Each file is owned by the skill that writes it (softure-shape, softure-prd,
softure-roadmap, softure-lesson); edit them through those skills when possible.

- `roadmap.md` is the one active roadmap. Queued thematic roadmaps live in `roadmaps/roadmap-<slug>.md`.
- `lessons.md` holds numbered rules from real incidents (`L-NNN`). Numbers are never reused.

## Updating
Edit in place. A refined goal, a new requirement or a shifted milestone changes the existing
file (the PRD bumps its version); no dated copies next to it.

## Archiving
When a document is replaced rather than refined (a finished roadmap, a superseded PRD), move it
to `archive/<YYYY-MM-DD>-<name>.md` and write the successor at the original path. Same-day
collisions get `-2`, `-3`. Nothing reads the archive routinely.

## Not here
Anything tied to one change (its research, frame, plan, reviews) belongs in
`context/changes/<change-id>/`.
```

## `context/changes/README.md`

```markdown
# Changes in flight
One folder per change: `changes/<change-id>/`, identified by `change.md`.
Created by `softure-new`, closed by `softure-archive` (moved to `archive/`).
Holds research.md, frame.md, plan.md and reviews/ for that change.
Execution state lives only in `plan.md` -> `## Progress`.
```

## `context/archive/README.md`

```markdown
# Archive
Finished changes, moved here by `softure-archive` as `<YYYY-MM-DD>-<change-id>/`, where the date
is the change's `created` date. Read-only history: skills read it for prior decisions and never
write into it. To continue archived work, open a new change.
```

## `context/backlog/README.md`

```markdown
# Backlog
Planned for later, never what is in flight. A topic lives in exactly one place: `backlog/`,
`changes/` or `archive/`.

- `roadmap-<slug>/`: entries of a queued roadmap (`foundation/roadmaps/roadmap-<slug>.md`):
  a README table and one `<change-id>/change.md` per entry with `status: backlog`.
  Taking an entry moves it into `changes/`; it is never copied.
- `<topic>.md`: deferred review findings and loose ideas, one line each:
  `- [ ] <YYYY-MM-DD> <source change-id or review>: <finding> (<severity>) <evidence path>`.
  `softure-roadmap` turns them into roadmap items.
```

## `context/foundation/lessons.md`

```markdown
# Lessons

Numbered rules from real incidents in this repo (`## L-NNN: <rule>` with **Why**, **How to apply**
and **Applies to**). Written by softure-lesson; read by research, frame, plan, implement and the reviews.
```
