# SOFTURE SKILLS

Agent skills (Claude Code and other `SKILL.md` agents) for building software in a
spec-driven chain: every step leaves a durable artifact the next one reads, and two
orchestrators run whole roadmaps in parallel git worktrees.

Package: [`@softure-ai/skills`](https://www.npmjs.com/package/@softure-ai/skills) · License: MIT ·
Sister repos: [SOFTURE/AI](https://github.com/SOFTURE/AI) (app modules `@softure-ai/*`),
[COMMON](https://github.com/SOFTURE/COMMON), [API](https://github.com/SOFTURE/API).

## Install

```bash
npm i -D @softure-ai/skills          # postinstall copies skills into .claude/skills/
# or, without adding a dependency:
npx @softure-ai/skills
```

What the installer does (idempotent; re-run on every `npm install`):

| Artifact | Destination |
|---|---|
| `skills/softure-*` | `.claude/skills/softure-*/` |
| `rules/AGENTS.md` | managed block in `AGENTS.md` (or `CLAUDE.md` if only that exists) |
| ignore entries | managed block in `.gitignore`: installed skills are restored by `npm install`, not committed |
| manifest | `.claude/softure-skills.json` |
| label `cockpit` | created on the forge when an authenticated `gh` can (outside CI); otherwise the command is printed |

It never overwrites a skill folder it did not install. Flags: `--dry-run`, `--target <dir>`,
`--no-gitignore` (commit the skills instead).

**CI job.** Run the doctor in a CI job named `context-doctor`, on `pull_request` and on `push` to the main
branch, with no paths filter and no condition, so documentation-only changes are checked too (in a project that already has history, once the rollout below
brings the doctor to zero). Keep that name: outside readers (`portfolio --source api`, an aggregator) look for
the `context-doctor` check run on the main branch's head. In GitHub Actions the doctor writes its failure codes on
that check run (the annotation `context-doctor failure codes`, then one per failure), as one plain line of the job's
log (`context-doctor failure codes: <code> (<count>), ...`) and in the job summary, so a reader gets the codes through
the forge API without a checkout, with Actions: read alone when a fine-grained token cannot read check runs.

```yaml
on:
  pull_request:
  push:
    branches: [main]  # your mainBranch

jobs:
  context-doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx --yes --package @softure-ai/skills@<version> softure-skills doctor
        env:
          npm_config_ignore_scripts: "true"
```

It fails on drift in `context/` (a roadmap left after its archive, archived changes not stamped,
`## Summary` placeholders, a stale `context/state.json`, …; WORKFLOW §12) and on a `context-doctor` job that
misses pushes to the main branch (`ci-doctor-trigger`: no `push` trigger for it, a paths filter, an `if:`; without
the push trigger the main branch's head has no check run to read). The installer prints the workflow until one runs
the doctor, asks to rename a job that runs it under another name, and prints the `on:` block while the trigger is
incomplete. `npx softure-skills state` regenerates `context/state.json`, which the
scripts otherwise write themselves. When nothing names the project, its first run (and the installer) writes the
repository name into `context/workflow.json` → `project`, so the name no longer depends on how the repository was cloned.

**Rolling out to an existing project** (WORKFLOW §12.4). A project that adopted the package earlier
usually fails on history. Put it right, in this order, one pass per repository:

1. `npx softure-skills doctor --fix`, then `--fix --write`: the mechanical repairs (archived change
   statuses, with the old value kept as `legacy_status`; archive index links to moved files). Commit.
2. `npx softure-skills doctor --sweep --json`, worked by an agent with the `softure-doctor` skill
   ("Sweep history to zero"): every entry settled with its evidence (commit, release, file), never
   without, in one change, until the doctor exits 0. Entries classed `superseded` (later roadmaps,
   releases or changes made them obsolete) are closed by the agent as obsolete, never forwarded; post-merge
   steps (a release after the merge, `close #N`) are checked with the forge through `gh`, by the sweep itself
   when it can reach it, else by the agent (class `forge`). A check carried to another roadmap (`→ roadmap-x`)
   is ticked by `--fix`.
3. The owner's short list: only real owner items (a decision about future work, a secret, account or
   connector, a step outside the repository), carried to the live roadmap or a `cockpit` issue.
4. The `context-doctor` job above, once the doctor is at zero.

`npx softure-skills doctor --baseline` exists only as a last resort, for a project that cannot finish
the history sweep at once: it accepts today's failures in `context/doctor-baseline.json`, the check
then fails on anything new, and the file only shrinks. The recommended path is the sweep to zero.

## Many projects at once

`npx softure-skills portfolio` is read-only: it reads `context/state.json` from the main branch of every
listed repository (arguments, or `~/.config/softure/portfolio.json` outside any project) and prints one table:

```
| project | active roadmap X/N | queued | open changes | owner queue | last release | doctor |
```

`--owner` prints only what waits for the owner across all projects, oldest first; `--json` gives the same
data to another tool; `--source api` reads through the GitHub API instead of git. The last release comes
from the forge (the latest GitHub release through `gh`, else the highest `v*` tag); a value only a roadmap
recorded is labelled `(roadmap)`. See WORKFLOW §12.3.

**Operating mode.** `context/workflow.json` → `mode` is `"manual"` (default) or `"autonomous"`, and the
installer injects only that mode's section into the rules block:

| | manual | autonomous |
|---|---|---|
| who decides | the owner, step by step; skills ask | the agent takes the recommended option and records it |
| implementation | one phase per run, commit on the owner's approval | all phases, one commit per phase |
| merge into the main branch | on the owner's signal | standing consent: serial merge queue, via PR (`autonomy.merge`) |
| parallel sessions, reports | only when the owner starts them | coordinator + one session per change, report every 60 min, around the clock |
| release | the owner | the owner while `release.owner` is true; production deploy always the owner |

The autonomous standard (roles of the coordinator and its threads, results always sent to the main
chat, condensed messages with the decision first, the coordinator's go on green PRs, threads closed only
after the merge, the report table `ID | What it does | Stage | Link` with the `X of N` counter, issues
for SOFTURE package bugs and for gaps in these skills) lives in the rules block, so every session that
runs in a checkout, cloud ones included, reads it from `AGENTS.md` without being told. A hosted
project's coordinator (for example a claude.ai project's main chat) is started outside the checkout:
paste the one-paragraph pointer from WORKFLOW §8.5 (`softure-init` prints it) into the project
instructions, and it starts the run by itself. The paste is checked, not assumed: the first thread
that finds it missing tells the coordinator, which then reads the rules from the main branch at once
and asks the owner to paste it. The roadmap state lives on the main branch, written only by
`wt-roadmap.py` (branches never edit `roadmap.md`), and a branch merges the main branch in again only
when `wt-merge-check.py` finds an overlap, a migration or a dependency change, so a serial merge
without overlap costs minutes, not a full test run. Tune it with `autonomy` (WORKFLOW §2). Switch modes only on the
owner's word: change `mode`, re-run the installer, commit both.

Per-project choices go into `context/workflow.json` → `install` and are applied on every install,
postinstall included: `"gitignore": false` commits the skills, and `"rules": ["workflow", "conventions"]`
injects only those sections of the rules block (sections: `language`, `workflow`, `conventions`; default:
all; the operating-mode section always ships, and so does `language` unless `"allowNonEnglishCode": true`
records the owner's explicit exception). The repository is always English; `chatLanguage` is the language
of every message to the owner, `language` only the prose of `context/` artifacts. Put project-specific skills in folders without the `softure-` prefix: installed folders are
overwritten on every install. Uninstall:
`node node_modules/@softure-ai/skills/scripts/uninstall.mjs`.

## First message of a session

[ONBOARD.md](ONBOARD.md) holds two prompts to paste as the first message of a fresh Claude Code
session, **AUTO** and **MANUAL**. In a project that is already set up the session changes nothing: it
reads the rules, the config, `context/` and the forge, reports where the work stands and restates the
rules it will work by. In a project that is not, it installs the skills and runs `softure-init` first.

## Routines

[routines/](routines/README.md) holds the scheduled sessions a project runs without the owner: the nightly
**package updates** (every `@softure-ai/*` package and pin to the newest, one pull request, never a release or
deploy) and the **roadmap heartbeat** of an autonomous run (reads the repository and the forge, hands the coordinator
the facts for the roadmap report, changes nothing). Every routine runs in a fresh session, never in the
coordinator's; the project's scheduled task only points at the file, so a routine improves with every bump of this
package. The **COCKPIT command** (`routines/cockpit-command.md`) is a task with no schedule that COCKPIT fires through
an API trigger after it opens a `cockpit` issue, with the issue's link: each fire starts one fresh project thread that
acts only on that issue and sends its start and result to the coordinator. The task needs the project's repository
attached with write access. `routines/README.md`
has the prompt that sets one up (WORKFLOW §13).

## The chain

See [WORKFLOW.md](WORKFLOW.md) for the full contract: artifacts, statuses, formats and
operating modes.

| Stage | Skill | Produces |
|---|---|---|
| setup | `softure-init` | `context/` + `context/workflow.json` (commands, branch, language) |
| discovery | `softure-shape` | `context/foundation/shape-notes.md` |
| | `softure-frame` | challenge what to build: `frame.md` |
| | `softure-prd` | `context/foundation/prd.md` |
| | `softure-roadmap` | `context/foundation/roadmap.md` |
| delivery | `softure-new` | `context/changes/<id>/change.md` |
| | `softure-research` | `research.md` |
| | `softure-plan` | `plan.md` with `## Progress` |
| | `softure-plan-review` | `reviews/plan-review.md` |
| | `softure-implement` | code, one commit per phase |
| | `softure-impl-review` | `reviews/impl-review.md` + fixes |
| | `softure-archive` | `context/archive/<date>-<id>/` |
| orchestration | `softure-worktree` | one change end to end in its own worktree; merge on your signal |
| | `softure-worktree-manager` | several worktrees in parallel; merges them one by one |
| hygiene | `softure-code-review` | review of a diff against conventions |
| | `softure-lesson` | numbered rule in `lessons.md` |
| | `softure-rule-review` | audit of AGENTS.md / CLAUDE.md / skills |
| | `softure-evidence` | screenshots and recordings in the evidence store (never git) + the evidence page |
| | `softure-doctor` | `context/state.json` (machine-readable state, `owner_queue`) + the `context/` contract check |

Every interactive skill accepts `--auto`: it decides instead of asking and records each
decision in the artifact. The orchestrators always use it, and `mode: "autonomous"` implies it.

Each `SKILL.md` stays scannable: the procedure, the questions it asks and its quality bar.
Long material (question banks, rubrics, templates, complete worked examples, good and bad)
lives next to it in `references/` and is read when the skill points to it.

## Releasing

Releases are tag-driven:

```bash
npm version patch          # or minor / major: bumps package.json and creates tag vX.Y.Z
git push --follow-tags
```

Where a tag cannot be pushed (a cloud agent session's git proxy lets only branches through), bump the
version without a tag (`npm version minor --no-git-tag-version`), commit and push it to `master`, then
run the **auto-release** workflow (Actions → auto-release → Run workflow, on `master`). It creates
`vX.Y.Z` on `master`'s head and starts `release.yml` on that tag, the same path as a pushed tag.

The `v*.*.*` tag runs `.github/workflows/release.yml`, which:
1. validates and test-installs the package, and checks that the tag matches `package.json`;
2. publishes `@softure-ai/skills` to **npmjs.com** through trusted publishing (OIDC, provenance,
   no stored token);
3. publishes `@softure/skills` to **GitHub Packages** (GitHub requires the scope to match the org);
4. creates the **GitHub Release** with generated notes and the package tarball attached.

Ways to install a release:

| Source | Command |
|---|---|
| npm | `npm i -D @softure-ai/skills` |
| GitHub Release (no auth) | `npm i -D https://github.com/SOFTURE/SKILLS/releases/download/vX.Y.Z/softure-ai-skills-X.Y.Z.tgz` |
| GitHub Packages | `npm i -D @softure/skills` with `@softure:registry=https://npm.pkg.github.com` and a token with `read:packages` |

`node scripts/validate.mjs` is the release gate: frontmatter, the `softure-` prefix, and no
third-party course branding in any shipped file.
