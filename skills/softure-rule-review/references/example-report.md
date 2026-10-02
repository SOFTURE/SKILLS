# Example rule review report

A fictional team wiki (Next.js, Postgres, pnpm). Root `AGENTS.md` (284 non-blank lines), a
nested `src/editor/AGENTS.md` (38 lines), `context/foundation/lessons.md` (12 lessons). Use it
for the level of detail, not the content.

```markdown
# Rule review: 2026-10-02

Files: 3 · Rules: 61 · Stale: 2 · Contradictions: 1 · Duplicates: 2 · Vague: 5 · Bloat: 1

## Scorecard
| File | Length | Snippets | Precise language | Redundant | Ordering |
|---|---|---|---|---|---|
| AGENTS.md | WARN (284 lines) | FAIL (3 blocks) | FAIL (4 phrases) | WARN (3) | FAIL (security rules at line 231) |
| src/editor/AGENTS.md | OK (38) | OK (0) | WARN (1) | OK (0) | OK |
| lessons.md | OK (96) | OK (0) | OK (0) | OK (0) | OK |

## Top 3 actions
1. Move "Permissions and private spaces" (AGENTS.md:231-248) to the top: it is the only CRITICAL section and sits after 230 lines of setup and style.
2. Resolve the commit contradiction (AGENTS.md:57 vs L-009): agents currently get two answers.
3. Replace the three copied config blocks (AGENTS.md:96-140) with pointers; they already differ from the real files.

## Contradictions (fix first)
1. AGENTS.md:57 "Commit only the files you changed" vs lessons.md L-009 "Commit the whole tree after each phase". Same scope: phase commits. Winner: L-009 (newer, specific, with incident). Edit: replace AGENTS.md:57 with "Phase commits include the whole tree (L-009)."

## Stale references
1. AGENTS.md:31 `pnpm db:fresh`: script does not exist in package.json. Edit: `pnpm db:reset`.
2. src/editor/AGENTS.md:12 `src/editor/legacy/`: directory removed in 4e1a9c0. Edit: delete the line (the rule was about that directory only).

## Duplicates
1. "Run pnpm test before pushing" appears at AGENTS.md:44, AGENTS.md:202 and src/editor/AGENTS.md:5 with three wordings. Keep AGENTS.md:44; replace the others with nothing (the root file is always loaded).

## Vague -> sharpened
1. AGENTS.md:62 "Handle errors properly" -> "Server actions return `{ ok: false, error: { code, message } }` for expected failures (see src/pages/actions.ts:20)."
2. AGENTS.md:63 "Write clean code" -> "Functions over 40 lines are split; no `any` without a comment saying why." (40 is **assumed**)
3. AGENTS.md:71 "Be consistent with naming" -> "Reads go in `<entity>.queries.ts`, writes in `<entity>.actions.ts`, as in src/pages/."
4. AGENTS.md:88 "Care about accessibility" -> "Every icon-only button has an `aria-label` from `messages/en.ts`; `pnpm lint` runs jsx-a11y."
5. src/editor/AGENTS.md:20 "Keep the editor fast" -> "Typing latency stays under 16 ms per keystroke in the editor benchmark (`pnpm bench:editor`)."

## Redundant knowledge
1. AGENTS.md:9-24 explains what server components are -> delete.
2. AGENTS.md:150-161 restates the folder layout from README.md -> pointer to README.md#layout.
3. AGENTS.md:170 "TypeScript strict mode is on" -> delete; tsconfig.json enforces it.

## Inline snippets
1. AGENTS.md:96-112 copy of tsconfig.json (already differs: `noUncheckedIndexedAccess` missing) -> pointer.
2. AGENTS.md:114-127 example page component -> pointer to src/app/pages/[slug]/page.tsx.
3. AGENTS.md:129-140 sample migration -> pointer to drizzle/0007_page_versions.sql.

## Ordering
Current: 1 Welcome (1) INTRO · 2 About the team (5) INTRO · 3 Setup (26) USEFUL · 4 Style (55) VAGUE · 5 Config examples (94) REDUNDANT · 6 Layout (148) REDUNDANT · 7 Testing (190) USEFUL · 8 Permissions and private spaces (231) CRITICAL · 9 Links (250) REFERENCE.
Problem: the only CRITICAL section is at line 231, after 25 lines of INTRO and two REDUNDANT blocks.
Proposed: Permissions (231) -> top · Testing (190) -> second · Setup (26) kept · Style (55) kept, after the rewrites · Config examples and Layout -> removed (pointers) · Welcome/Team -> one line under the title · Links kept at the bottom.

## Bloat
1. AGENTS.md:205-228 incident story about the March outage. Move to context/archive/notes/2026-03-outage.md; keep the rule "Never run migrations from a laptop against production" with a pointer.

## Could be enforced by tooling
1. "No `console.log` in src/" (AGENTS.md:80) -> ESLint `no-console`.
2. "Page slugs are unique per space" (AGENTS.md:236) -> unique index on pages(space_id, slug); today it is checked only in code.

## Proposed edits
<one unified diff per file>

## Reminder
Apply one structural edit at a time (reorder first), run one real task with an agent, then the next.
```

Why it is good: each file has its own scorecard row; every finding has `path:line` and an
edit; every vague phrase is rewritten from something in the repo, with assumed numbers marked;
the Top 3 are picked by leverage (the ordering fix first, although it is check 5); nothing new is
invented, only subtracted or sharpened.
