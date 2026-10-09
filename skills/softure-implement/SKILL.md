---
name: softure-implement
description: >
  Execute a reviewed plan phase by phase: write the code and tests for one phase, run the
  project gates, verify the criteria for real (manual ones too, where a machine can), pause
  for the user's manual checks, tick ## Progress and commit once per phase with the SHA
  recorded safely. Resumes from the first open item, including after a half-finished commit.
  Use after softure-plan-review. Triggers: "implement phase N", "continue implementation",
  "/softure-implement", "execute the plan", "next phase".
argument-hint: "<change-id> [phase N | next] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Agent
  - AskUserQuestion
---

# softure-implement: execute the plan, prove every box

Implementation follows the plan. It does not redesign it. Each phase ends in a single commit
whose ticked boxes are **true**: they were checked, not assumed. `## Progress` in `plan.md` is
the only state, so anyone can stop and anyone can resume.

Contract: `WORKFLOW.md` §4 (status), §6 (Progress and the SHA rule), §8 (`--auto`), §9 (commits).

Read when needed:
- `references/phase-commit.md`: the phase-end commit sequence step by step, with the edge cases
  (hook failure, no diff, unrelated dirty paths, issue references, resuming a half-done commit)
  and good and bad commit messages. Read before the first commit of a run.
- `references/worked-example.md`: a complete two-phase run on a booking app, with every message
  the user sees. Read when unsure what a gate message or a mismatch report should look like.
- `softure-plan/references/progress-format.md`: the Progress notation.

## Required inputs

- `context/changes/<id>/plan.md` and `change.md` with `status: plan_reviewed` or `implementing`.
  If the status is `planned`, run `softure-plan-review` first. If the path resolves under
  `context/archive/`, refuse: archived changes are closed; open a new one with `softure-new`.
- `context/workflow.json`, which provides the gates and `mainBranch`.
- `context/foundation/lessons.md`, when present.
- A clean working tree, apart from files this change owns. Unrelated uncommitted changes:
  in interactive mode, list them and ask (recommended: continue and never stage them); in
  `--auto`, stop and escalate. Never stash or discard them.

**No argument.** Interactive: list the folders in `context/changes/` whose status is
`plan_reviewed` or `implementing`, recommend the most recently `updated` one, and ask. If
there is none, say which skill comes next for each change and stop. `--auto`: a change-id is
mandatory; stop with an error.

## Procedure

1. **Locate the phase.**
   - `phase N` → that phase.
   - `next` or no phase → the phase holding the first `- [ ]` in an Automated group.
   - Every automated item ticked → go to step 10.

   Refuse to skip ahead over an unfinished earlier phase unless the user explicitly says so.
   Before starting, run the **resume check** in `references/phase-commit.md` ("Resuming"): a
   previous run may have committed without writing the SHA, or ticked items without committing.

2. **Load context fresh.** Re-read the phase section, its Progress items, change.md Constraints,
   the research sections the phase relies on, and the lessons whose "Applies to" matches the
   phase's files. Read files in full, not in slices. Set `status: implementing` (and `updated`)
   on the first run. Start the phase's **touched-file set**: the paths you edit or create during
   this phase, plus `plan.md`. In phase 1 it also includes the change folder's own uncommitted
   artifacts (change.md, research.md, plan.md, reviews/), so they land in the first commit.

