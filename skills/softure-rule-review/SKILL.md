---
name: softure-rule-review
description: >
  Audit the instructions agents follow in this repo (AGENTS.md, CLAUDE.md, nested rule
  files, .cursor/rules, copilot instructions, project skills under .claude/skills,
  context/foundation/lessons.md) for contradictions, stale paths and commands, duplication,
  vague or untestable rules and bloat. Scores each rule file on a five-point scorecard
  (length, inline snippets, precise language, redundant knowledge, rule ordering), proposes
  concrete edits with path:line and applies them on approval. Use when the user says "audit
  the rules", "review AGENTS.md", "check my CLAUDE.md", "score our agent instructions", "are
  our instructions consistent", "clean up the rules".
argument-hint: "[<path>...] [--apply] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
  - AskUserQuestion
---

# softure-rule-review: instructions that agree with each other and with the repo

Agents follow written rules literally. A stale command wastes a session, two rules that
contradict each other make behaviour random, and a long file full of things the model already
knows buries the few rules that matter. This skill keeps the rule set small, true, consistent
and well ordered. It reviews the rule file as an artifact for agents, not the project's
architecture.

## Inputs

Default set, when no paths are given:
- `AGENTS.md`, `CLAUDE.md` (root and nested), `.cursor/rules/**`, `.github/copilot-instructions.md`,
  `.windsurfrules` and other rule files for agents;
- `.claude/skills/*/SKILL.md` **owned by the project**. Skills installed by a package (listed in
  `.claude/softure-skills.json` or another manifest) are not edited here. Report issues with them
  upstream instead.
- `context/foundation/lessons.md` and `context/workflow.json`.

With paths: a file is reviewed as given; a directory or glob expands to its rule files, each
scored separately (never merged into one score); a path that does not exist is reported and
skipped, never guessed at. Read every file fully, in chunks if it is long.

The SOFTURE managed block (`<!-- softure-skills:begin … -->`) is read for contradictions but
never edited or scored. A conflict with it is resolved in the project's own text, or reported
upstream.

## Procedure

1. **Inventory.** Build a table of every rule: id (file:line), the rule in five words, its
   scope (paths and activities) and its strength (must / should / prefer).
2. **Verify facts against the repo.** Every path, script, command, env var and skill name
   mentioned must exist:
   - `ls` paths;
   - check that `npm run <x>` exists in package.json;
   - grep for symbols;
   - check that referenced skills are installed;
   - check that workflow.json commands exist.

   A missing target is a **Stale** finding.
3. **Find contradictions.** Look for pairs of rules with the same scope that demand different
   things. Typical cases:
   - "always X" vs. "never X when Y" with Y unstated;
   - a lesson that reverses an AGENTS.md rule;
   - a skill that tells the agent to commit while AGENTS.md forbids it.

   Name the winner by the priority: project > managed block > skill defaults, and newer lesson >
   older rule with the same scope.
4. **Find duplication.** The same rule stated in several places with drifting wording. Keep one
   canonical place and replace the rest with a pointer.
5. **Score each rule file** on the five checks below. Thresholds, the tests for redundancy, and
   the grounded-replacement method: read `references/scorecard.md` **before scoring**.

   | # | Check | What it catches |
   |---|---|---|
   | 1 | Length | files so long that rules in the middle lose attention |
   | 2 | Inline snippets | copied code or config that will drift from the real file |
   | 3 | Precise language | rules no diff can be checked against ("write clean code") |
   | 4 | Redundant knowledge | framework defaults, definitions, tutorial text, copies of README |
   | 5 | Rule ordering | critical rules buried in the middle, intro text at the top |

   Each check gets OK / WARN / FAIL and a count. Vague rules (check 3) always get a concrete,
   testable rewrite grounded in this project; label a rewrite **(assumed)** when the repo gives no
   signal. Deleting a vague rule is right only when check 4 also flags it.
6. **Find bloat.** Incident narratives, history, outdated rationale, and rules about code that
   no longer exists. Prefer moving the history to an archive file over deleting it, so the rule
   itself stays one or two lines. A rule that looks generic but exists because of a real
   incident stays; ask for a one-line pointer to the incident (a lesson number) so the next audit
   does not delete it.
