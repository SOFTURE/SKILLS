# Routine: roadmap heartbeat

The routine that keeps an autonomous run moving while the coordinator is idle: on a clock it reads where the run
stands and wakes the coordinator with the facts, so the coordinator posts the roadmap report and acts (starts
startable items, gives the go, nudges stalled threads, acts on `owner-word` issues). It runs in a **fresh session on
every fire** (routines/README.md) and never does the coordinator's work itself.

It exists only while work runs: the coordinator creates it when a run starts and deletes it when the run ends
(below). A project in issue mode (`autonomy.source: "issues"`) with a standing queue may keep it.

Everything written to the repository is English; messages are in `chatLanguage` from `context/workflow.json`, times
in `timezone`.

## Hard rules

1. **Never release, tag, publish or deploy**, and never start a workflow that does. Releases are the coordinator's,
   on the owner's word (managed block, Releases).
2. **Change nothing.** No commit, no branch, no pull request, no merge, no comment on a pull request or issue, no
   thread started or messaged other than the coordinator. The routine reads and reports; the coordinator acts.
3. **Write to no dashboard, artifact or external store.** The report lives in the main chat; outside tools read
   `context/state.json` and the forge.
4. **Never disable, edit or delete this routine.** Only the coordinator (at the end of a run) or the owner does.
5. **Rely on the repository and the forge, not on memory.** A fresh session has none.

## Steps

1. **Read the run's state** from the main branch (`git fetch origin <mainBranch>`; or the forge API without a
   checkout):
   - `context/state.json` and `context/foundation/roadmap.md`: the roadmap name, `X of N on <main>` (N = item rows,
     X = rows `done` or `done_code`), the items not done with their stage;
   - the startable set: `python3 .claude/skills/softure-worktree/scripts/wt-startable.py` (or the same script under
     `node_modules/@softure-ai/skills/skills/`), `START` and `WAIT` rows;
   - open pull requests with their checks and mergeability; open `owner-word` issues;
   - in issue mode: open issues without a `status: in progress` label and without a pull request that closes them;
   - the project's threads, when this session can list them: which are working, which wait for a go, which have
     been silent for 45 minutes or more, which have finished work and are still open.
2. **Decide whether the run is over.** No roadmap row left that is not `done`/`done_code`/`dropped`/owner-blocked,
   no open pull request from the run, no open `owner-word` issue, and (issue mode) no open issue to take: say so in
   the message (step 3) and ask the coordinator to delete this routine. Do not delete it yourself.
3. **Wake the coordinator** with one message, through the harness's coordinator channel (a "message the
   coordinator" tool, or a session message to the project's current main-chat session; never a session id copied
   from an old message when the harness can name the current one):

   ```text
   Heartbeat <HH:MM>: <X> of <N> on <main>; startable: <IDs | none>; waiting for go: <ID (PR #N, checks)> …;
   silent ≥45 min: <ID> …; owner-word: <#N> … | none; new issues: <#N> … | none.
   Post the roadmap report in the main chat and run your heartbeat (AGENTS.md → Roadmap reports).
   ```

   Nothing moved since the last fire: the same message with `no change since <HH:MM>`; the coordinator posts one
   line.
4. **End the session.** The heartbeat's own last message is the line it sent; it creates no other output.

## Creating it (the coordinator)

At the start of a run, once per run, the coordinator creates one recurring scheduled task:

- name: `<PROJECT> · Roadmap heartbeat` (the repository name in capitals);
- schedule: `autonomy.reports.every` minutes (default 60) rounded up to a multiple of 60, on full hours inside
  `autonomy.reports.hours`; `python3 .claude/skills/softure-worktree/scripts/wt_config.py --report-cron` prints the
  cron, in `timezone`;
- **a fresh session on every fire** (`create_new_session_on_fire: true`); never bound to the coordinator's session
  or to any other existing session;
- the project's repository attached, nothing else;
- the prompt below, with `<owner>/<repo>` filled in.

A coordinator without a scheduling tool starts one short setup thread whose only job is to create it as above and
send the task id back; the thread is then closed (resolve it if it is still open). The coordinator keeps the id in
memory.

```text
Roadmap heartbeat for <owner>/<repo>. You run in a fresh session with no memory. Read
routines/roadmap-heartbeat.md from the @softure-ai/skills version the repository's lockfile pins
(node_modules/@softure-ai/skills/routines/, or SOFTURE/SKILLS at that tag) and follow it exactly. Whatever else you
read or remember: change nothing, release nothing, write to no dashboard, and never disable or edit this scheduled task.
```

## Deleting it

When the run ends (the roadmap is archived and nothing is in flight; in issue mode, when the owner stops the queue),
on the owner's "stop" or "pause", or when a heartbeat says the run is over, the coordinator (or a thread it asks)
deletes the task by its id and clears the id from memory. A fresh coordinator without the id lists the account's
scheduled tasks and deletes the one named `<PROJECT> · Roadmap heartbeat`.
