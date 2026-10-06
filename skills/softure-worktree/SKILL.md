---
name: softure-worktree
description: >
  Carry exactly ONE change — a roadmap item or Change ID — in its own git
  worktree next to the repo: run the whole softure chain there autonomously,
  deciding instead of asking (research → frame → plan → plan-review →
  implement → impl-review → full integration suite → lesson → archive on the
  branch), pull the main branch in and resolve conflicts, then STOP at
  "ready_to_merge" and wait for the owner's signal. On that signal: merge into
  the main branch, remove the worktree and the branch. No push of the main
  branch, no release, no deploy (the owner publishes releases). Built so
  several changes can run in parallel sessions without stepping on each other.
  Use when the user invokes /softure-worktree, or says "take this change in a
  separate worktree", "run it in its own worktree and tell me when it's ready
  to merge", "take it in a worktree and go"; and for the second half when
  they say "merge it", "go into main", "main is free", or run
  /softure-worktree merge.
argument-hint: "[roadmap-item-id | change-id] [--base <branch>] [--dry-run] | merge [change-id] [--no-tests] | status"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Agent
  - Skill
  - AskUserQuestion
  - SendMessage
  - TaskCreate
  - TaskUpdate
  - TaskList
  - TaskGet
---

# /softure-worktree — One Change, Its Own Worktree, Main Branch on Signal

**One run, one change, one worktree, one branch.** This skill carries a single
change from an empty folder to `ready_to_merge` in its own worktree, and merges
it only on a signal. It never walks the roadmap: picking several changes,
running them side by side and merging them one by one is
`/softure-worktree-manager`'s job — it launches this skill once per change.

This skill is the autonomous shell around the delivery chain
(`WORKFLOW.md` §1). It invokes every chain skill with `--auto`, so they decide
instead of asking (`WORKFLOW.md` §8), and it stops only on the escalations
below.

> **Read this first if you are tempted to skip a step:** each chain skill
> consumes the artifact the previous one wrote. Skipping `/softure-research`
> does not save a step, it hands `/softure-plan` an empty input and produces a
> plan built on guesses. The chain is the point.

**Project configuration.** Everything project-specific — the main branch, the
gates, the integration suite, the migrations folder, the worktree setup, the
report language, whether releases belong to the owner — comes from
`context/workflow.json` (`WORKFLOW.md` §2). Read it at A0 with
`python3 <S>/wt_config.py --json`. Below, `<main>` is `mainBranch`, "the gates"
are every command in `gates`, and reports to the user are written in
`language`.

## Invocation

```
/softure-worktree                      # pick the next free, unblocked item → run to READY
/softure-worktree FC-2                 # this roadmap ID (or Change ID)
/softure-worktree FC-3 --base <branch> # item whose prerequisite is still an unmerged branch
/softure-worktree --dry-run            # show the pick and the overlap check, change nothing
/softure-worktree merge [change-id]    # owner's signal: merge into <main>, clean up
/softure-worktree merge --no-tests     # owner waived the test run on <main> after the merge
/softure-worktree status               # all worktrees, stages, free lesson and migration numbers
```

Invoked from inside an existing change worktree (or with a Change ID whose
branch already exists) → **resume**, not open (see A0).

`<S>` below is the scripts folder of this skill **in the main tree**:
`<MAIN>/.claude/skills/softure-worktree/scripts` (`<MAIN>` =
`python3 <S>/wt_config.py --root`, the first entry of `git worktree list`).
Always call the scripts through that absolute path — installed skills are
usually git-ignored, so a fresh worktree may not have its own copy.

## Two phases and one gate

```
PHASE A (autonomous)                                         GATE          PHASE B (on signal)
A0 preflight → A1 pick → A2 open → A3 chain (… → A3.8 integration) → A4 archive → A5 sync → READY ⏸ → B merge → cleanup
   <main>        <main>    <main>+wt   worktree                          worktree     worktree            <main>
```

**READY is the end of phase A and the end of the turn.** Report and stop. Do
not merge, push `<main>` or release on your own. `<main>` is shared; the moment
of entry is the owner's call — another process may be running on it.

**What may leave the machine:** the change branch itself (pushing it protects
the work) and whatever refs the project's remote integration command pushes
(A3.8). `<main>` changes only through the merge on the signal (Phase B or the
coordinator); a push of `<main>` only as Phase B or the roadmap header says.
**Tags and releases never** when `release.owner` is true — a published release
*is* the deploy, and it is the owner's (see *Deploy-bound work*).

> **Under `/goal`:** the condition is met at READY. If the owner set a goal
> such as "implement and merge", READY still comes first; merge only follows an
> explicit signal in the conversation or the goal text itself saying "merge
> without asking". Do not let a stop hook push you into phase B.

## Cloud session (Claude Code on the web) — branch instead of worktree

**Detect it first, in A0:** `[ "$CLAUDE_CODE_REMOTE" = true ]`. When it holds,
this run is a cloud session and the rules in this section **replace** the
matching steps below. Everything else (the chain, the gates, the Prime
Directive, the escalations) stays as written. Why a separate mode: the
container is fresh and ephemeral, it has one checkout on the session's own
branch, and the *other* sessions are other containers that see **only
`origin`** — a stage written to a local `<main>` is invisible to them, so two
cloud sessions could take the same item.

