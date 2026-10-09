---
name: softure-worktree-manager
description: >
  Coordinate several /softure-worktree changes at once from one session: read
  the roadmap, pick the ready items that can run side by side without touching
  the same code (worktree.maxParallel by default, more when more are safe),
  queue them in context/changes/, launch each in its own background Claude
  session, watch the roadmap until each reaches ready_to_merge, then merge
  them into the main branch one by one — resolving conflicts and migration
  collisions itself — mark them done, and immediately launch whatever became
  unblocked. Runs until the whole roadmap is realised — only items blocked on
  something outside the repo remain. Resumes by itself: started in a fresh
  session, it reads the roadmap, adopts every change already in flight (merges
  the ready ones, wakes stuck workers, relaunches dead ones) and carries on. No
  tag, no release, no deploy (the owner's); pushes the main branch only when
  the roadmap header orders it, then runs the full integration suite on it.
  Use when the user invokes /softure-worktree-manager, or says "run the
  roadmap in parallel", "coordinate the worktrees", "take over the roadmap",
  "launch the next batch and handle the merges", "take over the merges of these
  sessions", "resume the manager".
argument-hint: "[--max N] [--paste] [--dry-run] [--adopt ID,ID…] [--status-every N] | status"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Agent
  - Skill
  - Monitor
  - SendMessage
  - ListAgents
  - TaskStop
  - CronCreate
  - CronList
  - CronDelete
---

# /softure-worktree-manager — Parallel Changes, One Coordinator

`/softure-worktree` carries **one** change in its own worktree and stops at
READY, waiting for the owner's signal. This skill is the owner's side of that
loop, done by a session: it decides **which** changes may run together, starts
them, waits, and gives the merge signal itself — one change at a time.

**Project configuration** comes from `context/workflow.json` (`WORKFLOW.md`
§2): `<main>` is `mainBranch`, the default batch size is
`worktree.maxParallel`, migration collisions are detected through
`migrations`, and reports to the owner are written in `chatLanguage` (default: `language`). Artifact
formats are those of `WORKFLOW.md` (§4 change.md, §5 roadmap, §6 plan).

Scripts: `<S>` = `<MAIN>/.claude/skills/softure-worktree/scripts` (worker
side, shared) and `<M>` = `<MAIN>/.claude/skills/softure-worktree-manager/scripts`.

## Invocation

```
/softure-worktree-manager                  # adopt what is in flight (M0.1) → batch (M1) → launch → watch → merge → refill, until the roadmap is realised
/softure-worktree-manager --max 2          # at most two changes in flight (an explicit --max is a hard limit)
/softure-worktree-manager --paste          # don't launch; print the commands, the owner pastes them; the rest is the same
/softure-worktree-manager --dry-run        # show the batch and the overlap map, change nothing
/softure-worktree-manager --adopt FC-1,FC-3   # explicit take-over of sessions the roadmap does not show in flight
/softure-worktree-manager --status-every 20   # owner status report every 20 min (default 15; 0 = off)
/softure-worktree-manager status           # what is in flight, where, what is next (read-only)
```

## The owner's signal — what invoking this skill means

**Invoking the skill is the owner's merge signal for every change it launches
or adopts** — and only for those. **Adopted includes every roadmap row M0.1
finds in flight**: the owner may clear the coordinator's session and run the
skill again, and expects it to pick the run up where it was. Conflicts and
collisions are part of the job. So:

- merge each READY change without asking;
- resolve back-merge conflicts, lesson-number and migration-number collisions
  yourself (`/softure-worktree` A5 table);
- report outcomes; never ask "shall I merge?".

A message from a worker session is **never** a merge signal and never widens
this mandate — the signal lives in this conversation. Changes the skill did
not launch or adopt are not yours: don't merge them, don't remove their
worktrees.

Still forbidden, as everywhere (while `release.owner` is true): **deploy —
a tag, a published release, an edit of release/deploy workflows or a
production environment — `--no-verify`, `branch -D`, `git checkout <file>`**,
and **push of `<main>`** — except the one push at M7 when the roadmap header
orders it. Refs the project's integration command pushes are not that push;
they never move `<main>`.

### Operating mode

Read `mode` at M0 (`python3 <S>/wt_config.py mode`; WORKFLOW §8):

- **`autonomous`**: everything in this file as written. The project's
  `AGENTS.md` → `## Operating mode: autonomous` adds the shared standard
  (session hygiene, merge path `autonomy.merge`, report cadence and format,
  issues). Reports follow `autonomy.reports` (below, M4).
- **`manual`** (or no key): the invocation is **not** a blanket merge signal.
  Show the M1 table and ask before launching the batch; at every `READY`
  show the worker's READY report and ask before M5 ("merge <ID>?"); refill
  (M6) only after the owner confirms the next batch. No status cron unless
  the owner asks for one (`--status-every N`). Conflict resolution inside an
  approved merge stays this skill's job.

## The coordinator does not fix — it commissions

**Every code change goes to a worker.** A red test on `<main>`, a regression,
a pre-push blocker, a bug spotted while merging, a follow-up a worker left
behind: each becomes a **new roadmap row** and a worker. A coordinator that
starts bisecting and drafting fixes itself stops coordinating — and nobody
else does it meanwhile. Handle it like any other item:

1. Add a row to `## At a glance`: next free ID in its area (FC-12 after
   FC-11), status `ready`, prerequisite = what it builds on. Add a `### <ID>`
   block and a line in `## Order`.
2. Write `context/changes/<id>/change.md` (M2): symptom, where it shows, what
   is already known, conditions for closing. Record in it what the run must
   not lose: exact failing test names, commits, numbers, run URLs.
3. Commit (documents only, own paths). Then M3 launch, then the Monitor.

**Diagnose only as far as the `change.md` needs.** Read the failure output,
the handoff note, the trace a worker already left. **No bisection, no
experiments, no draft fixes of your own** — that is the worker's research, in
its own worktree under its own `/softure-research`.

What the coordinator does with its own hands:

- roadmap and `context/changes/` documents;
- merges, including conflict resolution inside M5 (that part is its mandate);
- cleanup (M0.2, M5);
- the push at M7 and the full integration run on `<main>`.

Nothing else.

## Loop

```
M0 preflight → M0.1 adopt in-flight → M0.2 leftovers → M1 pick batch → M2 queue in changes/ → M3 launch → M4 watch ─┬→ M5 merge one → M6 refill ─┐
                                                                                                    └──────────── (next event) ←─┘
                                                              nothing ready & nothing running → M7 report (+ push if the header orders it)
```

### M0 — Preflight (main tree, `<main>`)

```bash
python3 <S>/wt_config.py --json                # main branch, maxParallel, migrations, language
git branch --show-current                      # <main>
git status --short                             # record foreign WIP; never touch it
bash <S>/wt-status.sh --files                  # live worktrees, their files, free lesson/migration numbers
claude agents --json                           # background + interactive sessions
```

Plus `ListAgents` for peer sessions — its header names **this** session;
remember it, M0.1 compares against it. Read `context/foundation/roadmap.md`:
the header note (run-wide orders from the owner such as parallelism or the
final push), `## At a glance`, `## Order`, each candidate's `### <ID>` block.

### M0.1 — Resume what is already in flight (every run, before M1)

A run is often not the first one: the owner clears the coordinator's session
(or it dies — power cut, usage limit) and invokes the skill again, while the
workers keep running as background processes. The fresh session must pick the
run up **without being told what is in flight** — the roadmap on `<main>`
says it. So, before picking anything new:

```bash
bash <M>/wm-resume.sh
# RESUME <ID> <change-id> action=… stage="…" wt=… branch=… session=… proc=… coord=… coord_alive=… last="…"
```

One line per roadmap row in flight (`in_progress` or `ready_to_merge`).
**Every such row is adopted** — this session merges it and cleans it up,
exactly like one it launched. Act on each line:

| action | what it means | do |
| --- | --- | --- |
| `MERGE` | the row says `ready_to_merge` | M5 now, one at a time (after the whole table is handled) |
| `ADOPT` | worker process alive and working | nothing to wake — add it to the Monitor. When `coord` is not this session, also `SendMessage <change-id>`: "the coordinator is now <this session> — I do the merge; send questions here; keep working, no reply needed" |
| `NUDGE` | worker alive but its last message is a usage limit, a machine sleep or an API/network error | usage limit with a reset time still ahead → wait for it (one-shot `CronCreate` at that time); otherwise `SendMessage` "you were interrupted by <cause> — continue from <last commit/step>". If the send fails ("not reachable"), treat as `RELAUNCH` |
| `RELAUNCH` | no live worker process; worktree and branch still there | `claude stop <session>` (clears the dead entry — `wm-launch.sh` refuses a name whose state is not `done`), then `wm-launch.sh <ID> <change-id> <this session>`; the worker resumes from its branch (`/softure-worktree` A0, resume ladder). Check `git -C <WT> status` first — uncommitted files stay, the worker picks them up |
| `FIX-ROW` | `<main>` already has the merge commit, the row was never flipped | set the row (table and block) to `done` / `done_code` from the archived `change.md` and commit (documents only); remove a leftover worktree/branch if the merge is on `<main>` (`git branch -d` refuses otherwise — good) |
| `REPORT` | row in flight, no branch and no worktree | tell the owner; don't guess — the change may live on another machine or in a cloud session |

`coord` is the coordinator named in the worker's launch prompt (`wm-launch.sh`
writes it there as `coordinator-session <name>`); `coord_alive` says whether
that session still runs.

