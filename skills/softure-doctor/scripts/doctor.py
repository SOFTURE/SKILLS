#!/usr/bin/env python3
"""softure-doctor: check the `context/` contract of a project (WORKFLOW.md §12) and exit non-zero on drift.

    doctor.py [--root <dir>] [--json]
    doctor.py --fix [--write] [--json]    mechanical repairs of history (dry run unless --write)
    doctor.py --sweep [--json] [--no-forge]  every remaining failure as a worklist with evidence (read-only;
                                          asks the forge through `gh` about post-merge steps unless --no-forge)
    doctor.py --baseline                  last resort: accept today's failures in context/doctor-baseline.json
    npx softure-skills doctor [...]      (the same, from the installed package)

Adopting projects run it in a CI job named `context-doctor`, documentation-only changes included (that is where the
drift happens). In GitHub Actions it also writes the failure codes as annotations of that check run (the first one,
titled `context-doctor failure codes`, lists every code with its count), as one plain log line of the job
(`context-doctor failure codes: <code> (<count>), ...`, readable with Actions: read, where the checks API is not)
and as the job summary, so a reader of the forge API sees the codes on the main branch's head without a checkout. `softure-archive` and `softure-roadmap
--close` run it before their commit and fix what they own. Each problem is one line `FAIL <code> <path>: <what>`; the codes:

  roadmap-archived-not-removed    roadmap.md is still there although the same roadmap is in foundation/archive/
  roadmap-status-mismatch         roadmap.md `status` contradicts its rows (done with open rows; waiting)
  archived-change-status          an archived change.md whose status is not `archived`
  archived-change-progress        an archived plan.md with unticked Automated items in `## Progress` (an item
                                  struck through or noted dropped/cancelled/not applicable is dropped, not open)
  archived-roadmap-open-items     an archived roadmap with rows that are not done, done_code, dropped or carried
  archived-roadmap-summary        an archived roadmap whose `## Summary` item table holds a placeholder in its merge
                                  column (a SHA, a release tag, carried, dropped or a dash with a reason pass)
  archived-roadmap-open-checks    an archived roadmap with unticked owner decisions or checks (or pre-release
                                  steps, once its release is recorded or a later roadmap was closed)
  queued-roadmap-done             a queued roadmap in foundation/roadmaps/ whose rows are all done
  roadmap-item-shape              a live roadmap (roadmap.md or a queued one) that readers cannot parse (§5): item
                                  blocks but no at-a-glance rows, an item block whose ID has no row, a row status
                                  outside the vocabulary, an item block whose `Status` contradicts its row, or
                                  an item block without a title (a row without an item block passes)
  backlog-without-roadmap         a backlog/roadmap-<slug>/ folder without its queued (or promoted) roadmap
  index-missing-file              an index row (README.md / INDEX.md table under context/) links a missing file
                                  (a markdown link, or a cell that is only a path in a file column; a mention
                                  in a description cell is not a link)
  state-missing                   context/state.json is missing although the project has written it before
  state-stale                     context/state.json does not match the markdown
  baseline-stale                  context/doctor-baseline.json lists a failure that is fixed (remove it), or is unreadable
  ci-doctor-trigger               a workflow under .github/workflows/ whose `context-doctor` job does not run on every
                                  push to `mainBranch` (no `push` trigger for it, a `paths`/`paths-ignore` filter, an
                                  `if:` on the job), so the main branch's head has no `context-doctor` check run;
                                  see ci_config.py (a project without the job gets the installer's notice instead)
  owner-word-wake-invalid         context/workflow.json `autonomy.ownerWordWake` is not one of "routine", "heartbeat",
                                  "none" (WORKFLOW.md §8.6); an autonomous project that leaves the key out gets a note
                                  (`owner-word-wake-undeclared`), not a failure

`--fix` repairs what is mechanical (an archived change's status; an archived index row whose target
moved or was deleted on purpose, found through git history; a dropped Progress item, normalised) and prints every edit; see doctor_fix.py. It is a dry run unless
`--write` is given, and it writes only under `context/`. `--sweep` lists every remaining failure with
the evidence an agent needs to settle it from the repository alone, classed `evidence`, `superseded` (later
work made it obsolete; the agent closes it) or `owner`; see doctor_sweep.py.

`--baseline` is a last resort for a project that cannot finish the sweep at once: it writes the failures
that remain to `context/doctor-baseline.json`, and the check then fails only on new failures and on
baseline entries that were fixed but not removed. It only shrinks: run again, it drops the fixed
entries and never adds one. State findings are never baselined. The recommended path is the sweep to zero.

A project that has never written `context/state.json` (it adopted the package before the file existed)
gets a note, not a failure: the first run of `wt-roadmap.py`, `softure-archive` or `softure-roadmap`
creates it. Fix a stale or missing file with `npx softure-skills state` (or
`python3 .claude/skills/softure-doctor/scripts/context_state.py write`) and commit it.

Piped into a reader that stops early (`doctor --sweep | head`), it ends quietly with exit 141, no traceback.

Importable: `from doctor import run_checks` (takes any reader of context_state).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ci_config  # noqa: E402
from context_state import (  # noqa: E402
    ARCHIVE_ROADMAPS_DIR, CHANGES_DIR, OWNER_SECTION, QUEUED_DIR, RELEASE_SECTION, ROADMAP_PATH, STATE_PATH,
    WORKFLOW_PATH, FsReader, frontmatter, open_checkboxes, parse_status, pending_release_roadmap, quiet_broken_pipe, roadmap_rows,
    read_workflow, sections,
    staleness,
)

ARCHIVE_DIR = "context/archive"
BASELINE_PATH = "context/doctor-baseline.json"
NEVER_BASELINED = ("state-missing", "state-stale", "baseline-stale", "ci-doctor-trigger", "owner-word-wake-invalid")
BACKLOG_DIR = "context/backlog"
CLOSED_STATUSES = ("done", "done_code", "dropped", "carried")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
EMPTY_MERGE = {"—", "-", "–", "n/a", "none", "no merge", "not merged"}
RELEASE_TAG_RE = re.compile(r"(?<![\w.])v?\d+\.\d+\.\d+(?:-[\w.]+)?(?![\w.])")
MERGE_COLUMN_RE = re.compile(r"\bmerge")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INDEX_NAMES = ("README.md", "INDEX.md")
_PATH = r"(?:\.{1,2}/)?(?:[\w.-]+/)*[\w.-]+\.md|(?:\.{1,2}/)?(?:[\w.-]+/)+"
WHOLE_PATH_RE = re.compile(r"(?P<tick>`?)(?P<path>" + _PATH + r")(?P=tick)")  # a cell that is only a path
FILE_COLUMN_RE = re.compile(r"\b(?:files?|paths?|documents?|docs?|links?|artifacts?)\b")


class Finding:
    def __init__(self, code: str, path: str, message: str, severity: str = "fail") -> None:
        self.code, self.path, self.message, self.severity = code, path, message, severity

    def as_dict(self) -> dict:
        return {"code": self.code, "path": self.path, "message": self.message, "severity": self.severity}

    def __str__(self) -> str:
        label = {"fail": "FAIL", "baselined": "baselined"}.get(self.severity, "note")
        return f"{label} {self.code} {self.path}: {self.message}"


def _files(reader, directory: str, pattern: str) -> list[str]:
    return [f"{directory}/{name}" for name, is_dir in reader.listdir(directory)
            if not is_dir and re.match(pattern, name)]


def _archived_roadmaps(reader) -> list[str]:
    """Archived roadmap files: `<date>-roadmap*.md` in foundation/archive/ that carry a roadmap table."""
    paths = _files(reader, ARCHIVE_ROADMAPS_DIR, r"^\d{4}-\d{2}-\d{2}-roadmap.*\.md$")
    return [path for path in paths if roadmap_rows(reader.read(path) or "")]


def check_main_roadmap(reader) -> list[Finding]:
    findings: list[Finding] = []
    text = reader.read(ROADMAP_PATH)
    if text is None:
        return findings
    meta = frontmatter(text)
    slug, version = meta.get("roadmap"), meta.get("version")
    if slug:
        for path in _archived_roadmaps(reader):
            archived = frontmatter(reader.read(path) or "")
            if archived.get("roadmap") == slug and (not version or not archived.get("version")
                                                    or archived.get("version") == version):
                findings.append(Finding("roadmap-archived-not-removed", ROADMAP_PATH,
                                        f"roadmap `{slug}` is already archived as {path}; remove roadmap.md "
                                        "(the close moves it, WORKFLOW §5.2)"))
                break
    rows = roadmap_rows(text)
    status = meta.get("status")
    open_rows = [row["id"] for row in rows if row["status"] not in CLOSED_STATUSES]
    if status == "done" and open_rows:
        findings.append(Finding("roadmap-status-mismatch", ROADMAP_PATH,
                                f"status is done but rows are open: {', '.join(open_rows)}"))
    if status == "waiting":
        findings.append(Finding("roadmap-status-mismatch", ROADMAP_PATH,
                                "status is waiting, which belongs to a queued roadmap; the main roadmap is "
                                "draft, ready or done (a promote sets ready)"))
    return findings


def check_archived_changes(reader) -> list[Finding]:
    findings: list[Finding] = []
    for name, is_dir in reader.listdir(ARCHIVE_DIR):
        if not is_dir:
            continue
        folder = f"{ARCHIVE_DIR}/{name}"
        change = reader.read(f"{folder}/change.md")
        if change is not None:
            status = frontmatter(change).get("status")
            if status != "archived":
                findings.append(Finding("archived-change-status", f"{folder}/change.md",
                                        f"status is {status or 'missing'}, expected archived"))
        plan = reader.read(f"{folder}/plan.md")
        if plan is not None:
            open_items = unticked_automated(plan)
            if open_items:
                listed = "; ".join(open_items[:3]) + ("; …" if len(open_items) > 3 else "")
                findings.append(Finding("archived-change-progress", f"{folder}/plan.md",
                                        f"{len(open_items)} unticked Automated item(s) in ## Progress: {listed}"))
    return findings


DROP_WORDS = r"(?:dropped|cancell?ed|not applicable|n/a|obsolete|won't do|wontfix|skipped|replaced by)"
DROP_NOTE_RE = re.compile(r"\s+(?:—|–|--?)\s+(?P<note>" + DROP_WORDS + r"\b.*)$", re.IGNORECASE)
DROP_PAREN_RE = re.compile(r"\s*\((?P<note>" + DROP_WORDS + r"\b[^)]*)\)\s*$", re.IGNORECASE)
STRUCK_RE = re.compile(r"^~~(?P<body>.+?)~~(?P<rest>.*)$")


def dropped_item(text: str) -> tuple[str, str] | None:
    """(item, note) when a checkbox text says the item was dropped; None otherwise.

    Dropped by its own text: struck through (`~~1.1 ...~~`, with or without a note after it), or carrying an
    explicit note after a dash or in parentheses (`— cancelled, replaced by 1.12`, `(not applicable)`).
    """
    text = text.strip()
    struck = STRUCK_RE.match(text)
    if struck:
        rest = re.sub(r"^\s*(?:—|–|--?|:)?\s*", "", struck.group("rest")).strip()
        return struck.group("body").strip(), rest or "struck through, no reason recorded"
    for pattern in (DROP_NOTE_RE, DROP_PAREN_RE):
        found = pattern.search(text)
        if found and found.start() > 0:
            return text[:found.start()].strip(), found.group("note").strip()
    return None


def dropped_line(text: str) -> str | None:
    """The normalised `~~<item>~~ — dropped: <note>` for a dropped checkbox text; None when it is not dropped."""
    found = dropped_item(text)
    if not found:
        return None
    item, note = found
    note = re.sub(r"^dropped\s*:?\s*", "", note, flags=re.IGNORECASE) or "no reason recorded"
    return f"~~{item}~~ — dropped: {note}"


def unticked_automated(plan: str) -> list[str]:
    """Open `- [ ]` items of `## Progress` that are not under a `#### Manual` heading and not dropped.

    Open Manual items are legitimate in an archived plan (manual mode carries them to the owner). An item
    struck through or carrying a dropped/cancelled/not-applicable note is dropped by its own text.
    """
    progress = sections(plan).get("Progress", [])
    open_items = []
    manual = False
    for line in progress:
        if line.startswith("#### "):
            manual = line[5:].strip().lower().startswith("manual")
            continue
        if line.startswith("### "):
            manual = False
            continue
        match = re.match(r"^\s*- \[ \] (.+)$", line)
        if match and not manual and not dropped_item(match.group(1)):
            open_items.append(match.group(1).strip())
    return open_items


def open_checks(text: str, include_release: bool = True) -> list[str]:
    """Unticked entries of an archived roadmap's owner section (and its pre-release section)."""
    parts = sections(text)
    found = open_checkboxes(parts.get(OWNER_SECTION, []))
    if include_release:
        found += open_checkboxes(parts.get(RELEASE_SECTION, []))
    return found