**`worktree.cloudState: "branch"`** changes points 1 and 6: the claim and every
stage are committed **on the session branch only** (`wt-roadmap.py` does it by
itself in that mode) and nothing goes to `origin/<main>` before the merge. Use
it when a coordinator assigns the items — then the assignment, not a claim on
`<main>`, keeps two sessions off one item, so A1 takes the item it was given
and does not need `origin/<main>` to show it free. The branch carries the
state: push it at READY (point 5), and earlier only if the project wants the
board live (each first push of a ref may run the pre-push hook). Default
`"main"` is the flow below.

**1. Claim first, on origin, before anything else.** Right after A1 picks the
item — before installing dependencies, before research — mark it taken **on
`origin/<main>`**:

```bash
python3 <S>/wt-roadmap.py open <change-id>
```

In a cloud session the script (it detects `CLAUDE_CODE_REMOTE`) fetches
`origin/<main>`, commits that one row on top of it without touching the
checkout, and **pushes it at once** (retries on a race). Git hooks stay on:
the push goes from a throwaway worktree whose HEAD is the roadmap commit and
whose upstream is `origin/<main>`, so a pre-push hook that diffs
`HEAD @{push}` sees only `roadmap.md`. Never `--no-verify` a push, never
disable hooks. **Do not push the claim by hand from the session checkout or a
detached HEAD**: the hook then counts the session's code (or "all files") and
runs the full suite first, and the claim stays invisible to other sessions
meanwhile. **Check it landed:** `git ls-remote origin <main>` must show the new
SHA before you start research.

The row says `cloud session, branch <session-branch> — do not take in another
session`. If `open` refuses because the row is already `in_progress`, another
session owns it: pick again (A1), never take it over. Every `stage` call later
in the chain goes to origin the same way, so the owner and every other session
see live state. A1's "not already taken" check reads **`origin/<main>`**
(`git fetch origin <main> && git show origin/<main>:context/foundation/roadmap.md`),
not the local file.

**2. No worktree — the session branch is the change branch.** Skip
`wt-open.sh`. Work in the checkout, on the branch the session was started on;
it plays the role of `<change-id>` everywhere below (commits, `## Progress`
SHAs, the READY report). Relative paths are safe — there is no second tree. If
the session branch is not at `origin/<main>`'s tip when you start, merge
`origin/<main>` into it first. Record the branch in `change.md` (`branch:`).

**3. Dependencies.** Run the `worktree.setup` steps that make sense in the
container (installing dependencies; not copying a local `.env` that does not
exist). If a private package registry is unreachable (no token in the
container), install everything else and restore the manifests so nothing about
it lands in a commit: back up the manifest and lockfile to the scratchpad,
remove the private dependency, install, copy the backups back, and check
`git status --short` is clean.

**4. Fewer resources — plan for it.** Cloud containers have fewer CPUs and
often no outbound access to production hosts or ssh. So:

- Run the test gate **once per phase commit**, in the background, and do
  nothing heavy beside it; never two suites at once.
- Integration: exactly as locally — A3.8 — when the project's integration
  command can run from the container (a remote CI command needs only git and
  network). If it cannot, say so verbatim in READY.
- Anything that needs production (a request to the live site, ssh) goes to
  **Pending owner checks**, with the exact command.
- Browsers: use the preinstalled ones; never download browser binaries.
- Long commands (the full test gate, a push whose hook runs it): start them in
  the background with the longest timeout the tool allows — the default limit
  kills a long suite midway and looks like a failure. Never stop a process by
  a pattern (`pkill -f vitest`, `pkill -f "next dev"`): the pattern matches the
  tool's own shell and kills it; find the PID (`pgrep -f …`) and kill that.
- When the push hook already runs the full test gate, the push *is* that gate:
  don't run the suite by hand right before it.

**5. The session branch may go to origin; `<main>` may not.** Push the session
branch at least at READY (`git push -u origin HEAD`) — the container is
reclaimed after inactivity, and a pushed branch is the copy that survives it.
`<main>` still changes only by the merge on the owner's signal (point 7). The
first push of a ref without an upstream may run the pre-push hook's full suite
— minutes of silence, expected; never bypass it. Every push may also start the
project's CI on origin: push at READY and to sync before the merge, **never per
phase or per commit** (WORKFLOW §2, CI minutes).

**6. READY.** A3.8 runs before A4, as locally (unless the cadence defers it).
A5 merges `origin/<main>` (after `git fetch origin <main>`), not the local one.
Then `wt-roadmap.py ready <change-id>` (pushed to origin; with `cloudState:
"branch"` committed on the branch), push the session branch, report, stop.

