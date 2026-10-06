---
name: softure-roadmap
description: >
  Slice an accepted PRD (or a list of feedback items) into `context/foundation/roadmap.md`:
  checks the PRD is ready, inventories the codebase, asks at most three framing questions
  (what to optimise for, what proves the idea first, what most likely stalls it), then writes
  thin vertical slices with stable IDs, dependencies, ownership of hot files for parallel work,
  unknowns, baselines, and an at-a-glance table that orchestrators parse. Self-reviews before
  writing and ends with one recommended next item. Also queues thematic roadmaps, promotes
  them and closes a finished roadmap. Optionally opens a change folder for every ready item.
  Use after softure-prd, when feedback must be turned into work, or to revise the order.
  Triggers: "make a roadmap", "slice the PRD", "what do we build first", "order the work",
  "turn feedback into roadmap items", "close the roadmap".
argument-hint: "[--revise] [--open-changes] [--queue <slug> | --promote <slug> | --close] [--from-feedback <path>] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Agent
  - AskUserQuestion
---

# softure-roadmap: ordered, parallel-safe slices

## Purpose

Turn requirements into an ordered list of **changes**, each small enough to be planned,
built, reviewed and merged on its own, and safe to run in parallel where the roadmap says so.
The format is a contract: `softure-worktree` and `softure-worktree-manager` parse it
(WORKFLOW §5). Follow it exactly.

**Posture: a tech lead who arrives with a proposal.** Read the PRD, inventory the code, then
recommend. Ask the owner only the few calls the material cannot settle, each with a
recommendation and real alternatives. Never ask what the files already answer; never decide the
framing silently.

The roadmap names, orders and sizes slices. It does not choose libraries, design schemas or plan
steps (that is `softure-plan`), and it never estimates in time.

## Inputs

- `context/foundation/prd.md`. If missing, stop and point to `softure-prd`. Alternatively,
  `--from-feedback <path>` takes notes or screenshots and a short slice is made without a PRD;
  record that in the header, and make every item trace to a feedback point instead of an FR.
- `context/workflow.json` (for `language`, `worktree.maxParallel`, `migrations`, `research.sources`).
- Read when present: `context/foundation/shape-notes.md` (appetite, rabbit holes and no-gos shape
  the order), `context/foundation/lessons.md` (rules about ordering or readiness are priors), the
  stack documents listed in `research.sources`, and `context/foundation/roadmaps/*.md` (ID
  prefixes already taken).
- An existing `roadmap.md` decides the mode; see "Existing roadmap" below.

Read the PRD in full, not in excerpts.

## Modes

- **main** (default): writes `context/foundation/roadmap.md`, the one roadmap that is executed.
- **`--revise`**: edits the existing main roadmap in place (see "Existing roadmap").
- **`--queue <slug>`**: writes a queued thematic roadmap per WORKFLOW §5.1:
  `context/foundation/roadmaps/roadmap-<slug>.md` (`status: waiting`, `backlog:`, `trigger:`), plus
  `context/backlog/roadmap-<slug>/README.md` (table `| ID | Entry | Title | Condition | Kind |`, where Kind
  is `start`, `dependency` or `owner`) and one `<change-id>/change.md` per item (§4 format, `status: backlog`,
  `## Intent`, `## Context` with the item block, `## Constraints`). Use this for every theme that is not
  next in line. Several queued roadmaps can exist; each has its own ID prefix. The slug is English
  and names the **reason the items wait** (`roadmap-payments`: they need a provider account), not
  the page they touch: a page-named roadmap turns into a bin for every later edit of that page.
- **`--promote <slug>`**: the owner makes a queued roadmap the main one. Archive the current main
  roadmap, `git mv` the queued file to `roadmap.md`, set `status: ready`, and take its ready entries
  (`git mv …/change.md context/changes/<id>/backlog-input.md`, then the `softure-new` format).
  Never promote on your own initiative, not even in `--auto`.
- **`--close`**: the main roadmap is realised; archive it per WORKFLOW §5.2. Check the three gates
  first and report every failing one at once: rows not `done` / `done_code` and not carried over,
  leftover folders in `context/changes/` (archive each through `softure-archive`, a change without a
  plan included, before continuing), and the full integration result on `<main>` when configured.
  Then write `## Summary` (`| ID | Item | What changed | Merge |`, the merge SHA from
  `git log --merges --grep "<change-id>"` on `<main>`, plus the integration line), move the file to
  `foundation/archive/<YYYY-MM-DD>-roadmap.md`, clean up the promoted roadmap's backlog folder and
  index row, and commit. Do not promote the next roadmap in the same step: that is `--promote`, the
  owner's call. In `--auto`, a failing gate stops the close and is reported; it is never forced.
  A sample `## Summary` is at the end of [references/example-roadmap.md](references/example-roadmap.md).

