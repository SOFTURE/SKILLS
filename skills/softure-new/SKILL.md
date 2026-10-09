---
name: softure-new
description: >
  Open a new change: create context/changes/<change-id>/change.md with a clear intent,
  context and constraints, placed in a roadmap (the main one for work now, a queued thematic
  one for later) or explicitly left unlinked. Accepts a change id, a path, a roadmap item ID or
  a free-form description; takes over a prepared backlog entry when one exists. Use at the
  start of every unit of delivery work, before research. Triggers: "new change",
  "open a change", "start change <id>", "/softure-new", "start the next roadmap item".
argument-hint: "<change-id | path | roadmap-item-id> [free-form intent] [--title \"...\"] [--backlog <slug>] [--auto]"
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
and moves its `status`. The contract lives in `WORKFLOW.md` §3–§5.1 of the SOFTURE skills package.

## Required inputs

- `context/workflow.json`: if it is missing, say "run `softure-init` first" and stop.
- A change id, a path to a change folder, a roadmap item ID (`[A-Z]+-\d+`), or enough
  description to derive an id.

With no argument at all: interactive, ask for one, showing two or three forms
(`softure-new invoice-pdf-download`, `softure-new IN-3`, `softure-new search-titles people cannot
find pages by title`) and, when the conversation already describes the work, a proposed id as the
recommended answer. `--auto`: escalate, there is nothing to derive from.

## Procedure

1. **Read the configuration.** Load `context/workflow.json` and take `language`. Everything you
   write into `change.md` uses that language. Skill instructions stay in English.

2. **Parse the argument.** The first token is the reference, the rest is free-form intent.
   - Strip a leading `@` and a trailing `/`; if the token is a path, take its last segment.
   - A token matching `[A-Z]+-\d+` is a roadmap item ID.
   - The free-form intent is guidance for the title and the intent, never pasted in as the title.
     Keep the user's own words: quote them under `## Context` (or `## Notes` when short).

   | Input | Reference | Intent |
   |---|---|---|
   | `invoice-pdf-download` | id `invoice-pdf-download` | none |
   | `@context/changes/invoice-pdf-download/` | id `invoice-pdf-download` | none |
   | `IN-3` | roadmap item `IN-3` | from its block |
   | `search-titles people cannot find pages by title` | id `search-titles` | "people cannot find pages by title" |
   | `Search Titles fix it` | `Search` fails the id check | propose `search-titles` |

3. **Resolve the change id.**
   - The id matches `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, is at most 40 characters, and names the
     *outcome* (`pending-states`, not `fix-button`). An id that fails gets a proposed fix, not a
     silent rewrite.
   - If the user gave a roadmap item, read its block in `roadmap.md`. Use its `Change ID` when one
     is set. Otherwise propose one and write it back into the item block and the table row.
   - **Uniqueness:** the id must not exist as `context/changes/<id>/`, as
     `context/archive/*-<id>/`, nor as `context/backlog/roadmap-*/<id>/`. Check all three with Glob.
     On a clash, propose the first free numeric suffix (`-2`, `-3`, …) or a more precise noun. Never
     reuse an archived id; to revisit archived work, open a new change and link the archive folder
     under `## Context`.
   - **Existing state** is not a clash when it is this change's own:

     | Found | Do |
     |---|---|
     | `context/changes/<id>/change.md` | do not overwrite; report its `status` and the next step (WORKFLOW §4 table) |
     | `context/changes/<id>/` without `change.md` (queued by an orchestrator, or a `backlog-input.md`) | write `change.md` from what is there |
     | `context/backlog/roadmap-<slug>/<id>/change.md` | **take** the entry (WORKFLOW §5.1): `git mv` it to `context/changes/<id>/backlog-input.md`, remove the empty folder, fix relative links (they lose one `../`), then write the real `change.md` from it |
     | `context/archive/*-<id>/` | clash: a new id is needed |

4. **Place the change** when no roadmap item was given. A change outside every roadmap is
   invisible to the orchestrators and to whoever reads the roadmap as the board. Decide **now or
   later** from the material (genuinely split → later: leaving the backlog is one `git mv`,
   undoing a half-started folder is not), then offer, recommended option first:
   - **work now** → a new row and item block in the main `roadmap.md` (next free ID of the
     closest prefix, status `ready`, `- **Input:**` to the folder);
   - **later** → an entry in a queued thematic roadmap (`--backlog <slug>`):
     `context/backlog/roadmap-<slug>/<id>/change.md` with `status: backlog`, plus its row in the
     thematic roadmap and in the backlog README (WORKFLOW §5.1), and nothing in `changes/`;
   - **new theme** → only when no queued roadmap fits: `softure-roadmap --queue <slug>` first;
   - **unlinked** → a one-off with `roadmap_item: null`.

   Pick the queued roadmap by its *reason for existing*, not by a shared file or keyword. Record
   the placement and its one-line reason under `## Notes`. Signals, the three backlog writes, how
   to choose the roadmap and find a free ID: [references/placement.md](references/placement.md)
   (read whenever the change arrives without a roadmap item).

   The project's rules may make one of these mandatory (for example "every change belongs to a
   roadmap"); follow them. In `--auto`, take the project's rule, else "work now" when the request
   is for work now, else "later", and record the choice under `## Notes`.