- `coord` is **this session** (same name after `/clear` — the process stays)
  or `coord_alive=no` → adopt as the table says.
- `coord` is **another live session** → a second coordinator would merge the
  same branches twice. Send it a take-over notice first: `SendMessage <coord>`
  "I am taking over roadmap coordination (/softure-worktree-manager) — delete
  your status cron (CronDelete) and stop your wm-watch Monitor (TaskStop), do
  not merge; confirm in one sentence". Adopt after it confirms or goes idle
  without objecting; if it answers that it is mid-merge, wait for that merge,
  then adopt. The owner's invocation here is the signal — the old session
  gives way (M4, event "take-over notice").

Then report the resume table to the owner in one block (ID, stage, action
taken), arm the Monitor over **all** adopted IDs plus whatever M3 launches
(M4), arm the status cron (M4 — `CronList` first, a cleared session has none),
and continue with M1 for the free slots.

### M0.2 — Leftovers: every worktree, branch and session maps to a row in flight

Run on every run, after M0.1, and report it in the resume table:

```bash
git worktree list
for b in $(git branch --format='%(refname:short)' | grep -vx "<main>"); do
  echo "$b ahead=$(git rev-list --count <main>..$b) merged=$(git merge-base --is-ancestor $b <main> && echo yes || echo no)"
done
claude agents --json          # background sessions are named after their change-id
```

