# Example run: a booking app

A fictional repo, first run, interactive. Use it for the shape of the plan and the report.

## What detection read

- `pnpm-lock.yaml` -> install `pnpm install --frozen-lockfile`.
- `package.json` scripts: `typecheck: "tsc --noEmit"`, `lint: "eslint ."`, `test: "vitest run"`,
  `test:e2e: "playwright test"`, `stack:test: "docker compose -f docker/test.yml up -d && playwright test; docker compose -f docker/test.yml down"`,
  `db:generate: "drizzle-kit generate"`.
- `origin/HEAD` -> `origin/main`.
- `drizzle/` with `0000_init.sql` ... `0014_slots_index.sql`.
- `.env` present.
- `docs/` with `architecture.md` and `docs/adr/` with 6 ADRs. No PRD.
- `context/` does not exist.

## Plan shown before writing

```text
context/
  workflow.json              create
  foundation/README.md       create
  foundation/lessons.md      create
  changes/README.md          create
  archive/README.md          create
  backlog/README.md          create
```

```json
{
  "language": "en",
  "mainBranch": "main",
  "gates": {
    "typecheck": "pnpm typecheck",
    "lint": "pnpm lint",
    "test": "pnpm test"
  },
  "integration": { "local": "pnpm stack:test", "remote": null },
  "migrations": {
    "dir": "drizzle",
    "pattern": "^[0-9]{4}_.*\\.sql$",
    "regenerate": "pnpm db:generate"
  },
  "worktree": {
    "setup": ["pnpm install --frozen-lockfile", "cp ../{repo}/.env .env"],
    "maxParallel": 4
  },
  "release": { "owner": true },
  "research": { "sources": ["docs/architecture.md", "docs/adr/"] }
}
```

```text
read:     gates.*, migrations.dir, mainBranch (origin/HEAD)
inferred: integration.local -> stack:test (brings up its own stack; test:e2e expects a running app)
          migrations.pattern -> from 15 existing file names
Optional keys you may want: timezone, integration.cadence, worktree.cloudState, install.

Create this? (Recommended: yes)  [yes / edit a value / cancel]
```

## Report after writing

```text
context/workflow.json            created
context/foundation/README.md     created
context/foundation/lessons.md    created
context/changes/README.md        created
context/archive/README.md        created
context/backlog/README.md        created

Unresolved: integration.remote (no CI script found; set it if the suite runs on CI).
Inferred:
- integration.local -> pnpm stack:test (starts and stops its own stack; test:e2e needs a running app)
- migrations.pattern -> ^[0-9]{4}_.*\.sql$ (all 15 files in drizzle/ match)

Next: softure-shape for a new product or theme, or softure-new <change-id> for one concrete change.
```

## Second run, same repo

```text
context/workflow.json            present
context/foundation/README.md     present
...
Nothing to do.
```

## Second run after someone deleted `research` from workflow.json

```text
context/workflow.json            merged: research.sources
```

Only the missing key is added; `gates`, `integration` and every other existing value stay
exactly as the owner left them, including any key init does not know.