# A carry marker: the line says which roadmap took the entry over (`→ roadmap-later`, `carried to
# roadmaps/roadmap-later.md`, `carried over to roadmap.md`).
CARRY_RE = re.compile(r"(?:→|->|\bcarried(?:\s+over)?\s+to)\s*\**\s*`?(?P<target>(?:[\w.-]+/)*roadmap"
                      r"(?:-[A-Za-z0-9][\w-]*?(?:\.md)?|\.md))(?![\w-])`?", re.IGNORECASE)


def carry_target(text: str) -> str | None:
    """The roadmap a carry marker in `text` names (as written), or None."""
    match = CARRY_RE.search(text or "")
    return match.group("target") if match else None


def resolve_carry(reader, target: str | None) -> str | None:
    """The file of the roadmap a carry marker names, when it exists (queued, archived, or the live one)."""
    if not target:
        return None
    name = target.rsplit("/", 1)[-1]
    if name == "roadmap.md":
        text = reader.read(ROADMAP_PATH)
        return ROADMAP_PATH if text is not None else None
    slug = name[len("roadmap-"):]
    slug = slug[:-3] if slug.endswith(".md") else slug
    queued = f"{QUEUED_DIR}/roadmap-{slug}.md"
    if reader.read(queued) is not None:
        return queued
    live = reader.read(ROADMAP_PATH)
    if live is not None and frontmatter(live).get("roadmap") == slug:
        return ROADMAP_PATH
    for path in _files(reader, ARCHIVE_ROADMAPS_DIR, r"^\d{4}-\d{2}-\d{2}-roadmap.*\.md$"):
        if frontmatter(reader.read(path) or "").get("roadmap") == slug or path.endswith(f"roadmap-{slug}.md"):
            return path
    return None


