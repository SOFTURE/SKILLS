---
name: softure-roadmap
description: >
  Slice an accepted PRD (or a list of feedback items) into `context/foundation/roadmap.md`:
  thin vertical slices with stable IDs, dependencies, ownership of hot files for parallel
  work, unknowns, baselines, and an at-a-glance table that orchestrators parse. Optionally
  opens a change folder for every ready item. Use after softure-prd, when feedback must be
  turned into work, or to revise the order. Triggers: "make a roadmap", "slice the PRD",
  "what do we build first", "order the work",
  "turn feedback into roadmap items".
argument-hint: "[--revise] [--open-changes] [--queue <slug> | --promote <slug> | --close] [--from-feedback <path>] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

# softure-roadmap: ordered, parallel-safe slices

## Purpose

Turn requirements into an ordered list of **changes**, each small enough to be planned,
built, reviewed and merged on its own, and safe to run in parallel where the roadmap says so.
The format is a contract: `softure-worktree` and `softure-worktree-manager` parse it
(WORKFLOW §5). Follow it exactly.

## Inputs

- `context/foundation/prd.md` with `status: accepted`. If missing, stop and point to
  `softure-prd`. Alternatively, `--from-feedback <path>` takes notes or screenshots and a
  short slice is made without a PRD; record that in the header.
- `context/workflow.json` (for `language`, `maxParallel`, `migrations`).
- If an existing `roadmap.md` has items not yet `done`, this is **revise mode**. Never
  renumber IDs and never drop an `in_progress` item. Move a finished roadmap to
  `context/foundation/archive/<YYYY-MM-DD>-roadmap.md` before starting a new one.

## Modes

- **main** (default): writes `context/foundation/roadmap.md`, the one roadmap that is executed.
- **`--queue <slug>`**: writes a queued thematic roadmap per WORKFLOW §5.1:
  `context/foundation/roadmaps/roadmap-<slug>.md` (`status: waiting`, `backlog:`, `trigger:`), plus
  `context/backlog/roadmap-<slug>/README.md` (table `| ID | Entry | Title | Condition | Kind |`, where Kind
  is `start`, `dependency` or `owner`) and one `<change-id>/change.md` per item (§4 format, `status: backlog`,
  `## Intent`, `## Context` with the item block, `## Constraints`). Use this for every theme that is not
  next in line. Several queued roadmaps can exist; each has its own ID prefix.
- **`--promote <slug>`**: the owner makes a queued roadmap the main one. Archive the current main
  roadmap, `git mv` the queued file to `roadmap.md`, set `status: ready`, and take its ready entries
  (`git mv …/change.md context/changes/<id>/backlog-input.md`, then the `softure-new` format).
  Never promote on your own initiative, not even in `--auto`.
- **`--close`**: the main roadmap is realised; archive it per WORKFLOW §5.2. Check the three gates
  first and report every failing one at once: rows not `done` / `done_code` and not carried over,
  leftover folders in `context/changes/` (archive each through `softure-archive`, a change without a
  plan included, before continuing), and the full integration result on `<main>` when configured.
  Then write `## Summary` (`| ID | Item | What changed | Merge |`, the merge SHA from
  `git log --merges --grep "<change-id>"` on `<main>`, plus the integration line), move the file to
  `foundation/archive/<YYYY-MM-DD>-roadmap.md`, clean up the promoted roadmap's backlog folder and
  index row, and commit. Do not promote the next roadmap in the same step: that is `--promote`, the
  owner's call. In `--auto`, a failing gate stops the close and is reported; it is never forced.

## Procedure

1. **List the capabilities** from the FRs (or feedback points). Group points that change the
   same user-visible behaviour.
2. **Slice vertically.** Each item delivers one observable outcome end to end (data → logic →
   UI → test), never "all the database work". Each item should:
   - fit one plan of 1 to 4 phases;
   - be mergeable on its own without breaking main;
   - carry its own verification (a baseline and an after measurement).

   Too big → split by user path, by data subset, or into a walking skeleton plus enhancements.
