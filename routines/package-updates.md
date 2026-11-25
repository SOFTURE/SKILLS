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
   release: not "the server is ready", not "the owner released yesterday", not "the change is tiny". For the same
   reason it never runs `wt-roadmap.py released <tag>`: settling the context after a release belongs to the session
   that saw that release through (WORKFLOW §5.2).
2. **One pull request at most.** If an open pull request from an earlier run already bumps packages, finish that one
   instead of opening another.
3. **Bump and fix, never skip.** A package whose upgrade breaks a gate is still bumped: the run adapts the project in
   the same pull request (code, config, messages, migrations, regenerated files) and adds tests that prove the
   adapted behaviour, each seen red without the fix. A package is held back only when the break is a defect in the
   package itself that the project could fix only by working around SOFTURE code (step 6), or when the owner must
   decide how existing data is treated (step 5).
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
- **Held packages:** `context/workflow.json` → `routines.packageUpdates.hold` lists `{ "package", "issue", "since" }`
  for a package defect (step 6) and `{ "package", "issue", "since", "owner" }` for a bump that waits for the owner's
  decision (step 5). A defect hold stays until its issue is closed **and** a published version contains the fix (check
  the release notes); an owner hold stays until its issue in this repository carries the owner's answer (closed, or
  the owner's word in a comment), and the bump then applies that answer. Remove the entry in the same pull request
  that bumps the package.
- **Owner steps of earlier bumps:** `routines.packageUpdates.ownerSteps` lists steps of merged bumps that wait for the
  owner (step 5). An entry with `confirmed` is settled: remove it in this run's pull request (or in none, when nothing
  else changes).
- **Everything current:** change nothing, open nothing, and go to step 7 (the report). A quiet night still reports.

### 3. Read before bumping

For every package that moves, read its release notes or changelog for each version crossed (SOFTURE/AI for the
`@softure-ai/*` packages, SOFTURE/SKILLS for `@softure-ai/skills`). Note breaking changes, migrations the package
brings, upgrade steps it asks of an adopting app, and re-runs of generators (`softure-deploy init`). Every step the
notes ask for is applied in this project. A break the notes do not explain is investigated, not skipped: find what
changed in the package (its source and tests at the new tag) and adapt the project to it (step 4); only a defect in
the package goes to step 6. A step the notes leave to the owner (a new secret, a variable, a data decision) goes to
step 5.

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
- **`autonomy.cockpitWake`:** this routine never writes `"routine"`, also when release notes ask a project to set
  the key: only the setup brief in `routines/cockpit-wake.md` writes it, after its test issue was claimed. A key
  that is already set stays as it is. When the key is missing, write `"none"` and record the owner step "set up
  the cockpit wake routine (routines/cockpit-wake.md → Setting it up)" in the same pull request: with a live
  roadmap a line under `## Owner decisions and checks`
  (`- [ ] Owner step: set up the cockpit wake routine (routines/cockpit-wake.md → Setting it up) (<YYYY-MM-DD>)`),
  with none an `ownerSteps` entry (step 5). An `autonomy` key that WORKFLOW §2 no longer lists is removed in the
  same pull request, with no note.
- **The `context-doctor` check run on the main branch** (WORKFLOW §12.2): check that the main branch's head has one
  (`gh api repos/<owner>/<repo>/commits/<mainBranch>/check-runs?check_name=context-doctor`; with a fine-grained
  token that cannot read check runs, the latest workflow runs of that head through the Actions API and their
  `context-doctor` job). When it has none, or the doctor or the installer reports `ci-doctor-trigger` (no `push`
  trigger for the main branch, a `paths`/`paths-ignore` filter, an `if:` on the job), fix the workflow in this same
  pull request: `on:` gets `pull_request` and `push` with `branches: [<mainBranch>]`, the filter and the condition go.
  This is a CI configuration fix, not SOFTURE code (hard rule 4); name it in the pull request body. After the merge,
  check that the new head of the main branch has the `context-doctor` check run and say so in the report.
- Apply what the release notes require (messages, exports, config, migrations, regenerated files), and fix every
  gate the bump turns red in the project itself, in this pull request.
- **Tests with every fix:** each adaptation gets a unit test (and an integration test where the behaviour is visible
  on the running app) that names the behaviour, fails without the fix and passes with it; record that red/green run
  in `## Progress`. A bump that changed nothing in the project's code needs no new test.
- Gates: every gate in `context/workflow.json` → `gates`, plus whatever the project's `AGENTS.md` adds for a
  dependency change; the language scan of the diff. Long commands run in the background with a long timeout.
- Pull request titled `chore(deps): bump SOFTURE packages (<YYYY-MM-DD>)`, its body listing every package from →
  to, held packages with their issue, and "No release, no deploy: this rides the next release the owner orders."
- Wait for green checks. When pull request events cannot reach the session, check the checks yourself every few
  minutes (a scheduled wake-up), for at most about 60 minutes. Merge on green through the project's merge path
  (`autonomy.merge`, `autonomy.remergeMain`); a red check you cannot fix within the rules leaves the pull request
  open and is named in the report.

