---
name: softure-doctor
description: >
  Check a project's context/ contract and keep its machine-readable state current: regenerate
  context/state.json (active roadmap, queued roadmaps, open changes, and one owner_queue of
  everything live that waits for the owner) and fail on drift: a roadmap left after its archive, archived
  changes that are not stamped or have unticked Automated items, Summary placeholders instead of
  merge SHAs, archived roadmaps with open rows, queued roadmaps that are fully done, backlog folders
  without their roadmap, index rows pointing at missing files, and a missing or stale state.json.
  Repairs history: --fix for the mechanical shapes, --sweep for a worklist with evidence that an
  agent settles to zero. Use in CI, before an archive or roadmap commit, or when the user says
  "check the context", "run the doctor", "what waits for me", "refresh the state", "clean up the
  history", "sweep the doctor to zero".
argument-hint: "[doctor [--fix [--write] | --sweep | --baseline | --protection] | state write|print|check] [--root <dir>] [--json] [--staged]"
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
| `python3 <S>/doctor.py --fix [--write]` | the mechanical repairs of history, printed edit by edit; a dry run unless `--write` |
| `python3 <S>/doctor.py --sweep [--json]` | every remaining failure as a worklist entry with evidence pointers; read-only |
| `python3 <S>/doctor.py --baseline` | last resort only: accept today's failures in `context/doctor-baseline.json`; it only shrinks |
| `python3 <S>/doctor.py --protection [--json]` | asks the forge (`gh`, read-only) whether the main branch requires every pull-request CI job before a merge, administrators included (`FAIL main-checks-not-required` per gap); exit 75 when it cannot tell. Same as `npx softure-skills doctor --protection` |
| `python3 <S>/context_state.py write` | regenerate `context/state.json` from the working tree |
| `python3 <S>/context_state.py write --staged` | regenerate it from what is staged, and stage it (use right before a commit) |
| `python3 <S>/context_state.py print` / `check` | show it / exit 1 when it is missing or stale |

`<S>` is `.claude/skills/softure-doctor/scripts` in an installed project.

## When it runs

- **CI of every adopting project**, documentation-only changes included: `npx softure-skills doctor` in a job
  named `context-doctor`, on `pull_request` and on `push` to the main branch, with no paths filter and no condition
  (the installer prints the workflow; WORKFLOW §12.2). The doctor fails with `ci-doctor-trigger` when that job misses
  pushes to `mainBranch` (no `push` trigger for it, a `paths`/`paths-ignore` filter, an `if:`): fix the workflow's
  `on:` block and drop the condition, never baseline it.
  Keep the name: outside readers look for that check run on the main branch's head; in GitHub Actions the doctor
  writes its failure codes there as annotations (the first, `context-doctor failure codes`, lists them all), as
  one plain line of the job's log (for readers with Actions: read only) and as the job summary. A project with history adds it after the rollout (WORKFLOW §12.4):
  `--fix --write`, the sweep to zero, the owner's short list, then the CI job. Drift happens in the documents, so a CI that skips doc-only
  changes misses it.