3. **Prefer modules.** Items whose FR is marked `Module: @softure-ai/<name>` become "adopt and
   configure the module" items, which are much smaller than building it.
4. **Order:**
   - risk first (whatever could invalidate the plan);
   - then dependencies;
   - then value.

   Name the prerequisite IDs explicitly. Put a "finish" item last when the theme needs a
   final measurement or review across items.
5. **Parallel safety.** For every item, list the files and areas it will touch (from a quick
   code search; this is an estimate, so say so). Two items may run in parallel only if:
   - their file sets are disjoint;
   - at most one of them adds a migration (`workflow.json` → `migrations`);
   - neither changes a shared primitive the other uses.

   Assign **exclusive owners** for hot files and write the groups that can run together under
   `## Order`.
6. **Per item, write:** Change ID (kebab-case, unique across `changes/` and `archive/`),
   Outcome, Prerequisites, Unknowns (the questions research must answer), Risk, Baseline (how
   it is measured before and after) and PRD refs.
7. **Header:**
   - frontmatter: `prd_version` = the PRD `version`;
   - run-wide orders in the quote block: push main or not; parallelism (default:
     `workflow.json` → `worktree.maxParallel`); which items need the owner at the keyboard.
8. **Review with the user.** Show the at-a-glance table and the parallel groups, then ask
   "Accept the order? (Recommended: accept)". Apply edits and set `status: ready`.
9. **`--open-changes`.** For every `ready` item without a folder, create
   `context/changes/<change-id>/change.md` in the `softure-new` format (WORKFLOW §4):
   - `status: new` and `roadmap_item: <ID>`;
   - `## Intent` = the item outcome;
   - `## Context` quotes the item block verbatim;
   - `## Constraints` lists the exclusively owned files.

## Output: `context/foundation/roadmap.md`

Exactly the structure of WORKFLOW §5. Parser-critical rules:
- Table header: `| ID | Change | Outcome | Depends on | Mode | Status |`.
- Row: `| **FC-1** | \`change-id\` | … | FC-0, FC-2 or — | autonomous or owner | <status> |`.
  The **status is the last cell**, and there is one row per change-id.
- IDs match `[A-Z]+-\d+`. Use a 2 to 4 letter prefix per roadmap theme and keep numbers
  stable forever.
- Status vocabulary only: `proposed`, `ready`, `blocked (<why>)`, `in_progress (…)`,
  `ready_to_merge (…)`, `done`, `done_code (…)`. A new roadmap uses only `proposed`, `ready`
  and `blocked`.
- Every item block has `- **Change ID:** \`<id>\`` followed directly by `- **Status:** <same as row>`.
- `## Done` lists finished items, one line each, with their archive path.

Write prose in `workflow.json` → `language`. Keep the IDs, the status tokens and the table
header in English, because scripts parse them.

## `--auto`

Slice and order without asking:
- mark an item `proposed` when its value is doubtful;
- mark it `blocked (<why>)` when it needs an owner decision;
- record ordering choices under `## Decisions (auto)` at the end of the file.

## Quality bar

- [ ] Every `must` FR is covered by at least one item, or explicitly deferred.
- [ ] No item is a horizontal layer ("backend for X").
- [ ] Each item has unknowns and a baseline. "None" is allowed only with a reason.
- [ ] Items running in parallel have disjoint files and at most one migration between them.
- [ ] The table and item blocks agree on IDs, change-ids and statuses.
- [ ] The first item can start today with no open owner decision.

## Do not

- Do not plan implementation steps. That is `softure-plan`, per change.
- Do not change the status of an item that is in progress. That belongs to the orchestrators
  and `softure-archive`.
- Do not estimate in hours. Order and slice size are the planning tools here.

## Handoff

`softure-new <change-id>` for the first item (or use `--open-changes`). For parallel execution
→ `softure-worktree-manager`. For a single item end to end → `softure-worktree <ID>`.