## Existing roadmap

| What is there | Do |
|---|---|
| no `roadmap.md` | main mode |
| every row `done` / `done_code` | it is finished: run `--close` first (recommended), then write the new one |
| rows still open | **revise mode** (recommended); "archive and start over" only on the owner's explicit choice, and every open row must first be carried to the new roadmap or a queued one |

Revise mode rules: never renumber an ID; new items take the next free number of the prefix; never
drop or re-status an `in_progress`, `ready_to_merge`, `done` or `done_code` row; remove a row only
when it is `proposed` or `ready` with no folder in `changes/` and no branch; bump `version`; set
`prd_version` to the PRD's; name every item whose `PRD refs` cite an FR the new PRD version changed.
Overwriting a roadmap without archiving it is never an option. In `--auto`: revise in place.

## Procedure

1. **Readiness check.** Score the PRD, one point each:
   - the summary names the problem, who has it and the outcome (no TODO);
   - at least one `must` FR has Given/When/Then acceptance;
   - goals or success metrics carry a number (baseline and target);
   - no open question gates a `must` FR.

   Show the four signals and the score, plus the PRD `status` and the count of open questions.
   With 3 or 4 points and `status: accepted`, continue. Otherwise name each missing signal and
   what it will do to the roadmap ("FR-5 has no acceptance: its item will be `blocked`"), then
   ask: "Finish the PRD first (Recommended) / Proceed: thin areas become blocked items / Cancel".
   `--auto`: proceed, write the roadmap with `status: draft`, make every item over a thin area
   `blocked (PRD gap: <what>)`, and record the decision.

2. **Codebase baseline.** Find out what already exists instead of asking. Probe each layer: UI,
   server/API, data (driver, migrations), auth, mail and other integrations, deploy/CI, tests,
   observability. Skip a layer a stack document already states and cite that document. When the
   `Agent` tool is available, run the probes in parallel, one short prompt each: *"Inventory the
   <layer> of this repository in under 100 words: verdict present, partial (scaffolded but not
   wired) or absent; cite a file for anything present; do not speculate or edit files."* Without
   it, run them in sequence. Show a one-screen summary and ask once "Does this match? Correct or
   add anything". `--auto`: use the probes as they are, and say so in `## Decisions (auto)`. The
   baseline decides which foundations may exist: a `present` layer is never scaffolded again.

3. **Framing interview.** At most three anchor questions, one at a time, each with a
   recommendation grounded in a quoted line or ID, up to two real alternatives with the condition
   under which they win, and a free-form option:
   - what this roadmap optimises for (feedback, quality, simplicity, speed, learning, other);
   - which item proves the idea first (the north star);
   - what most likely stalls the work (decisions, capacity, time, skills, external, none).

   Skip an anchor only when the material states the value outright, and say so with the quote.
   Derive where to invest depth from the answers; do not ask it. Close with a recap the owner can
   accept with "go" or correct line by line. Signals, the unusual-product exception, phrasing and
   a good and a bad question: [references/interview.md](references/interview.md) (read before
   asking). `--auto`: take each recommendation and record it.

4. **List the capabilities** from the FRs (or feedback points). Group points that change the
   same user-visible behaviour. Every item will cite at least one of them.

5. **Slice vertically.** Each item delivers one observable outcome end to end (data → logic →
   UI → test), never "all the database work". Each item should:
   - fit one plan of 1 to 4 phases, add at most one migration and have one primary surface;
   - be mergeable on its own without breaking main;
   - carry its own verification (a baseline and an after measurement).

   Too big → split by user path, by data subset, by role, read before write, or into a walking
   skeleton plus enhancements. Too small → fold into the item it serves. Horizontal work is
   allowed only as a **foundation**: outcome marked `(foundation) …` and an `Unlocks:` line naming
   the items, the blocking unknown or the verification path it enables; without one, fold it into
   its first consumer. Nothing becomes an item that the PRD (or the feedback) does not contain:
   new ideas from the conversation go to `## Owner decisions and checks` (a real gap) or to
   `context/backlog/<topic>.md` (deferred). Patterns, good and bad items:
   [references/slicing.md](references/slicing.md) (read when an item feels too big, too small or
   horizontal).