- **`softure-init`**, and whenever a red check reached the main branch through a merge: `doctor --protection`.
  It is not part of the CI run (a CI token cannot read branch protection); a gap goes to the owner, who turns on
  the required checks (classic protection with "include administrators", or a ruleset with an empty bypass list).
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
| `archived-change-progress` | the change was archived with open Automated items: tick them with their SHA when the work is on the main branch, or mark them `~~dropped~~ — dropped: <reason>`. An item struck through or carrying a dropped/cancelled/not-applicable note is already dropped and never counts (`--fix` normalises it) |
| `archived-roadmap-open-items` | rows of an archived roadmap end `done`, `done_code`, dropped or carried (with where they went) |
| `archived-roadmap-open-checks` | an archived roadmap still holds unticked owner entries: tick each with its evidence (`— done: <sha / release / path>`), as obsolete (`— obsolete: <reason>`), or carry it to a live roadmap or a `cockpit` issue and tick it with where it went |
| `archived-roadmap-summary` | put the merge SHA (`git log --merges --grep "<change-id>"`) into the row's merge cell. Only the item table (the one with a merge column) is read; a SHA, a release tag (where the roadmap records a release instead of a merge), `carried`, `dropped` and `— <reason>` pass |
| `queued-roadmap-done` | archive the finished queued roadmap to `foundation/archive/` |
| `roadmap-item-shape` | a live roadmap (`roadmap.md` or a queued one) apps cannot read: give every `### <ID>: <title>` block its at-a-glance row, keep row statuses in the vocabulary (§5), give each block a title. A block `Status` that contradicts its row is mechanical (`--fix` copies the row's status) |
| `backlog-without-roadmap` | move live entries to a queued roadmap, then remove the folder |
| `index-missing-file` | a real link (a markdown link, or a cell that is only a path in a file column) points at a missing file: fix or drop the row; a path mentioned in a description cell never fails |
| `state-missing` / `state-stale` | `context_state.py write`, commit `context/state.json` |
| `baseline-stale` | a baselined failure is fixed: `doctor.py --baseline` rewrites the file without it (commit it) |
| `ci-doctor-trigger` | the workflow's `context-doctor` job misses pushes to `mainBranch`: give its `on:` `pull_request` and `push` with `branches: [<mainBranch>]`, drop any `paths`/`paths-ignore` filter and the job's `if:` (never baselined) |
| `owner-entry-put-off` | a note, not a failure: an open `## Owner decisions and checks` entry that still carries `(later: #N)` (the settle shape before 0.37.0). Move the item to `roadmaps/roadmap-later.md` under a new ID and tick the entry `— later: #N → <new ID>` (WORKFLOW §8.6) |

## Mechanical repairs: `--fix`

`doctor.py --fix` prints every edit it would make and the failures left after them; `--fix --write`
applies them. It writes only under `context/`, and a second run changes nothing. These shapes are
mechanical:

- `archived-change-status`: the archived `change.md` gets `status: archived`, and the old value is kept
  as `legacy_status` in its front matter (`implemented`, `done`, `impl_reviewed`, … stay readable);
- `index-missing-file` in an index inside an archive folder: the link is rewritten to the file's current
  path when git history shows where it moved (renames followed across several moves); a file deleted on
  purpose (git shows the deletion, no rename) is marked `(removed in <sha>)` with the deleting commit;
- a dropped Progress item of an archived plan (unticked, but struck through or carrying an explicit
  dropped/cancelled/not-applicable note) is normalised to `- [x] ~~<item>~~ — dropped: <note>`;
- a carried entry of an archived roadmap: an unticked owner check or pre-release step, or an open row, whose
  text carries a carry marker (`→ roadmap-<slug>`, `carried to <roadmap>`) naming a roadmap that exists
  (queued, archived or the live one) is ticked `- [x] <text> — carried to <path>` (a row becomes
  `carried (to <path>)`). A marker whose roadmap does not exist is left alone and named: it stays a failure.
- an item block of a live roadmap whose `- **Status:**` contradicts its at-a-glance row takes the row's status cell
  (the row is what scripts write; the block mirrors it).

It skips, and names, every row it cannot settle from history (a live index, a target whose move or
deletion the history does not show). A shallow clone works on the commits it holds and names what lies
past its edge (`git fetch --deepen <n>` reaches further). Those and every other failure are judgement cases.

## Sweep history to zero

`doctor.py --sweep --json` lists every failure left after `--fix` as one entry per thing to settle:
`code`, `path`, `line` and the exact `text` of the line, `evidence` (pointers of kind `commit`,
`release` or `file`, each with a note), `settle` (what to do), and a `class`:

| Class | Means | Who settles it |
|---|---|---|
| `evidence` | the repository holds proof (below) | the agent, with that proof |
| `superseded` | no direct proof, but later work made it obsolete: for an owner check or open row of an archived roadmap, a later roadmap was closed and a release shipped after it, or the same item ID or file area appears in a later archived change; for a Progress item, a later phase of the same plan is ticked. Its `evidence` names the roadmap, release or change | the agent, as obsolete; never forwarded |
| `owner` (`owner: true`) | still meaningful today and only the owner can settle it: a decision about future work (`owner_reason: decision`), a secret, account or connector (`secret`), a step outside the repository whose effect the agent cannot see (`outside`), or nothing found at all (`unsettled`). `tried` says what the sweep looked for | the owner |

The evidence it looks for:

| Code | Evidence |
|---|---|
| `archived-change-progress` | the SHA ticked items of the same phase cite; commits that touched the phase's files after the plan's date; the change's merge commit |
| `archived-roadmap-summary` | the merge (or squash) commit of the item's change on the main line; the last SHA of its archived plan |
| `archived-roadmap-open-items` | the item's archived change folder, its merge commit, the release that contains it, later roadmaps that mention it |
| `archived-roadmap-open-checks` | the same for the item the check names, plus the first release after the close (for pre-release steps) |
| carried entries | a check or row with a carry marker whose roadmap exists: that roadmap (`--fix --write` ticks it) |
| post-merge steps | a release after the merge, `close #N`, the Dependabot pull requests: asked of the forge through `gh` (the first release published on or after the merge date, the state of `#N`, open Dependabot pull requests); class `forge` when the forge cannot be reached (`--no-forge` skips it) |
| anything else | the file to fix (`index-missing-file`: where git history says the file went, or that it never existed) |

Work the list in one change per repository (`docs(context): settle history to zero`):

1. `doctor.py --fix --write` first, and commit it, so the sweep holds only judgement cases.
2. For every entry, open its evidence (`git show <sha>`, the file, the release notes) and decide what
   it proves. **Settle with evidence, never without:** write the proof into the line itself.
   - Progress item: `- [x] <text> — <sha>` when that commit did it; `- [x] ~~<text>~~ — dropped: <reason>`
     when the evidence shows it was never done and is no longer wanted.
   - Summary placeholder: the merge SHA in the `Merge` cell (a release tag, `carried`, `dropped` or
     `— <reason>` where there is no merge).
   - Open row: `done` (it shipped), `carried (to <path>)` (a later roadmap took it), `dropped (<reason>)`.
   - Open check: `- [x] <text> — done: <sha | release | path>`, `- [x] <text> — obsolete: <reason, with
     the evidence that made it obsolete>`, or carried (below).
   - `superseded` entry: close it yourself as obsolete, with its evidence: `- [x] <text> — obsolete:
     superseded by <release / roadmap / change>` (a row: `dropped (obsolete: superseded by <ref>)`).
     Never forward it to the owner: a screenshot review of a page rebuilt since, or "after the release,
     re-run X" for a release long gone, has no answer the owner could give.
3. **`forge` entries are yours, not the owner's.** Check each with `gh` before anything goes to the owner:
   `gh release list` (a release published after the merge), `gh issue view <N>` / `gh pr view <N>`,
   `gh pr list --author app/dependabot`. Tick it with what the forge shows (`— done: v1.5.0`,
   `— done: #12 closed`); only a step the forge shows not done, and only the owner can do, goes on.
4. **Only true owner items stay open, in one place.** An entry is the owner's when the evidence does
   not settle it, nothing later superseded it, and only the owner can: a decision about future work
   that is still open, a secret, account or connector, or a step outside the repository (a production
   setting, a real device) whose effect the agent cannot see. Before forwarding an `unsettled` entry,
   try what its `tried` lines did not, and say in the report what you tried. Carry it to the
   live roadmap's `## Owner decisions and checks` (or a `cockpit` issue, WORKFLOW §8.6) and tick
   the archived line `— carried to <path | #N>`. Never carry a check whose work the evidence shows done,
   and never tick a decision on the owner's behalf.
5. Regenerate the state (`context_state.py write`) and re-run `doctor.py` until it exits 0. Commit.
6. Report: failures per code before and after, and **one short list for the owner**: `ID | what the
   owner decides or does | where it lives now`. Nothing else is left open.

An entry the agent cannot settle and that is not the owner's (the evidence is ambiguous) is named in
the report with its evidence, not ticked.

## Baseline: the last resort

`doctor.py --baseline` writes the failures that remain to `context/doctor-baseline.json`. The check
then reports them as `baselined` and fails only on a new failure and on a baseline entry that was
fixed but not removed (`baseline-stale`). It only shrinks: run again, it drops the fixed entries,
refuses to add new ones (exit 1, it names them) and removes the file once it is empty. State findings
are never baselined, and `--fix` and `--sweep` ignore the baseline.

Use it only when the owner decides a project cannot finish the sweep in one change; never to get a red
CI green, and never on your own initiative. Record why in the commit. The sweep to zero is the path.

A project that has never written `context/state.json` gets a `note`, not a failure, until the first
script run creates it.

## Rules

- `context/state.json` is written by scripts only. Never edit it by hand; regenerate it.
- Never tick, fill or close anything in the sweep without the evidence written into the line.
- The doctor never edits anything, except `--fix --write`, which is run on purpose and edits only the
  mechanical shapes above. A skill that runs it fixes only the files it owns in that run.
- `open_changes`, `updated_at` and owner-queue entries from open changes are refreshed on every write
  and never make the file stale, so a change branch that edits its own `change.md` keeps a green doctor.
- `owner_queue` reads only what is live (WORKFLOW §12.1): an unticked entry left in an archived roadmap
  is a failure to settle, not something that waits for the owner.
- Cockpit issues (label `cockpit`, WORKFLOW §8.6) live on the forge, not in `state.json`;
  an aggregator reads both. The exception is a package bump's owner work, which the package-update
  routine records in `context/workflow.json` (`routines.packageUpdates`: holds with `owner`,
  `ownerSteps` until `confirmed`): those feed `owner_queue`, so editing them needs a `state` write.
