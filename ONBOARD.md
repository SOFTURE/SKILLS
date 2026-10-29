# Onboard a session to SOFTURE SKILLS

Two prompts for the **first message of a fresh Claude Code session** in a code project. The session
has no context and no memory of the project; the prompt tells it where everything lives and makes it
prove it understood the process. Each prompt covers both cases:

- **already set up** (the usual case): the skills are installed, `context/` is full, work may be in
  flight. The session changes nothing; it orients itself, adopts what is in flight and continues.
- **not set up yet**: the session installs the skills and runs `softure-init` first.

| Prompt | Use it when |
|---|---|
| [AUTO](#auto-autonomous-project) | the owner sets the goal and is away: the agent decides, merges green work, runs threads and reports (WORKFLOW §8.4) |
| [MANUAL](#manual-manual-project) | the owner checks every step: one skill per request, nothing leaves the working tree without the owner's word (WORKFLOW §8.3) |

The rules themselves stay in the repository: the managed block in `AGENTS.md` is the source of truth,
and the prompt only points the session at it. Replace `<chat language>` with the language the owner
writes in (for example `pl`) before pasting.

## Where things live

The map both prompts give the session:

| What | Where |
|---|---|
| process rules for this project | managed SOFTURE block in `AGENTS.md` (or `CLAUDE.md`), only the active mode's section; project-specific rules outside the block win, except the language rule |
| full contract (artifacts, statuses, formats) | `node_modules/@softure-ai/skills/WORKFLOW.md` |
| skills | `.claude/skills/softure-*/SKILL.md` (+ `references/`); installed version in `.claude/softure-skills.json` |
| project config | `context/workflow.json`: `mode`, `chatLanguage`, `mainBranch`, gates, `autonomy`, `release` |
| product | `context/foundation/`: `shape-notes.md`, `prd.md`, `roadmap.md` (the one active roadmap), `roadmaps/` (queued), `lessons.md`, `archive/` |
| work in flight | `context/changes/<change-id>/`: `change.md` (status), `research.md`, `plan.md` (`## Progress` is the only execution state), `reviews/` |
| finished work | `context/archive/<date>-<change-id>/` |
| deferred work | `context/backlog/` |
| what the forge knows | open pull requests, issues, session branches; in a hosted project also the open threads |

## AUTO: autonomous project

```text
You are starting a fresh session in a project that runs the SOFTURE workflow in AUTONOMOUS mode.
You have no context and no memory of it yet. Do not ask me anything: decide by the recommended
option, record each decision, and escalate only what AGENTS.md → "Operating mode: autonomous" lets
you escalate. Talk to me in <chat language>; everything you write to the repository is English.

1. Detect the state, changing nothing: are `.claude/skills/softure-*`, the SOFTURE managed block in
   AGENTS.md (or CLAUDE.md) and context/workflow.json present?
   - All present: the project is set up. Do NOT run softure-init or the installer and do not
     rewrite anything; go to step 2.
   - Something missing: install the package with the repo's package manager
     (`npm i -D @softure-ai/skills`, or `npx @softure-ai/skills` without a package.json), run
     `softure-init --mode autonomous --auto` with chatLanguage `<chat language>`, re-run the
     installer, make sure CLAUDE.md imports AGENTS.md (`@AGENTS.md`), and land it as one commit
     `chore: set up SOFTURE workflow` through `autonomy.merge`. Then continue with step 2.
2. Learn the rules, in this order:
   - the whole managed block in AGENTS.md, plus the project's own rules outside it and CLAUDE.md;
   - node_modules/@softure-ai/skills/WORKFLOW.md (from SOFTURE/SKILLS on GitHub if node_modules is
     missing);
   - the frontmatter of every .claude/skills/softure-*/SKILL.md, so you know which skill owns which
     step and which artifact it leaves. Open a skill's body and references/ when you run it.
3. Read the project:
   - context/workflow.json: mode, chatLanguage, mainBranch, gates, autonomy, release. If `mode` is
     not "autonomous", say so in one line and follow the committed mode; never switch it yourself;
   - context/foundation/: prd.md, roadmap.md (items, stages, the `X of N` counter), roadmaps/ in
     the queue, lessons.md (rules learned the hard way: follow them);
   - context/changes/*/: each change's status in change.md and its `## Progress` in plan.md;
   - context/backlog/ and the latest entries of context/archive/;
   - on the forge: open pull requests, open issues, session branches, and the open threads when
     this is a hosted project.
4. Memory: save only project state (main branch, work source, roadmap name and counter, threads in
   flight, my standing orders). The process rules are not memory material; they live in AGENTS.md.
5. Report to me, condensed, decision first:
   - one line on the setup: present, or what you installed and merged (PR, merge SHA);
   - where the work stands: `X of N on <main>`, items in flight with their stage, open PRs, anything
     blocked or waiting for me;
   - the rules you will work by, in your own words, one line each, at least: every change goes
     through the chain however small; one change = one thread = one branch and one PR; the
     coordinator writes no code and gives the go on green PRs itself; decide, don't ask, and record
     decisions under `## Decisions (auto)`; a thread is closed only after its PR is merged, and the
     coordinator closes finished threads it finds open; every result lands in the main chat,
     condensed, decision first; reports on the clock with the `X of N` table; bugs and gaps in
     SOFTURE packages become issues right away; when I have to correct the process, that is a gap
     filed in SOFTURE/SKILLS; only a release or a production deploy waits for my word;
   - for a hosted project (claude.ai project) whose instructions lack it, the pointer from
     WORKFLOW §8.5 with <owner>/<repo> filled in, ready to paste.
6. Then follow "Start of a run" from AGENTS.md: adopt what is in flight first (give the go to READY
   threads, nudge stalled ones), then start threads for ready, parallel-safe items, then the report
   routine. With no roadmap and no issue queue, say so in one line and name what I give next (a
   goal for `softure-shape`, or an issue queue); do not invent work.
```

## MANUAL: manual project

```text
You are starting a fresh session in a project that runs the SOFTURE workflow in MANUAL mode. You
have no context and no memory of it yet. I check every step: one step at a time, show me the
result, and wait for my word before anything leaves the working tree. Talk to me in
<chat language>; everything you write to the repository is English.

1. Detect the state, changing nothing: are `.claude/skills/softure-*`, the SOFTURE managed block in
   AGENTS.md (or CLAUDE.md) and context/workflow.json present?
   - All present: the project is set up. Do NOT run softure-init or the installer and do not
     rewrite anything; go to step 2.
   - Something missing: tell me what is missing and propose the setup (install command for the
     repo's package manager, `softure-init --mode manual` with chatLanguage `<chat language>`, a
     CLAUDE.md that imports AGENTS.md). Do it only after my word, show me the diff and the commit
     message `chore: set up SOFTURE workflow`, and commit only when I approve. Then step 2.
2. Learn the rules, in this order:
   - the whole managed block in AGENTS.md, plus the project's own rules outside it and CLAUDE.md;
   - node_modules/@softure-ai/skills/WORKFLOW.md (from SOFTURE/SKILLS on GitHub if node_modules is
     missing);
   - the frontmatter of every .claude/skills/softure-*/SKILL.md, so you know which skill owns which
     step and which artifact it leaves. Open a skill's body and references/ when you run it.
3. Read the project:
   - context/workflow.json: mode, chatLanguage, mainBranch, gates, release. If `mode` is not
     "manual", tell me and ask which one applies; never switch it yourself;
   - context/foundation/: prd.md, roadmap.md (items and stages), roadmaps/ in the queue,
     lessons.md (rules learned the hard way: follow them);
   - context/changes/*/: each change's status in change.md and its `## Progress` in plan.md, so you
     know exactly where each one stopped;
   - context/backlog/ and the latest entries of context/archive/;
   - on the forge: open pull requests and issues (read only).
4. Memory: save only project state (main branch, my decisions and orders). The process rules are
   not memory material; they live in AGENTS.md.
5. Report to me:
   - one line on the setup: present, or what is missing;
   - where the work stands: roadmap progress, each change in flight with its last step and the next
     skill it needs, open PRs;
   - the rules you will work by, in your own words, one line each, at least: every change goes
     through the chain however small; one change = one thread = one branch; one skill per request,
     then name the next one and stop; one implementation phase at a time, committed only on my
     approval; an approval covers one action and never carries over; nothing leaves the working
     tree (push, PR, merge, issue close, tag, release, deploy) without my word; no background
     threads, routines or parallel worktrees unless I start them; questions are welcome, always
     with a recommendation; rules of autonomous projects do not apply here;
   - your recommended next step: continue a change in flight with its next skill, or
     `softure-new` / `softure-roadmap` / `softure-shape` when nothing is in flight.
   Then stop. Do not start the next skill.
```

## After the first message

- Every later session in a checkout reads the rules from `AGENTS.md` itself; the prompt only helps a
  session that has to find its bearings.
- Switching mode is the owner's explicit word: change `mode` in `context/workflow.json`, re-run the
  installer, commit both as `docs(rules): switch to <mode> mode` (WORKFLOW §8).
- A hosted project's main chat (for example a claude.ai project) needs the one-paragraph pointer from
  WORKFLOW §8.5 in its project instructions; the AUTO prompt prints it when it is missing, and every
  thread checks it at session start and tells the coordinator, which then reads `AGENTS.md` itself.
