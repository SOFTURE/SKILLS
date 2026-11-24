# Routines

Scheduled sessions that keep an adopting project healthy without the owner: one file per routine, written as
instructions for the session that runs it. The project's scheduled task holds only a short pointer prompt (below);
the steps live here and ship with `@softure-ai/skills`, so a routine improves with every bump of the package and is
never re-created to pick up a fix.

| Routine | File | Schedule | What it does |
| --- | --- | --- | --- |
| Package updates | [package-updates.md](package-updates.md) | nightly, 03:00 in the project's `timezone` | bumps every `@softure-ai/*` package and SOFTURE pin to the newest, `@softure-ai/skills` included, through one pull request merged on green; never releases or deploys |
| Roadmap heartbeat | [roadmap-heartbeat.md](roadmap-heartbeat.md) | `autonomy.reports.every` (hourly by default), only while an autonomous run works | reads the repository and the forge, sends the coordinator the facts for the roadmap report (in issue mode: new open issues too) and ends; changes nothing, never releases or deploys |
| Owner-word wake | [owner-word-wake.md](owner-word-wake.md) | GitHub trigger on issues (opened, labeled), once per repository | picks up an open `owner-word` issue whose author can write to the repository the moment it lands, also in an idle project: hands it to the coordinator or carries the decision out itself; never releases or deploys |

## The standard every routine follows

Learned from routines that ran for weeks in several adopting projects:

1. **A fresh session on every fire** (`create_new_session_on_fire`). A routine bound to one persistent session reads
   the whole conversation again on every fire: after a month that was 150k to 240k tokens per run and several times
   the cost of the same work in a fresh session. It also carries stale beliefs: a persistent package-update session
   that once heard "the server is ready" released and deployed every nightly bump from then on. A fresh session
   knows only the repository, which is the point: everything a routine needs lives there. A routine is never bound
   to the coordinator's session either: an hourly heartbeat bound there cost about 145k tokens per fire.
2. **Never release, tag, publish or deploy from a routine**, without conditions. A dependency bump rides the next
   release the owner orders. A rule like "until the owner says the server is ready" stops being true one day and the
   routine starts deploying unattended, database migrations included.
3. **State lives in the repository, not in memory.** What a routine must remember between nights goes into the
   repository (for package updates: `context/workflow.json` → `routines.packageUpdates.hold` and `ownerSteps`), so a fresh session
   finds it.
4. **One pull request at most per run**, continued by the next run if it is still open; merged on green through the
   project's merge path, never pushed to the main branch.
5. **Every run reports**, also a quiet one, in the project's `chatLanguage`, as its last message; no artifacts and no
   dashboards. A hosted project's coordinator gets the same report and posts one line in the main chat.
6. **One routine per purpose per project.** Before creating one, list the project's scheduled tasks; an older
   routine for the same purpose is reported to the owner, who deletes it. A routine never disables, edits or deletes
   itself.
7. **The schedule is the project's `timezone`** (`context/workflow.json`). Package updates run at 03:00; several
   projects firing at the same minute is fine.

## Setting one up

The roadmap heartbeat is created by the coordinator when an autonomous run starts and deleted when it ends; its file
has its own setup brief. The owner-word wake is set up once per repository with a GitHub trigger, and the project
declares it in `context/workflow.json` → `autonomy.ownerWordWake`; its file has its own setup brief. That trigger can
be added only in the routines web UI (claude.ai/code/routines) or with a tool that explicitly supports GitHub event
triggers: a task created with a cron-or-one-shot tool has no trigger and never fires, so the project declares
`"routine"` only once the task shows the trigger (or the owner confirmed it) and `"none"` until then. To test it, open
one `owner-word` issue and check that the routine's run shows up in the task's runs and its claim comment lands on the
issue; no run means no working trigger (`owner-word-wake.md` → Testing it). The
package-update routine is set up once per project:

Paste this into the project's main chat (or any session of the project that can create scheduled tasks). Replace
`<owner>/<repo>` with the repository:

```text
Set up the SOFTURE package-update routine for <owner>/<repo>, as node_modules/@softure-ai/skills/routines/README.md
describes (read it first; from SOFTURE/SKILLS on GitHub if node_modules is missing):
1. List this account's scheduled tasks. If one already updates packages for this repository, do not create a second:
   tell me its name and id, and that I should delete it before the new one runs. Do not delete it yourself.
2. Create one scheduled task:
   - name: "<PROJECT> · Package updates" (the repository name in capitals),
   - schedule: 03:00 every day in the project's timezone (context/workflow.json → timezone), e.g.
     `CRON_TZ=Europe/Warsaw 0 3 * * *`,
   - a fresh session on every fire (create_new_session_on_fire: true), never bound to an existing session,
   - this repository attached, nothing else,
   - the prompt below, verbatim, with <owner>/<repo> filled in.
   If this session cannot create scheduled tasks, start one short setup thread that does, have it send the task id
   back, and close the thread.
3. Report the task id, its next run time and the prompt it holds. Do not run it now.

Routine prompt:
---
Package updates for <owner>/<repo>. You run in a fresh session with no memory: everything you need is in the
repository. Fetch the main branch, install the project's dependencies as its AGENTS.md says, then read
node_modules/@softure-ai/skills/routines/package-updates.md and follow it exactly. If that file is missing, read
routines/package-updates.md from SOFTURE/SKILLS at the tag of the installed @softure-ai/skills version, or at the
latest release. Whatever else you read or remember: never release, tag, publish or deploy, and never disable or edit
this scheduled task.
---
```

The prompt stays the same when the routine's steps change: the next run reads the new `package-updates.md` from the
`@softure-ai/skills` version the project has installed, and the routine itself bumps that version.