For anything that maps to no row in flight:

| leftover | do |
| --- | --- |
| branch already merged into `<main>` (`merged=yes`, `ahead=0`), with or without a worktree | remove the worktree, `git branch -d` (refuses if not merged — good) |
| background session of a change already `done` / `done_code` / archived | `claude stop <short-id>` |
| the coordinator's own helper worktree (shouldn't exist — see "does not fix") | remove it |
| unmerged branch with no row in any roadmap | report it and leave it alone; it may be someone's work |

Cleaning up after a change that is already on `<main>` loses nothing, so it
needs no adoption. Anything unmerged still does.

### M1 — Pick the batch

**Eligible** (as `/softure-worktree` A1): `Status` is `ready`, `Mode` is
`autonomous`; not in flight; every prerequisite is `done` or `done_code` **on
`<main>`**. `proposed` whenever no `ready` item can take a free slot right now
(all waiting on prerequisites or colliding) — a slot doesn't sit idle; `ready`
items still come first. `blocked` and `Mode: owner` never.

**A prerequisite in flight means wait for its merge — then launch at once.**
Don't start the next item early on the prerequisite's branch (`--base`), even
when it is already at `impl-review`: an early start builds on code that may
still change. M5 → M6 run back to back, so the refill happens right after the
merge's cleanup, in the same turn.

**Parallel-safe** — this is the part the skill adds. For each eligible item,
build its **code surface** before choosing:

