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
`--no-gitignore` (commit the skills instead). Uninstall:
`node node_modules/@softure-ai/skills/scripts/uninstall.mjs`.

## The chain

See [WORKFLOW.md](WORKFLOW.md) for the full contract: artifacts, statuses, formats and
autonomous mode.

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
decision in the artifact. The orchestrators always use it.

## Releasing

Bump `version` in `package.json` and merge to the main branch. The workflow validates the
package, test-installs it into a scratch project, and publishes to npm with provenance, but
only if that version is not published yet.

Publishing uses npm **trusted publishing (OIDC)**: the trusted publisher on npmjs.com is
`SOFTURE/SKILLS` → `release.yml`, and no token is stored. An `NPM_TOKEN` secret (a granular
token with "Bypass 2FA") is only needed when bootstrapping a brand-new package, before its
trusted publisher can be configured.

`node scripts/validate.mjs` is the release gate: frontmatter, the `softure-` prefix, and no
third-party course branding in any shipped file.
