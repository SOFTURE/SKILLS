# The five-point scorecard

Read before step 5 of softure-rule-review. Score each rule file separately. Score the file as it
is before any edit; a reorder or trim done later does not change the recorded verdict.

## 1. Length

Count non-blank lines, excluding separator lines (`---`), frontmatter of `.mdc` files and the
SOFTURE managed block.

| Non-blank lines | Verdict |
|---|---|
| up to 200 | OK |
| 201 to 500 | WARN |
| over 500 | FAIL |

Why: every line is paid for in every session, and rules in the middle of a long context get the
least attention. For WARN or FAIL, propose one or more of: move area rules into nested files next
to their code (`src/billing/AGENTS.md`); replace copied documentation with a pointer to the
canonical file; drop rules not tied to a recurring agent mistake.

## 2. Inline snippets

Flag fenced blocks and long inline code (more than about 3 lines) that copy something living
elsewhere: example components, endpoints, migrations, schemas, queries, tests, scripts, config
files (`tsconfig.json`, lint config, `package.json`), boilerplate templates.

Do not flag: short blocks that define an output *format* the agent must produce (a 2 to 4 line
error shape, a commit message pattern), command examples, diagrams.

| Flagged blocks | Verdict |
|---|---|
| 0 | OK |
| 1 to 2 | WARN |
| 3 or more | FAIL |

Fix: point at the real file (`see src/invoices/actions.ts for the action shape`). A copy is
wrong in two places after the next refactor; a pointer cannot drift.

## 3. Precise language

Flag rules that no diff can be checked against: "write clean code", "follow best practices",
"keep it simple", "be consistent", "handle errors properly", "make it maintainable", "use modern
patterns", "care about performance".

Every flagged phrase gets a **grounded rewrite**: a rule a reviewer could check against a diff,
built from signals in this repo. Look for the signal in the same file (stack, stated naming,
hard rules elsewhere), around the phrase (what was the author about to say?), and in the repo
(`package.json`, lint and type config, sibling rule files, existing code). When the repo gives
no signal, propose a sensible default for the stack and mark it **(assumed)** so the owner
confirms it.

| Vague phrase | Signal found in the repo | Grounded rewrite |
|---|---|---|
| "Handle errors properly" | server actions return `{ ok: false, error }` in `src/bookings/actions.ts` | "Server actions return `{ ok: false, error: { code, message } }` on expected failures and never throw for them." |
| "Be consistent with naming" | existing files are `<entity>.queries.ts` | "Database reads live in `<entity>.queries.ts` next to the entity, not in components." |
| "Keep components small" | React + Tailwind, `cn()` helper in `src/ui/cn.ts` | "Split components over 150 lines; conditional classes go through `cn()`." (150 is **assumed**) |
| "Use modern patterns" | no date library in `package.json`, `Intl` used in `src/format/` | "Format dates with `Intl.DateTimeFormat` via `src/format/date.ts`; do not add a date library." |
| "Care about performance" | slow page logged in a lesson (L-008) | "List pages paginate at 50 rows; no unbounded `findMany`." |

| Vague phrases | Verdict |
|---|---|
| 0 | OK |
| 1 to 3 | WARN |
| 4 or more | FAIL |

## 4. Redundant knowledge

Read the file as the agent that will receive it, and after each paragraph ask: *did I know this
already?* Tests:

- **No surprise:** could you have written this paragraph without seeing the project? Redundant.
- **Tool default:** does it restate what the framework, type checker, linter or test runner
  already enforces ("use strict mode", "React keys must be unique")? Redundant: the tool catches it.
- **Definition:** does it explain a general term (what a migration is, what REST means)? Redundant.
- **Could be a pointer:** does it copy the README, the scripts list, the folder layout or lint
  settings? Replace with a pointer.
- **Tutorial smell:** does it read like a framework's getting-started page? Redundant.

Not redundant, never flag:
- conventions that deliberately differ from the framework default;
- local traps you could not infer from the code ("the reports DB is a read replica; writes fail silently");
- internal naming, layout and workflow rules;
- rules that look generic but trace back to a real incident (ask for the lesson number inline).

For each flagged paragraph: **delete**, **replace with a pointer**, or **keep only with its
incident**.

| Redundant paragraphs | Verdict |
|---|---|
| 0 | OK |
| 1 to 3 | WARN |
| 4 or more | FAIL |

## 5. Rule ordering

Models attend most to the beginning and the end of a long context. Critical rules in the
middle are followed less reliably.

1. **List** the current headings (H1/H2, or H3 when there are no H2) with line numbers. A file
   with no headings is noted as one undifferentiated block.
2. **Tag** each section:
   - CRITICAL: load-bearing (security, money, data loss, irreversible actions, project "never" rules);
   - USEFUL: real project knowledge that is not a tripwire;
   - INTRO: welcome, mission, team, history;
   - REDUNDANT: flagged in check 4;
   - VAGUE: flagged in check 3;
   - REFERENCE: pointers to other files (cheap anywhere).
3. **Diagnose** in one paragraph: where the CRITICAL sections sit, what fills the top.
4. **Propose moves** only if there is a problem: to top / kept / to bottom / removed. No rule
   text is rewritten by a reorder.

| Situation | Verdict |
|---|---|
| top is dense with CRITICAL and USEFUL, clear headings, no INTRO at the start | OK |
| mixed: some critical rules on top, others buried, or a noticeable INTRO at the start | WARN |
| a CRITICAL rule after line 200, no headings at all, or the first 30+ lines are INTRO | FAIL |

## Edge cases

- **Short file (under 50 lines):** run all five checks anyway; short files fail checks 3 and 4 most.
- **Mostly pointers:** a good sign for checks 2 and 4; do not penalise.
- **`.mdc` with frontmatter (`globs`, `alwaysApply`):** count from after the frontmatter; check
  that the globs match existing paths (a stale glob is a Stale finding).
- **Generated stub, never edited:** still review it; check 4 usually dominates, which is the
  signal to trim it.
- **Root and nested files overlap:** score each separately, and report the duplication between
  them under Duplicates, keeping the rule in the file closest to its code.
- **Installed skills and the managed block:** never scored or edited; issues go upstream.