1. files named in its roadmap block and in `context/changes/<id>/` (or the
   backlog entry);
2. `grep -rl` for the symbols and constants those name — the importers the
   change will likely edit, not every reader;
3. whether it will need a **migration** (schema column, new table).

Then choose greedily in `## Order`, up to `--max` (default
`worktree.maxParallel`, soft — see below), keeping the batch **pairwise
disjoint in code files** and with **at most one migration**. Shared documents
(`roadmap.md`, `lessons.md`, `prd.md`) don't count — A5 resolves them
mechanically.

**Hot files.** Every codebase has a few files that most changes touch (a
central page, a large form component, the API or tool catalogue, the main
dashboard). Find them once per run (`git log --since=60.days --name-only
--format= | sort | uniq -c | sort -rn | head -20`, plus what `## Order` says)
and allow at most one change per batch on each. Assume an item that adds a
field to the core model also touches the layers that expose and display it,
unless its block says otherwise.

Semantic dependency counts as overlap too: an item whose **content** depends
on another's result waits even without a shared file.

Print the table — item, surface, migration?, verdict (`in batch` / `waits for
<ID>` / `collides with <ID>: <file>`) — so the owner can see why the batch is
what it is. `--dry-run` stops here.

Fewer parallel-safe items than slots is a normal result. Launch what is safe;
don't fill slots with a colliding item.

**The default batch size is soft, not a ceiling.** More parallel-safe items
than `maxParallel` → launch all of them (one at a time, as M3 says). An
explicit `--max N` from the owner is a hard limit, and so is a number in the
roadmap header. **Scale back when sessions starve each other.** Check before
every launch above the default, and in each status report while more than the
default are in flight. Act on a sustained trend or its effects, not one
reading:

| signal | how to read it |
| --- | --- |
| load average | `uptime` — the 5-minute value keeps staying above ~2× cores (`getconf _NPROCESSORS_ONLN`, or `nproc` / `sysctl -n hw.ncpu`) |
| memory | Linux: `free -m` (available below ~20%, swap growing); macOS: `memory_pressure \| tail -1` or `vm_stat` pageouts growing |
| in the workers | the test gate much slower than usual; timing-sensitive tests red that are green alone; workers reporting timeouts |

**Scaling back means not refilling freed slots** until the signals drop.
Workers already running are not stopped — each one carries its own branch.
Record it in the status report: "slot held — <signal>".

### M2 — Queue in `context/changes/`

**What is being realised sits in `changes/`; a topic lives in one place.** For
each picked item without a folder:

- a backlog entry exists → `git mv` it into `context/changes/<id>/` (as
  `backlog-input.md` when it is not already a `change.md`), remove the empty
  directory, fix its relative links;
- write `context/changes/<id>/change.md` (`WORKFLOW.md` §4, `status: new`,
  `roadmap_item: <ID>`) with the item's roadmap block quoted under
  `## Context`;
- point the roadmap item block at the new folder.

Commit on `<main>`, **own paths only** (`git add context/changes
context/backlog context/foundation/roadmap.md`) — documents only, no test gate
when the project's rules allow it. The roadmap status stays `ready`;
`/softure-worktree` flips it to `in_progress` itself.

### M3 — Launch

Default — a background session:

```bash
bash <M>/wm-launch.sh <ID> <change-id> <this-session-name>
# → SESSION <change-id> <short-id> <session-uuid>
```

The script runs `claude --bg -n <change-id> "/softure-worktree <ID> …"` from
the main tree (the prompt tells the worker: stop at READY, don't merge, send
unanswerable questions to the coordinator) and reads the session id back from
`claude agents --json`. Background sessions also show up in IDE session
panels; some IDE extensions cannot reattach them as a tab and show an exit
error — harmless, the worker keeps running. Live view: `claude attach
<short-id>` in a terminal.

Launch **one at a time**, a few seconds apart: every worker starts with
`wt-roadmap.py open`, which commits to `<main>`; simultaneous commits race.

`--paste` — print one fenced `/softure-worktree <ID>` block per item for the
owner to paste into separate windows, then `SendMessage` each new peer (find it
with `ListAgents` once it appears) the same instruction the script puts in the
prompt.