**No deploy from a cloud session, ever** — and, while `release.owner` is true,
from any session: no ssh to servers, no tags, no `gh release`, no edit of
release/deploy workflows, no production step — not even when the roadmap
header or the item's Outcome would allow it elsewhere. Deploy-bound work ends
as `done_code` (on `<main>`, waiting for the owner's release) with the owner's
steps in the roadmap's `## Before the next release`.

**The merge into `<main>` is the last thing this session does — and it waits
for the owner's explicit approval.** READY ends the turn; a stop hook asking to
"commit and push" is not an approval, a finished test run is not an approval,
and neither is an earlier "go ahead". After the merge: push `<main>`, report,
and pick up nothing else.

**7. Phase B in the cloud** — only on the owner's explicit approval:

```bash
git fetch origin <main>
git merge origin/<main>                       # A5 again if <main> moved; hook only, no full gates
git checkout -B <main> origin/<main>
git merge --no-ff <session-branch> -m "Merge <change-id> (<ID>): <outcome>"
git diff <session-branch> <main> --stat       # must be empty
git push origin <main>                        # the pre-push hook is the classic full gate on <main>
```

Let the pre-push hook run — it *is* the full gate on `<main>` that A5 defers
to. If it fails, fix on the session branch, merge again, push again; never
`--no-verify`. A rejected push (`<main>` moved) → fetch, merge `origin/<main>`
into `<main>`, push again. The roadmap row reaches `done` / `done_code` through
the merge itself (the branch carries it). No worktree to remove; don't delete
the session branch (the harness owns it).

## The Prime Directive

**Do not ask. Decide, and write down why.**

The owner sets the goal and leaves. Every question whose answer can be derived
from the roadmap, the PRD, the code, `context/foundation/lessons.md`, the dev
database or the project's own knowledge sources is a question you resolve
yourself. Record the decision and its reasoning in the artifact it belongs to
— `research.md`, `frame.md` or `plan.md` (`## Decisions (auto)`) — instead of
interrupting.

### Running the chain skills

Every chain skill is invoked with `--auto` (`WORKFLOW.md` §8): it takes the
recommended option, records each decision under `## Decisions (auto)` and stops
only for its own three escalations. If a chain skill still asks something
(an older version, an unexpected branch), answer it yourself by the same rule:
the recommended option, unless the roadmap, research or `lessons.md` argues
otherwise — then the better-argued option, written down with its reason. "I'm
not sure" is never your answer; you have the material.

### The three escalations

Stop and use `AskUserQuestion` only here. Everything else you resolve. When the
run was launched by `/softure-worktree-manager` (the prompt names a
coordinator), send the escalation to the coordinator with `SendMessage`
instead — nobody watches a background session's prompt.

1. **The work would destroy or overwrite someone else's work.** Uncommitted WIP
   you would have to discard, a migration that drops a populated column, a force
   push, anything irreversible that is not yours.
2. **A measurement falsifies the premise of the whole item.** Not "a phase got
   harder" — that you re-plan. This is "the roadmap item assumes X, X is
   measurably false, so the item as written builds nothing." Report the
   measurement and wait. Do not plan around a refuted premise.
3. **The run spans sessions and unpushed `<main>` is the only copy.** The
   change branch is no reason to ask: push it (`git push -u origin
   <change-id>`) whenever machine loss would cost real work, and say so in the
   report. Only `<main>` cannot be pushed early on your own (Phase B step 6):
   if a merge made `<main>` the only copy of real work, ask.

A fourth, weaker case: an **irreversible production change** — ask, but only
when the roadmap item does not already call for it. Dropping a populated
production table, sending mail to real addresses, a force push: irreversible
*and* unasked-for. A change the item names in its own Outcome is **authorized
by that Outcome** — do it, verify it, report it afterwards. Reversible changes
you always make.

### The failure mode this section exists to prevent

**Stopping is not the safe default. Stopping is a failure.** The owner set a
goal and left precisely so the work would continue without them; a run that
halts to confirm a decision the material already settles has turned an
autonomous run into a slow interactive one, and the owner comes back to a
question instead of a result.

Three habits that look like diligence and are not:

- **The pre-emptive check-in.** "The plan is ready — shall I start?" No. The
  chain says implement next, so implement.
- **Escalating a product judgement because it *feels* like the owner's.** A
  choice between two options you can argue from research, `lessons.md`, the PRD
  or a measurement is **yours**, even when it touches copy, naming or what a
  page claims. Pick the better one, write down why, move on. The owner corrects
  it later if they disagree — cheaper for them than being asked.
- **Listing "decisions I need from you" at the end of a step.** If you can name
  a recommendation, you have already made the decision. Record it as a
  decision, not a question.

The test: *could I defend this choice from something written down?* If yes,
decide. Only a genuine escalation stops the run — and escalation 2 means a
**measurement refuted the premise**, not that a choice felt weighty.

## Only your change

You own **one** change: the one whose Change ID is your branch name. Other
folders in `context/changes/` belong to other worktrees or are queued for them
— never resume, edit, archive or "tidy" them.

### Resume ladder

`change.md`'s `status` (`WORKFLOW.md` §4) tells you where the chain broke.
Re-entering a completed step is safe; the chain skills are idempotent by
artifact.

| `status` | Re-enter at |
| --- | --- |
| `new` | A3.1 — research |
| `preparing` | A3.2 — frame (if `frame.md` is absent and needed), else A3.3 — plan |
| `planned` | A3.4 — plan review |
| `plan_reviewed` | A3.5 — implement, from the first `- [ ]` in `## Progress` |
| `implementing` | A3.5 — implement, from the first `- [ ]` in `## Progress` |
| `implemented` | A3.6 — implementation review |
| `impl_reviewed` | A3.7 — triage, then A3.8 — integration, then A4 — archive |
| `archived` | A4 — finish the move, then A5 |

The first `- [ ]` in `## Progress` (`WORKFLOW.md` §6) is the resume point
*within* implementation. Trust it over any memory of what you did.

This skill does **not** walk the roadmap item after item (that is
`/softure-worktree-manager`), push at archive, or edit the main tree's roadmap
by hand — the stage lives on `<main>` and is written only by `wt-roadmap.py`.

## Phase A

### A0 — Preflight (main tree, `<main>`)

> **Cloud session?** (`CLAUDE_CODE_REMOTE=true`) → see *Cloud session* above:
> claim on origin first, no worktree; the session branch may be pushed,
> `<main>` changes only on the signal.

```bash
python3 <S>/wt_config.py --json          # the project's commands, branch, language
bash <S>/wt-status.sh --files
git status --short && git diff --cached --quiet || echo STAGED
```

- **Resume check first.** If the requested Change ID already has a branch, or
  the session was started inside `../<repo>-<id>`, it is a resume: enter it
  (A2, *working through paths*), read `change.md` `status` and use the resume
  ladder. Never open a second worktree for the same change.
- Staged changes on `<main>` are someone else's commit in progress. Fine for
  reading, but `wt-roadmap.py` refuses to commit under them. Wait and retry;
  don't unstage them.
- Uncommitted WIP on `<main>` is **normal** (other sessions). Record it; never
  touch it.
- No `context/workflow.json` → the project has not run `/softure-init`. Run it
  with `--auto` (it detects the stack) and commit the file on `<main>` as its
  own docs-only commit before anything else.

### A1 — Pick

Source: an argument wins — match it against the roadmap `ID` column first
(`FC-2`), then the Change ID. Without one, pick from `## At a glance`
(`WORKFLOW.md` §5):

- **Eligible** = `Status` is `ready` and `Mode` is `autonomous`; never `done`,
  never `blocked`. `proposed` only when no `ready` item remains — say so in
  `change.md`'s Notes, because `proposed` means the owner marked it droppable.
- Read the item's `### <ID>` block (`Outcome`, `Change ID`, `Prerequisites`,
  `Risk`, `Unknowns`, `Baseline`). **Its Unknowns are your planning agenda** —
  each is a decision you will make and record, not a question you will ask.