def check_archived_roadmaps(reader) -> list[Finding]:
    findings: list[Finding] = []
    pending = pending_release_roadmap(reader)
    for path in _archived_roadmaps(reader):
        text = reader.read(path) or ""
        open_rows = [f"{row['id']} ({row['status']})" for row in roadmap_rows(text)
                     if row["status"] not in CLOSED_STATUSES]
        if open_rows:
            findings.append(Finding("archived-roadmap-open-items", path,
                                    f"rows not done, done_code, dropped or carried: {', '.join(open_rows)}"))
        checks = open_checks(text, include_release=path != pending)
        if checks:
            listed = "; ".join(checks[:3]) + ("; …" if len(checks) > 3 else "")
            findings.append(Finding("archived-roadmap-open-checks", path,
                                    f"{len(checks)} unticked owner entr{'y' if len(checks) == 1 else 'ies'} in an "
                                    f"archived roadmap (settle, mark obsolete or carry over): {listed}"))
        bad = summary_placeholders(text)
        if bad:
            findings.append(Finding("archived-roadmap-summary", path,
                                    "## Summary merge column holds placeholders instead of merge SHAs or outcomes: "
                                    + "; ".join(bad[:4])))
    return findings


def summary_rows(text: str) -> list[dict]:
    """Rows of the item table under `## Summary`: the table whose header has a merge column.

    Other tables under `## Summary` (finding numbers, test counts) are not the item table and are skipped.
    Each row: `line` (1-based in `text`), `text`, `item` (first cell), `cell` (the merge cell) and `ok`.
    """
    rows: list[dict] = []
    in_summary = False
    header: list[str] | None = None
    merge = None
    for number, line in enumerate((text or "").split("\n"), start=1):
        if line.startswith("## "):
            in_summary = line[3:].strip() == "Summary"
            header = None
            continue
        if not in_summary:
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = _table_cells(line)
        if header is None:
            header = [cell.strip("*` ").lower() for cell in cells]
            merge = next((index for index, name in enumerate(header) if MERGE_COLUMN_RE.search(name)), None)
            continue
        if merge is None or _is_separator(cells):
            continue
        cell = cells[merge] if merge < len(cells) else ""
        rows.append({"line": number, "text": line, "item": cells[0], "cell": cell, "ok": merge_cell_ok(cell)})
    return rows


