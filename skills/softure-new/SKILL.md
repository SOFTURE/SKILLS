---
name: softure-new
description: >
  Open a new change: create context/changes/<change-id>/change.md with a clear intent,
  context and constraints, linked to a roadmap item when there is one. Use at the start of
  every unit of delivery work, before research. Triggers: "new change", "open a change",
  "start change <id>", "/softure-new",
  "start the next roadmap item".
argument-hint: "<change-id> [roadmap-item-id] [--title \"...\"] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

# softure-new: open a change

A change is the unit of delivery: one outcome, one folder, one branch. This skill creates its
identity file, `change.md`. Every later step (research, plan, implement, review, archive) reads it
and moves its `status`. The contract lives in `WORKFLOW.md` §3–§4 of the SOFTURE skills package.

## Required inputs

- `context/workflow.json`: if it is missing, say "run `softure-init` first" and stop.
- A change id, or enough description to derive one.
- Optional: a roadmap item ID (`[A-Z]+-\d+`) that exists in `context/foundation/roadmap.md`.

## Procedure

1. **Read the configuration.** Load `context/workflow.json` and take `language`. Everything you
   write into `change.md` uses that language. Skill instructions stay in English.

2. **Resolve the change id.**
   - The id is kebab-case ASCII, at most 40 characters, and names the *outcome*
     (`pending-states`, not `fix-button`).
   - If the user gave a roadmap item, read its block in `roadmap.md`. Use its `Change ID` when one
     is set. Otherwise propose one and write it back into the item block and the table row.
   - **Uniqueness:** the id must not exist as `context/changes/<id>/` nor as
     `context/archive/*-<id>/`. Check both with Glob. On a clash, propose a suffixed alternative
     (`-v2` or a more precise noun). Never reuse an archived id.

3. **Gather the content.** Fill these four sections. Ask only for what you cannot infer.
   - **Intent:** what must be true when this change is done, and for whom. One short paragraph.
     Phrase it as an observable outcome.
   - **Context:** where the change comes from. Include the roadmap item (link, outcome,
     prerequisites, unknowns), any feedback quoted **verbatim** in a blockquote with author and
     date, and what is already known about the current state, with file paths when obvious.
     Do not research here; that is the next skill's job.
   - **Constraints:** files or areas this change owns exclusively, what it must not touch,
     deadlines, and decisions already made by the owner.
   - **Notes:** dependencies on other items. Leave this section empty when there are none.

4. **Ask at most three questions** (interactive mode). Ask only when the intent is ambiguous,
   when two readings would lead to different work, or when the scope boundary is unclear. Ask
   them one at a time and put your recommended answer first.

5. **Write `context/changes/<id>/change.md`** using the template below. Create the
   `context/changes/` folder if it does not exist yet.

6. **Update the roadmap** when the change is linked to an item:
   - The item block gets `- **Change ID:** \`<id>\``.
   - The table row's second cell is `` `<id>` ``.
   - Leave the item status unchanged. The orchestrator or the owner sets `in_progress`.

7. **Report.** Give the path, a one-line intent, and the next step (`softure-research <id>`).

## Output template

```markdown
---
change_id: <id>
title: "<one sentence: the outcome, not the activity>"
status: new
roadmap_item: <ID or null>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
archived_at: null
---

## Intent
<what must be true when done, and for whom>

## Context
<roadmap item link and its outcome/unknowns; feedback quoted verbatim; known current state>

## Constraints
<exclusively owned files/areas; must-not-touch; deadlines; owner decisions>

## Notes
```

## Status transitions

- Creates the change with `status: new`. Sets `created` and `updated` to today.

## `--auto`

- Never ask. Derive the id from the roadmap item or the description.
- If the id clashes, append the first free numeric suffix (`-2`, `-3`, …) and record the choice
  under `## Notes` as `- Decision (auto): id <x> taken → <y>`.
- If the intent cannot be derived at all (no roadmap item and no description), escalate. Do not
  invent scope.

## Quality checklist

- [ ] The id is unique across `changes/` and `archive/`, kebab-case and ≤ 40 characters.
- [ ] The title states an outcome a reviewer can verify.
- [ ] Feedback is quoted verbatim and attributed.
- [ ] Constraints name concrete paths when ownership matters for parallel work.
- [ ] The roadmap row and item block point to the same id.
- [ ] Nothing in the file is a plan or a solution. Those belong to later steps.

## Anti-patterns

- Writing the solution into Intent ("add a spinner to Button"). Write the outcome instead
  ("every operation longer than 300 ms shows it is working").
- Paraphrasing feedback. The original words carry information that a paraphrase loses.
- Opening two changes for one outcome, or one change for two unrelated outcomes.
- Starting research or editing code from this skill.

## Handoff

Next: `softure-research <change-id>`.
