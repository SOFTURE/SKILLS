# Initialize a project with SOFTURE SKILLS

Two prompts for the **first message of a fresh Claude Code session** in a code project, new or
existing, that has no SOFTURE context yet: no `context/workflow.json`, no managed block in
`AGENTS.md`, nothing in memory. Paste one of them as the first thread. The session installs the
skills, reads the process, sets the project up and confirms the rules it will work by.

| Prompt | Use it when |
|---|---|
| [AUTO](#auto-autonomous-project) | the owner sets the goal and is away: the agent decides, merges green work, runs threads and reports (WORKFLOW §8.4) |
| [MANUAL](#manual-manual-project) | the owner checks every step: one skill per request, nothing leaves the working tree without the owner's word (WORKFLOW §8.3) |

Both prompts are written so the session learns the rules from the repository, not from the prompt:
the managed block in `AGENTS.md` is the source of truth, and every later session (cloud ones and
threads included) reads it there without being told again. The prompt only makes the first session
put it in place, read it, and prove it understood.

Replace `<chat language>` with the language the owner writes in (for example `pl`) before pasting.

## AUTO: autonomous project

```text
Initialize this repository for the SOFTURE workflow in AUTONOMOUS mode. This is the first thread of
the project; you have no context yet. Do not ask me anything: decide by the recommended option,
record each decision, and escalate only what AGENTS.md → "Operating mode: autonomous" lets you
escalate. Talk to me in <chat language>; everything you write to the repository is English.

1. Install. If `.claude/skills/softure-*` or the SOFTURE managed block in AGENTS.md (or CLAUDE.md)
   is missing, install the package with the repo's package manager (`npm i -D @softure-ai/skills`,
   or `npx @softure-ai/skills` when the repo has no package.json). Never overwrite a folder the
   installer did not create.
2. Learn the process before touching anything else:
   - read the whole managed block in AGENTS.md;
   - read node_modules/@softure-ai/skills/WORKFLOW.md (or WORKFLOW.md from SOFTURE/SKILLS on GitHub
     when there is no node_modules);
   - list .claude/skills/softure-* and read the frontmatter of every SKILL.md, so you know which
     skill owns which step and what artifact it leaves.
3. Set the project up: run `softure-init --mode autonomous --auto` with chatLanguage
   `<chat language>`. If context/workflow.json already exists, only add missing keys and never
   change `mode` on your own. Then re-run the installer so AGENTS.md carries the autonomous section.
4. Make the rules load in every session: if the block lives in AGENTS.md, make sure CLAUDE.md
   exists and imports it (`@AGENTS.md`). Project-specific standing orders go into AGENTS.md outside
   the managed block, never into memory.
5. If the repo already has rule files of its own (CLAUDE.md, AGENTS.md, .cursorrules, docs on
   process), run `softure-rule-review --auto` once and fix what contradicts the workflow.
6. Land the setup like any other work in autonomous mode: one commit `chore: set up SOFTURE
   workflow`, pushed and merged by the merge path in `autonomy.merge` (pull request by default),
   hooks on, no force-push.
7. Memory: save only project state (main branch, work source, roadmap name, counters, my orders).
   The process rules are not memory material; they live in AGENTS.md.
8. Report to me, condensed, decision first:
   - what was installed, created and merged (PR, merge SHA);
   - the values you inferred and the ones still null;
   - the rules you will work by, in your own words, one line each, at least: every change goes
     through the chain however small; one change = one thread = one branch and one PR; the
     coordinator writes no code and gives the go on green PRs itself; decide, don't ask, and record
     decisions under `## Decisions (auto)`; a thread is closed only after its PR is merged, and the
     coordinator closes finished threads it finds open; every result lands in the main chat,
     condensed, decision first; reports on the clock with the `X of N` table; bugs and gaps in
     SOFTURE packages become issues right away; when I have to correct the process, that is a gap
     filed in SOFTURE/SKILLS; only a release or a production deploy waits for my word;
   - for a hosted project (claude.ai project), the project-instructions pointer from WORKFLOW §8.5
     with <owner>/<repo> filled in, ready to paste.
9. Then follow "Start of a run" from AGENTS.md. If there is no roadmap and no issue queue yet, say
   so in one line and name what I give next (a goal for `softure-shape`, or an issue queue); do not
   invent work.
```

## MANUAL: manual project

```text
Initialize this repository for the SOFTURE workflow in MANUAL mode. This is the first thread of
the project; you have no context yet. I check every step: one step at a time, show me the result,
and wait for my word before anything leaves the working tree. Talk to me in <chat language>;
everything you write to the repository is English.

1. Install. If `.claude/skills/softure-*` or the SOFTURE managed block in AGENTS.md (or CLAUDE.md)
   is missing, propose the install command for the repo's package manager
   (`npm i -D @softure-ai/skills`, or `npx @softure-ai/skills` when the repo has no package.json)
   and run it once I confirm.
2. Learn the process before touching anything else:
   - read the whole managed block in AGENTS.md;
   - read node_modules/@softure-ai/skills/WORKFLOW.md (or WORKFLOW.md from SOFTURE/SKILLS on GitHub
     when there is no node_modules);
   - list .claude/skills/softure-* and read the frontmatter of every SKILL.md, so you know which
     skill owns which step and what artifact it leaves.
3. Set the project up: run `softure-init --mode manual` with chatLanguage `<chat language>`. Show
   me the plan it prints and ask before writing. If context/workflow.json already exists, only add
   missing keys and never change `mode`.
4. Make the rules load in every session: if the block lives in AGENTS.md, propose a CLAUDE.md that
   imports it (`@AGENTS.md`). Project-specific orders go into AGENTS.md outside the managed block,
   never into memory.
5. If the repo already has rule files of its own, recommend whether `softure-rule-review` should
   run once; do not run it without my word.
6. Show me the diff and the proposed commit message `chore: set up SOFTURE workflow`. Commit only
   when I approve it. No push, no pull request, no merge without my word for that exact action.
7. Memory: save only project state (main branch, my decisions and orders). The process rules are
   not memory material; they live in AGENTS.md.
8. Report to me:
   - what was installed and created, the inferred values and the ones still null;
   - the rules you will work by, in your own words, one line each, at least: every change goes
     through the chain however small; one change = one thread = one branch; one skill per request,
     then name the next one and stop; one implementation phase at a time, committed only on my
     approval; an approval covers one action and never carries over; nothing leaves the working
     tree (push, PR, merge, issue close, tag, release, deploy) without my word; no background
     threads, routines or parallel worktrees unless I start them; questions are welcome, always
     with a recommendation; rules of autonomous projects do not apply here;
   - the next step: `softure-shape` for a new product or theme, `softure-roadmap` for an existing
     PRD, `softure-new` for one concrete change.
   Then stop. Do not start the next skill.
```

## After the first thread

- Every later session reads the rules from `AGENTS.md` itself; do not paste the prompt again.
- Switching mode later is the owner's explicit word: change `mode` in `context/workflow.json`,
  re-run the installer, commit both as `docs(rules): switch to <mode> mode` (WORKFLOW §8).
- A hosted project's main chat (for example a claude.ai project) still needs the one-paragraph
  pointer from WORKFLOW §8.5 in its project instructions; the AUTO prompt prints it.