def merge_cell_ok(cell: str) -> bool:
    """A merge cell records an outcome: a SHA, a release tag, carried/dropped, or a dash (with or without a reason)."""
    value = cell.strip("`* ").lower()
    if SHA_RE.search(cell) or RELEASE_TAG_RE.search(cell):
        return True
    if value in EMPTY_MERGE or value[:1] in ("—", "–", "-"):
        return True
    return bool(re.match(r"(?:carried|dropped|obsolete|superseded|cancell?ed|not merged|no merge)\b", value))


def summary_placeholders(text: str) -> list[str]:
    """Item-table rows of `## Summary` whose merge cell is a placeholder, not an outcome."""
    return [f"{row['item']}: \"{row['cell']}\"" for row in summary_rows(text) if not row["ok"]]


ITEM_BLOCK_RE = re.compile(r"^###\s+\*{0,2}(?P<id>[A-Z]+-\d+)\*{0,2}\s*:\s*(?P<title>.*\S)?\s*$")
BLOCK_STATUS_RE = re.compile(r"^- \*\*Status:\*\*\s*(?P<status>.+)$")
STATUS_VOCABULARY = ("proposed", "ready", "blocked", "in_progress", "ready_to_merge", "done", "done_code",
                     "dropped", "carried")


def item_blocks(text: str) -> list[dict]:
    """`### <ID>: <title>` blocks with the status keyword of their `- **Status:**` line (None when it has none)."""
    blocks: list[dict] = []
    current = None
    for line in (text or "").splitlines():
        heading = ITEM_BLOCK_RE.match(line)
        if heading:
            current = {"id": heading.group("id"), "title": heading.group("title"), "status": None}
            blocks.append(current)
            continue
        if line.startswith("#"):
            current = None
            continue
        status = BLOCK_STATUS_RE.match(line)
        if current is not None and status and current["status"] is None:
            current["status"] = parse_status(status.group("status"))["status"]
    return blocks


def roadmap_shape(path: str, text: str) -> list[Finding]:
    """What keeps a live roadmap readable by scripts and apps: a row for every item, statuses they understand."""
    rows = roadmap_rows(text)
    blocks = item_blocks(text)
    findings: list[Finding] = []
    if blocks and not rows:
        return [Finding("roadmap-item-shape", path,
                        f"{len(blocks)} item blocks but no at-a-glance row (`| **<ID>** | `<change-id>` | ... | "
                        "<status> |`); readers and context/state.json see no item (WORKFLOW §5)")]
    row_ids = {row["id"]: row for row in rows}
    unknown = [f"{row['id']} ({row['status']})" for row in rows if row["status"] not in STATUS_VOCABULARY]
    if unknown:
        findings.append(Finding("roadmap-item-shape", path,
                                f"row status outside the vocabulary: {', '.join(unknown)}; use one of "
                                f"{', '.join(STATUS_VOCABULARY)} (WORKFLOW §5)"))
    orphans = [block["id"] for block in blocks if block["id"] not in row_ids]
    if orphans:
        findings.append(Finding("roadmap-item-shape", path,
                                f"item blocks without an at-a-glance row: {', '.join(orphans)}; add the row "
                                "(readers list items from the table only)"))
    contradicting = [f"{block['id']} (block {block['status']}, row {row_ids[block['id']]['status']})"
                     for block in blocks if block["id"] in row_ids and block["status"] is not None
                     and block["status"] != row_ids[block["id"]]["status"]]
    if contradicting:
        findings.append(Finding("roadmap-item-shape", path,
                                f"item block status contradicts its row: {', '.join(contradicting)}; the block "
                                "mirrors the row (WORKFLOW §5)"))
    untitled = [block["id"] for block in blocks if not block["title"]]
    if untitled:
        findings.append(Finding("roadmap-item-shape", path,
                                f"item blocks without a title: {', '.join(untitled)} (`### <ID>: <title>`)"))
    return findings


