---
name: softure-archive
description: >
  Close a finished change: verify nothing is left uncommitted or staged by someone else, check
  plan Progress and the review, stamp change.md as archived, move context/changes/<change-id>/
  to context/archive/<created>-<change-id>/, mark the roadmap row and item as done (or
  done_code when something still waits for a release or the owner), record pending manual
  checks for the owner, fix links, and commit. Handles changes without a plan, a roadmap with
  someone else's uncommitted edits, and a half-finished earlier run. Use when the user says
  "archive the change", "close this change", "we're done with X", or after softure-impl-review.
argument-hint: "<change-id | path> [--auto] [--done-code \"<what waits>\"]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - AskUserQuestion
---

# softure-archive: the change leaves `changes/`, and the record of it stays

Contract: `WORKFLOW.md` §3 (paths), §4 (status), §5 (roadmap rows and statuses), §6 (Progress
notation), §9 (commit).

The argument is a change id or a path (`@context/changes/<id>/`: strip `@` and the trailing `/`,
take the last segment). With none, list the folders in `context/changes/` with their `status`
and ask which one; in `--auto`, escalate.

## Resolve

A failed run is never rolled back; each step leaves a state the next run recognises, so
re-running is always safe. Report what you found and what you completed.

| Found | Do |
|---|---|
| `context/changes/<id>/change.md` | continue |
| no folder in `changes/`, but `context/archive/*-<id>/` | already archived: report the path. If its roadmap row is not `done` / `done_code`, offer to finish only steps 3 to 8 on the archived folder |
| `status: archived`, folder still in `changes/` | an earlier run stopped after the stamp. An uncommitted diff of change.md limited to the stamp is that run's own and does not count as uncommitted work; resume at step 2 once the other checks pass |
| `created` missing or not `YYYY-MM-DD` | stop: the archive folder name cannot be derived |
| nothing | stop: name the folders that do exist |

## Preconditions (check all, report all, then decide)

| Check | Hard stop | Soft warning |
|---|---|---|
| no uncommitted changes in the change folder or the files the change touched (`git status --porcelain -- <paths>`) | yes: commit them first; never archive over uncommitted work of the change | other uncommitted paths (someone else's WIP): leave them, never stage them |
| nothing staged that is not part of this change (`git diff --cached --name-only`) | yes: it would ride along in the archive commit. Name the paths; never unstage them yourself, they may be someone's work | |
| change.md `status` is `impl_reviewed` | | `implemented` (no review) or earlier |
| plan.md exists | | no: work done without the chain (interactively, or a change that turned out to need no code). Archive it anyway, see "Without a plan" |
| plan.md Progress: no open `#### Automated` items | yes: name them | |
| plan.md Progress: open `#### Manual` items | | yes: they become owner checks (step 4) |
| Progress without `#### Automated` / `#### Manual` headings (an older or hand-written plan) | open items count as Automated, unless the owner marks one as a human check (interactive only) | |
| done rows carry ` — <sha>` (7+ hex, optionally followed by `(verified by agent: …)`), or are `~~dropped~~ — dropped: …` | | rows without one: name them. Legitimate for phases with no code; never add SHAs yourself, that is `softure-implement`'s job |
| `reviews/impl-review.md` exists | | no review on file |
| `reviews/impl-review*.md` has no CRITICAL without a decision (`**Decision:** pending` counts as none) | yes | |
| target `context/archive/<created>-<change-id>/` does not exist | yes | |

`context/foundation/roadmap.md` with uncommitted edits is **not** a stop: step 3 handles it.

Show every result in one report. Interactive: when only warnings remain, ask once:
"Archive anyway / Resume implementation (`softure-implement <id>`) / Stop". Recommend "Archive
anyway" when the only warnings are open Manual items or SHA-less rows (both are expected
outcomes); otherwise recommend running the missing step. `--auto`: proceed on warnings, stop on
hard stops. Sample reports: [references/example-archive.md](references/example-archive.md).

## Procedure

1. **Stamp change.md:**
   - `status: archived`;
   - `archived_at: <today>`;
   - `updated: <today>`;
   - one closing line under `## Notes`: `Archived <date>: <outcome in one sentence>.`
   Leave `change_id` and `created` untouched. Dates use `workflow.json` → `timezone` when set.
2. **Move.** Run `git mv context/changes/<id> context/archive/<created>-<id>`, where `<created>`
   is the `created` date from change.md, not today. `git mv` stages the rename with the
   committed content only, so run `git add context/archive/<created>-<id>` afterwards or the
   stamp stays out of the commit.