`--adopt` — for sessions already running that the roadmap does not show in
flight (M0.1 adopts the rest by itself): `SendMessage` each peer that merges
are now done by this session; nothing else changes for them.

Never start a second session for a change that already has one
(`wm-launch.sh` refuses: exit 3).

### M4 — Watch

```
Monitor(
  description: "softure-worktree-manager: <IDs>",
  timeout_ms: 1800000,
  command: "bash <M>/wm-watch.sh FC-1:landing-hero-balance FC-3:pricing-one-section")
```

Events: `STAGE <ID> <status>` on every stage change, `READY <ID>` at
`ready_to_merge`, `SESSION <change-id> <kind>/<status>/<state>` and `GONE
<change-id>` for the worker process. The monitor expires after 30 minutes —
**re-arm it at each expiry** with the IDs still in flight. Don't poll by hand
and don't sleep; events wake the session.

Between events, end the turn with one line (what is in flight, which stage).

**Periodic status for the owner — arm it together with the first Monitor.**
Stage events arrive irregularly, and a worker can sit in one stage for half an
hour. Right after the first launch (M3), `CronList` (reuse an existing status
job), then:

```
CronCreate(
  cron: "4,19,34,49 * * * *",            # every 15 min, off the :00/:30 marks
  recurring: true,
  prompt: "Status for the owner + loop heartbeat (/softure-worktree-manager). If several of these fired while busy, do one. 1) bash <M>/wm-resume.sh + the latest commits of the worker branches. 2) Report as the status table (format under 'The report itself'); nothing moved → one line. 3) Resume the loop by the wm-resume actions (M0.1 table): MERGE → M5 and M6; NUDGE → SendMessage 'continue' (usage limit: after its reset time); RELAUNCH → claude stop + wm-launch.sh; wm-watch Monitor expired → re-arm with the IDs in flight; free slot and a ready item without collision → M1–M3. Work until the roadmap is done / done_code. 4) End → M7 (integration suite on <main>, unless the release covers it; close the roadmap and push <main> only if the roadmap header orders it; tag, release and deploy never — those are the owner's) and CronDelete this job. Write the report in chatLanguage (default: language) and the times in the timezone from context/workflow.json; paste the content into the message, never a file to link.")
```

This prompt is also the run's **heartbeat**: a worker stuck on a usage limit
or a machine that slept emits no stage event, so without it the run stalls
silently.

**Autonomous mode:** the clock follows `autonomy.reports` instead of the
default: every `every` minutes (default 30) at the :00/:30 marks
(`cron: "0,30 * * * *"`), inside `hours` when set; `every: 0` = off. An
explicit `--status-every` still wins.

`--status-every N` changes the period (build the minute list from an
off-mark offset: N=20 → `7,27,47 * * * *`); `--status-every 0` skips it. Arm
it **once** per run — M6 re-arms the Monitor, not the cron. Remember its id:
M7 deletes it. Tell the owner the first fire time, that it waits while a merge
is in progress (cron fires only when the session is idle), and that stage
events and merges are still reported immediately.

The report itself — the same shape every time, on the clock and on request
(`status`): a title, one sentence with the current counter `X of N on <main>`
(what is done), then one table with **every row not done yet** (done rows are
only counted), then `Decision: …` when there is one and one line with the
times:

| ID | What it does | Stage | Link |
| --- | --- | --- | --- |
| **FC-3** | <outcome in a few words> | implement 2/3 | `<change-id>` (`claude attach <short-id>`) |
| **FC-6** | <outcome in a few words> | waiting for FC-4, FC-5 | — |

