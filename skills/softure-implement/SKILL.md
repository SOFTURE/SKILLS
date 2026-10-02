---
name: softure-implement
description: >
  Execute a reviewed plan phase by phase: write the code and tests for one phase, run the
  project gates, verify the criteria for real, tick ## Progress and commit once per phase.
  Resumes from the first open item. Use after softure-plan-review. Triggers: "implement
  phase N", "continue implementation", "/softure-implement",
  "execute the plan", "next phase".
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

## Required inputs

- `context/changes/<id>/plan.md` and `change.md` with `status: plan_reviewed` or `implementing`.
  If the status is `planned`, run `softure-plan-review` first.
- `context/workflow.json`, which provides the gates and `mainBranch`.
- `context/foundation/lessons.md`, when present.
- A clean working tree, apart from files this change owns. Unrelated uncommitted changes:
  in interactive mode, ask; in `--auto`, stop and escalate. Never stash or discard them.

## Procedure

1. **Locate the phase.**
   - `phase N` → that phase.
   - `next` or no argument → the phase holding the first `- [ ]` in an Automated group.
   - Every automated item ticked → go to step 9.

   Refuse to skip ahead over an unfinished earlier phase unless the user explicitly says so.

2. **Load context fresh.** Re-read the phase section, its Progress items, change.md Constraints,
   relevant research sections, and the lessons whose "Applies to" matches the phase's files.
   Set `status: implementing` (and `updated`) on the first run.

3. **Reconcile plan and code.** Before editing, confirm that the files and symbols the phase names
   exist and look as research described. When they differ:
   - **Small drift** (renamed symbol, moved file, an extra call site): adapt and record it under
     `## Decisions (auto)` in plan.md, or ask in interactive mode.
   - **The approach no longer holds** (a wrong assumption about data, an API that does not exist,
     the Constraints would be violated): stop. Do not improvise a new design. Report what is
     wrong and recommend `softure-plan` (re-plan) for the remaining phases.

4. **Implement with the phase's discipline.**
   - **TDD:** write the failing test first and run it to see it red for the right reason.
     Then implement until green, then refactor.
   - **Test-after:** implement, then write the tests named in the criteria.

   Follow the project conventions (AGENTS.md / CLAUDE.md). Keep changes inside the phase's
   files. If a necessary file is outside the list, add it and record why.

5. **Run the gates** from `workflow.json` (`typecheck`, `lint`, `test`), all of them, every phase.
   - A red gate is fixed, never skipped.
   - A failure that existed before your change must be proven to pre-exist: check out
     `mainBranch` in a scratch worktree and run the same command. Then report it. Do not silence it.

6. **Verify the criteria for real.**
   - Automated items: run the exact command or test and read its output.
   - Data criteria: read the database (a query against dev or test data), never only the
     rendered UI.
   - Manual items: try to verify them yourself where a machine can stand in for the eye, for
     example screenshots at the stated widths and themes, a recorded request/response, or a DB
     read. Tick such an item with `(verified by agent: <how>)`. Anything that needs the owner's
     judgement stays `- [ ]`.

7. **Commit the phase.**
   - Stage only this change's files and check `git status` before committing.
   - One commit per phase, with message `<type>(<change-id>): <phase title> (p<N>)`, where type
     is `feat`, `fix`, `refactor`, `test`, `docs` or `chore`.
   - Then tick the verified boxes and append ` — <short sha>` of that commit. Do **not** amend the
     Progress edit into it: amending changes the SHA you just recorded. The edit rides with the
     next commit of the change (next phase, review fix, archive); after the last phase, or when the
     branch is about to be pushed, commit it as `docs(<change-id>): progress p<N>`. Never push, tag,
     release or deploy.

8. **Continue or pause.** In interactive mode, report the phase result and ask whether to continue
   to the next phase. In `--auto`, continue until all phases are done or an escalation is hit.

9. **Finish.** When every Automated item is ticked:
   - set `status: implemented` and update `updated`;
   - list the open Manual items for the owner;
   - recommend `softure-impl-review <change-id>`.

## Progress rules (short form)

Use the format in `softure-plan/references/progress-format.md`:
- tick only verified items;
- never rename or delete items;
- add new items with the next free number;
- mark dropped ones `~~text~~ — dropped: <reason>`.

## Status transitions

- `plan_reviewed` → `implementing` at the start of the first phase.
- `implementing` → `implemented` once every Automated item is ticked.

## `--auto`

- Never ask. Run all remaining phases in order.
- Apply small drift and record it under `## Decisions (auto)` in plan.md.
- Stage only files you touched for this change.
- Escalate (stop with a report) when:
  - the approach is invalid (re-plan needed);
  - a gate stays red after a reasonable fix attempt and you cannot prove the failure pre-exists;
  - a destructive or irreversible operation is needed;
  - a secret or access is missing.

## Quality checklist

- [ ] Every ticked box was actually checked in this session, by command, query or screenshot.
- [ ] Gates are green at every phase commit.
- [ ] The diff follows the language rule in AGENTS.md (when the project carries one).
- [ ] There is one commit per phase with the WORKFLOW §9 message, and nothing unrelated is staged.
- [ ] TDD phases show a red test before the implementation.
- [ ] Drift is recorded. No silent design changes.
- [ ] Nothing was pushed, tagged, released or deployed.

## Anti-patterns

- Ticking a box because the code "should" make it true.
- "Verifying" a write by looking at the UI, which may show form defaults or a cache.
- Fixing a red gate by skipping, disabling or loosening the test.
- `git add -A` with unrelated files in the tree.
- Quietly redesigning when the plan is wrong, instead of stopping for a re-plan.
- Bundling several phases into one commit.

## Handoff

Next: `softure-impl-review <change-id>`. Open manual items go to the owner. In a roadmap, they
are listed under "Owner decisions and checks".