5. **Gather the content.** Fill these four sections. Ask only for what you cannot infer.
   - **Intent:** what must be true when this change is done, and for whom. One short paragraph.
     Phrase it as an observable outcome a reviewer could check.
   - **Context:** where the change comes from. Include the roadmap item (link, and its block
     quoted, not retold), any feedback quoted **verbatim** in a blockquote with author and date,
     and what is already known about the current state, with file paths when obvious.
     Do not research here; that is the next skill's job.
   - **Constraints:** files or areas this change owns exclusively, what it must not touch
     (name the neighbour that owns it when items run in parallel), deadlines, and decisions
     already made by the owner.
   - **Notes:** dependencies on other items, the placement decision, the user's original words
     when they did not fit in Context. Leave it empty when there is nothing.

6. **Ask at most three questions** (interactive mode), one at a time, recommended answer first
   with a one-line reason. Ask only when two readings would lead to different work:
   - the outcome and for whom ("title match first, or a wider overhaul?");
   - the scope boundary ("does this include the mobile layout?");
   - the placement, when step 4 left it open.

   Push back when the request is a solution ("add a spinner"): offer the outcome it serves as the
   recommended intent. `--auto`: take the reading the source supports best and record it.

7. **Write `context/changes/<id>/change.md`** (or the backlog path from step 4) using the template
   below. Create the `context/changes/` folder if it does not exist yet. Title: one sentence,
   at most 80 characters, no trailing period; with nothing else to go on, humanize the id.

8. **Update the roadmap** when the change is linked to an item:
   - The item block gets `- **Change ID:** \`<id>\`` and `- **Input:**` pointing at the file.
   - The table row's second cell is `` `<id>` ``.
   - Leave the item status unchanged. The orchestrator or the owner sets `in_progress`.

9. **Report.** Give the path, the placement, a one-line intent, and the next step:
   `softure-research <id>`. When the intent is bug-shaped ("broken", "regression", "why does")
   or carries a self-diagnosed fix, or when its scope is in doubt ("should we even…"), add that
   `softure-frame <id>` should follow research.

Complete good and bad examples (from a roadmap item, from raw feedback, a bad one, a backlog
placement): [references/example-change.md](references/example-change.md) (read before the first
change in a project or when the input is raw feedback).

## Output template

```markdown
---
change_id: <id>
title: "<one sentence: the outcome, not the activity>"
status: new
roadmap_item: <ID or null>
branch: null
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
archived_at: null
---

## Intent
<what must be true when done, and for whom>

## Context
<roadmap item link and its block quoted; feedback quoted verbatim; known current state>

## Constraints
<exclusively owned files/areas; must-not-touch; deadlines; owner decisions>

## Notes
```

Dates come from `date +%Y-%m-%d` (in `workflow.json` → `timezone` when set). In the backlog,
`status: backlog`.

## Status transitions

- Creates the change with `status: new` (or `backlog` for a later entry). Sets `created` and
  `updated` to today.

## `--auto`

`mode: "autonomous"` in `context/workflow.json` implies `--auto` for every run of this skill; `mode: "manual"` (or no key) never does (WORKFLOW §8).

- Never ask. Derive the id from the roadmap item or the description.
- If the id clashes, append the first free numeric suffix (`-2`, `-3`, …) and record the choice
  under `## Notes` as `- Decision (auto): id <x> taken → <y>`.
- Placement and readings as in steps 4 and 6, each recorded under `## Notes`.
- If the intent cannot be derived at all (no roadmap item and no description), escalate. Do not
  invent scope.

## Quality checklist

- [ ] The id is unique across `changes/`, `archive/` and `backlog/`, kebab-case and ≤ 40 characters.
- [ ] The change is placed: a roadmap row (main or thematic) or a recorded decision to leave it unlinked.
- [ ] The title states an outcome a reviewer can verify.
- [ ] Feedback is quoted verbatim and attributed; the user's own words are kept.
- [ ] Constraints name concrete paths when ownership matters for parallel work.
- [ ] The roadmap row and item block point to the same id and the same folder.
- [ ] Nothing in the file is a plan or a solution. Those belong to later steps.

## Anti-patterns

- Writing the solution into Intent ("add a spinner to Button"). Write the outcome instead
  ("every operation longer than 300 ms shows it is working").
- Paraphrasing feedback. The original words carry information that a paraphrase loses.
- Opening two changes for one outcome, or one change for two unrelated outcomes.
- Copying a backlog entry into `changes/` instead of moving it: one topic, one place.
- Overwriting an existing `change.md`, or writing anything inside `context/archive/`.
- Starting research, writing `research.md` or `plan.md`, or editing code from this skill.

## Handoff

Next: `softure-research <change-id>`.
