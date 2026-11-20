---
name: softure-doctor
description: >
  Check a project's context/ contract and keep its machine-readable state current: regenerate
  context/state.json (active roadmap, queued roadmaps, open changes, and one owner_queue of
  everything that waits for the owner) and fail on drift: a roadmap left after its archive, archived
  changes that are not stamped or have unticked Automated items, Summary placeholders instead of
  merge SHAs, archived roadmaps with open rows, queued roadmaps that are fully done, backlog folders
  without their roadmap, index rows pointing at missing files, and a missing or stale state.json.
  Use in CI, before an archive or roadmap commit, or when the user says "check the context",
  "run the doctor", "what waits for me", "refresh the state".
argument-hint: "[doctor | state write|print|check] [--root <dir>] [--json] [--staged]"
allowed-tools:
  - Read
  - Bash
---

# softure-doctor: the context/ contract as a check

Contract: `WORKFLOW.md` §12 (state.json and the doctor), §5 (roadmap), §5.1 (queued roadmaps and the
backlog), §5.2 (closing a roadmap), §6 (Progress). Two scripts next to this file (`<S>` below):

| Command | Does |
|---|---|
| `python3 <S>/doctor.py [--json]` | every check; exit 1 on a failure. Same as `npx softure-skills doctor` |
| `python3 <S>/context_state.py write` | regenerate `context/state.json` from the working tree |
| `python3 <S>/context_state.py write --staged` | regenerate it from what is staged, and stage it (use right before a commit) |
| `python3 <S>/context_state.py print` / `check` | show it / exit 1 when it is missing or stale |

`<S>` is `.claude/skills/softure-doctor/scripts` in an installed project.

## When it runs

- **CI of every adopting project**, documentation-only changes included: `npx softure-skills doctor`
  (the installer prints this line). Drift happens in the documents, so a CI that skips doc-only
  changes misses it.
- **`softure-archive`** (on the main branch) and **`softure-roadmap`** (record, `--queue`, `--promote`,
  `--close`): `context_state.py write --staged` right before the commit, then `doctor.py`; each fixes
  what it owns and names the rest in its report.
- **`wt-roadmap.py`** writes `context/state.json` itself in every mode, in the same commit as `roadmap.md`.

## Reading the result

Each problem is one line `FAIL <code> <path>: <what>`. Fix the file it names, never the check:

| Code | Fix |
|---|---|
| `roadmap-archived-not-removed` | the close moved a copy and left `roadmap.md`: remove it (promote the next one only on the owner's word) |
| `roadmap-status-mismatch` | set `status` to match the rows (`done` only when every row is closed; `waiting` belongs to queued roadmaps) |
| `archived-change-status` | stamp the archived `change.md` `status: archived` (and `archived_at`) |
| `archived-change-progress` | the change was archived with open Automated items: tick them with their SHA when the work is on the main branch, or mark them `~~dropped~~ — dropped: <reason>` |
| `archived-roadmap-open-items` | rows of an archived roadmap end `done`, `done_code`, dropped or carried (with where they went) |
| `archived-roadmap-summary` | put the merge SHA (`git log --merges --grep "<change-id>"`) into each `## Summary` row |
| `queued-roadmap-done` | archive the finished queued roadmap to `foundation/archive/` |
| `backlog-without-roadmap` | move live entries to a queued roadmap, then remove the folder |
| `index-missing-file` | fix or drop the index row |
| `state-missing` / `state-stale` | `context_state.py write`, commit `context/state.json` |

A project that has never written `context/state.json` gets a `note`, not a failure, until the first
script run creates it.

## Rules

- `context/state.json` is written by scripts only. Never edit it by hand; regenerate it.
- The doctor never edits anything. A skill that runs it fixes only the files it owns in that run.
- `open_changes` and `updated_at` are refreshed on every write and never make the file stale, so a
  change branch that edits its own `change.md` keeps a green doctor.
- Owner-word issues (label `owner-word`, WORKFLOW §8.6) live on the forge, not in `state.json`;
  an aggregator reads both.