7. **Find enforcement candidates.** Rules that a test, lint rule or database constraint could
   enforce. List them with the proposed mechanism.
8. **Propose the order** (only when check 5 is WARN or FAIL). List the current headings with
   line numbers, tag each section (CRITICAL, USEFUL, INTRO, REDUNDANT, VAGUE, REFERENCE), state
   the structural problem in one paragraph, and propose a target order as moves (to top / kept /
   to bottom / removed), never as a rewrite of rule text.
9. **Report** (template below), with **Top 3 actions** ordered by leverage across all checks,
   not by check number.
10. **Apply on approval** (interactive). Ask one question per group, recommendation first:
    - contradictions and stale references: apply all / pick / leave in the report;
    - reorder (when proposed): reorder now / lift only the CRITICAL rules to the top / show the
      reordered file first / leave in the report.

    A reorder moves headings and their blocks only; every byte of rule text survives. Show
    proposed edits as diffs before writing. With `--apply`, apply what `--auto` applies.
11. **Remind** at the end of every run: change rules one structural edit at a time (reorder,
    then split, then dedupe), and run one representative agent task after each. Rule edits change
    behaviour only in the next session, and bundled edits make any shift impossible to attribute.

Edge cases (short files, reference-heavy files, `.mdc` frontmatter, generated stubs, root and
nested files that overlap): see the end of `references/scorecard.md`.

## Output

Written in `workflow.json` -> `language`; headings stay English.

```markdown
# Rule review: <date>

Files: N · Rules: M · Stale: a · Contradictions: b · Duplicates: c · Vague: d · Bloat: e

## Scorecard
| File | Length | Snippets | Precise language | Redundant | Ordering |
|---|---|---|---|---|---|
| AGENTS.md | WARN (312 lines) | OK (0) | FAIL (5) | WARN (3) | FAIL (hard rules at line 240) |

## Top 3 actions
1. …

## Contradictions (fix first)
1. AGENTS.md:40 "…" vs lessons.md L-017 "…". Same scope: <scope>. Winner: L-017 (newer, specific).
   Edit: replace AGENTS.md:40 with "…".

## Stale references
1. AGENTS.md:88 `npm run db:fresh`: script does not exist. Edit: `npm run db:reset`.

## Duplicates
## Vague -> sharpened (path:line "phrase" -> "testable rewrite")
## Redundant knowledge (path:line -> delete | pointer | keep with incident)
## Inline snippets (path:line-range -> pointer to the real file)
## Ordering (current order, tags, proposed moves)
## Bloat
## Could be enforced by tooling
## Proposed edits (unified diff per file)
```

A check that is OK gets one line in its section and nothing more. A complete example report
on a fictional repo: `references/example-report.md`, read it **before writing your first report
in a repo**.

## --auto

Apply only edits that cannot change behaviour:
- fixing stale paths to their verified current location;
- removing exact duplicates and leaving a pointer;
- trimming narrative history into an archive file.

Contradictions, vague rules, redundant-knowledge deletions and reordering are reported, not
applied, because they need the owner's intent and a reorder changes what agents attend to.
Record each skipped group under `## Decisions (auto)` in the report. Commit applied edits as
`docs(rules): rule review <date>` only when inside a change or when asked.

## Checklist

- [ ] Every referenced path, script and skill verified against the repo.
- [ ] Every contradiction has a named winner and a concrete edit.
- [ ] Every rule file has a scorecard row; each vague phrase has a grounded rewrite.
- [ ] Top 3 actions ordered by leverage.
- [ ] Package-managed blocks and skills untouched.
- [ ] Proposed edits shown as diffs before applying (interactive).

## Anti-patterns

- Adding new rules during an audit. This skill subtracts and sharpens.
- Rewording everything into a new style. Only change what is wrong.
- "Just delete it" for a vague rule: the author meant something; translate it.
- Generic rewrites ("follow SOLID") that are as uncheckable as the original.
- Deleting a lesson's history without keeping its rule and number.
- Editing installed skills locally. The next install overwrites the edit.
- Several structural edits in one go, with no task run in between.

## Handoff

New rules that emerged from the audit go through `softure-lesson`. Upstream issues with
SOFTURE skills or the managed block are filed at https://github.com/SOFTURE/SKILLS.
