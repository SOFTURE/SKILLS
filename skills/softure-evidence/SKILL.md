---
name: softure-evidence
description: >
  Keep run evidence (screenshots, frame grabs, recordings) out of git and easy to browse: name
  each file by the rule `<change-id>/<NN>-<what>-<before|after>-<width>-<theme>.webp`, convert it
  to WebP, store it in the project's evidence store (a folder, the hosted project's shared files,
  an upload command or the asset store of one evidence page), refresh the per-project evidence
  page, and return the link that `## Progress` cites. Also lists a change's evidence, checks a
  folder for committed binaries, and prunes evidence of long-archived changes. Use when a Manual
  item is verified by a screenshot or a recording, when softure-implement or softure-impl-review
  produce visual evidence, or when the user says "save the screenshot", "where are the
  screenshots", "show the evidence", "prune old screenshots".
argument-hint: "save <file> --change <id> --what <slug> --state before|after --width <px> --theme light|dark | list --change <id> | check <path> | prune --months <N>"
allowed-tools:
  - Read
  - Glob
  - Bash
---

# softure-evidence: every screenshot kept, none in git

Contract: `WORKFLOW.md` §11 (project files and evidence) and §2 (`evidence`). The script is
`scripts/evidence.py` next to this file (`<S>` below); it reads `context/workflow.json` of the
repository it runs in.

## Why

Evidence committed to git is carried by every clone forever; evidence written to an ignored
folder in a cloud container is gone when the container goes. Both leave the owner and the
reviewer unable to open what the run looked at. The store keeps every file once, outside the
repository, under a name that says what it shows.

## Name

`<change-id>/<NN>-<what>-<before|after>-<width>-<theme>.<ext>`, all lowercase kebab-case:

- `NN`: two digits, the order within the change (the script picks the next one in file stores);
- `what`: the screen or state shown (`map-panel`, `cancel-button-disabled`);
- `before` (the main branch, or the state before the phase) or `after` (this change);
- `width`: the viewport width in px (`390`, `1280`); `theme`: `light` or `dark`;
- `ext`: `webp` (quality 85); `png` only when a side exceeds the WebP limit of 16383 px; a recording
  keeps its format (`webm`, `mp4`).

Example: `add-side-map/01-map-panel-after-390-dark.webp`. A pair `before`/`after` with the same
`what`, `width` and `theme` sits side by side on the evidence page.

## Stores (`evidence.store`)

| store | where | link `## Progress` cites | page |
|---|---|---|---|
| `dir` | a folder outside the repository (`path`, `~` allowed) | the file path | `<path>/index.html`, rewritten on every save |
| `project-files` | the hosted project's shared files (`path` under `/mnt/project-files`, or `projectFilesRoot`, or `$SOFTURE_PROJECT_FILES`) | `<path>/<key>` | `<path>/index.html`, rewritten on every save |
| `command` | object storage behind the project's own `upload` command (`{file}`, `{key}`; prints the link last) | the printed link | the store's own listing |
| `artifact` | the asset store of one evidence page (`url`) | the asset url | that page, republished by the agent |

No store configured: the script keeps the file in `~/.cache/softure-evidence/<repo>/`, prints
`"durable": false`, and the Progress line says `(evidence not stored: no evidence.store)`.
Report it once to the owner as a setup gap (`softure-init` proposes a store); never commit the file
instead.

## Procedure: save one file

1. Take the screenshot or recording into a scratch folder **outside** the repository (or a
   git-ignored one), never into `context/`.
2. `python3 <S>/evidence.py save <file> --change <id> --what <slug> --state after --width 390 --theme dark`.
   It prints one JSON line: `key`, `link`, `durable`, an optional `warning` (for example "kept PNG")
   and, for `artifact`, `next`.
3. `artifact` store only: upload the converted file (`file` in the output) to the asset store of the
   page at `evidence.url` with your artifact tool, read the page's current HTML, then
   `python3 <S>/evidence.py render --from-page <page.html> --add <key>=<asset url> --out <page.html>`
   and republish the page to the same url. The page's data block is the manifest: never rebuild it
   from memory.
4. Cite the link in the Progress item that relied on it:
   `- [x] 2.4 … — <sha> (verified by agent: <how> → <result>; <link>[, <link>])`.
5. Delete the scratch copy once the store holds it.

## Other commands

- `list --change <id>`: the change's stored files (file stores; the others say where to look).
- `check <path> …`: exit 1 when any image or recording lies under the paths. `softure-archive` runs it
  on the change folder as a hard stop.
- `prune --months <N> [--apply]`: delete the evidence of changes archived N or more months ago (file
  stores; dry run without `--apply`). Only on the owner's word or a set `evidence.retainMonths`;
  the default is to keep evidence forever.
- `render --from-dir <store> --out <store>/index.html`: rebuild the page of a file store by hand.

## Exceptions

Visual-regression baselines that tests compare against stay in the repository, next to their
tests (`__screenshots__/`, `*-snapshots/`). They are test fixtures, not run evidence.

## Checklist

- [ ] No image or recording added under `context/` or anywhere else in the diff, baselines excepted.
- [ ] Every file named by the rule, WebP unless the script said why not.
- [ ] Every Progress item that relied on visual evidence links its stored files.
- [ ] `artifact` store: the page republished with the new entries, nothing dropped from its data block.

## Anti-patterns

- `reviews/p2-*.png` in the change folder "just for the review".
- A Progress line that says "screenshot looked fine" with nothing anyone can open.
- Copying owner material (briefs, real data) into the repository instead of referencing its path in
  the project files (WORKFLOW §11).