def check_roadmap_shape(reader) -> list[Finding]:
    findings: list[Finding] = []
    for path in [ROADMAP_PATH, *_files(reader, QUEUED_DIR, r"^roadmap-.+\.md$")]:
        text = reader.read(path)
        if text is not None:
            findings += roadmap_shape(path, text)
    return findings


def check_queued_and_backlog(reader) -> list[Finding]:
    findings: list[Finding] = []
    queued_slugs = set()
    for path in _files(reader, QUEUED_DIR, r"^roadmap-.+\.md$"):
        text = reader.read(path) or ""
        slug = os.path.basename(path)[len("roadmap-"):-len(".md")]
        queued_slugs.add(slug)
        rows = roadmap_rows(text)
        if rows and all(row["status"] in ("done", "done_code") for row in rows):
            findings.append(Finding("queued-roadmap-done", path,
                                    f"all {len(rows)} rows are done but the roadmap is still queued; "
                                    "archive it to foundation/archive/ (WORKFLOW §5.2)"))
    main = frontmatter(reader.read(ROADMAP_PATH) or "")
    for name, is_dir in reader.listdir(BACKLOG_DIR):
        if not is_dir or not name.startswith("roadmap-"):
            continue
        slug = name[len("roadmap-"):]
        promoted = main.get("roadmap") == slug or (main.get("backlog") or "").rstrip("/").endswith(name)
        if slug not in queued_slugs and not promoted:
            findings.append(Finding("backlog-without-roadmap", f"{BACKLOG_DIR}/{name}/",
                                    f"no {QUEUED_DIR}/roadmap-{slug}.md and the main roadmap is not `{slug}`; "
                                    "move live entries to a queued roadmap or remove the folder (WORKFLOW §5.1)"))
    return findings


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell) and any(cells)


def missing_index_targets(reader) -> list[dict]:
    """Every real link in an index row (README.md / INDEX.md table under context/) whose target does not exist.

    A real link is a markdown link anywhere in the row, or a cell whose whole content is a path (in backticks
    or bare) in a column that indexes files (`File`, `Path`, `Document`, `Link`, ...). A path merely mentioned
    in a description cell (see `change.md`) is not a link and never fails.

    Each entry: `path` (the index), `line` (1-based), `text` (the line), `kind` (`link` or `code`), `target`
    (as written), `base` (the index folder) and `candidates` (the repository paths the target may mean).
    """
    out: list[dict] = []
    for path in _walk(reader, "context"):
        if os.path.basename(path) not in INDEX_NAMES:
            continue
        base = os.path.dirname(path)
        header: list[str] | None = None
        for number, line in enumerate((reader.read(path) or "").splitlines(), start=1):
            if not line.strip().startswith("|"):
                header = None
                continue
            cells = _table_cells(line)
            if header is None:
                header = [cell.strip("*` ").lower() for cell in cells]
                continue
            if _is_separator(cells):
                continue
            for target in LINK_RE.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                    continue
                rel = target.split("#", 1)[0]
                if not rel:
                    continue
                resolved = os.path.normpath(os.path.join(base, rel)).replace(os.sep, "/")
                if resolved.startswith("..") or not resolved.startswith("context/"):
                    continue  # outside context/: not this check's business
                if not reader.exists(resolved.rstrip("/")):
                    out.append({"path": path, "line": number, "text": line, "kind": "link", "target": target,
                                "base": base, "candidates": [resolved.rstrip("/")]})
            for column, cell in enumerate(cells):
                if column >= len(header) or not FILE_COLUMN_RE.search(header[column]):
                    continue
                whole = WHOLE_PATH_RE.fullmatch(cell)
                if not whole:
                    continue
                target = whole.group("path")
                # A path cell: relative to the index, to context/ or to the repository root.
                candidates = [os.path.normpath(os.path.join(prefix, target)).replace(os.sep, "/").rstrip("/")
                              for prefix in (base, "context", ".")]
                inside = [c for c in candidates if c.startswith("context/")]
                if inside and not any(reader.exists(c) for c in inside):
                    out.append({"path": path, "line": number, "text": line, "kind": "code", "target": target,
                                "base": base, "candidates": inside})
    return out


def check_indexes(reader) -> list[Finding]:
    findings: list[Finding] = []
    for missing in missing_index_targets(reader):
        verb = "links" if missing["kind"] == "link" else "names"
        findings.append(Finding("index-missing-file", missing["path"],
                                f"row {verb} `{missing['target']}`, which does not exist"))
    return findings


def _walk(reader, directory: str) -> list[str]:
    out = []
    for name, is_dir in reader.listdir(directory):
        path = f"{directory}/{name}"
        if is_dir:
            out += _walk(reader, path)
        else:
            out.append(path)
    return out


def ever_written(root: str | None) -> bool | None:
    """Whether git history has ever held context/state.json; None when that cannot be told."""
    if not root:
        return None
    probe = subprocess.run(["git", "-C", root, "rev-parse", "--is-shallow-repository"],
                           capture_output=True, text=True)
    if probe.returncode != 0 or probe.stdout.strip() == "true":
        return None
    log = subprocess.run(["git", "-C", root, "log", "--all", "-1", "--format=%H", "--", STATE_PATH],
                         capture_output=True, text=True)
    return log.returncode == 0 and bool(log.stdout.strip())


