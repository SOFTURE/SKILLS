# `## Progress`: canonical format

`## Progress` in `plan.md` is the **only** execution state of a change: no sidecar files, no
checklists elsewhere. `softure-implement` reads it to find where to resume. Orchestrators read it
to report progress. It must stay machine-friendly.

## Shape

```markdown
## Progress

> `- [ ]` pending, `- [x]` done. A phase ends with ` — <commit sha>` on its done items. Never rename items.

### Phase 1: <exact title of "## Phase 1:">

#### Automated
- [ ] 1.1 <criterion checkable by a command, test or query>
- [ ] 1.2 Gates green (typecheck, lint, test)

#### Manual
- [ ] 1.3 <criterion only a human can judge>

### Phase 2: <exact title of "## Phase 2:">

#### Automated
- [ ] 2.1 ...
```

## Rules

1. `## Progress` is the **last** section of `plan.md`.
2. There is one `### Phase N: <title>` per `## Phase N: <title>`, in the same order and with
   **identical** titles.
3. Each phase has `#### Automated`, and `#### Manual` only when it has manual criteria. Automated
   comes first.
4. Items are numbered `N.M`, continuously within a phase across both groups (1.1, 1.2, 1.3…).
5. One item is one checkable criterion. Write it as a statement of the end state, not as an
   activity ("Unsubscribe link returns 303 to /unsubscribe", not "Implement unsubscribe link").
6. The last automated item of every phase is `Gates green (typecheck, lint, test)`.
7. Only `softure-implement` ticks boxes:
   - `- [ ]` becomes `- [x]` only after the criterion was **actually checked**;
   - after the phase commit, append ` — <short sha>` to every item ticked in that phase;
   - a manual item verified by the agent itself (screenshot, DB read) gets
     ` — <sha> (verified by agent: <how>)`;
   - a manual item that only the owner can check stays `- [ ]`.
8. The resume point is the **first `- [ ]` in an Automated group**. Manual items still open do
   not block the next phase. They are listed for the owner at the end.
9. Never delete or rename an item after implementation starts. When the plan changes
   mid-flight, add new items with the next free number and mark obsolete ones
   `- [x] ~~1.4 old text~~ — dropped: <reason>`. Numbers are never reused, so gaps are fine.
   Before implementation starts (plan and plan review), items may still be renumbered.
10. Within a phase, boxes may be ticked as each criterion is checked; the SHA is appended to all
    of them at once after the phase commit. A ticked item without a SHA in the phase being
    worked on is a valid intermediate state, not drift.
11. Checkboxes appear **only** here. The `## Phase N:` blocks above list their Done-when
    criteria as plain `- ` bullets, and every one of them has exactly one item here.

## What does not belong in Progress

- Nested checkboxes. One criterion is one line; sub-steps belong in the phase block.
- Estimates, owners, due dates.
- Prose between phases or groups. The section is headings and items only, because tools parse it.
- Status markers or completion banners. The status lives in change.md frontmatter; completion
  is derived from the boxes.

## Deriving state (for skills and scripts that read Progress)

- **Resume point:** the first `- [ ]` under an `#### Automated` heading.
- **Current phase:** the phase that holds the resume point, or the last phase when there is none.
- **Completion:** ticked items divided by all items, dropped items counted as ticked.
- **Open owner checks:** every `- [ ]` under `#### Manual`. They go to the roadmap's
  `## Owner decisions and checks` at archive time.

Drift between change.md and Progress, worth reporting wherever it is noticed:

| change.md status | Progress shows | Likely meaning |
| --- | --- | --- |
| `planned` or `plan_reviewed` | a ticked item without a SHA | work started without moving the status (ticked items with SHAs are normal after a re-plan) |
| `implementing` | nothing ticked | the status moved, no work was recorded |
| `implementing` | every Automated item ticked | the status should be `implemented` |
| `implemented` | an open Automated item | a phase was skipped or a box was never ticked |
| any | a ticked item without a SHA in a phase that is not the current one | a phase was committed without its bookkeeping |

## Example (one phase done, one in flight)

```markdown
## Progress

> `- [ ]` pending, `- [x]` done. A phase ends with ` — <commit sha>` on its done items. Never rename items.

### Phase 1: Pending state in the shared button

#### Automated
- [x] 1.1 `Button` with `isPending` renders a spinner and `aria-busy="true"` — 4f2a9c1
- [x] 1.2 Gates green (typecheck, lint, test) — 4f2a9c1

#### Manual
- [x] 1.3 Spinner visible in both themes at 390 px — 4f2a9c1 (verified by agent: screenshots in reviews/)

### Phase 2: Every long action uses it

#### Automated
- [x] 2.1 All server-action forms pass `isPending` from `useFormStatus`
- [ ] 2.2 E2E: clicking "Recalculate" shows the pending state within 100 ms
- [ ] 2.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 2.4 Owner confirms the pending state feels responsive on a slow network
```

Resume point here: item 2.2. Item 2.1 is ticked without a SHA because phase 2 is not committed
yet. Item 2.4 stays open for the owner and does not block phase 3.

## Example: a re-plan in the middle of phase 2

Research for the remaining work showed that the E2E check belongs to a later phase, and a new
criterion appeared. Nothing is renamed or renumbered:

```markdown
### Phase 2: Every long action uses it

#### Automated
- [x] 2.1 All server-action forms pass `isPending` from `useFormStatus`
- [x] ~~2.2 E2E: clicking "Recalculate" shows the pending state within 100 ms~~ — dropped: moved to phase 3
- [ ] 2.5 Disabled buttons expose `aria-disabled` while pending
- [ ] 2.3 Gates green (typecheck, lint, test)

#### Manual
- [ ] 2.4 Owner confirms the pending state feels responsive on a slow network
```

The gates item keeps its number and stays last. The new item takes the next free number (2.5,
because 2.4 is the manual item).
