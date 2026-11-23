"""Settle the context after a release and its deploy: the text side of `wt-roadmap.py released <tag>`.

`settle(read, carried, tag, tag_date, today, ...)` returns the files to write (path -> text, None: remove) without
touching git; `wt-roadmap.py` builds the commit. What a release settles (WORKFLOW.md §5.2):

- every row `done_code (…; waiting: release)` whose change the tag carries (its archived change folder is in the
  tag's tree) loses the release part of its waiting text: `done` when nothing else waits, else `done_code` with the
  rest. Its item block follows, and its `## Done` line gets `released: <tag>` as the evidence;
- open `## Owner decisions and checks` entries that name a release or a deploy, and open `## Before the next release`
  steps, of a carried item (or of no item) are ticked `— done: <tag>`;
- the live roadmap, once every row is `done` (or `dropped`) and its header orders "Archive roadmap: at the end", is
  closed: `## Summary` (merge SHA per row), the `Release:` line, moved to `foundation/archive/<date>-roadmap.md`;
- a roadmap closed before its release (the newest archived one without a `Release:` line) gets the same settling and
  its `Release: <tag> (<date>)` line, so the owner queue stops reading its pre-release steps.
"""
from __future__ import annotations

import re
from typing import Callable

ROADMAP = "context/foundation/roadmap.md"
ARCHIVE_DIR = "context/foundation/archive"
CHANGES_DIR = "context/changes"
BACKLOG_DIR = "context/backlog"
OWNER_SECTION = "Owner decisions and checks"
RELEASE_SECTION = "Before the next release"

ROW_RE = re.compile(r"^\|\s*\*\*(?P<id>[A-Z]+-\d+)\*\*\s*\|")
DONE_CODE_RE = re.compile(r"^done_code \((?P<date>[0-9-]+; )?waiting: (?P<waiting>.+)\)$")
RELEASE_WORD_RE = re.compile(r"\b(releas\w*|deploy\w*)\b", re.IGNORECASE)
OPEN_RE = re.compile(r"^- \[ \] (?P<text>.+?)\s*$")
ITEM_REF_RE = re.compile(r"\*\*(?P<id>[A-Z]+-\d+)\*\*")
ARCHIVE_ORDER_RE = re.compile(r"Archive roadmap:\s*at the end", re.IGNORECASE)
RELEASE_LINE_RE = re.compile(r"^(?:- )?\**Release:?\**:?\s*v?\d+\.\d+\.\d+")
ARCHIVED_ROADMAP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-roadmap.*\.md$")
SKIP_IN_CHANGES = {"README.md", ".gitkeep"}


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def plain_status(line: str) -> str:
    return cells(line)[-1].replace("**", "").strip()


def set_status(line: str, status: str) -> str:
    head, _, _ = line.rstrip("\n").rstrip().rstrip("|").rpartition("|")
    return f"{head}| {status} |\n"


def strip_release(waiting: str) -> tuple[bool, str | None]:
    """(`waiting` named a release, what still waits). Owner steps keep their words ("owner step: deploy key")."""
    parts = [part.strip() for part in re.split(r"[;,]", waiting) if part.strip()]
    kept = [part for part in parts if part.lower().startswith("owner") or not RELEASE_WORD_RE.search(part)]
    return len(kept) != len(parts), "; ".join(kept) or None


