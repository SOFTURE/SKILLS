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

It never overwrites a skill folder it did not install. Flags: `--dry-run`, `--target <dir>`,
`--no-gitignore` (commit the skills instead).

**Operating mode.** `context/workflow.json` → `mode` is `"manual"` (default) or `"autonomous"`, and the
installer injects only that mode's section into the rules block:

| | manual | autonomous |
|---|---|---|
| who decides | the owner, step by step; skills ask | the agent takes the recommended option and records it |
| implementation | one phase per run, commit on the owner's approval | all phases, one commit per phase |
| merge into the main branch | on the owner's signal | standing consent: serial merge queue, via PR (`autonomy.merge`) |
| parallel sessions, reports | only when the owner starts them | coordinator + one session per change, report every 30 min |
| release | the owner | the owner while `release.owner` is true; production deploy always the owner |

The autonomous standard (roles of the coordinator and its threads, results always sent to the main
chat, condensed messages with the decision first, the coordinator's go on green PRs, threads closed only
after the merge, the report table `ID | What it does | Stage | Link` with the `X of N` counter, issues
for SOFTURE package bugs) lives in the rules block, so every session, cloud ones included, reads it from
`AGENTS.md` without being told. Tune it with `autonomy` (WORKFLOW §2). Switch modes only on the
owner's word: change `mode`, re-run the installer, commit both.

Per-project choices go into `context/workflow.json` → `install` and are applied on every install,
postinstall included: `"gitignore": false` commits the skills, and `"rules": ["workflow", "conventions"]`
injects only those sections of the rules block (sections: `language`, `workflow`, `conventions`; default:
all; the operating-mode section always ships, and so does `language` unless `"allowNonEnglishCode": true`
records the owner's explicit exception). The repository is always English; `chatLanguage` is the language
of every message to the owner, `language` only the prose of `context/` artifacts. Put project-specific skills in folders without the `softure-` prefix: installed folders are
overwritten on every install. Uninstall:
`node node_modules/@softure-ai/skills/scripts/uninstall.mjs`.

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
