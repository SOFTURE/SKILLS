---
name: softure-init
description: >
  Scaffold the SOFTURE workflow in a repository: create the `context/` tree and a
  `context/workflow.json` filled in by detecting the stack (package manager, scripts,
  default branch, migrations directory). Idempotent, never overwrites existing files.
  Use once per repo before any other softure-* skill, or when a skill reports a missing
  `context/workflow.json`. Triggers: "init the workflow", "set up context", "softure init",
  "prepare the repo for the skills".
argument-hint: "[--language pl|en] [--dry-run] [--auto]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Bash
  - AskUserQuestion
---

# softure-init: scaffold the workflow in a repository

## Purpose

Every other `softure-*` skill reads `context/workflow.json` and writes under `context/`.
This skill creates that ground once, with values detected from the repository rather than
guessed. Contract: `WORKFLOW.md` §2 and §3 of the `@softure-ai/skills` package.

## Inputs

- A git repository (the working directory or the path given). If it is not a git repo, say
  so and stop. Do not run `git init` on your own.
- Nothing else is required.

## Procedure

1. **Inventory what exists.** List `context/` recursively, if present. Record each file that
   already exists. You will not touch these, apart from adding missing keys to
   `workflow.json` (step 5).
2. **Detect the stack.** Read these, and only these, to fill the config:
   - `package.json` → `scripts`. Map the gates:
     - typecheck: the script that runs `tsc`, otherwise `npx tsc --noEmit` when `tsconfig.json` exists.
     - lint: `lint`.
     - test: `test` (unit only, never the e2e script).
     - integration: a script whose name contains `integration`, `e2e` or `playwright`, preferring one that brings up its own stack.
   - Package manager, from the lockfile: `package-lock.json` → `npm ci`, `pnpm-lock.yaml` →
     `pnpm install --frozen-lockfile`, `yarn.lock` → `yarn install --immutable`,
     `bun.lockb`/`bun.lock` → `bun install --frozen-lockfile`.
   - Non-JS stacks: `*.sln`/`*.csproj` → `dotnet build` / `dotnet test`; `pyproject.toml` →
     `ruff check` / `pytest`; `go.mod` → `go vet ./...` / `go test ./...`. Use them only if the
     tool's config is actually present.
   - Main branch: `git symbolic-ref refs/remotes/origin/HEAD`, falling back to whichever of
     `main`/`master` exists locally.
   - Migrations: look for `drizzle/`, `migrations/`, `prisma/migrations/`, `db/migrate/` and
     `supabase/migrations/`, and infer the file pattern from the existing names. For drizzle,
     `regenerate` is the script that calls `drizzle-kit generate`.
   - `.env` present → add `cp ../{repo}/.env .env` to `worktree.setup`.
3. **Pick the language.** Use `--language` when given. Otherwise use the language of the
   existing docs/README; if mixed, use the language the user is writing in. In `--auto`
   without a signal, use `en`.
4. **Show the plan.** Without `--auto`, print the proposed tree and the full `workflow.json`,
   then ask one question: "Create this? (Recommended: yes)". Offer the options yes / edit a
   value / cancel. In `--auto`, skip the question.
5. **Write only what is missing:**
   - `context/workflow.json`: new file, or only the missing keys merged into an existing one.
     Never change an existing value.
   - `context/foundation/` with an empty `lessons.md` (`# Lessons` + one sentence explaining
     the format, WORKFLOW §7).
   - `context/changes/README.md`, `context/archive/README.md`, `context/backlog/README.md`
     (templates below).
   - Do **not** create `shape-notes.md`, `prd.md` or `roadmap.md`. Their skills do that.
6. **Verify.** Re-read `workflow.json` and check that it parses as JSON. For every gate
   command, check that the referenced script exists in `package.json` (or that the binary is
   on PATH). Mark any gate you could not resolve as `null`, never as a guess.
7. **Report:** created, skipped (already existed) and unresolved values, plus the next step.

## `workflow.json` template

```json
{
  "language": "en",
  "mainBranch": "main",
  "gates": { "typecheck": null, "lint": null, "test": null },
  "integration": { "local": null, "remote": null },
  "migrations": null,
  "worktree": { "setup": [], "maxParallel": 4 },
  "release": { "owner": true }
}
```

`migrations` is either `null` or `{ "dir", "pattern", "regenerate" }`. Keep `release.owner: true`
unless the user explicitly says otherwise. Skills never release or deploy on their own.

## README templates

`context/changes/README.md`:

```markdown
# Changes in flight
One folder per change: `changes/<change-id>/`, identified by `change.md`.
Created by `softure-new`, closed by `softure-archive` (moved to `archive/`).
Execution state lives only in `plan.md` → `## Progress`.
```

`context/archive/README.md`: one paragraph saying that folders are `<created-date>-<change-id>`
and are read-only history.

`context/backlog/README.md`: one paragraph saying that ideas not yet on the roadmap live here
as free-form notes, and `softure-roadmap` pulls them in.

## `--auto`

Detect, write and report without asking. Record every value you inferred (rather than read
directly) in the report, e.g. `- mainBranch → master (origin/HEAD missing; local master exists)`.

## Quality bar

- [ ] Running the skill twice changes nothing the second time.
- [ ] No existing file is overwritten. `workflow.json` only gains keys.
- [ ] Every gate in `workflow.json` points at something that exists, or is `null`.
- [ ] The report lists the unresolved values the owner should fill in.

## Do not

- Do not invent commands. A wrong gate is worse than `null`.
- Do not write roadmap, PRD or change folders.
- Do not commit. Leave that to the user or to the calling orchestrator.

## Handoff

New product or theme → `softure-shape`. An existing PRD that needs slicing → `softure-roadmap`.
A single concrete change → `softure-new`.