def check_state(reader, root: str | None) -> list[Finding]:
    if not reader.exists("context"):
        return []
    problem = staleness(reader)
    if problem is None:
        return []
    if problem == "missing":
        if ever_written(root):
            return [Finding("state-missing", STATE_PATH,
                            "missing, but git history holds it: regenerate it (`npx softure-skills state`) and commit")]
        return [Finding("state-missing", STATE_PATH,
                        "not written yet; the next wt-roadmap.py, softure-archive or softure-roadmap run creates it",
                        severity="note")]
    return [Finding("state-stale", STATE_PATH,
                    f"{problem}; regenerate it (`npx softure-skills state`) and commit")]


def check_ci(reader) -> list[Finding]:
    """The `context-doctor` job must run on every push to the main branch: readers look for its check run there."""
    branches = ci_config.main_branches_from(reader)
    return [Finding("ci-doctor-trigger", path, f"{'; '.join(found)}; {ci_config.fix_text(branches[0])}")
            for path, found in ci_config.check(reader, branches)]


OWNER_WORD_WAKES = ("routine", "heartbeat", "none")


def check_owner_word_wake(reader) -> list[Finding]:
    """How owner-word issues wake the project (WORKFLOW §8.6): declared, since the routine is not in the repository."""
    workflow = read_workflow(reader)
    autonomy = workflow.get("autonomy") if isinstance(workflow.get("autonomy"), dict) else {}
    if "ownerWordWake" not in autonomy:
        if workflow.get("mode") != "autonomous":
            return []
        return [Finding("owner-word-wake-undeclared", WORKFLOW_PATH,
                        'autonomy.ownerWordWake is not set: declare "routine" (routines/owner-word-wake.md is set up), '
                        '"heartbeat" or "none" (WORKFLOW.md §8.6)', severity="note")]
    value = autonomy["ownerWordWake"]
    if value in OWNER_WORD_WAKES:
        return []
    return [Finding("owner-word-wake-invalid", WORKFLOW_PATH,
                    f'autonomy.ownerWordWake is {json.dumps(value)}; use "routine", "heartbeat" or "none" '
                    "(WORKFLOW.md §8.6)")]


def run_checks(reader, root: str | None = None, baseline: bool = True) -> list[Finding]:
    """Every finding for the project `reader` sees. `root` (a git checkout) enables the history check.

    With `baseline` (the default) a failure listed in context/doctor-baseline.json is reported with severity
    `baselined` instead of `fail`, and a listed failure that no longer occurs is a `baseline-stale` failure.
    """
    if not reader.exists("context"):
        return []
    findings: list[Finding] = []
    for check in (check_main_roadmap, check_archived_changes, check_archived_roadmaps,
                  check_queued_and_backlog, check_roadmap_shape, check_indexes, check_ci, check_owner_word_wake):
        findings += check(reader)
    findings += check_state(reader, root)
    return apply_baseline(reader, findings) if baseline else findings


def _key(code: str, path: str) -> tuple[str, str]:
    return code, path


def read_baseline(reader) -> tuple[list[dict] | None, str | None]:
    """(entries, problem): entries None when there is no baseline; problem when the file is unreadable."""
    raw = reader.read(BASELINE_PATH)
    if raw is None:
        return None, None
    try:
        data = json.loads(raw)
        entries = data["entries"]
        if not isinstance(entries, list) or not all(isinstance(e, dict) and "code" in e and "path" in e
                                                    for e in entries):
            raise ValueError("entries must be objects with code and path")
        return entries, None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return [], f"not a valid baseline ({exc}); restore it from git or remove it"


def apply_baseline(reader, findings: list[Finding]) -> list[Finding]:
    entries, problem = read_baseline(reader)
    if entries is None:
        return findings
    if problem:
        return findings + [Finding("baseline-stale", BASELINE_PATH, problem)]
    accepted = {_key(entry["code"], entry["path"]) for entry in entries}
    present = set()
    out = []
    for finding in findings:
        key = _key(finding.code, finding.path)
        if finding.severity == "fail" and key in accepted and finding.code not in NEVER_BASELINED:
            present.add(key)
            out.append(Finding(finding.code, finding.path, finding.message, severity="baselined"))
        else:
            out.append(finding)
    for entry in entries:
        key = _key(entry["code"], entry["path"])
        if key not in present:
            out.append(Finding("baseline-stale", BASELINE_PATH,
                               f"`{entry['code']} {entry['path']}` is fixed but still in the baseline: remove the "
                               "entry (`doctor --baseline` rewrites the file without it)"))
    return out


