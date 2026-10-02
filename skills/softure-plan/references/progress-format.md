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
   `- [x] ~~1.4 old text~~ — dropped: <reason>`.

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

Resume point here: item 2.2.
