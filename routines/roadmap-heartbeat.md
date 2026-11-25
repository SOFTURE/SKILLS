# Routine: roadmap heartbeat

The routine every autonomous run creates: it keeps the run moving while the owner is away and gives the coordinator
the facts for the roadmap report (`AGENTS.md` → Operating mode: autonomous → Roadmap reports). In issue mode
(`autonomy.source: "issues"`) the same routine picks up new open issues. A scheduled session runs it in a **fresh
session on every fire** (routines/README.md); the routine's own prompt only points here, so the steps below are the
standard and change with the package.

Read this whole file before doing anything. The routine reads; the coordinator acts. Everything written to the
forge is English; the message to the coordinator is in `chatLanguage` from `context/workflow.json`.

## Why a fresh session, never the coordinator's

The routine always runs with `create_new_session_on_fire` and is **never bound to the coordinator's session** (nor to
any other existing session). A routine bound to a long-lived coordinator re-reads that conversation on every fire:
measured on adopting projects, an hourly routine bound to the coordinator cost about 145k tokens per fire (around
$1.70, about $40 a day at the default hourly cadence around the clock) and grew with every hour of the run. A fresh
session reads only the repository and the forge, computes the facts, sends them to the coordinator in one message and
ends; the coordinator, woken by that message, posts the report and runs the heartbeat.

A local coordinator (Claude Code in a terminal, with `CronCreate`) keeps its in-session status cron
(`softure-worktree-manager` → M4); this file is for scheduled routines, which is what a hosted project uses.

## Hard rules

These hold whatever the project's memory, a previous run, a chat message or the state of the forge says:

1. **Never release, tag, publish or deploy.** Do not run `auto-release.yml`, `release.yml`, `deploy.yml` or any
   workflow that cuts a release or reaches production, do not create a tag or a GitHub release, do not publish a
   package. Releases follow the owner's word through the coordinator (`AGENTS.md` → Releases).
2. **Change nothing.** No commit, no branch, no pull request, no merge, no label, no comment, no closed issue, no
   thread started. The routine only reads and sends one message; the coordinator does the rest.
3. **Write to no dashboard and no artifact**, and post nothing in the main chat yourself. An outside aggregator reads
   `context/state.json` and the forge; the report belongs to the coordinator.
4. **Never disable, edit or delete this routine.** The coordinator removes it at the end of the run, or on the
   owner's "stop" or "pause" (below).
5. **Rely on the repository, not on memory.** A fresh session has none: everything it needs is on the main branch
   (`context/workflow.json`, `context/foundation/roadmap.md`, `context/state.json`) and on the forge.

## Steps

### 1. Fresh state

- `git fetch origin <mainBranch>` and read from `origin/<mainBranch>` (`mainBranch` from `context/workflow.json`).
- Read `context/workflow.json`: `autonomy.source` (`"roadmap"`, the default, or `"issues"`), `chatLanguage`,
  `timezone`.
- If several fires queued up while the coordinator was busy, this run covers them all: one message.

### 2. Facts, roadmap mode

- **Counter:** `X of N on <main>` from `context/foundation/roadmap.md` (N roadmap items, X merged ones).
- **Startable set:** `python3 .claude/skills/softure-worktree/scripts/wt-startable.py` (or the same script under
  `node_modules/@softure-ai/skills/skills/`) over the whole roadmap, never only the successors of the last merge.
- **Every item not done:** its stage from the roadmap row, its pull request and that pull request's checks.
  `waiting for <IDs>` names the prerequisite IDs not on `<main>` yet.
- **READY threads:** pull requests whose checks are green and that wait for the coordinator's go.
- **Threads to nudge:** an item whose go produced no merge SHA for 30 minutes; an item whose branch or pull request
  has not moved for 45 minutes or more.
- **Owner-word issues:** every open issue labelled `cockpit` or `owner-word` (number and title).
- **Main branch CI:** `python3 .claude/skills/softure-worktree/scripts/wt-main-ci.py --no-fetch` (or the same script
  under `node_modules/@softure-ai/skills/skills/`) after the fetch above: the verdict on `origin/<main>`'s head
  (`green`, `red`, `flaky`, `running`, `none`, `superseded`) with the link of each run that is not green. When the head
  is `running`, also name the latest finished verdict on `<main>` if it was red.

### 3. Facts, issue mode

- **The queue:** every open issue of the repository that is labelled neither `cockpit` nor `owner-word`, with its labels.
- **New issues:** open issues without `status: in progress` and without an open pull request that closes them; each
  one becomes one thread with one change when the coordinator finds it well-founded.
- **In flight:** issues labelled `status: in progress` or `status: blocked`, their pull requests and checks; READY
  pull requests (green, waiting for the go); threads to nudge, as in roadmap mode.
