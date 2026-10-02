---
name: softure-rule-review
description: >
  Audit the instructions agents follow in this repo (AGENTS.md, CLAUDE.md, nested rule
  files, project skills under .claude/skills, context/foundation/lessons.md) for
  contradictions, stale paths and commands, duplication, vague or untestable rules and bloat.
  Produces a report with concrete edits and applies them on approval. Use when the user says
  "audit the rules", "review AGENTS.md", "are our instructions consistent", "clean up the
  rules", "audit AGENTS.md".
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

Agents follow written rules literally. A stale command wastes a session, and two rules that
contradict each other make behaviour random. This skill keeps the rule set small, true and
consistent.

## Inputs

Default set, when no paths are given:
- `AGENTS.md`, `CLAUDE.md` (root and nested), `.cursor/rules/**`, `.github/copilot-instructions.md`;
- `.claude/skills/*/SKILL.md` **owned by the project**. Skills installed by a package (listed in
  `.claude/softure-skills.json` or another manifest) are not edited here. Report issues with them
  upstream instead.
- `context/foundation/lessons.md` and `context/workflow.json`.

The SOFTURE managed block (`<!-- softure-skills:begin … -->`) is read for contradictions but
never edited. A conflict with it is resolved in the project's own text, or reported upstream.

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
5. **Find vague rules.** A rule an agent cannot check ("write clean code", "be careful with X")
   is either sharpened into something testable or deleted.
6. **Find bloat.** Incident narratives, history, outdated rationale, and rules about code that
   no longer exists. Prefer moving the history to an archive file over deleting it, so the rule
   itself stays one or two lines.
7. **Find enforcement candidates.** Rules that a test, lint rule or database constraint could
   enforce. List them with the proposed mechanism.
8. **Report** (template below). Interactive: ask which groups to apply. With `--apply`, apply all
   non-controversial ones (see --auto).

## Output

```markdown
# Rule review: <date>

Files: N · Rules: M · Stale: a · Contradictions: b · Duplicates: c · Vague: d · Bloat: e

## Contradictions (fix first)
1. AGENTS.md:40 "…" vs lessons.md L-017 "…". Same scope: <scope>. Winner: L-017 (newer, specific).
   Edit: replace AGENTS.md:40 with "…".

## Stale references
1. AGENTS.md:88 `npm run db:fresh`: script does not exist. Edit: `npm run db:reset`.

## Duplicates
## Vague → sharpened or removed
## Bloat
## Could be enforced by tooling
## Proposed edits (unified diff per file)
```

## --auto

Apply only edits that cannot change behaviour:
- fixing stale paths to their verified current location;
- removing exact duplicates and leaving a pointer;
- trimming narrative history into an archive file.

Contradictions and vague rules are reported, not applied, because they need the owner's
intent. Commit applied edits as `docs(rules): rule review <date>` only when inside a change or
when asked.

## Checklist

- [ ] Every referenced path, script and skill verified against the repo.
- [ ] Every contradiction has a named winner and a concrete edit.
- [ ] Package-managed blocks and skills untouched.
- [ ] Proposed edits shown as diffs before applying (interactive).

## Anti-patterns

- Adding new rules during an audit. This skill subtracts and sharpens.
- Rewording everything into a new style. Only change what is wrong.
- Deleting a lesson's history without keeping its rule and number.
- Editing installed skills locally. The next install overwrites the edit.

## Handoff

New rules that emerged from the audit go through `softure-lesson`. Upstream issues with
SOFTURE skills or the managed block are filed at https://github.com/SOFTURE/SKILLS.
