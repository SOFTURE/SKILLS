# Report routine: template for coordinators without a scheduling tool

Used when the coordinator cannot create a recurring routine itself (a hosted project's main-chat
session; `rules/AGENTS.md` → Roadmap reports). The coordinator starts one short **setup thread**
with the brief below. Every project gets the same routine, so every project gets the same report.

## Brief for the setup thread

```text
Setup thread: create the roadmap report routine (SOFTURE workflow, autonomous mode).
Coordinator session: <coordinator session id>.
1. Read the cron: `python3 .claude/skills/softure-worktree/scripts/wt_config.py --report-cron`
   (or the same script under node_modules/@softure-ai/skills/skills/), and `timezone` from
   context/workflow.json.
2. Create ONE recurring routine named "Roadmap report <roadmap name>", with that cron in that
   timezone and the routine prompt from softure-worktree-manager/references/report-routine.md,
   "Routine prompt", with the placeholders filled in. Bind it, in this order of preference:
   a) to the coordinator's session (the routine wakes the coordinator);
   b) otherwise to a fresh session per firing.
   Never bind it to this thread: this thread is closed next.
3. Send the routine id and its first fire time to the coordinator's session, then close this
   thread. Write no code, open no pull request.
```

When the id arrives, the coordinator records it and checks that the setup thread is resolved;
if it is still open, the coordinator resolves it itself.

## Routine prompt

Fill in `<roadmap name>`, `<coordinator session id>` and `<owner/repo>`.

```text
Roadmap report for <roadmap name> (SOFTURE workflow, AGENTS.md → Operating mode: autonomous → Roadmap reports).
If several firings queued up while busy, do one.
- Running as the coordinator: post the roadmap report in the main chat in the standard shape
  (title, "X of N on <main>", the four-column table of the items not done yet, Decision, times),
  in chatLanguage, times in timezone. Before posting, run the heartbeat: recompute the startable set
  from roadmap.md on origin/<main> (softure-worktree/scripts/wt-startable.py; never only the
  successors of the last merge) and start a thread for every item that is not done, has no thread
  and has all prerequisites on <main> or none; give the go to every READY thread; nudge every
  thread whose go has produced no merge SHA for 30 minutes and every working thread silent for
  45 minutes or more. Stage "waiting for <IDs>" names the prerequisite IDs not on <main> yet.
  Nothing moved: one line.
- Running in a session of its own: read <owner/repo> on the main branch (context/foundation/roadmap.md,
  open pull requests and their checks; the startable set from wt-startable.py), send the
  coordinator's session <coordinator session id> the facts in one message ("Report due <HH:MM>: X of
  N on <main>; startable: <IDs>; <ID> <stage> (PR #N, checks); ...") and ask it to post the report
  and run its heartbeat. Then end this session. Change nothing in
  the repository.
```

## Removing it

At the end of the run, or on the owner's "stop" or "pause", the coordinator asks a thread (the setup
thread's successor or any running thread) to delete the routine by its id, and clears the id from
memory once the thread confirms. A fresh coordinator finds the id in memory; without one, it asks a
thread to list the account's routines and delete the one named after the roadmap.
