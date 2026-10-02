# Phase-end commit: the sequence and its edge cases

Every phase ends the same way. The order matters: the SHA can only be written after the commit
exists, and it must never be amended back into that commit (`WORKFLOW.md` §6).

```
verify → manual gate → staging set → dirty-path check → stage by path → message
       → commit → confirm HEAD → write SHA into Progress → bump change.md → reset the set
```

## 1. The touched-file set

Keep a list, in working memory, of every path you create or edit during the phase. It is the
only input to `git add`. `git status` is used to find what is *outside* the set, never to decide
what goes in.

- `plan.md` is always in the set: ticks happen in every phase, and the previous phase's SHA
  edit is waiting in it.
- Phase 1 also takes the change folder's uncommitted artifacts (`change.md`, `research.md`,
  `frame.md`, `plan.md`, `reviews/plan-review.md`), so planning output lands with the first code.
- Files that the phase's own commands regenerate (generated types, a lockfile after an install
  the plan asked for, a migration snapshot) join the set when you see them appear.
- The set is cleared after the commit. The next phase starts with `plan.md` only.

When the project's rules prescribe a different staging policy (for example "commit the whole
tree", or a dedicated worktree where every path is the change's), follow the project. Its rules
outrank this default.

## 2. Manual gate (interactive)

Skip it when the phase has no open Manual item. Otherwise show one message and wait:

```
Phase 2 of 3 is ready to commit: Reminder email 24 hours before a booking

Passed automatically:
- 2.1 reminder job selects bookings starting in 23-25 h (test "selects only the next-day window")
- 2.2 a cancelled booking gets no reminder (test "skips cancelled bookings")
- 2.4 Gates green: typecheck, lint, test (412 tests)

Verified by me:
- 2.5 email renders in light and dark mail themes (screenshots in reviews/p2-email-*.png)

Please check:
- 2.6 the reminder wording reads naturally to a customer (preview: GET /dev/mail/reminder)

Still waiting from earlier phases:
- 1.5 calendar badge colour matches the design file
```

The last block appears only in the **final** phase, and only when earlier phases left Manual
items open. List them as `N.M text`, without the checkbox and without any SHA.

Ask with three options:
- **"Checked, all good"**: tick the items the user confirmed (plain `- [x]`, no "verified by
  agent" note), then commit.
- **"Commit now, check later"**: commit with the items still `- [ ]`. They are carried to the
  owner at archive time and never block the next phase.
- **"Found a problem"**: take the description, fix it inside this phase, re-run the gates and
  the affected criteria, then show the gate again.

Recommend "Checked, all good" when a later phase builds on what the item checks (a layout the
next phase extends, a data shape the next phase reads); otherwise recommend "Commit now, check
later". `--auto`: no gate; open items stay open and go into the final summary.

## 3. Dirty paths outside the set

Run `git status --porcelain` and remove every path in the touched-file set. Whatever is left
is someone else's, or something you forgot.

- Something you forgot (a file you did edit): add it to the set. This is the most common case
  after a long phase; check before blaming anyone else.
- Interactive, otherwise: show the paths and ask "Leave them out" (recommended), "Include them
  in this commit" (the user takes responsibility for the wider scope) or "Stop" (the user tidies
  first, then the sequence restarts here).
- `--auto`: leave out paths that were already dirty when the run started (they were reported
  then); any new unknown path is an escalation, because something wrote where it should not.

Never stash, reset or check out a path that is not yours.

## 4. Stage by path

```bash
git add -- <path> <path> ...
git diff --cached --stat
```

Read the staged stat once. A file you do not recognise in it means the set is wrong; fix the set,
not the stat. `git add -A` and `git add .` are not used unless the project's rules say so.