3. **Reconcile plan and code.** Before editing, confirm that the files and symbols the phase names
   exist and look as research described. When they differ, describe it in this shape:

   ```
   Mismatch in phase N, step S
   Plan says:      <what the plan expects>
   Code has:       <what is actually there, with path:line>
   Why it matters: <what goes wrong if we follow the plan literally>
   Recommendation: <adapt | drop the step | re-plan>, because <reason>
   ```

   - **Small drift** (renamed symbol, moved file, an extra call site): interactive, ask with the
     options "Adapt and continue" (recommended), "Drop this step", "Stop and re-plan"; `--auto`,
     adapt. Either way record it in plan.md (`## Decisions (auto)` in `--auto`, a note under the
     phase otherwise) and in the commit body.
   - **A step is no longer needed:** mark its item `- [x] ~~N.M text~~ — dropped: <reason>`.
   - **The approach no longer holds** (a wrong assumption about data, an API that does not exist,
     the Constraints would be violated): stop in both modes. Do not improvise a new design. Report
     the mismatch and recommend `softure-plan` for the remaining phases; landed phases and their
     SHAs stay.

4. **Implement with the phase's discipline.**
   - **TDD:** write the failing test first and run it to see it red for the right reason (the
     assertion, not an import error). Then implement until green, then refactor.
   - **Test-after:** implement, then write the tests named in the criteria.

   Follow the project conventions (AGENTS.md / CLAUDE.md). Keep changes inside the phase's
   files. If a necessary file is outside the list, add it and record why. For unfamiliar code or
   a stubborn failure, a read-only subagent may explore; the main thread keeps the plan.

5. **Run the gates** from `workflow.json` (`gates.*`), all of them, every phase.
   - A red gate is fixed, never skipped.
   - A failure that existed before your change must be proven to pre-exist: check out
     `mainBranch` in a scratch worktree and run the same command. Then report it. Do not silence it.

6. **Verify the criteria for real**, ticking each Progress item the moment it is proven.
   - Automated items: run the exact command or test and read its output.
   - Data criteria: read the database (a query against dev or test data), never only the
     rendered UI.
   - Manual items: first try to verify them yourself where a machine can stand in for the eye:
     screenshots at the stated widths and themes, a recorded request/response, a DB read. Tick
     such an item with `(verified by agent: <how>)`. Anything that needs the owner's judgement
     stays `- [ ]`.