def section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    start = next((k for k, line in enumerate(lines) if line.rstrip() == f"## {heading}"), None)
    if start is None:
        return None
    end = next((k for k in range(start + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    return start, end


def append_line(lines: list[str], heading: str, entry: str) -> None:
    """Append `entry` at the end of `## <heading>` (created at the end of the file when missing)."""
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    bounds = section_bounds(lines, heading)
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend([f"## {heading}\n", f"{entry}\n"])
        return
    start, end = bounds
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, f"{entry}\n")


def open_entries(lines: list[str], heading: str) -> list[int]:
    bounds = section_bounds(lines, heading)
    if bounds is None:
        return []
    return [k for k in range(bounds[0] + 1, bounds[1]) if OPEN_RE.match(lines[k])]


def rows(lines: list[str]) -> list[tuple[int, str, str]]:
    """(line index, item ID, change ID) of every at-a-glance row."""
    found = []
    for k, line in enumerate(lines):
        match = ROW_RE.match(line)
        if match:
            parts = cells(line)
            found.append((k, match["id"], parts[1].strip("` ") if len(parts) > 1 else ""))
    return found


def settle_text(text: str, carried: set[str], tag: str) -> tuple[str, list[str]]:
    """Settle one roadmap file for a release of `tag`. Returns (new text, IDs of the rows it settled)."""
    lines = text.splitlines(keepends=True)
    settled: list[str] = []
    carried_ids = {rid for _, rid, cid in rows(lines) if cid in carried}
    for k, rid, cid in rows(lines):
        match = DONE_CODE_RE.match(plain_status(lines[k]))
        if not match or cid not in carried:
            continue
        named, rest = strip_release(match["waiting"])
        if not named:
            continue
        status = f"done_code ({match['date'] or ''}waiting: {rest})" if rest else "done"
        lines[k] = set_status(lines[k], status)
        settled.append(rid)
        block = next((j for j, line in enumerate(lines) if line.strip() == f"- **Change ID:** `{cid}`"), None)
        if block is not None:
            end = next((j for j in range(block + 1, len(lines))
                        if lines[j].startswith(("#", "- **Change ID:**"))), len(lines))
            sidx = next((j for j in range(block + 1, end) if lines[j].startswith("- **Status:**")), None)
            if sidx is None:
                lines.insert(block + 1, f"- **Status:** {status}\n")
            else:
                lines[sidx] = f"- **Status:** {status}\n"
        if rest:
            continue
        prefix = f"- **{rid}** `{cid}`:"
        done = next((j for j, line in enumerate(lines) if line.startswith(prefix)), None)
        if done is None:
            append_line(lines, "Done", f"{prefix} released: {tag}")
        elif "released:" not in lines[done]:
            line = lines[done].rstrip("\n")
            lines[done] = (line.replace("; archived in", f"; released: {tag}; archived in", 1)
                           if "; archived in" in line else f"{line}; released: {tag}") + "\n"

    def answered(entry: str, needs_word: bool) -> bool:
        ref = ITEM_REF_RE.search(entry)
        if ref and ref["id"] not in carried_ids:
            return False
        if not ref and not settled:
            return False  # an entry of no item is answered only by a release that shipped something here
        return not needs_word or bool(RELEASE_WORD_RE.search(entry))

    for heading, needs_word in ((OWNER_SECTION, True), (RELEASE_SECTION, False)):
        for k in open_entries(lines, heading):
            entry = OPEN_RE.match(lines[k])["text"]
            if answered(entry, needs_word):
                lines[k] = f"- [x] {entry} — done: {tag}\n"
    return "".join(lines), settled


def waiting_release(text: str) -> list[str]:
    """IDs of rows that still wait for a release."""
    out = []
    for k, rid, _ in rows(text.splitlines(keepends=True)):
        match = DONE_CODE_RE.match(plain_status(text.splitlines(keepends=True)[k]))
        if match and strip_release(match["waiting"])[0]:
            out.append(rid)
    return out


def has_release_line(text: str) -> bool:
    bounds = section_bounds(text.splitlines(keepends=True), "Summary")
    if bounds is None:
        return False
    lines = text.splitlines()
    return any(RELEASE_LINE_RE.match(line.strip()) for line in lines[bounds[0] + 1:bounds[1]])


def frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{key}:\s*\"?([^\"\n]*)\"?\s*$", text.split("\n---", 1)[0] if text.startswith("---")
                      else "")
    return match.group(1).strip() if match else None


def set_frontmatter(text: str, key: str, value: str) -> str:
    return re.sub(rf"(?m)^{key}: .*$", f"{key}: {value}", text, count=1)


def close_gates(text: str, listdir: Callable[[str], list[tuple[str, bool]]]) -> list[str]:
    """Why the live roadmap cannot be closed by the release (empty: it can)."""
    lines = text.splitlines(keepends=True)
    if not ARCHIVE_ORDER_RE.search(text):
        return ["the header does not order \"Archive roadmap: at the end\""]
    gates = []
    found = rows(lines)
    open_rows = [rid for k, rid, _ in found if plain_status(lines[k]).split(" ")[0] not in ("done", "dropped")]
    if not found or open_rows:
        gates.append(f"rows not done: {', '.join(open_rows) or 'none at all'}")
    left = open_entries(lines, OWNER_SECTION) + open_entries(lines, RELEASE_SECTION)
    if left:
        gates.append(f"{len(left)} open owner or pre-release entr{'y' if len(left) == 1 else 'ies'}")
    changes = [name for name, _ in listdir(CHANGES_DIR) if name not in SKIP_IN_CHANGES]
    if changes:
        gates.append(f"context/changes/ holds {', '.join(changes)} (archive them first)")
    slug = frontmatter_value(text, "roadmap")
    if slug and any(name == f"roadmap-{slug}" for name, _ in listdir(BACKLOG_DIR)):
        gates.append(f"backlog/roadmap-{slug}/ is still there (softure-roadmap --close cleans it up)")
    return gates


def close(text: str, tag: str, tag_date: str, merges: dict[str, str]) -> str:
    """The archived form of a finished roadmap: `status: done`, `## Summary`, the integration and `Release:` lines."""
    lines = text.splitlines(keepends=True)
    table = ["| ID | Item | What changed | Merge |\n", "| --- | --- | --- | --- |\n"]
    for k, rid, cid in rows(lines):
        parts = cells(lines[k])
        outcome = parts[2] if len(parts) > 3 else cid
        dropped = plain_status(lines[k]).startswith("dropped")
        table.append(f"| **{rid}** | `{cid}` | {outcome} | {'dropped' if dropped else merges.get(cid) or tag} |\n")
    out = set_frontmatter("".join(lines).rstrip("\n") + "\n", "status", "done")
    return (out + "\n## Summary\n\n" + "".join(table) + "\n"
            + f"integration: covered by the release {tag}\n\nRelease: {tag} ({tag_date})\n")


def archive_path(exists: Callable[[str], bool], today: str) -> str:
    path = f"{ARCHIVE_DIR}/{today}-roadmap.md"
    n = 2
    while exists(path):
        path = f"{ARCHIVE_DIR}/{today}-roadmap-{n}.md"
        n += 1
    return path


def pending_release(read: Callable[[str], str | None], listdir: Callable[[str], list[tuple[str, bool]]]) -> str | None:
    """The newest archived roadmap with rows whose `## Summary` records no release yet."""
    paths = [f"{ARCHIVE_DIR}/{name}" for name, is_dir in listdir(ARCHIVE_DIR)
             if not is_dir and ARCHIVED_ROADMAP_RE.match(name)]
    paths = [path for path in sorted(paths) if rows((read(path) or "").splitlines(keepends=True))]
    if not paths or has_release_line(read(paths[-1]) or ""):
        return None
    return paths[-1]


def settle(read: Callable[[str], str | None], listdir: Callable[[str], list[tuple[str, bool]]],
           exists: Callable[[str], bool], carried: set[str], tag: str, tag_date: str, today: str,
           merges: Callable[[set[str]], dict[str, str]]) -> tuple[dict[str, str | None], list[str]]:
    """The files a release of `tag` changes, and a report line per thing it did."""
    changes: dict[str, str | None] = {}
    report: list[str] = []

    pending = pending_release(read, listdir)
    if pending:
        old = read(pending) or ""
        new, settled = settle_text(old, carried, tag)
        carries = any(cid in carried for _, _, cid in rows(old.splitlines(keepends=True)))
        if carries and not waiting_release(new):
            lines = new.splitlines(keepends=True)
            append_line(lines, "Summary", f"Release: {tag} ({tag_date})")
            at = next(k for k in range(len(lines) - 1, -1, -1) if lines[k].startswith("Release: "))
            if at > 0 and lines[at - 1].strip():
                lines.insert(at, "\n")
            new = "".join(lines)
            report.append(f"{pending}: release {tag} recorded")
        if new != old:
            changes[pending] = new
            if settled:
                report.append(f"{pending}: {', '.join(settled)} settled by {tag}")

    old = read(ROADMAP)
    status = frontmatter_value(old or "", "status") or ""
    if old is not None and status.lower() != "idle" and (frontmatter_value(old, "roadmap") or "").lower() != "none":
        new, settled = settle_text(old, carried, tag)
        if settled:
            report.append(f"roadmap.md: {', '.join(settled)} settled by {tag}")
        if new != old:
            new = re.sub(r"(?m)^updated: .*$", f"updated: {today}", new, count=1)
        gates = close_gates(new, listdir)
        if not gates:
            cids = {cid for _, _, cid in rows(new.splitlines(keepends=True))}
            target = archive_path(exists, today)
            changes[ROADMAP] = None
            changes[target] = close(new, tag, tag_date, merges(cids))
            report.append(f"roadmap {frontmatter_value(new, 'roadmap') or ''} closed: {target} (release {tag})")
        else:
            if new != old:
                changes[ROADMAP] = new
            if ARCHIVE_ORDER_RE.search(new) and settled:
                report.append("roadmap.md stays open: " + "; ".join(gates))
    return changes, report