6. **Prefer modules.** Items whose FR is marked `Module: @softure-ai/<name>`, or whose layer the
   baseline reports absent and a module covers (WORKFLOW §10), become "adopt and configure the
   module" items, which are much smaller than building it.

7. **Order.**
   - Prerequisites are item IDs plus concrete external state ("sending domain verified"), never
     "backend ready". Sort topologically: no cycles, nothing depends on a later item.
   - Risk first (whatever could invalidate the plan), then dependencies, then value.
   - Place the north star as early as its prerequisites allow.
   - Break remaining ties by the goal from the interview (table in references/slicing.md).
   - Do not choose an order that prejudges an open owner question; the items it decides are
     `blocked (<question>)` until it is answered.
   - Put a "finish" item last when the theme needs a final measurement or review across items.
     With `integration.cadence: "roadmap"` it does not start the full integration suite of its own:
     the coordinator's run on `<main>` (M7), or the release when it covers the roadmap, is that run.

8. **Unknowns and blockers.** Per item, `- <question> (owner: research | <person>; blocks: yes | no)`.
   One with `blocks: yes` makes the row `blocked (<question, short>)`. External dependencies the
   team cannot resolve alone are prerequisites. Questions that gate several items go to
   `## Owner decisions and checks`, naming the IDs they gate.

9. **Parallel safety.** For every item, list the files and areas it will touch
   (`- **Touches (estimate):** …`, from a quick code search; it is an estimate, so say so). Two
   items may run in parallel only if:
   - their file sets are disjoint;
   - at most one of them adds a migration (`workflow.json` → `migrations`);
   - neither changes a shared primitive the other uses.

   Assign **exclusive owners** for hot files and write the lanes under `## Order` as
   `| Lane | Chain | Owns | Note |` (two to five lanes, each item in exactly one). When the main
   risk is capacity, look hardest for parallel lanes.

