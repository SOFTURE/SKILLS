# Fanning out research to subagents

Read this when step 3 of softure-research launches subagents. The goal is breadth without
overlap: each subagent covers one area nobody else covers, and you keep the conclusions.

## Roles

Pick 2 to 4 that fit the change. Never more than 5. A role that has nothing to find for this
change is not launched (no padding).

| Role | Agent type | Question it answers | Typical sources |
| --- | --- | --- | --- |
| **Locator** | fast search (Explore-type) | Where does X live? Which files define, call, test and configure it? | grep for symbols, routes, table names, message keys |
| **Flow tracer** | general-purpose, told read-only | What happens, step by step, when a real user does Y? Where does data enter, change, and leave? | entry point (route, action, job, CLI) through to the response, UI or side effect |
| **History miner** | fast search | What did earlier work decide here, and why? What broke before? | `context/changes/*/`, `context/archive/*/` (research, plan, reviews), `context/foundation/lessons.md`, `git log --follow` on the hot files, commit messages |
| **Data and test scout** | general-purpose, told read-only | What does the schema say, what invariants hold, what do the tests cover, how are they run? | schema files, migrations, fixtures, test files, `workflow.json` gates |
| **Sources reader** | fast search | What do the configured docs say about this area? | `workflow.json` -> `research.sources` |

For `quick` depth, one locator plus your own reading is usually enough. For `deep`, add the
history miner and the data and test scout even when they seem unlikely to find much: in money,
auth and migration work, the surprise is usually in the history or the data.

## Brief template

Every brief is self-contained. The subagent has not seen the conversation.

```text
Role: <locator | flow tracer | history miner | data and test scout | sources reader>.
Change: <change-id>. Intent (verbatim from change.md): "<Intent>".
Your area: <one area, one or two concrete questions>.
Out of your area: <what the other subagents cover, so you do not duplicate it>.

Rules:
- Read-only. Do not edit, create or delete files. Do not write to any database.
- Cite path:line (or doc path + heading) for every claim. A claim without a citation is dropped.
- Report facts, not proposals. "Function X writes column Y" is a fact; "we should add an index" is not.
- Report usage, not only definitions: who calls it, with what arguments, under what conditions.
- Say explicitly what you looked for and did not find.
- At most <N> words.

Answer format:
1. Findings (bullets, each with a citation).
2. Not found (what you searched for, where).
3. Surprises (anything that contradicts the Intent or common sense).
```

## Synthesis rules

- **Wait for all.** Do not draft conclusions while a subagent is still running; a late answer
  often reverses an early one.
- **Live code beats documents.** When an archived plan says one thing and the code does
  another, the code is the current state; the plan explains how it got there. Record both.
- **Disagreement means reading.** When two subagents contradict each other, open the disputed
  lines yourself and record which was right.
- **Surprises get verified.** Every item in a subagent's "Surprises" is checked by you before it
  enters research.md.
- **Absence is a finding.** "No test covers the retry path" or "no earlier change touched this"
  is worth a line; it saves the planner from searching again.
- **Connect, do not concatenate.** research.md is organised by the template sections, not by
  subagent. A finding from the flow tracer and one from the history miner about the same function
  belong in the same paragraph.