def build_baseline(reader, root: str | None) -> tuple[dict, dict]:
    """The baseline file to write and what changed: {"kept", "dropped", "refused"} (lists of keys)."""
    import datetime as dt

    failures = [f for f in run_checks(reader, root, baseline=False)
                if f.severity == "fail" and f.code not in NEVER_BASELINED]
    current: dict[tuple, Finding] = {}
    for finding in failures:
        current.setdefault(_key(finding.code, finding.path), finding)
    previous, problem = read_baseline(reader)
    if problem:
        raise ValueError(f"{BASELINE_PATH}: {problem}")
    if previous is None:
        keep = list(current)
        dropped: list[tuple] = []
        refused: list[tuple] = []
        created = dt.date.today().isoformat()
    else:
        old = [_key(entry["code"], entry["path"]) for entry in previous]
        keep = [key for key in old if key in current]
        dropped = [key for key in old if key not in current]
        refused = [key for key in current if key not in old]
        created = (json.loads(reader.read(BASELINE_PATH) or "{}").get("created")) or dt.date.today().isoformat()
    data = {
        "note": "Last resort (WORKFLOW §12.2): failures accepted while the history is swept. It only shrinks: "
                "`doctor --baseline` drops fixed entries and never adds one. The goal is an empty file, then none.",
        "created": created,
        "entries": [{"code": key[0], "path": key[1], "message": current[key].message} for key in sorted(keep)],
    }
    return data, {"kept": keep, "dropped": dropped, "refused": refused}


def _take(args: list[str], flag: str) -> bool:
    if flag in args:
        args.remove(flag)
        return True
    return False


def run_fix(reader, root: str, git_root: str | None, write: bool, as_json: bool) -> int:
    """`--fix`: print (and with `write` apply) the mechanical repairs; exit 0."""
    import doctor_fix

    plan = doctor_fix.plan_fixes(reader, git_root)
    after = FsReader(root, plan["files"])
    remaining = [f for f in run_checks(after, git_root, baseline=False) if f.severity == "fail"]
    if write and plan["files"]:
        doctor_fix.apply_fixes(root, plan["files"])
    if as_json:
        print(json.dumps({"root": root, "written": write, "edits": plan["edits"], "skipped": plan["skipped"],
                          "remaining": [f.as_dict() for f in remaining]}, indent=2))
        return 0
    mode = "applied" if write else "dry run"
    print(f"softure-doctor --fix ({mode}): {len(plan['edits'])} edit(s) in {len(plan['files'])} file(s)")
    for edit in plan["edits"]:
        line = f":{edit['line']}" if edit.get("line") else ""
        print(f"edit {edit['path']}{line}: {edit['what']}")
    for skip in plan["skipped"]:
        print(f"skip {skip['path']}: `{skip['target']}`: {skip['why']}")
    print(f"after these edits: {len(remaining)} failure(s) remain"
          + (" (`doctor --sweep` lists them with evidence)" if remaining else ""))
    if plan["files"] and not write:
        print("run again with --write to apply")
    return 0


def run_baseline(reader, root: str, git_root: str | None) -> int:
    """`--baseline`: write context/doctor-baseline.json; it never grows once it exists."""
    try:
        data, change = build_baseline(reader, git_root)
    except ValueError as exc:
        print(f"softure-doctor --baseline: {exc}", file=sys.stderr)
        return 1
    target = os.path.join(root, BASELINE_PATH)
    if not data["entries"]:
        if os.path.exists(target):
            os.remove(target)
            print(f"softure-doctor --baseline: every entry is fixed; removed {BASELINE_PATH}")
        else:
            print("softure-doctor --baseline: nothing fails, no baseline written")
        return 0
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"softure-doctor --baseline: wrote {BASELINE_PATH} with {len(data['entries'])} entr"
          f"{'y' if len(data['entries']) == 1 else 'ies'} (last resort: sweep them to zero, WORKFLOW §12.2)")
    for key in change["dropped"]:
        print(f"dropped (fixed): {key[0]} {key[1]}")
    for key in change["refused"]:
        print(f"not added (the baseline only shrinks; fix it): {key[0]} {key[1]}")
    return 1 if change["refused"] else 0


def run_sweep(reader, root: str, git_root: str | None, as_json: bool, use_forge: bool = True) -> int:
    """`--sweep`: the worklist of every failure with its evidence; exit 1 while anything is left."""
    import doctor_sweep

    entries = doctor_sweep.sweep(reader, git_root, doctor_sweep.Forge(git_root, enabled=use_forge))
    owner = [entry for entry in entries if entry["class"] == "owner"]
    superseded = [entry for entry in entries if entry["class"] == "superseded"]
    forge = [entry for entry in entries if entry["class"] == "forge"]
    with_evidence = len(entries) - len(owner) - len(superseded) - len(forge)
    if as_json:
        print(json.dumps({"root": root, "entries": entries,
                          "summary": {"total": len(entries), "with_evidence": with_evidence,
                                      "superseded": len(superseded), "forge": len(forge), "owner": len(owner)}},
                         indent=2, ensure_ascii=False))
        return 1 if entries else 0
    if not entries:
        print("softure-doctor --sweep: nothing to settle, the context/ contract is OK")
        return 0
    for entry in entries:
        where = f"{entry['path']}:{entry['line']}" if entry.get("line") else entry["path"]
        print(f"{entry['code']} {where}: {entry['subject']}")
        for evidence in entry["evidence"]:
            print(f"    evidence {evidence['kind']} {evidence['ref']}: {evidence['note']}")
        if entry["class"] == "superseded":
            print("    superseded: later work made it obsolete; close it yourself, never forward it")
        if entry["class"] == "forge":
            print("    forge: check it with `gh` before anything goes to the owner")
            for tried in entry["tried"]:
                print(f"    tried: {tried}")
        if entry["owner"]:
            print(f"    owner ({entry['owner_reason']}): only the owner can settle it")
            for tried in entry["tried"]:
                print(f"    tried: {tried}")
        print(f"    settle: {entry['settle']}")
    print(f"softure-doctor --sweep: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to settle, "
          f"{with_evidence} with evidence, {len(superseded)} superseded, {len(forge)} to check with the forge, "
          f"{len(owner)} for the owner")
    return 1