3. **Update the roadmap** (when change.md has `roadmap_item`, or a row with `` `<id>` `` exists):
   - Match exactly: the row whose second cell is `` `<id>` ``. One item can spawn several
     changes, so a near miss is never closed. If `roadmap_item` names an ID whose row carries a
     different change-id, report it and leave the row alone.
   - Choose the row status:
     - `done` when everything is delivered and verified;
     - `done_code (<today>; waiting: <what>)` when the code is finished but something still
       waits. Examples: a release, an open Manual item, a deploy-only check. `--done-code`
       forces this, using the given text.
   - Replace only the **last cell** of the row; leave the other cells alone.
   - Update `- **Status:** …` in the item block under `- **Change ID:**`.
   - Append to `## Done`:
     `- **<ID>** \`<id>\`: <outcome>; archived in \`archive/<created>-<id>/\``.
   - Set frontmatter `updated` to today.
   - The roadmap shape is not this skill's to fix: when a target (row, block line, `## Done`) is
     missing or hand-formatted, skip that edit, keep going, and name it in the report. Never
     abort the archive over the roadmap's shape.
   - **Dirty roadmap.** Before editing, `git status --porcelain -- context/foundation/roadmap.md`.
     Clean, or every uncommitted hunk is this item's own row and block → edit and stage it.
     Otherwise it holds someone else's edits: make the edits in the working tree, do **not**
     stage the file, and say so in the report so its owner commits it with their work.
4. **Owner checks.** For each open Manual item, add a line under `## Owner decisions and checks`:
   `- [ ] **<ID>**: <item text> (Manual N.M). archive/<created>-<id>/plan.md`. Do the same for
   deferred review findings that target the owner. Anything that must happen before the next
   deploy (an environment variable, a manual migration step, a production check) goes under
   `## Before the next release` as `- [ ] <what> (**<ID>**)`. Unlinked change: these stay under
   `## Notes` of its change.md.
5. **Fix links.** `grep -rn "changes/<id>" context/ docs/ AGENTS.md CLAUDE.md` and rewrite each
   hit to `archive/<created>-<id>`. Links inside the archived folder are relative and stay valid.
6. **Verify** that the old folder is gone, the new one exists, the roadmap row has exactly one
   match, and no dangling `changes/<id>` links remain.
7. **Commit** with `chore(archive): close <change-id>`, staging only the touched paths: the
   archive folder, the roadmap (unless step 3 left it unstaged), and the files whose links you
   fixed. Before committing, `git diff --cached --name-only` must list nothing else. Never
   `--no-verify`; if a hook fails, fix the cause and commit again (a new commit, never an amend).
   In `--auto`, the commit body lists the soft warnings.
8. **Report:** old and new path, the stamp, the roadmap transition (or "no matching row"), owner
   checks added, links fixed, edits skipped or left unstaged, and the commit SHA. The commit is
   local: never push from this skill.

## Without a plan

A change folder must not outlive its work: a delivered change left in `changes/` looks in flight
to every orchestrator and blocks closing the roadmap. When there is no `plan.md`:

- under `## Notes`, record what delivered the outcome (commit SHAs or the merge) and how it was
  verified, or that it was dropped and why;
- open items that need no code (an owner's visual check, a decision) go to the roadmap's
  `## Owner decisions and checks` (or stay under `## Notes` for an unlinked change); they never
  keep the folder in `changes/`;
- the row becomes `done`, `done_code (…)` or, for a dropped change, `done` with the reason in `## Done`.

## --auto

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

Proceed on soft warnings. Record each one in the archive commit body and in the roadmap owner
checks. Pick `done_code` whenever any Manual item is open or the change affects deployment
(migrations, env vars, infrastructure). Hard stops stay stops: report them all and end.

## Inside a worktree

Archive **on the change branch**, before the merge. The roadmap edits will then conflict
textually with other merged changes; that is expected. `softure-worktree` resolves them row by
row during the merge. Do not touch rows of other items.

## Checklist

- [ ] No uncommitted files of the change before and after; nobody else's WIP or staged work in the commit.
- [ ] `status: archived` and `archived_at` set, the stamp inside the commit; folder named by `created`.
- [ ] Roadmap row last cell, item block status, `## Done` and `updated` all changed (or the skip is reported).
- [ ] Open Manual items listed for the owner; deploy prerequisites under `## Before the next release`.
- [ ] No dangling links; one commit, conventional message, not pushed.

## Anti-patterns

- Ticking Manual items to make archiving clean. They go to the owner list instead.
- Archiving with a red gate "to clean up later".
- Rewriting history in the archived plan, or adding SHAs to it. It is a record and stays as it was executed.
- Marking `done` when a release is still needed. That is `done_code`.
- Staging the whole tree, or someone else's roadmap edits, to get a clean status.
- Writing into an archived folder later. To revisit archived work, open a new change with
  `softure-new` and link the archive folder; there is no unarchive.

## Handoff

`softure-worktree` continues with syncing the main branch and the READY report. Standalone, the
change is closed. Suggest `softure-lesson` if the review proposed lessons that were not recorded.