This is the report standard of every SOFTURE project (`AGENTS.md` → Operating
mode: autonomous → Roadmap reports): the same four columns, headers in
`chatLanguage` (default `language`);
Link is the session that carries the item (here the background session), never
a forge URL. Stage is one of: `waiting for <IDs>` · a chain stage (`research`
… `archive`, `implement N/M`; `stalled` when the session has not moved) ·
`ready to merge` · `blocked (<why>)` · `waits for the owner (<what>)`. The
content goes into the message itself, never into a file to link. Every claim carries its evidence — a merge SHA, a commit, a run URL —
never "done" without one. Times are shown in `workflow.json` → `timezone`
(default: the machine's zone), with the zone named once. Nothing moved since
the last report → one line; don't pad it.

| event | action |
| --- | --- |
| `STAGE` | one line to the owner; nothing else |
| `READY <ID>` | M5 for that item (queue if a merge is running) |
| `SESSION …/done` or `GONE` **without** READY | the worker stopped early. Read `bash <M>/wm-report.sh <change-id>` (its last message) or the stage / `## Progress` in the worktree. An escalation from `/softure-worktree` → handle below. A crash mid-chain → relaunch with `wm-launch.sh` (the worker resumes from its branch). |
| no stage event for a long time, `claude agents --json` shows workers `state: blocked` | most likely the **usage limit**: every worker stops at once with a "session limit · resets <time>" message (read the transcript tail with `wm-report.sh`). Nothing is broken and the branch is intact; after the reset time `SendMessage` each worker "the limit has reset — continue from <last commit/step>" and it resumes in the same session. Don't relaunch — a second session for the same change is refused anyway. If the worker was mid-integration (A3.8), tell it to read the finished run's result before starting a new one. |
| a worker's `SendMessage` question | answer it if the material settles it (code, `lessons.md`, PRD, dev database); otherwise relay to the owner and let the worker continue with other work |
| a worker's signal for **another** change (a file of theirs, a shared contract) | relay it to that worker by `SendMessage` with the contract spelled out (props, labels its tests use); if the other change has not started yet, append it to its `change.md` under `## Notes` instead |
| a **take-over notice** from another session running this skill (M0.1) | the owner started a newer coordinator — give way: `CronDelete` the status job, `TaskStop` the Monitor, finish a merge already under way (never leave `<main>` mid-merge), reply one sentence with what you handed over, then stop coordinating |

### M5 — Merge one (on READY)

Run `/softure-worktree` **Phase B** for that change (`Skill
softure-worktree`, args `merge <change-id>`), from the main tree, with these
points of this skill:

- **Signal:** given (invocation). Don't wait for "merge".
- **One merge at a time.** `<main>` moves with each; the next READY branch is
  then behind — B2 back-merges it inside its worktree (`git -C <WT> merge
  <main>`) with the A5 conflict table, commits with the hook only, and comes
  back. That is this session's job now, not the worker's.
- **Conflicts and collisions — resolve, don't stop:** roadmap row → branch,
  other rows → `<main>`; `lessons.md` → renumber to the next free
  (`wt-status.sh`) and fix references; migration number clash → `<main>`
  keeps its number, regenerate yours (`migrations.regenerate`) and restore
  hand edits (A5); code → on the merits, then run the tests of the touched
  files.
  **Resolve the roadmap row by row, never hunk by hunk.** One conflict hunk
  often spans several adjacent table rows: yours plus a neighbour whose stage
  moved on `<main>` meanwhile. Taking the whole hunk from the branch puts that
  neighbour back to a stale stage. Inside each hunk, pair the lines by row ID:
  take the merged change's row (`| **<ID>** |` and its `### <ID>` block) from
  the branch and every other line from `<main>`. After the commit, compare
  every `in_progress` row's stage with its `### <ID>` block.
- **B3 foreign WIP on `<main>`:** only another session's roadmap/lessons lines
  → park and restore as B3 says; code → wait for that session, report.
- **Cleanup** removes the worktree and the branch of the merged change (the
  skill launched or adopted it — B5's "only your own" means exactly these).
  Then stop the worker: `claude stop <short-id>` for a background session;
  `SendMessage` "merged — you can close" for a pasted/adopted one.
- **Carry every signal into the roadmap — only when there is one.** The READY
  report lives in a worker session that closes after the merge; the release
  and the roadmap's archive happen later, from `<main>`. Whatever the worker
  left for the owner must survive in the roadmap, or it is lost. Sources,
  before the merge:
  1. the READY report — `wm-report.sh <change-id>` (background) or
     `wm-report.sh <sessionId>` (pasted/adopted), or the report the worker sent
     by `SendMessage`;
  2. the branch's `plan.md` → `## Progress`: every `- [ ]` left open (Manual
     items the worker could not verify);
  3. `reviews/impl-review.md`: findings accepted as risk or deferred.

  Sort each signal into one of two roadmap sections:

  | signal | section | entry |
  | --- | --- | --- |
  | a pre-release step: migration to watch, production secret, build-time variable, scheduled job, one-off command, production check | **`## Before the next release`** (the owner's checklist before publishing; create it above `## Owner decisions and checks` if missing) | numbered step with the exact command/file |
  | anything else for the owner: visual/tone check, open question, product decision, suggestion, deferred finding | **`## Owner decisions and checks`** | `- [ ] **<ID>**: <what to decide/check> (<Manual N.M / finding>). <evidence path>` |

  One signal, one place: if a check gates the deploy, it goes to the release
  section and the decisions section only points at it. Don't duplicate what
  the worker already wrote there. **Nothing to report → write nothing** — an
  empty entry is noise in the lists the owner reads before a deploy. Commit
  together with the merge's roadmap fix-up (documents only, own paths).

  **Integration line of the READY report** (with `integration.cadence:
  "roadmap"` it reads `deferred to the roadmap run` — that is expected; the
  run happens once at M7). New reds must be "none" — a worker
  reporting READY with new reds has not finished A3.8; send it back
  (`SendMessage`), don't merge. Reds the worker lists as **already on
  `<main>`** are a signal of their own: unless a roadmap row already carries
  them, queue them as a new row and a worker ("does not fix"), with the test
  names and the run URL in its `change.md`.
- **Roadmap:** after the merge the row must read `done` / `done_code` (the
  branch wrote it at archive). Check it on `<main>`; if it still says
  `ready_to_merge`, fix that row (table and block) alone and commit.
- **Report** per merge, three lines: merge SHA, conflicts and how resolved,
  what waits for the release.

### M6 — Refill

**The run does not stop between items.** Closing one change is never an end
point: pick the next item, queue it, launch it, keep the order of `## Order`,
without asking.

After every merge, run M1 again with the free slots: items whose prerequisites
just landed become eligible now, not after the whole batch. Queue (M2), launch
(M3), add them to the watch (re-arm the Monitor with the new ID list —
`TaskStop` the old one first).

### M7 — Done

**Done means the roadmap is realised:** every item is `done` / `done_code`,
except items `blocked` on something outside the repo or `Mode: owner`. A
`ready` item waiting on a prerequisite in flight is **not** done — keep
watching. A `proposed` item is not done either — it runs under M1's rule. Only
then, with nothing in flight → `TaskStop` the monitor, `CronDelete` the status
job (M4), and report: what merged (SHAs), what waits for the release
(`## Before the next release`), the result of the full integration suite on
`<main>` (below), every open entry in `## Owner decisions and checks` (the
owner answers these before the release and before the roadmap is archived),
what is left and why (`blocked`, `owner`, `proposed`, a collision), and
whether `<main>` was pushed.

**The final push — only when the roadmap header orders it** ("Push main
branch: at the end"). Then, and only then, after the report's facts are
settled: `git push origin <main>` through the pre-push hook — never
`--no-verify`. A red hook stops the push — **and does not end the run**: queue
the failure as a new roadmap row and a worker, keep watching, push after its
merge. No header order → no push of `<main>`; say so.

**Then the full integration suite on `<main>`** — from the main tree on
`<main>`:

```bash
bash <S>/wt-integration.sh <main>     # exit 0 green, 1 red, 75 no result yet, 78 not configured
```

Run it after the push (or, with no push ordered, on the local `<main>`). Its
result is the baseline every next worker's "new reds" are measured against,
and the owner's signal before the release. Put the line into the final report:
`integration <main>: <green|red> <passed>/<total> on <sha> — <url>; reds:
<list or "none">`. Red → **does not end the run** either: each red becomes a
new roadmap row and a worker (test names and the run URL in its `change.md`,
the header note points to the row); after its merge, push (if ordered) and run
this again. `75` → the run is still going; wait for it and read the result,
don't start a new run over a moving one. With `integration.cadence:
"roadmap"` this is the roadmap's only full run, so its reds are measured
against the previous result on `<main>`, not per change.

**One run per commit, not more.** With `integration.lookup` configured, the
script reuses a green result already stored for the same `<main>` commit (for
example a run a worker or the release made on it) instead of starting a new
one — the same commit is the same code. `--fresh` only when a run died or
could not start.

**Covered by the release** — `integration.coveredByRelease: true` **and** the
header orders "Release: at the end" (the owner's approval, quoted): the
release pipeline runs the same full suite on the released commit, so a run
here would test that commit twice. Skip the run and write in the report:
`integration <main>: covered by the release pipeline on <sha>
(coveredByRelease)`. The release itself is still the owner's (or follows the
project's own rules) — this skill never starts it. Its red result is handled
as above: each red becomes a row and a worker. Without that header order, run
the suite here as usual.

**Then close the roadmap — only when the header orders it** ("Archive roadmap:
at the end") and the run above is green (covered by the release → the gate
reads the release's stored green result for the final `<main>` commit,
WORKFLOW §5.2; no result yet → leave the close as the step after the release
and say so): `/softure-roadmap --close --auto`
(WORKFLOW §5.2). A failing gate (a leftover folder in `context/changes/`, a
row not settled) is fixed first — leftovers are archived, unsettled rows go to
a worker — never forced. The close is a documents-only commit on `<main>`; if a
push is ordered, push it too (a second, documents-only push, through the hook). No header order → leave the roadmap in
place and list it in the report as the owner's step.

**Tag, release and deploy never** — the owner publishes the release after
answering `## Owner decisions and checks`.

## status

`wm-resume.sh` (one line per row in flight, with the action a fresh run would
take), `wt-status.sh`, `claude agents --json` → a table: ID, change-id, stage,
session (background id / window), action, next in line. Read-only — `status`
changes nothing.

## Escalations — the only reasons to stop and ask the owner

1. A code conflict whose right resolution changes **what a user sees or is
   told** in a way neither branch's plan decided.
2. A worker needs something only the owner has (a secret, a production step, a
   product rule) and no other ready work remains for the coordinator.
3. `/softure-worktree` escalation 3 (work spans sessions and `<main>` is the
   only copy) — ask about pushing.

Everything else is decided and written into the report.

## Invariants

- **One coordinator per repo.** A newer invocation takes over from an older
  live coordinator by the take-over notice (M0.1) — never two coordinating at
  once.
- **Every run starts with M0.1.** A fresh session adopts every roadmap row in
  flight before it launches anything new; nothing in flight is left without a
  coordinator.
- **Only launched or adopted changes are merged or cleaned up** (adopted =
  M0.1 or `--adopt`). One exception: leftovers of changes already on `<main>`
  (M0.2), because removing them loses nothing.
- **The coordinator writes no code.** Every fix, even a one-line test fix and
  even a pre-push blocker, is a roadmap row and a worker. The coordinator
  commits only roadmap and `changes/` documents, merges, and merge-conflict
  resolutions.
- **Every worktree, branch and background session maps to a row in flight**
  (M0.2). Stale ones get removed, not carried over.
- **Merges are serial; launches are serial; workers run in parallel.**
- **The batch is pairwise disjoint in code files, ≤ 1 migration**, and
  respects content dependencies and hot files.
- **`context/changes/` holds exactly the queued and running changes**; the
  roadmap on `<main>` always shows each one's stage.
- **No signal is lost.** Every open Manual item, question, suggestion or
  pre-release step a worker left stands in one of the two roadmap sections
  before its worktree is removed.
- **The run ends only when the roadmap is realised** (M7) — never after one
  item, never after one batch.
- **The owner hears from the run on a clock** — a status cron is armed while
  anything is in flight (unless `--status-every 0`) and deleted at M7.
- **No tag, no release, no deploy, ever** (while `release.owner` is true).
  **No push of `<main>`** — except the single push at M7 that the roadmap
  header orders; the full integration suite on `<main>` follows it (or the
  release covers it, `integration.coveredByRelease`) and goes into the final
  report.
