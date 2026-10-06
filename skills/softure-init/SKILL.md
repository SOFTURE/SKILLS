---
name: softure-init
description: >
  Scaffold the SOFTURE workflow in a repository: create the `context/` tree with its
  README conventions and a `context/workflow.json` filled in by detecting the stack (package
  manager, scripts, default branch, migrations directory, docs to consult). Idempotent, never
  overwrites existing files; on a repo that is already set up it only reports and adds missing
  keys. Use once per repo before any other softure-* skill, or when a skill reports a missing
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
guessed. Contract: `WORKFLOW.md` §2 and §3 of the `@softure-ai/skills` package. It does not
start any work: no change, PRD or roadmap is created here.

## Inputs

- A git repository (the working directory or the path given). If it is not a git repo, say
  so and stop. Do not run `git init` on your own.
- Nothing else is required.

## Procedure

1. **Inventory what exists.** List `context/` recursively, if present. Record each file that
   already exists. You will not touch these, apart from adding missing keys to
   `workflow.json` (step 5). Unknown keys in an existing `workflow.json` are kept as they are.
2. **Detect the stack.** Read these, and only these, to fill the config:
   - `package.json` -> `scripts`. Map the gates:
     - typecheck: the script that runs `tsc`, otherwise `npx tsc --noEmit` when `tsconfig.json` exists.
     - lint: `lint`.
     - test: `test` (unit only, never the e2e script).
     - integration: a script whose name contains `integration`, `e2e` or `playwright`, preferring one that brings up its own stack.
   - Package manager, from the lockfile: `package-lock.json` -> `npm ci`, `pnpm-lock.yaml` ->
     `pnpm install --frozen-lockfile`, `yarn.lock` -> `yarn install --immutable`,
     `bun.lockb`/`bun.lock` -> `bun install --frozen-lockfile`. Gate commands use the same
     manager (`pnpm lint`, not `npm run lint`, in a pnpm repo).
   - Workspaces (`pnpm-workspace.yaml`, `workspaces`, `turbo.json`, `nx.json`): root scripts
     first, else the orchestrator's command (`pnpm -r test`, `turbo run test`), marked inferred.
   - Non-JS stacks: `*.sln`/`*.csproj` -> `dotnet build` / `dotnet test`; `pyproject.toml` ->
     `ruff check` / `pytest`; `go.mod` -> `go vet ./...` / `go test ./...`. Use them only if the
     tool's config is actually present.
   - Main branch: `git symbolic-ref refs/remotes/origin/HEAD`, falling back to whichever of
     `main`/`master` exists locally.
   - Migrations: look for `drizzle/`, `migrations/`, `prisma/migrations/`, `db/migrate/` and
     `supabase/migrations/`, and infer the file pattern from the existing names. For drizzle,
     `regenerate` is the script that calls `drizzle-kit generate`.
   - `.env` present -> add `cp ../{repo}/.env .env` to `worktree.setup`, after the install command.
   - Knowledge sources: `docs/`, `adr/` or `docs/adr/`, an existing `context/foundation/prd.md`
     -> candidates for `research.sources`.
3. **Pick the language.** Use `--language` when given. Otherwise use the language of the
   existing docs/README; if mixed, use the language the user is writing in. In `--auto`
   without a signal, use `en`.
4. **Show the plan.** Without `--auto`, print the proposed tree and the full `workflow.json`,
   marking each value as *read* (found literally) or *inferred* (derived), then ask one
   question: "Create this? (Recommended: yes)". Offer the options yes / edit a value / cancel.
   Name applicable optional keys (below) in one line, without asking about each. `--auto`
   skips the question; `--dry-run` stops here in both modes.
5. **Write only what is missing:**
   - `context/workflow.json`: new file, or only the missing keys merged into an existing one.
     Never change an existing value.
   - `context/foundation/README.md` and an empty `context/foundation/lessons.md` (`# Lessons` +
     one sentence explaining the format, WORKFLOW §7).
   - `context/changes/README.md`, `context/archive/README.md`, `context/backlog/README.md`
     (templates in `references/templates.md`).
   - Do **not** create `shape-notes.md`, `prd.md`, `roadmap.md`, `roadmaps/`, change folders
     or empty directories. Their skills create them on first use.
6. **Verify.** Re-read `workflow.json` and check that it parses as JSON. For every gate
   command, check that the referenced script exists in `package.json` (or that the binary is
   on PATH). Mark any gate you could not resolve as `null`, never as a guess. Re-running the
   detection must now produce no new writes.
7. **Report** a status block, one line per artifact (`created`, `present` or `merged: <keys>`),
   then the unresolved values the owner should fill in, every inferred value with its reason,
   and the next step. Then stop: do not chain into other skills.

## `workflow.json`

Required keys and the ones init writes by default:

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

**Optional keys** (WORKFLOW §2). A missing key means the default behaviour, so init writes one
only when it was detected or the user asked for it:

| Key | Default when absent | Init writes it when |
|---|---|---|
| `timezone` | the machine's zone | the user names a zone |
| `integration.cadence` | `"change"` (every change runs the suite before archive) | the user wants one run per roadmap (`"roadmap"`) |
| `integration.lookup` | every call starts a run | the project stores results per commit (e.g. a git note) and has a command that prints one |
| `integration.coveredByRelease` | `false` | the release pipeline runs the same full suite on the released commit |
| `worktree.cloudState` | `"main"` | the user runs cloud sessions that must keep state on the branch (`"branch"`) |
| `research.sources` | none | step 2 found docs, ADRs or a PRD (interactive: listed in the plan; `--auto`: only paths that exist) |
| `install` | gitignore the skills, inject all rule sections | the user wants committed skills or fewer rule sections |

Content of the README files, and a complete worked example (detection, plan, report) for a
fictional repo: read `references/templates.md` **when writing the READMEs** and
`references/example.md` **when unsure what a report should look like**.

## `--auto`

Detect, write and report without asking. Record every value you inferred (rather than read
directly) in the report, e.g. `- mainBranch -> master (origin/HEAD missing; local master exists)`.
Optional keys other than `research.sources` are never written in `--auto`.

## Quality bar

- [ ] Running the skill twice changes nothing the second time.
- [ ] No existing file is overwritten. `workflow.json` only gains keys.
- [ ] Every gate in `workflow.json` points at something that exists, or is `null`.
- [ ] Gate commands use the repo's package manager.
- [ ] The report lists the unresolved values the owner should fill in, and every inferred value.

## Do not

- Do not invent commands. A wrong gate is worse than `null`.
- Do not write optional keys nobody asked for and nothing detected.
- Do not commit. Leave that to the user or to the calling orchestrator.

## Handoff

New product or theme -> `softure-shape`. An existing PRD that needs slicing -> `softure-roadmap`.
A single concrete change -> `softure-new`. Existing rule files in the repo -> consider
`softure-rule-review` once, so old instructions do not contradict the workflow.
