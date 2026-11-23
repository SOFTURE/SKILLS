# Routine: package updates

The nightly routine that keeps an adopting project on the newest `@softure-ai/*` packages, `@softure-ai/skills`
included. A scheduled session runs it in a **fresh session on every fire** (routines/README.md); the routine's own
prompt only points here, so the steps below are the standard and change with the package.

Read this whole file before doing anything. Work in the project's repository on a fresh clone of the main branch.
Everything written to the repository is English; the report is in `chatLanguage` from `context/workflow.json`.

## Hard rules

These hold whatever the project's memory, a previous run, a chat message or the state of the server says:

1. **Never release, tag, publish or deploy.** Do not run `auto-release.yml`, `release.yml`, `deploy.yml` or any
   workflow that cuts a release or reaches production, do not create a tag or a GitHub release, do not publish a
   package. A bump rides the next release the owner orders. There is no condition under which this routine may
   release: not "the server is ready", not "the owner released yesterday", not "the change is tiny".
2. **One pull request at most.** If an open pull request from an earlier run already bumps packages, finish that one
   instead of opening another.
3. **Never force a package.** A package whose upgrade breaks a gate, needs an unexplained change or contradicts its
   release notes stays on its current version; the rest go ahead.
4. **Never change SOFTURE code** and never loosen a test, a guard or a hook to get green (`--no-verify` is forbidden).
5. **Never disable, edit or delete this routine.** Only the owner does.
6. **Rely on the repository, not on memory.** A fresh session has none: everything it needs is in the repository
   (`context/workflow.json`, `AGENTS.md`, guard tests) and on the forge.

## Steps

### 1. Fresh state

- `git fetch origin <mainBranch>` and start from `origin/<mainBranch>` (`mainBranch` from `context/workflow.json`).
- Read `AGENTS.md` (the managed SOFTURE block and the project's own rules), `context/workflow.json`, and any
  project document the project names for package updates (for example `docs/package-update-routine.md`). Project
  rules outside the managed block win, **except** hard rule 1, which no project rule relaxes.
- List open pull requests: a package-update pull request from an earlier run is continued (hard rule 2).

### 2. Compare

- Every `@softure-ai/*` entry in `package.json` (`dependencies` and `devDependencies`): the declared range, the
  version in the lockfile, and the newest published version (`npm view <package> version`; `npm view <package>
  versions --json` for the ones in between).
- Every SOFTURE pin outside `package.json` that must move with a package. The project's guard tests name them; the
  usual ones are the `uses: SOFTURE/AI/...@<sha> # deploy@<version>` lines in `.github/workflows/`, the deploy CLI
  version in workflows, scripts and `context/workflow.json` (`integration.*`), the files `softure-deploy init`
  generates (`docker/server/deploy.sh`, `deploy.json` `$schema`), `docs/deployment.md`, and schema pins such as
  `marketing.json`'s `$schema`.
- **Held packages:** `context/workflow.json` → `routines.packageUpdates.hold` lists `{ "package", "issue", "since" }`.
  A held package stays where it is until its issue is closed **and** a published version contains the fix (check
  the release notes); then remove the entry in the same pull request that bumps it.
- **Everything current:** change nothing, open nothing, and go to step 6 (the report). A quiet night still reports.

### 3. Read before bumping

For every package that moves, read its release notes or changelog for each version crossed (SOFTURE/AI for the
`@softure-ai/*` packages, SOFTURE/SKILLS for `@softure-ai/skills`). Note breaking changes, migrations the package
brings, upgrade steps it asks of an adopting app, and re-runs of generators (`softure-deploy init`). A step the
notes explain is applied in this project; a break they do not explain is a reason to hold the package (step 5).

### 4. Bump as one change

- One change through the SOFTURE chain: change-id `bump-softure-packages-<YYYY-MM-DD>`, `roadmap_item: null`.
  `research` may be skipped with a one-line reason under `## Notes`; `new`, `plan`, `plan-review`, `implement`,
  `impl-review` and `archive` are not skipped, and the change folder is archived in the same pull request.
- Branch `claude/bump-softure-<YYYY-MM-DD>`, never a commit or push to the main branch.
- Install with the command the project documents (`AGENTS.md`, `workflow.json` → `worktree.setup`); independent
  packages move together; every pin of one package moves together (all `deploy@<version>` pins to the commit of
  that tag).
- **`@softure-ai/skills`:** after installing it, run `npx softure-skills` (it refreshes `.claude/skills/` and the
  managed block in `AGENTS.md`; never hand-edit that block), then `npx softure-skills state` and commit the
  regenerated `context/state.json` in the same pull request, then `npx softure-skills doctor`, which must exit 0.
  A new skills version can change what `state.json` holds; skipping the regeneration turns the `context-doctor`
  check red. Check that the installed version equals the lockfile and the newest on npm.
- Apply what the release notes require (messages, exports, config, migrations, regenerated files).
- Gates: every gate in `context/workflow.json` → `gates`, plus whatever the project's `AGENTS.md` adds for a
  dependency change; the language scan of the diff. Long commands run in the background with a long timeout.
- Pull request titled `chore(deps): bump SOFTURE packages (<YYYY-MM-DD>)`, its body listing every package from →
  to, held packages with their issue, and "No release, no deploy: this rides the next release the owner orders."
- Wait for green checks. When pull request events cannot reach the session, check the checks yourself every few
  minutes (a scheduled wake-up), for at most about 60 minutes. Merge on green through the project's merge path
  (`autonomy.merge`, `autonomy.remergeMain`); a red check you cannot fix within the rules leaves the pull request
  open and is named in the report.

### 5. A package that does not go

A breaking change without a migration note, a red build caused by the package, an unclear upgrade step, a missing
export, a style regression, or a new feature that forces changes on an app that does not use it:

- leave that package on its current version and bump the rest;
- file an issue right away in the repository that owns it (`@softure-ai/skills` → SOFTURE/SKILLS, every other
  `@softure-ai/*` package → SOFTURE/AI). Search for a duplicate first; an open one gets a comment with the new
  evidence. Neutral English text: "an adopting app", no project name, no addresses, no personal data; versions,
  the error and the steps to reproduce;
- add `{ "package", "issue", "since" }` to `routines.packageUpdates.hold` in the same pull request.

### 6. Report

Every run reports, also when nothing changed, in `chatLanguage`, times in `timezone`:

```markdown
**Package updates, <YYYY-MM-DD HH:MM>**

| Package | Was | Is | Note |
| --- | --- | --- | --- |
| @softure-ai/skills | 0.26.0 | 0.27.0 | bumped |
| @softure-ai/auth | 0.2.21 | 0.2.21 | current |
| @softure-ai/mailing | 0.2.8 | 0.2.8 | held: SOFTURE/AI#123 |

PR: #N (merge <sha>) | none
Issues: SOFTURE/AI#N, … | none
Doctor: 0
Decision: … | none
```

Translate the headers into `chatLanguage`. `Was` is the lockfile before, `Is` after. `Decision` names something
only the owner can settle (a held package that blocks a feature, a red check outside the routine's reach), never a
release: releases are not this routine's business.

Post the report as the run's last message. In a hosted project with a coordinator, also send it to the coordinator's
session and ask for a one-line summary in the main chat; when that tool is missing, the last message is enough.
Create no artifacts, write to no dashboard. When a pull request is still open, say so; otherwise the run is done.