7. **Manual gate** (interactive only). When manual items remain open, pause before committing
   and show the gate message (format and options in `references/phase-commit.md`): what passed
   automatically, what you verified yourself and how, and what the user should check now. In the
   **final phase**, add the open manual items of earlier phases ("still waiting from earlier
   phases"). Recommend checking now when a later phase builds on the result; otherwise recommend
   committing and leaving the items open. A problem the user reports is fixed inside this phase
   before the commit. `--auto`: no pause; open items stay `- [ ]` and are listed at the end.

8. **Commit the phase**, following `references/phase-commit.md`: stage the touched-file set by
   path, check for unrelated dirty paths, propose the message
   `<type>(<change-id>): <phase title> (p<N>)` (interactive: approve, edit or replace it;
   `--auto`: use it), commit, then append ` — <short sha>` to every item ticked in this phase.
   Never amend that edit into the phase commit: it rides with the next commit of the change
   (next phase, review fix, archive), or becomes `docs(<change-id>): progress p<N>` when nothing
   follows. Never `--no-verify`, never `--amend`. Never push, tag, release or deploy.

9. **Continue or pause.** Interactive: report the phase (items ticked, open manual items,
   progress `done/total`) and ask:
   - "Continue to phase N+1" (recommended while the context is still small);
   - "Stop here, resume later": print `softure-implement <change-id> next` for a fresh session;
   - "Review this phase first": run `softure-impl-review <change-id> phase N`, then ask again
     without this option.

   When the user asked for several phases at once, skip the question between them. `--auto`:
   continue until all phases are done or an escalation is hit. Manual mode: stop after the phase
   (see "Manual mode" below).

10. **Finish.** When every Automated item is ticked:
    - re-scan Progress and list any open item as `N.M text`, grouped Automated / Manual. An open
      Automated item means the plan is not done: go back to step 1;
    - set `status: implemented` and update `updated`;
    - commit the trailing Progress SHA edit and the status change together as
      `docs(<change-id>): progress p<N>` (stage plan.md and change.md by path; skip when nothing
      is staged; never write this commit's own SHA anywhere);
    - print the completion summary: phases with their SHAs, key files changed, open Manual items
      for the owner, decisions recorded;
    - interactive: ask whether to run `softure-impl-review <change-id>` now (recommended) or
      later. `--auto`: hand off.

## Progress rules (short form)

Use the format in `softure-plan/references/progress-format.md`:
- tick only verified items; edit only `## Progress`, never the phase sections above it;
- never rename or delete items; add new items with the next free number;
- mark dropped ones `~~text~~ — dropped: <reason>`;
- "where am I" is derived, never stored: the first open Automated item is the next step, and
  `count([x]) / count(all)` is the progress.

## Status transitions

- `plan_reviewed` → `implementing` at the start of the first phase.
- `implementing` → `implemented` once every Automated item is ticked.

## Manual mode (`mode: "manual"` or no key, and no `--auto`)

The owner checks every phase separately and commits by hand or on an explicit word. This narrows
steps 7 to 9:

- **One phase per run**, even when more remain, unless the owner names several phases in this
  request.
- **The gate always shows**, with or without open Manual items: what passed, what you verified and
  how, what the owner should check, `git diff --stat` of the touched-file set, and the proposed commit
  message. Options: "Commit" / "I'll commit it myself" / "Change something".
- **Commit only on "Commit" for this phase.** An approval of an earlier phase or a general "go ahead"
  does not cover this one. "I'll commit it myself": stage the touched-file set by path, so the owner sees
  exactly what belongs to the phase, and stop; the next run's resume check (`references/phase-commit.md`) finds the commit
  and writes its SHA into Progress.
- **After the phase: stop.** Report the phase and name the next step (`softure-implement <change-id>
  next` or `softure-impl-review <change-id> phase N`). Do not start it.
- Never push, never open a pull request.

## `--auto`

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

- Never ask. Run all remaining phases in order, with no manual gate and no question between phases.
- Apply small drift and record it under `## Decisions (auto)` in plan.md.
- Stage only files you touched for this change. A dirty path the phase's own commands produced
  (generated types, a lockfile, a snapshot) joins the touched-file set; any other unknown path is
  an escalation.
- Use the proposed commit message as is.
- Escalate (stop with a report) when:
  - the approach is invalid (re-plan needed);
  - a gate stays red after a reasonable fix attempt and you cannot prove the failure pre-exists;
  - a hook rejects the commit and the cause lies outside the change;
  - a destructive or irreversible operation is needed;
  - a secret or access is missing.

## Quality checklist

- [ ] Every ticked box was actually checked in this session, by command, query or screenshot.
- [ ] Gates are green at every phase commit.
- [ ] The diff follows the language rule in AGENTS.md (when the project carries one).
- [ ] There is one commit per phase with the WORKFLOW §9 message, and nothing unrelated is staged.
- [ ] Every ticked item carries its phase SHA, and no Progress edit was amended into its own commit.
- [ ] TDD phases show a red test before the implementation.
- [ ] Drift is recorded. No silent design changes.
- [ ] Open Manual items are listed for the owner, not ticked on the user's behalf.
- [ ] Nothing was pushed, tagged, released or deployed.

## Anti-patterns

- Ticking a box because the code "should" make it true.
- "Verifying" a write by looking at the UI, which may show form defaults or a cache.
- Fixing a red gate by skipping, disabling or loosening the test.
- `git add -A` with unrelated files in the tree.
- Quietly redesigning when the plan is wrong, instead of stopping for a re-plan.
- Bundling several phases into one commit.
- Amending after a failed hook: the failed commit never happened, so `--amend` rewrites the
  previous phase.
- Handing every manual item to the user when a screenshot or a query would have settled it.

## Handoff

Next: `softure-impl-review <change-id>`. Open manual items go to the owner. In a roadmap, they
are listed under "Owner decisions and checks" at archive time.