### 5. A step only the owner can take

A bump that needs something only the owner can do (a new production secret, an environment or build-time variable,
an account, a decision about existing data) must reach the owner where the owner looks: the `owner_queue` of
`context/state.json`, which every dashboard reads. Wiring the step into compose files and deploy workflows is not
enough: without a record the next release fails at the secret check and nothing warned. Decide which applies:

- **Merge, with the step recorded**, when the code can adapt and only the owner's step is missing (for example a
  secret the deploy needs: the code, compose and the deploy workflow are wired, only the secret is missing). Record
  the step in the same pull request:
  - with a live roadmap (`context/foundation/roadmap.md`, the idle placeholder included): one line under
    `## Before the next release` (create it above `## Owner decisions and checks` if missing):
    `- [ ] Set the production secret SOFTURE_EMAIL_KEY_SECRET (@softure-ai/mailing 0.3.0, <YYYY-MM-DD>)`;
  - with no live roadmap: a cockpit-style issue in the project's repository (label `cockpit`, the step, the
    package and version, the gate it blocks; neutral text, no secret values), and the entry
    `{ "package", "version", "issue": "#N", "since", "step" }` in `routines.packageUpdates.ownerSteps`.
- **Hold, with an issue**, when the owner must choose how existing data is treated (a migration that rewrites or
  drops data, a changed default for records already stored). Leave the package on its version, file the same kind
  of issue in the project's repository with the choices, and add `{ "package", "issue": "#N", "since", "owner":
  "<the decision in one line>" }` to `routines.packageUpdates.hold`. The `owner` field marks the hold as owner work.

Every one of these is regenerated into `context/state.json` (`npx softure-skills state`) in the same pull request:
the `owner_queue` lists `## Before the next release` lines, `ownerSteps` entries and owner holds, with `kind:
"secret"` when the step names a secret, key, token or password (`SOFTURE_EMAIL_KEY_SECRET` included).

A step is settled once the owner confirms it (in the main chat, or a cockpit issue answering the entry's `id`,
WORKFLOW §8.6): the session that hears it ticks the roadmap line `— done: <the owner's word or #N>` or sets
`"confirmed": "<#N or YYYY-MM-DD>"` on the `ownerSteps` entry, and closes the issue; a release that ships the bump
settles a `## Before the next release` line as well (`wt-roadmap.py released`, never this routine). The routine
never confirms a step itself, and never sets or asks for a secret's value.

### 6. A defect in a package

Hold a package back only when the break is a defect in the package itself, not a change the project has to adapt
to: a bug the package's own tests should have caught, a missing export the release notes promise, a regression of
behaviour the package documents, or a new feature that forces changes on an app that does not use it and that the
project could undo only by patching or wrapping SOFTURE code. Then:

- leave that package on its current version, bump and fix the rest;
- file an issue right away in the repository that owns it (`@softure-ai/skills` → SOFTURE/SKILLS, every other
  `@softure-ai/*` package → SOFTURE/AI). Search for a duplicate first; an open one gets a comment with the new
  evidence. Neutral English text: "an adopting app", no project name, no addresses, no personal data; versions,
  the error and the steps to reproduce;
- add `{ "package", "issue", "since" }` to `routines.packageUpdates.hold` in the same pull request.

### 7. Report

Every run reports, also when nothing changed, in `chatLanguage`, times in `timezone`:

```markdown
**Package updates, <YYYY-MM-DD HH:MM>**

| Package | Was | Is | Note |
| --- | --- | --- | --- |
| @softure-ai/skills | 0.26.0 | 0.27.0 | bumped |
| @softure-ai/auth | 0.2.21 | 0.2.21 | current |
| @softure-ai/mailing | 0.2.8 | 0.3.0 | bumped; owner step: secret SOFTURE_EMAIL_KEY_SECRET |
| @softure-ai/billing | 0.3.2 | 0.3.2 | held: #41 (owner decision) |
| @softure-ai/storage | 0.1.4 | 0.1.4 | held: SOFTURE/AI#123 |

PR: #N (merge <sha>) | none
Issues: SOFTURE/AI#N, … | none
Doctor: 0 (check run on <mainBranch>: ok | failing | missing)
Decision: set the production secret SOFTURE_EMAIL_KEY_SECRET before the next release (Before the next release); #41: choose how existing invoices are treated | none
```

Translate the headers into `chatLanguage`. `Was` is the lockfile before, `Is` after. `Decision` names something
only the owner can settle, never a release (releases are not this routine's business): every open owner step from
step 5, this run's and earlier ones still waiting, by its exact step and where it is recorded (`Before the next
release`, the issue); an owner hold with its issue and the decision; a held package that blocks a feature; a red check
outside the routine's reach.

Post the report as the run's last message. In a hosted project with a coordinator, also send it to the coordinator's
session and ask for a one-line summary in the main chat; when that tool is missing, the last message is enough.
Create no artifacts, write to no dashboard. When a pull request is still open, say so; otherwise the run is done.