# The annotation that lists every failure code of a run; readers of the check run (portfolio --source api) find it
# by this title. GitHub keeps only the first few annotations of a step, so the codes come first, in one annotation.
# The same list is printed as one plain line, `CI_CODES_TITLE: <codes>`, into the job's log: annotations need the
# Checks permission, which a fine-grained token cannot hold, while the job log needs only Actions: read.
CI_CODES_TITLE = "context-doctor failure codes"
CI_ANNOTATION_LIMIT = 9


def failure_codes(failures: list[Finding]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for failure in failures:
        counts[failure.code] = counts.get(failure.code, 0) + 1
    return sorted(counts.items())


def _escape(value: str, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if property_value else value


def report_to_ci(failures: list[Finding], env: dict | None = None, out=None) -> None:
    """In GitHub Actions: the failure codes as annotations of the check run, and a job summary.

    The first annotation (title `CI_CODES_TITLE`) lists every code with its count, so a reader of the check run
    through the forge API gets the codes without a checkout; one annotation per failure follows, up to the limit.
    The same list goes into the job log as the plain line `CI_CODES_TITLE: <codes>` for a reader with Actions: read
    only (a fine-grained token on a private repository cannot read check runs).
    The job summary (`$GITHUB_STEP_SUMMARY`) holds the same table. Outside Actions nothing changes.
    """
    env = os.environ if env is None else env
    out = out or sys.stdout
    if env.get("GITHUB_ACTIONS") != "true":
        return
    codes = failure_codes(failures)
    if codes:
        listed = ", ".join(f"{code} ({count})" for code, count in codes)
        print(f"::error title={_escape(CI_CODES_TITLE, True)}::{_escape(listed)}", file=out)
        print(f"{CI_CODES_TITLE}: {listed}", file=out)
        for failure in failures[:CI_ANNOTATION_LIMIT]:
            print(f"::error file={_escape(failure.path, True)},title={_escape(failure.code, True)}::"
                  f"{_escape(failure.message)}", file=out)
    target = env.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    lines = ["### context-doctor", ""]
    if codes:
        lines += [f"{len(failures)} problem(s) in the context/ contract (WORKFLOW.md §12).", "",
                  "| Code | Count | First path |", "| --- | --- | --- |"]
        for code, count in codes:
            first = next(failure.path for failure in failures if failure.code == code)
            lines.append(f"| `{code}` | {count} | `{first}` |")
    else:
        lines.append("context/ contract OK")
    try:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    as_json = _take(args, "--json")
    fix = _take(args, "--fix")
    write = _take(args, "--write")
    do_sweep = _take(args, "--sweep")
    no_forge = _take(args, "--no-forge")
    do_baseline = _take(args, "--baseline")
    root = None
    if "--root" in args:
        k = args.index("--root")
        root = os.path.abspath(args[k + 1])
        del args[k:k + 2]
    if args or (write and not fix) or sum((fix, do_sweep, do_baseline)) > 1 or (no_forge and not do_sweep):
        print(__doc__, file=sys.stderr)
        return 2
    top = subprocess.run(["git", "-C", root or os.getcwd(), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    toplevel = os.path.realpath(top.stdout.strip()) if top.returncode == 0 else None
    root = root or toplevel or os.getcwd()
    git_root = root if toplevel and toplevel == os.path.realpath(root) else None
    reader = FsReader(root)
    if not reader.exists("context"):
        if as_json:
            print(json.dumps({"root": root, "failures": [], "notes": ["no context/ directory"]}, indent=2))
        else:
            print(f"softure-doctor: no context/ directory in {root}, nothing to check")
        return 0
    if fix:
        return run_fix(reader, root, git_root, write, as_json)
    if do_sweep:
        return run_sweep(reader, root, git_root, as_json, use_forge=not no_forge)
    if do_baseline:
        return run_baseline(reader, root, git_root)
    findings = run_checks(reader, git_root)
    failures = [f for f in findings if f.severity == "fail"]
    if as_json:
        print(json.dumps({"root": root, "failures": [f.as_dict() for f in failures],
                          "notes": [f.as_dict() for f in findings if f.severity != "fail"]}, indent=2))
        return 1 if failures else 0
    for finding in findings:
        print(finding)
    report_to_ci(failures)
    baselined = sum(1 for f in findings if f.severity == "baselined")
    if baselined:
        print(f"softure-doctor: {baselined} failure(s) accepted by {BASELINE_PATH} (last resort; sweep them to zero)")
    if failures:
        print(f"softure-doctor: {len(failures)} problem(s) in the context/ contract (WORKFLOW.md §12)")
        mechanical = sum(1 for f in failures if f.code in ("archived-change-status", "index-missing-file"))
        if mechanical:
            print(f"softure-doctor: {mechanical} of them may be mechanical: `doctor --fix` shows the edits")
        return 1
    print("softure-doctor: context/ contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(quiet_broken_pipe(main))