10. **Per item, write:** Change ID (kebab-case, names the outcome, unique across `changes/`,
    `archive/` and `backlog/`), Status, Outcome (a verb-led state of the world: "a visitor books a
    free slot", never a noun like "booking system"), `Unlocks` (foundations only), Prerequisites,
    Touches (estimate), Unknowns, Risk (one line: why it sits here and what could go wrong),
    Baseline (how it is measured before and after) and PRD refs (literal IDs, not paraphrases).

11. **Header and `## Order`.**
    - frontmatter: `prd_version` = the PRD `version`;
    - run-wide orders in the quote block: push main or not; archive the roadmap at the end or not;
      release at the end or not (only with the owner's approval, quoted: it tells the coordinator a release
      follows, and with `integration.coveredByRelease` the release's suite is the roadmap's run; skills
      still never release); parallelism (default: `workflow.json` → `worktree.maxParallel`); which items need the owner
      at the keyboard (`Mode: owner`);
    - `## Order` opens with the framing (optimising for, first proof, main risk, depth), then the
      reasoning for the order, `### Starting point` (the confirmed baseline, one line per layer
      with a file), `### Lanes`, and one line pointing to deferred ideas in the backlog.
    - Define any strategy term (north star, riskiest assumption, …) in one plain sentence on first
      use, or replace it with plain words. A teammate must be able to read the roadmap cold.

12. **Self-review before writing.** Run the checklist under "Quality bar". If any check fails,
    do not write the file: report each failure precisely ("FR-6 (must) is not cited by any item",
    "BK-5 depends on BK-6, which comes later", "BK-1 scaffolds auth, but the baseline reports auth
    present"), fix it, and run the checks again. In `--auto`, fix and re-check; if a failure cannot
    be fixed from the material, stop and report it instead of writing a table orchestrators would
    act on.

13. **Review with the user.** Show the at-a-glance table and the lanes, then ask
    "Accept the order? (Recommended: accept)". Apply edits, re-run the self-review, and set
    `status: ready` (or keep `draft` after a thin-PRD proceed).

14. **`--open-changes`.** For every `ready` item without a folder, create
    `context/changes/<change-id>/change.md` in the `softure-new` format (WORKFLOW §4):
    - `status: new` and `roadmap_item: <ID>`;
    - `## Intent` = the item outcome;
    - `## Context` quotes the item block verbatim;
    - `## Constraints` lists the exclusively owned files;
    - add `- **Input:** context/changes/<change-id>/change.md` to the item block.

A complete, realistic roadmap in this format, with a bad version and why it fails:
[references/example-roadmap.md](references/example-roadmap.md) (read before the first roadmap in a
project).

## Output: `context/foundation/roadmap.md`

Exactly the structure of WORKFLOW §5. Parser-critical rules:
- Table header: `| ID | Change | Outcome | Depends on | Mode | Status |`.
- Row: `| **FC-1** | \`change-id\` | … | FC-0, FC-2 or — | autonomous or owner | <status> |`.
  The **status is the last cell**, and there is one row per change-id.
- IDs match `[A-Z]+-\d+`. Use a 2 to 4 letter prefix per roadmap theme, not used by any other
  roadmap (`grep -ho '\*\*[A-Z]\+-[0-9]' context/foundation/roadmap.md context/foundation/roadmaps/*.md | sort -u`),
  and keep numbers stable forever.
- Status vocabulary only: `proposed`, `ready`, `blocked (<why>)`, `in_progress (…)`,
  `ready_to_merge (…)`, `done`, `done_code (…)`. A new roadmap uses only `proposed`, `ready`
  and `blocked`. `ready` means the item itself has no open decision; whether its prerequisites
  are merged is checked by the orchestrator.
- Every item block has `- **Change ID:** \`<id>\`` followed directly by `- **Status:** <same as row>`.
  Extra fields (`Unlocks`, `Touches (estimate)`, `Input`) come after those two.
- The framing, baseline, lanes and deferred ideas live under `## Order`; owner questions under
  `## Owner decisions and checks`. Do not add other top-level sections.
- `## Done` starts empty; `softure-archive` is its only writer.

Write prose in `workflow.json` → `language`. Keep the IDs, the status tokens, the headings and the
table header in English, because scripts parse them.

## `--auto`

Never ask. In place of each question:
- thin PRD → proceed as `status: draft`, thin items `blocked (PRD gap: …)`;
- baseline → use the probes unconfirmed;
- framing anchors → take the recommendations; on a tie, the value that orders risk earlier;
- an item of doubtful value → `proposed`; one that needs an owner decision → `blocked (<why>)`;
- existing open roadmap → revise in place;
- final review → accept, after a green self-review.

Record each choice under `## Decisions (auto)` at the end of the file:
`- <question> → <choice> (<one-line reason>)`. Never `--promote`; never force `--close`.

## Quality bar (the self-review)

- [ ] Every `must` FR is cited by at least one item, or explicitly deferred with a reason.
- [ ] Every item cites at least one PRD ID or feedback point; none is invented.
- [ ] No item is a horizontal layer; every foundation has `Unlocks` and none re-scaffolds a `present` layer.
- [ ] Every prerequisite ID exists; the graph has no cycles; the order is topological.
- [ ] Each item has unknowns and a baseline. "None" is allowed only with a reason.
- [ ] Every `blocked` row has an unknown with `blocks: yes` or a named external dependency.
- [ ] Items running in parallel have disjoint files and at most one migration between them; each
      item sits in exactly one lane.
- [ ] The table and item blocks agree on IDs, change-ids and statuses; change-ids are unique
      kebab-case outcomes, not IDs, dates or activities.
- [ ] No estimates, sizes or dates for delivery; no implementation steps.
- [ ] Strategy terms are defined on first use.
- [ ] The first item can start today with no open owner decision.

## Do not

- Do not plan implementation steps. That is `softure-plan`, per change.
- Do not change the status of an item that is in progress. That belongs to the orchestrators
  and `softure-archive`.
- Do not estimate in hours, days, points or sizes. Order and slice size are the planning tools here.
- Do not chain into the next skill on your own; the handoff is a recommendation.

## Handoff

Print a short summary: path, slug and version, the framing in one line, item counts by status,
PRD coverage (`must` FRs cited / total), and owner decisions waiting. Then recommend **one** next
item, not a menu. Take the first rule that applies:

1. the north star is `ready` with its prerequisites done → it;
2. a `ready` prerequisite of the north star → it, saying "this unlocks <north star>";
3. nothing is `ready` → the owner decision that unblocks the most items, with what it unblocks;
4. otherwise → the `ready` item that unblocks the most others; ties by the goal.

Name the command (`softure-new <change-id>`, or `--open-changes` then `softure-worktree-manager`
for parallel execution, `softure-worktree <ID>` for one item end to end), the next two items after
it, and what waits for the owner.