**A phase with no code diff** (a verification-only phase, or one whose steps were all dropped)
still gets its commit: the staged diff is `plan.md` itself (the ticks, the dropped markers, the
previous phase's SHA). Use type `test` or `chore` and say in the body why there is no code. This
keeps every ticked item carrying a SHA. If even `git diff --cached --quiet` reports nothing
(the ticks were already committed by a previous run), there is nothing to commit: say so and
go to step 8 with the existing phase commit.

## 5. The message

Subject: `<type>(<change-id>): <phase title> (p<N>)`, the phase title as written in plan.md.

| type | when |
|---|---|
| `feat` | new behaviour a user or caller can observe |
| `fix` | corrects behaviour that was wrong |
| `refactor` | structure changes, behaviour does not |
| `test` | only tests, or a verification-only phase |
| `docs` | only documentation or artifacts |
| `chore` | tooling, config, dependencies, prompts |

Body, a few lines:
- what the phase delivers and anything a reviewer would otherwise ask about: adaptations,
  dropped steps, a pre-existing red test you proved and reported;
- the touched paths, grouped when there are many;
- `Refs: <ids>` when the conversation contains issue or task references for this work (a
  tracker key such as `BOOK-214`, a GitHub `#87`, a full issue URL). Copy them exactly, comma
  separated on one line, and repeat them on every commit of the change unless the user tied one to
  a single phase. Never derive a reference from the branch name, the change-id or a file name.
- the trailers the project's rules ask for (co-author, sign-off), and nothing else.

Interactive: show the message and ask "Use as proposed" (recommended), "Edit the subject" or
"Replace it". `--auto`: use it.

Good:

```
feat(booking-reminders): Reminder email 24 hours before a booking (p2)

Adds the hourly reminder job and the reminder template. The plan named
jobs/scheduler.ts; the scheduler moved to jobs/registry.ts in a refactor
after research, so the job is registered there (recorded in plan.md).

Files: jobs/registry.ts, jobs/send-reminders.ts, jobs/send-reminders.test.ts,
mail/templates/reminder.tsx, context/changes/booking-reminders/plan.md
Refs: BOOK-214
```

Bad, and why:
- `wip` / `phase 2 done`: no type, no change-id, no phase; nobody can map it back to the plan.
- `feat(booking-reminders): phases 2 and 3 (p2)`: two phases in one commit; one of them cannot
  be reverted alone.
- `feat: add reminder job and fix the timezone bug in invoices`: the second half belongs to
  another change; split it out or leave it.
- `docs(booking-reminders): progress p2` on a commit that also carries code: the bookkeeping
  subject is only for a commit that carries nothing but Progress and status edits.

## 6. Commit, and what to do when a hook refuses

```bash
git commit -F - <<'EOF'
feat(booking-reminders): Reminder email 24 hours before a booking (p2)

...
EOF
```

Never `--no-verify`, never `--amend`, never a flag that skips signing.

When a hook fails, **the commit did not happen**. HEAD is still the previous phase's commit,
so `--amend` now would rewrite that phase. Instead:
- read the hook output and fix the cause in the change's own files;
- a formatter hook that rewrote files: re-add those files (they are already in the set);
- re-run the gates the fix could affect, then create the commit again, as a new commit;
- the cause lies outside the change (someone else's work in progress breaks a tree-wide
  typecheck): use the bypass the project's rules document for that situation, if any, and say so
  in the body; otherwise ask the user (interactive) or escalate (`--auto`).

## 7. Confirm HEAD before trusting the SHA

```bash
git log -1 --format='%h %s'
```

The subject must be the one you just proposed. If it is the previous phase's subject, the commit
silently failed: go back to step 6. Only then take `%h` as the phase SHA.

## 8. Write the SHA into Progress

For every item ticked in this phase that has no suffix yet:

```
- [x] 2.1 reminder job selects bookings starting in 23-25 h
→ - [x] 2.1 reminder job selects bookings starting in 23-25 h — 7c41e0b
- [x] 2.5 email renders in light and dark mail themes (verified by agent: screenshots in reviews/)
→ - [x] 2.5 email renders in light and dark mail themes — 7c41e0b (verified by agent: screenshots in reviews/)
```

Skip items that already carry a SHA; a re-entered sequence must not append twice. Dropped items
(`~~…~~ — dropped: …`) take no SHA. This edit stays uncommitted on purpose: it rides with the
next commit of the change. When nothing follows (last phase, or the branch is about to be pushed),
commit plan.md and change.md as `docs(<change-id>): progress p<N>`, and never record that commit's
own SHA.

## 9. Bump change.md, reset

Set `updated: <today>` (status stays `implementing` until the finish step). Clear the
touched-file set.

## Resuming

At the start of every run, read Progress and `git log --format='%h %s' <mainBranch>..HEAD`
before writing anything. Match what you find:

| What you find | What happened | What to do |
|---|---|---|
| Items of phase N ticked with a SHA, plan.md edit uncommitted | normal end of a phase | continue; the edit rides with the next commit |
| Items of phase N ticked without a SHA, and a commit `(pN)` exists | committed, then the run stopped before step 8 | write that commit's SHA (from the log, not HEAD, if later commits exist), then continue |
| Items of phase N ticked without a SHA, no `(pN)` commit, code changes in the tree | work done, never committed | re-run the gates and re-check the ticked items (they were never proven at a commit), then run the sequence from step 2 |
| Items ticked without a SHA, no commit, no code changes | ticks without work | re-check each one; untick what is not true and implement it |
| Some items of phase N carry a SHA, others do not, all in one commit | the write-back was interrupted | append the same SHA to the rest |
| Earlier phases fully ticked with SHAs | done | trust them; re-verify only if the gates are red at the start |

When a row does not fit any line, describe what you see and ask (interactive) or escalate
(`--auto`). Never guess a SHA.
