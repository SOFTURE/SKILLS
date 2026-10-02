---
name: softure-archive
description: >
  Close a finished change: verify nothing is left uncommitted, stamp change.md as archived,
  move context/changes/<change-id>/ to context/archive/<created>-<change-id>/, mark the
  roadmap row and item as done (or done_code when something still waits for a release or the
  owner), record pending manual checks for the owner, fix links, and commit. Use when the
  user says "archive the change", "close this change", "we're done with X", or after
  softure-impl-review.
argument-hint: "<change-id> [--auto] [--done-code \"<what waits>\"]"
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

Contract: `WORKFLOW.md` §3 (paths), §4 (status), §5 (roadmap rows and statuses), §9 (commit).

## Preconditions (check all, report all, then decide)

| Check | Hard stop | Soft warning |
|---|---|---|
| `git status --porcelain` is empty | yes: commit or stash first; never archive over uncommitted work | |
| change.md `status` is `impl_reviewed` | | `implemented` (no review) or earlier |
| plan.md Progress: no open `#### Automated` items | yes: name them | |
| plan.md Progress: open `#### Manual` items | | yes: they become owner checks (step 4) |
| `reviews/impl-review.md` has no CRITICAL without a decision | yes | |
| target `context/archive/<created>-<change-id>/` does not exist | yes | |

Interactive: show the warnings and ask once ("Archive anyway" / "Stop"). `--auto`: proceed
on warnings, stop on hard stops.

## Procedure

1. **Stamp change.md:**
   - `status: archived`;
   - `archived_at: <today>`;
   - `updated: <today>`;
   - one closing line under `## Notes`: `Archived <date>: <outcome in one sentence>.`
2. **Move.** Run `git mv context/changes/<id> context/archive/<created>-<id>`, where `<created>`
   is the `created` date from change.md, not today.
3. **Update the roadmap** (when change.md has `roadmap_item`, or a row with `` `<id>` `` exists):
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
4. **Owner checks.** For each open Manual item, add a line under `## Owner decisions and checks`:
   `- [ ] **<ID>**: <item text> (Manual N.M). archive/<created>-<id>/plan.md`. Do the same for
   deferred review findings that target the owner.
5. **Fix links.** `grep -rn "changes/<id>" context/ docs/ AGENTS.md CLAUDE.md` and rewrite each
   hit to `archive/<created>-<id>`. Links inside the archived folder are relative and stay valid.
6. **Verify** that the old folder is gone, the new one exists, the roadmap row has exactly one
   match, and no dangling `changes/<id>` links remain.
7. **Commit** with `chore(archive): close <change-id>`, staging only the touched paths.

## --auto

Proceed on soft warnings. Record each one in the archive commit body and in the roadmap owner
checks. Pick `done_code` whenever any Manual item is open or the change affects deployment
(migrations, env vars, infrastructure).

## Inside a worktree

Archive **on the change branch**, before the merge. The roadmap edits will then conflict
textually with other merged changes; that is expected. `softure-worktree` resolves them row by
row during the merge. Do not touch rows of other items.

## Checklist

- [ ] No uncommitted files before and after.
- [ ] `status: archived`, `archived_at` set.
- [ ] Folder name uses the `created` date.
- [ ] Roadmap row last cell, item block status, `## Done` and `updated` all changed.
- [ ] Open Manual items listed for the owner.
- [ ] No dangling links.
- [ ] One commit, conventional message.

## Anti-patterns

- Ticking Manual items to make archiving clean. They go to the owner list instead.
- Archiving with a red gate "to clean up later".
- Rewriting history in the archived plan. It is a record and stays as it was executed.
- Marking `done` when a release is still needed. That is `done_code`.

## Handoff

`softure-worktree` continues with syncing the main branch and the READY report. Standalone, the
change is closed. Suggest `softure-lesson` if the review proposed lessons that were not recorded.