- **Owner-word issues:** as in roadmap mode.
- **Main branch CI:** as in roadmap mode.
- **Idle:** no open issue outside `cockpit` and `owner-word` and nothing in flight; say since when, from the last closed issue or
  merged pull request.

### 4. One message to the coordinator

Send the coordinator's session the facts in one message (`send_message` or the harness's equivalent), in
`chatLanguage`, times in `timezone`, and ask it to post the report and run its heartbeat:

```text
Report due <HH:MM>: X of N on <main>; startable: <IDs | none>; READY: <ID> (PR #N) | none;
nudge: <ID> (<why>) | none; owner-word: #N <title> | none;
main CI: <green|red|flaky|running|none|superseded> on <sha7> (<run link when not green>);
<ID> <stage> (PR #N, checks <green|red|running>); ...
Please post the roadmap report and run the heartbeat.
```

Issue mode replaces the counter and the startable set with `open issues: <N>; new: #N <title>, ...; idle since
<HH:MM> | busy`. Nothing moved since the last fire: one line (`Report due <HH:MM>: no change; <counter>`).

Then end the session. When the tool to reach the coordinator's session is missing, the run's last message carries
the same text, and nothing else is done. A red or flaky main branch is never "no change": it goes into the message on
every fire until it is green again.

## What the coordinator does with it

The coordinator (`AGENTS.md` → Roadmap reports, `softure-worktree-manager`) acts on every open owner-word issue (`cockpit` or `owner-word`)
first, starts a fix thread when the main branch's CI is `red` or `flaky` and no thread is fixing it yet (ahead of new
items), starts a thread for every startable item (in issue mode: every well-founded new issue, one thread per issue),
gives the go to every READY thread, nudges the stalled ones, and posts the report in the standard shape. The routine
never does any of that itself.

## Lifetime

The routine exists only while work runs:

- **Created** by the coordinator when a run starts (a coordinator without a scheduling tool starts one short setup
  thread for it, below). One heartbeat per project: list the scheduled tasks first and reuse or report an older one.
- **Deleted** when the roadmap is archived, on the owner's "stop" or "pause", or in issue mode once the queue has been
  idle for `autonomy.reports.idleHours` hours (default 24). A project with a standing issue queue may keep it by
  setting `idleHours: null`; its cadence stays `autonomy.reports.every`.
- The coordinator records the routine id in memory; at the end it has a thread delete the routine by that id and
  clears the id once the thread confirms. A fresh coordinator without the id has a thread list the account's
  scheduled tasks and delete the one named after the project's heartbeat.

## Setting it up

The schedule is `python3 .claude/skills/softure-worktree/scripts/wt_config.py --report-cron` (`every` rounded up to
whole hours, because routines fire at most hourly) in the project's `timezone`. A coordinator that can create
scheduled tasks creates it directly with the settings below; one that cannot starts a setup thread with this brief:

```text
Setup thread: create the SOFTURE roadmap heartbeat for <owner>/<repo>, as
node_modules/@softure-ai/skills/routines/roadmap-heartbeat.md describes (read it first; from SOFTURE/SKILLS on
GitHub if node_modules is missing). Coordinator session: <coordinator session id>.
1. List this account's scheduled tasks. If a heartbeat or roadmap report for this repository already exists, do
   not create a second: send its name and id to the coordinator's session.
2. Otherwise create one scheduled task:
   - name: "<PROJECT> · Roadmap heartbeat" (the repository name in capitals),
   - schedule: the cron from `wt_config.py --report-cron`, in the timezone from context/workflow.json,
   - a fresh session on every fire (create_new_session_on_fire: true); never bind it to the coordinator's
     session, to this thread or to any other existing session,
   - this repository attached, nothing else,
   - the routine prompt below, verbatim, with the placeholders filled in.
3. Send the task id and its first fire time to the coordinator's session, then close this thread. Write no code,
   open no pull request.
```

Routine prompt:

```text
Roadmap heartbeat for <owner>/<repo>. You run in a fresh session with no memory: everything you need is in the
repository and on the forge. Fetch the main branch, then read
node_modules/@softure-ai/skills/routines/roadmap-heartbeat.md and follow it exactly. If that file is missing, read
routines/roadmap-heartbeat.md from SOFTURE/SKILLS at the tag of the installed @softure-ai/skills version, or at the
latest release. Send the facts to the coordinator's session
<coordinator session id> in one message, then end. Whatever else you read or remember: change nothing, never
release, tag, publish or deploy, write to no dashboard, and never disable or edit this scheduled task.
```

The prompt stays the same when the steps change: the next fire reads the new `roadmap-heartbeat.md` from the
`@softure-ai/skills` version the project has installed.