- Order: `## Order`, then table order.

Plus three rules for parallel work:

1. **Not already taken.** A row that says `in_progress` or `ready_to_merge`
   belongs to another session, even if its worktree looks idle.
2. **Prerequisites delivered in code.** `done` and `done_code` both count,
   because the code is on `<main>`. A prerequisite that is still a live branch
   makes the item eligible **only** with `--base <that-branch>`; record the
   merge order in the roadmap note (`merge after FC-1`).
3. **No overlap with running worktrees.** Compare the item's likely surface
   (its roadmap block, the PRD refs, a quick grep) with `wt-status.sh --files`
   of every live branch. Shared *documents* (`roadmap.md`, `lessons.md`,
   `prd.md`) are expected and resolvable. Shared **code files, or both needing
   a migration,** is a collision — two branches will generate the same
   migration number. Prefer a different item. Take it anyway only when nothing
   else is eligible, and write the collision into `research.md` so the merge
   step expects it.

**Nothing eligible → report what is taken, what is blocked and why, then
stop.** Don't invent work and don't take an overlapping item to keep busy.

If the owner names a different source ("from the backlog", "from the changes
folder"), use exactly that source. Moving an entry from `context/backlog/` into
`context/changes/` is a `git mv`.

`--dry-run`: print the pick, the overlap table, the base branch. Stop.

### A2 — Open

> **Cloud session:** replaced by *Cloud session* points 1–3.

Order matters: **mark the roadmap on `<main>` first, then branch from it**, so
the branch already carries its own `in_progress` row and the first back-merge
has one conflict less.

```bash
python3 <S>/wt-roadmap.py open <change-id> [--note "prerequisite X on branch Y — merge after X"]
bash    <S>/wt-open.sh <change-id> [--base <branch>]      # prints WT=<path>
```

`wt-open.sh` creates `../<repo>-<change-id>` on branch `<change-id>`, runs
every `worktree.setup` step inside it (installing dependencies, copying local
env files), and exits non-zero unless the worktree is clean afterwards. A setup
step that writes tracked files (an installer refreshing committed files) is a
bug in the setup — restore the files and fix the step; never commit them.
Prefer a real install over symlinking dependency folders from the main tree:
some bundlers break on symlinked dependencies.

Then **work in the worktree through paths, not through the session's cwd.**
The session stays launched in the main tree, and every Bash call may reset
there. So:

- every Bash call starts with `cd <WT> &&` (or uses `git -C <WT>`);
- every `Read`/`Edit`/`Write` takes an **absolute `<WT>/…` path**. Check the
  prefix before each edit. One slip writes into `<main>` while another session
  is editing the same file;
- chain skills write to `context/changes/<id>/…`. Translate that to
  `<WT>/context/changes/<id>/…` every time, never the main tree's copy; tell
  each chain skill the worktree root when you invoke it;
- sanity check at the start of each step: `cd <WT> && git branch
  --show-current` must print `<change-id>`.

`EnterWorktree(path: "<WT>")` would move the session's cwd into the worktree
and make relative paths safe; use it only when the owner allows it in this
repo.

Finally, the change folder: `/softure-new <change-id> --auto` if it doesn't
exist. If it arrived with `<main>` (queued in `context/changes/`), it is
already there. If it lives in `context/backlog/`, `git mv` it. Set `branch:` in
`change.md` to `<change-id>` (worktree `<WT>`).

### A3 — The chain (inside the worktree)

The chain runs **inside the worktree** (paths, not cwd — A2). First the
worktree-specific rules that hold across all its steps, then the steps.

**Stage on `<main>`, every step.** At research, frame, plan, plan-review,
`implement N/M`, impl-review, integration and archive:

```bash
python3 <S>/wt-roadmap.py stage <change-id> "implement 2/5"
```

It works from any worktree (it finds the main one itself) and commits only that
row. The owner reads `<main>`'s roadmap as the live board — don't make them
ask whether it is up to date.

**Gates run in the worktree** — every command in `gates` — and `git add -A`
there. The worktree has no one else's WIP, so "the whole tree" means only your
work, and a tree-wide pre-commit hook sees only your tree. Disabling hooks
should never be needed here; if it seems to be, something foreign got in —
find it.

**Integration: the full suite, once per item — A3.8** (with the default
`integration.cadence: "change"`). Running only "your" integration tests lets
regressions through that no session sees; the full suite on the final tree is
what READY reports. With `"roadmap"` the project trades that per-item signal
for one run on `<main>` at the end (the coordinator's M7): skip A3.8 and say
so in READY.

**Baseline for "see it red first".** Put a baseline worktree **in the
scratchpad**, detached, never as a sibling `../<repo>-baseline` — a sibling
directory is indistinguishable from a change worktree to everyone else.

```bash
git worktree add --detach "$SCRATCH/baseline" <sha>
# provide dependencies (install, or symlink when the test runner tolerates it)
# … run the test, see it fail …
git worktree remove --force "$SCRATCH/baseline"
```

**Lesson numbers.** Before `/softure-lesson`, run `wt-status.sh`. It prints
the highest `L-` across `<main>` **and every worktree** and the next free one —
an unmerged branch may already hold the number `<main>` would give you.
Numbers can still collide with a branch opened later; A5 re-checks.

**Migrations.** Migration generators number from your branch's state, so two
branches can produce the same number. Don't write the migration's number into
prose (roadmap notes, deployment docs) until A5 has confirmed it.

#### A3.1 — Research

```
/softure-research <change-id> --auto
```

Scope is the roadmap item's Outcome plus its PRD refs; depth is "deep" for
anything touching money arithmetic, auth, migrations, data integrity or the
product's core engine, "standard" otherwise. Pass that along.

Before moving on, confirm `research.md` exists and actually answers the item's
`Unknowns`. If it does not, dispatch targeted sub-agents for the gaps and
append the findings. A plan built on a thin research file is the most
expensive mistake in this chain.

#### A3.2 — Frame (conditional)

`/softure-frame` challenges **what** to build. Run
`/softure-frame <change-id> --auto` when **any** holds:

- The Outcome names a mechanism rather than a user-visible result ("add a
  feature flag store") and research suggests a cheaper mechanism reaches the
  same result.
- Research contradicted a roadmap `Baseline` claim, or found the thing already
  half-built.
- The item's `Unknowns` contain a genuine fork where the branches differ in
  cost to the owner, not just in taste.
- `PRD refs` conflict with each other or with `lessons.md`.

Otherwise skip, and **write one line in `research.md` saying you skipped
framing and why**. A silent skip is indistinguishable from forgetting. When
frame finishes, continue with the plan.

#### A3.3 — Plan

```
/softure-plan <change-id> --auto
```

Two hard requirements before you leave this step:

- **No open questions in the plan.** For you, an open question means *decide
  it now and write the decision in*. An open question that survives into
  `plan.md` becomes an interruption during implementation.
- **`## Progress` is well-formed** (`WORKFLOW.md` §6): last section, one
  `### Phase N:` per `## Phase N:`, every success criterion as `- [ ] N.M`,
  `#### Automated` and `#### Manual` split honestly. `/softure-implement`
  cannot resume without it.

**Split Automated vs Manual by who can verify, not by who traditionally
does.** A3.5 verifies most "manual" checks itself (browser automation, the
database, HTTP, the product's own tools). A check you can drive belongs under
`#### Automated` with the command that drives it. Reserve `#### Manual` for
what genuinely needs the owner's eyes — visual taste, copy tone, a third-party
console.

##### Choose the implementation discipline here

Write the choice into the plan, per phase (`**Discipline:** TDD | test-after`).
Use TDD when the phase changes **arithmetic, money handling, tax or business
rules, migrations, or fixes a reported wrong number**: an arithmetic defect
gets an oracle of a *different kind* than the implementation, and you must
**see the new test fail before the fix**. For UI, wiring, copy and
scaffolding, test-after is fine. `/softure-impl-review` checks you did what you
picked.

#### A3.4 — Plan review

```
/softure-plan-review <change-id> --auto
```

Resolve every finding yourself:

| Severity | Autonomous disposition |
| --- | --- |
| CRITICAL | Always fix. Re-run the review afterwards. |
| WARNING | Fix unless the fix contradicts the item's scope; then "Accept risk" with a one-line reason. |
| SUGGESTION | Apply when it fits inside files this plan already touches and adds no phase. Otherwise skip with a one-line reason. |

Never leave a finding without a decision — the review file is the audit trail
of a run nobody watched. If triage rewrote phases, **re-check `## Progress`
consistency** before implementing.

#### A3.5 — Implement every phase

```
/softure-implement <change-id> phase 1 --auto
```

Then phase 2, 3, … to the end, without stopping between phases. Re-read
`plan.md` at each phase start — earlier phases may have taught you something
the plan did not know.

##### Gates before every phase commit

Every command in `gates`, in the worktree. Green or there is no commit. A
pre-push hook may run the tests again on later pushes; per commit, these gates
are the line.

No integration run per phase: the full suite runs once, at A3.8, on the final
tree. A phase that writes a new integration test and wants to see it run
earlier uses the same script with its own name
(`wt-integration.sh <change-id>-p<N>`) — it is the full suite, so do it only
when the test is the point of the phase.

##### Staging

In a worktree the whole tree is your work — nobody else edits it — so stage
the whole tree: `git add -A`. Something foreign in the worktree's diff means a
path slipped into the wrong tree (A2); find out how before committing. Never
use `git checkout <file>` to undo an experiment — copy to the scratchpad and
restore from there.

The one exception, when the project's rules allow it: **if the entire change
touched only documentation (`*.md`, `context/`)**, the test gate may be
skipped; stage only your own paths and verify with `git status --short` that
no code rode along. Any touch of code, migrations, scripts or config puts you
back on full gates.

Keep the commit subject form `<type>(<change-id>): <phase title> (p<N>)`
(`WORKFLOW.md` §9). Never `--no-verify`, never `--amend` (the Progress SHA goes in
with the next commit, `WORKFLOW.md` §6).

##### Verify the manual checks yourself

This is what makes the run autonomous. When a phase ends, do not hand manual
verification back. Work through each `#### Manual` item and drive it:

- **Browser** — automation (e.g. Playwright) against the dev server for
  anything with a UI: render, navigate, fill, click, screenshot, read the
  result. Look at the screenshot; do not assume.
- **The product's own interfaces** — its API, CLI or MCP server read the same
  logic the UI shows; often the fastest oracle for "is the number right".
- **Database** — query it directly; for history or migration correctness,
  compare row counts and values, not the rendered page.
- **HTTP** — `curl` for routes, headers, status codes, redirects, cookie
  attributes.

Tick the box **only on evidence you actually looked at**;
`/softure-implement` is the sole writer of `## Progress`.

What you genuinely cannot verify — visual taste, production DNS, a third-party
dashboard, real email delivery — stays `- [ ]` and goes into a **Pending owner
checks** list in the READY report. It does not block archiving.

##### When the plan and the code disagree

- Plan is right, reality shifted slightly → adapt and continue; note the
  adaptation in the phase commit body.
- A plan step is genuinely unnecessary now → skip it; note why.
- The mismatch invalidates the *remaining* phases → re-plan: back to A3.3 for
  the remaining phases only, keep the landed phases and their SHAs, resume.
- The mismatch invalidates the *whole item* → escalation 2. Report and wait.

#### A3.6 — Implementation review

```
/softure-impl-review <change-id> --auto
```

Full-plan review, not per phase. It writes
`context/changes/<id>/reviews/impl-review.md`.

#### A3.7 — Triage every finding

Same dispositions as A3.4, plus:

- Fixes land as their own commit, `fix(<change-id>): address impl review`,
  after the same full gates.
- A finding that is a **class of mistake** rather than a one-off becomes a
  lesson (A3.9) — and the code is fixed too, unless the lesson is purely about
  process.
- Deferred findings go to the backlog (`WORKFLOW.md` §3), never into thin air.

Re-run `/softure-impl-review` after fixes if any finding was CRITICAL. Leave
the review file with every finding decided.

#### A3.8 — Full integration suite

**`integration.cadence: "roadmap"`** → skip this step: no stage `integration`,
no run — a "finish" item (the roadmap's last, cross-item one) included: the
coordinator's M7 run, or the release when it covers the roadmap, is the
measurement. READY says `integration: deferred to the roadmap run (cadence:
roadmap)`. The touched files' own integration tests still run if the project
can run them cheaply; their result goes into READY as `own tests:`.

Otherwise: after the impl-review fixes are committed and before archiving — the tree the
item delivers is final except for paperwork. Stage `integration` on `<main>`,
then:

```bash
cd <WT> && bash <S>/wt-integration.sh <change-id>     # [--wait MIN], default 30
```

It runs `integration.remote` (a project command that runs the suite on CI for
the committed HEAD and waits) or else `integration.local`, for the
**committed** HEAD — uncommitted files do not ride along (it warns; commit
first). Output lines and exit codes:

| exit | meaning | do |
| --- | --- | --- |
| `0` | green (flaky tests that passed on retry are listed as `flaky:`) | on to A3.9. A flaky test in a file your change touched is yours: remove the cause, don't raise retries |
| `1` | red — or the run could not start | **`new-red:` lines are yours** (reds absent from `<main>`'s latest result). Fix them before READY (see it red first — the run itself is the red), commit `fix(<change-id>): integration — <what>` after full gates, run A3.8 again with the same name. **Reds already on `<main>`** (`red:` but not `new-red:`) are not the item's to fix: report them in READY; the coordinator queues them as their own row. When the command cannot tell new from old, treat every red as yours unless you show it red on `<main>` (scratchpad worktree detached at `origin/<main>`, the same script with name `<change-id>-baseline`) |
| `75` | no result in time | nothing is lost — the run continues. Follow the printed link, wait for it to finish, read its result. Running A3.8 again starts a **new** run — do that only when the run itself failed to start or died (`--fresh`). Never report READY without a result |
| `78` | integration not configured | READY says `integration: not configured`; suggest configuring it in the report |

With `integration.lookup` configured, a green result already stored for the
same HEAD is reused (`stored green result reused`): the same commit is the
same code, so it is never tested twice.

**Only documentation in the whole change** (the docs-only case, no test gate
either) → no integration run; READY says `integration: n/a — documentation
only`.

#### A3.9 — Capture the lesson

If this change taught something that generalizes — a trap in the stack, a
wrong assumption the tests did not catch, a pattern worth repeating:

```
/softure-lesson "<one-line rule>" --auto
```

Fill its fields from the run, in the worktree's `lessons.md`. **The number
comes from `wt-status.sh`** (next free across all worktrees), not `<main>`'s
max + 1 — tell the skill which number to use, or renumber its entry right
after it writes.

Do not manufacture a lesson every change. A lessons file padded with the
unremarkable is a file nobody reads. Roughly: if you would not want to be told
this at the start of the next change, do not write it.

#### Deploy-bound work

Code that needs a release, a new production secret or a production check ends
as **`done_code (<date>; waiting: <what>)`** — on `<main>`, waiting for the
owner's release. Put the owner's steps in the roadmap section
`## Before the next release` (create it above `## Owner decisions and checks`
if missing): a new secret (where it must be set, under which name), a new
build-time value, a migration to watch, a one-off command, a production check
(an exact `curl`). It is the owner's checklist before they publish.

While `release.owner` is true: never create a tag, never publish a release,
never trigger a release workflow, never edit release/deploy workflows or add a
production environment to any workflow without an explicit order from the
owner. This rule may be the only thing between a session and production.

### A4 — Archive on the branch

Stage `archive`, then `/softure-archive <change-id> --auto` — **no push of
`<main>`** (the change branch may go to origin, `<main>` never). It stamps
`change.md`, moves the folder to `context/archive/<created>-<id>/` and commits
`chore(archive): close <change-id>`. Commit uncommitted files of the change
folder first (they are yours). Then, on the branch:

- The roadmap row (table **and** item block) must read `done` — or
  `done_code (<date>; waiting: <what waits for the release>)` when the change
  awaits a deploy. Pure document changes stay `done`. Add the `## Done` line
  (`WORKFLOW.md` §5) if the archive step did not.
- Re-point links: documents that referenced `context/changes/<id>/` must now
  point to `context/archive/<date>-<id>/` (`grep -rn "changes/<id>"`).
- Commit on the branch.

### A5 — Sync with `<main>` and prove it

`<main>` moved while you worked. It always does.

```bash
cd <WT> && git merge <main>      # merge, NOT rebase: ## Progress holds the branch's SHAs
```

Conflict rules, applied the same way in every run so the owner never has to
check them:

| File | Resolution |
| --- | --- |
| `roadmap.md`, your row and block | **branch** (`done` / `done_code`) |
| `roadmap.md`, every other row and section | **`<main>`** |
| `lessons.md` | `<main>`'s entries first, yours after, **renumbered** to the next free number (`wt-status.sh`). Update every reference to your old numbers (plan, reviews, archive docs, code comments): `grep -rn "L-<old>"`. |
| migration number collision (`migrations.dir`) | `<main>`'s migration keeps its number. Save your migration body (it may hold hand edits). Remove your migration and whatever metadata the generator keeps for it, take `<main>`'s metadata, run `migrations.regenerate`, then diff the new file against the saved body and restore any hand edits. Update prose that names the number. |
| `change.md` / archive docs of other changes | union: keep `<main>`'s links and add yours |
| code | resolve on the merits; this is the only row that needs thought |

Then commit the merge. **No full gates after a back-merge.** The pre-commit
hook is enough; don't run the test gate or integration on the merged tree, and
don't repeat A3.8 — the item's integration run was on the pre-merge branch,
and that is the one READY reports. Full gates run twice anyway: in the
worktree before the back-merge, and the classic way on `<main>` after Phase B
(the pre-push hook or the owner's own run); the full suite runs again on
`<main>` after the roadmap and on every release. A third run in between buys
nothing and, with several worktrees live, mostly measures machine load.

What still has to hold: no conflict markers left
(`git grep -nE '^(<<<<<<<|>>>>>>>)'` → nothing) and the hook green. If a
*code* conflict needed resolving on the merits, that part is new code: run the
tests for the files you touched, not the whole suite.

Record the stage on `<main>`:

```bash
python3 <S>/wt-roadmap.py ready <change-id>
```

### READY — report and stop

Write it in the configured `language`, for someone who wasn't there:

```
<ID> `<change-id>` — ready to merge.

Branch <change-id> (worktree ../<repo>-<change-id>), <N> commits, <main> merged in @ <sha>.
Gates on the branch before merging <main>: <each gate> ✓ (tests <count>)
integration: <green|red|n/a|not configured> <passed>/<total> on <sha> — <url>; new reds: <list or "none">
  (reds already on <main>: <list or "none">; flaky: <list or "none">)
After merging <main>: hook ✓ — full gates the classic way on <main>.

What it delivers: <2–4 sentences: the outcome for the user, not a file list>
Conflicts when merging <main>: <file — how resolved>, lessons <L-x…>, migration <number>
Waits for the release: <migration, secret, steps — or "nothing, documentation only">
For your eyes: <Manual items you could not verify yourself>
Decisions worth knowing: <one line each, pointing to the artifact>

On your signal ("merge") I'll merge into <main> and remove the worktree and the branch. No push of <main> and no deploy — the release is yours.
```

Then end the turn. Don't poll, don't schedule wake-ups, and don't ask "shall I
merge?". The report already says what happens next.

## Phase B — merge (only on the owner's signal)

Signals (in any language the owner uses): "merge", "go into main", "main is free",
`/softure-worktree merge`. "Wait", "I'll let you know" mean wait, even if earlier you were told to
merge at the end.

1. **Main tree on `<main>`:** `git branch --show-current` in the main tree
   must print `<main>`. Commands for the branch go through `git -C <WT>`.
2. **Is the branch current?** `git merge-base --is-ancestor <main>
   <change-id>` must succeed. If `<main>` moved again, repeat A5 inside the
   worktree (`git -C <WT> merge <main>`, conflicts, commit with the hook only —
   **no full gates**), then come back. When a dependency branch was used
   (`--base`), check it is already in `<main>` (`git merge-base --is-ancestor
   <base> <main>`). If not, wait for it.
3. **Foreign WIP on `<main>` that the merge would touch:**
   ```bash
   comm -12 <(git diff --name-only HEAD | sort) <(git diff --name-only <main>...<change-id> | sort)
   ```
   - Empty → go.
   - Only `context/foundation/roadmap.md` / `lessons.md` → park it, merge, put
     it back:
     ```bash
     git stash push -- <those paths>
     git merge --no-ff …                     # step 4
     git stash pop                           # both sides append at the end → usually CONFLICTS
     # resolve by keeping both sides (no markers left), then UNSTAGE it:
     git reset -q -- <those paths>           # a conflicted pop leaves them staged/unmerged
     git diff -- <those paths>               # must show ONLY the other session's lines
     git stash drop                          # only after that diff checks out
     ```
     Skip the `git reset` and the other session's WIP stays in the index,
     where the next commit (theirs or yours) picks it up untested. A failed pop
     keeps the stash, so nothing is lost until you drop it.
   - Anything else → another session is editing the same code right now.
     Report the files and wait; don't stash code that isn't yours.
4. **Merge:** `git merge --no-ff <change-id> -m "Merge <change-id> (<ID>):
   <outcome, one line>"`. The pre-commit hook runs. Since step 2 made `<main>`
   an ancestor, `git diff <change-id> <main> --stat` must now be **empty** —
   proof that `<main>` holds exactly the branch's tree. The full gates on that
   tree run the classic way on `<main>` afterwards; say that in the report.
   With `--no-tests`, the owner has also waived that later run; say so.
5. **Cleanup — only your own:**
   ```bash
   git -C <WT> status --short            # must be empty (ignored files are fine)
   git worktree remove <WT>              # --force only if the refusal names nothing but ignored files
   git branch -d <change-id>             # -d, never -D: refuses if not merged, which is the point
   git worktree list                     # yours gone, others untouched
   ```
6. **No push of `<main>`.** Say so in one line and offer it. If the work has
   spanned sessions and `<main>` is the only copy, that is escalation 3: ask.
   If you pushed the change branch earlier, delete it from origin now
   (`git push origin --delete <change-id>`) — it is merged.
7. **Report:** merge SHA, conflicts and how they were resolved, what waits for
   the release (and the roadmap section it is written in), worktree and branch
   removed, `<main>` not pushed.

## Escalations specific to worktrees (in addition to the three above)

- **Another session's uncommitted code overlaps your merge** (B3) → wait and
  report. Never stash, overwrite or commit it.
- **Someone else's worktree or branch looks abandoned** → report it. Never
  remove it. `git worktree remove` and `git branch -d` are only for your own.
- **The pick is only possible by colliding** with a live branch's code → take
  nothing, report the table (A1).

## Invariants

- **One run, one change, one worktree, one branch** — all named
  `<change-id>`. Never pick a second change after READY; the manager does that.
- **`## Progress` in `plan.md` is the only execution state.**
  `/softure-implement` is its only writer; the roadmap stage is a pointer at
  it, never a copy.
- **Every chain skill runs with `--auto`**, and every decision you made instead
  of asking is written down in `research.md`, `frame.md` or `plan.md`.
- **A commit per completed phase, SHA in `## Progress`, full gates first.**
- **See the test fail before you believe the fix**; an arithmetic fix gets an
  oracle of a different kind.
- **`<main>` is written by exactly two things:** `wt-roadmap.py` (one row per
  commit) and the final `--no-ff` merge. Nothing else from this skill lands on
  `<main>`, and nothing lands there before the owner's signal. Refs this skill
  may push: the change branch and whatever the project's integration command
  pushes — nothing else.
- **The roadmap on `<main>` always shows where the change is:** `in_progress`
  from A2 with the current stage, `ready_to_merge` at READY,
  `done` / `done_code` after the merge.
- **Every file edit from A2 to B1 lands under `<WT>`**, never in the main tree.
- **Integration: the full suite, once per item** (cadence `change`; once per
  roadmap at the coordinator's M7 with cadence `roadmap`) — A3.8, after impl-review and
  its fixes, before archive. New reds are fixed before READY; reds already on
  `<main>` are reported.
- **Lesson numbers come from `wt-status.sh`**, never from `<main>` alone.
- **No push of `<main>` before the signal, no tag, no release, no deploy, no
  `--no-verify`, no `git checkout <file>`, no `branch -D`.**
- **After the merge, `<main>`'s tree equals the branch's tree**
  (`git diff <change-id> <main>` empty).
- **Full gates run in the worktree before the back-merge and on `<main>` after
  it, never on the merged tree in between.**
