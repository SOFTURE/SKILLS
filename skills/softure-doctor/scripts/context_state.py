#!/usr/bin/env python3
"""Build `context/state.json`: the machine-readable state of a project (WORKFLOW.md §12).

    context_state.py write  [--root <dir>] [--staged]   regenerate context/state.json
    context_state.py print  [--root <dir>] [--staged]   print what `write` would write
    context_state.py check  [--root <dir>]              exit 1 when the file is missing or stale
    context_state.py pin-project [--root <dir>]         write the derived `project` into context/workflow.json

The file is written only by scripts, never by hand: `wt-roadmap.py` (every mode) commits it together
with `roadmap.md`, and `softure-archive` and `softure-roadmap` (record, promote, close) run
`write --staged` right before their commit. `--staged` reads what is staged (the index) instead of
the working tree, so someone else's uncommitted edits never leak into the file, and stages the result.

Everything in the file is derived from the markdown under `context/` (and `context/workflow.json`):
the active roadmap, the queued roadmaps, the change folders, and one `owner_queue` that lists every
entry that waits for the owner. The queue is built only from what is live: the active roadmap, the
queued roadmaps, the open changes, the pre-release steps of the newest closed roadmap until its
release is recorded, and the owner work of package bumps in `context/workflow.json` (`routines.packageUpdates`:
holds with `owner`, `ownerSteps` without `confirmed`). An unticked entry left in any other archived roadmap is history to settle
(the doctor's `archived-roadmap-open-checks`), never an owner-queue item. The schema ships next to this script
(`../references/state.schema.json`). A reader needs this one file per repository instead of parsing
the markdown.

Every owner-queue entry has an `id`: a short hash of its `source`, `item` and text, taken when the entry first
appears. `id` and `since` are kept from the previous file for an entry that is still there, also when only its
wording changed or its heading moved within the same file (the same item, or text that is still close enough),
so a reader can follow one entry across rewrites and "oldest first" stays true. `updated_at` changes only when the
content does.

`project` is workflow.json's `project`, else the active roadmap's, else the repository name. The repository name
depends on how the checkout was cloned (`owner/REPO` or `owner/repo`), so the first `write` that falls back to it
pins it in `context/workflow.json` (`project`), and `check` compares a name that came from the repository without
regard to letter case. `pin-project` does only the pinning (the installer runs it).

Importable: `from context_state import build_state, render_state, FsReader, GitReader, IndexReader`.
"""
from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills

SCHEMA_VERSION = 2
STATE_PATH = "context/state.json"
WORKFLOW_PATH = "context/workflow.json"
ROADMAP_PATH = "context/foundation/roadmap.md"
QUEUED_DIR = "context/foundation/roadmaps"
ARCHIVE_ROADMAPS_DIR = "context/foundation/archive"
CHANGES_DIR = "context/changes"
# Fields a script rewrites without the markdown changing: never a reason to call the file stale.
VOLATILE_FIELDS = ("updated_at", "open_changes")
# Owner-queue entries from these sources are refreshed like open_changes: a change branch edits them.
VOLATILE_SOURCES = ("context/changes/",)
HANDOFF_SECTION = "Roadmap handoff"
HANDOFF_OWNER_RE = re.compile(r"^- \*\*Owner (?P<what>step|check):\*\*\s*(?P<text>.+)$")

ROW_RE = re.compile(r"^\|\s*\*\*(?P<id>[A-Z]+-\d+)\*\*\s*\|")
ID_RE = re.compile(r"\b[A-Z]+-\d+\b")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
STATUS_RE = re.compile(r"^(proposed|ready_to_merge|ready|blocked|in_progress|done_code|done|dropped|carried)\b")
SINCE_RE = re.compile(r"since (\d{4}-\d{2}-\d{2})")
DONE_CODE_DATE_RE = re.compile(r"^done_code \((\d{4}-\d{2}-\d{2})")
CHECKBOX_RE = re.compile(r"^\s*- \[(?P<mark>[ xX])\] (?P<text>.+)$")
ITEM_REF_RE = re.compile(r"\*\*(?P<id>[A-Z]+-\d+)\*\*")
# Word boundaries that also split environment variable names (`SOFTURE_EMAIL_KEY_SECRET`, `STRIPE_API_KEY`).
SECRET_RE = re.compile(r"(?<![A-Za-z0-9])(secret|api[ _-]?key|token|credential|password|private[ _]key)s?(?![A-Za-z0-9])",
                       re.IGNORECASE)
RELEASE_LINE_RE = re.compile(
    r"^(?:- )?\**Release:?\**:?\s*(?P<version>v?\d+\.\d+\.\d+[0-9A-Za-z.+-]*)(?:\s*\((?P<date>\d{4}-\d{2}-\d{2})\))?")
OWNER_SECTION = "Owner decisions and checks"
RELEASE_SECTION = "Before the next release"
DONE_STATUSES = ("done", "done_code")
# A package bump's owner work that the package-update routine records in workflow.json (routines/package-updates.md).
HOLD_SOURCE = f"{WORKFLOW_PATH}#routines.packageUpdates.hold"
OWNER_STEPS_SOURCE = f"{WORKFLOW_PATH}#routines.packageUpdates.ownerSteps"


# ---------------------------------------------------------------- readers


class FsReader:
    """Reads the working tree under `root`; `overrides` maps a path to replacement text (None: absent)."""

    def __init__(self, root: str, overrides: dict | None = None) -> None:
        self.root = os.path.abspath(root)
        self.overrides = dict(overrides or {})

    def read(self, rel: str) -> str | None:
        if rel in self.overrides:
            return self.overrides[rel]
        try:
            with open(os.path.join(self.root, rel), encoding="utf-8") as fh:
                return fh.read()
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError, UnicodeDecodeError):
            return None

    def listdir(self, rel: str) -> list[tuple[str, bool]]:
        """Entries of a directory as (name, is_dir), sorted; [] when it does not exist."""
        full = os.path.join(self.root, rel)
        entries: dict[str, bool] = {}
        if os.path.isdir(full):
            for name in os.listdir(full):
                entries[name] = os.path.isdir(os.path.join(full, name))
        _merge_overrides(entries, rel, self.overrides)
        return sorted(entries.items())

    def exists(self, rel: str) -> bool:
        if rel in self.overrides:
            return self.overrides[rel] is not None
        return os.path.exists(os.path.join(self.root, rel))


class GitReader:
    """Reads a commit (`rev`) of the repository at `repo`, plus `overrides`."""

    def __init__(self, repo: str, rev: str, overrides: dict | None = None) -> None:
        self.repo = repo
        self.rev = rev
        self.overrides = dict(overrides or {})
        self._tree: dict[str, str] | None = None

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, text=True)

    def _paths(self) -> dict[str, str]:
        if self._tree is None:
            listed = self._git("ls-tree", "-r", "-t", self.rev, "--", "context").stdout
            tree: dict[str, str] = {}
            for line in listed.splitlines():
                meta, _, path = line.partition("\t")
                fields = meta.split()
                tree[path] = fields[1] if len(fields) > 1 else "blob"
            self._tree = tree
        return self._tree

    def read(self, rel: str) -> str | None:
        if rel in self.overrides:
            return self.overrides[rel]
        if self._paths().get(rel) != "blob":
            return None
        shown = self._git("show", f"{self.rev}:{rel}")
        return shown.stdout if shown.returncode == 0 else None

    def listdir(self, rel: str) -> list[tuple[str, bool]]:
        prefix = rel.rstrip("/") + "/"
        entries: dict[str, bool] = {}
        for path, kind in self._paths().items():
            if path.startswith(prefix) and "/" not in path[len(prefix):]:
                entries[path[len(prefix):]] = kind == "tree"
        _merge_overrides(entries, rel, self.overrides)
        return sorted(entries.items())

    def exists(self, rel: str) -> bool:
        if rel in self.overrides:
            return self.overrides[rel] is not None
        return rel in self._paths()


class IndexReader(GitReader):
    """Reads what is staged (the index) of the repository at `repo`."""

    def __init__(self, repo: str, overrides: dict | None = None) -> None:
        super().__init__(repo, "", overrides)

    def _paths(self) -> dict[str, str]:
        if self._tree is None:
            files = self._git("ls-files", "--", "context").stdout.splitlines()
            tree: dict[str, str] = {}
            for path in files:
                tree[path] = "blob"
                parts = path.split("/")
                for depth in range(1, len(parts)):
                    tree.setdefault("/".join(parts[:depth]), "tree")
            self._tree = tree
        return self._tree

    def read(self, rel: str) -> str | None:
        if rel in self.overrides:
            return self.overrides[rel]
        if self._paths().get(rel) != "blob":
            return None
        shown = self._git("show", f":{rel}")
        return shown.stdout if shown.returncode == 0 else None


def _merge_overrides(entries: dict[str, bool], rel: str, overrides: dict) -> None:
    prefix = rel.rstrip("/") + "/"
    for path, text in overrides.items():
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix):]
        name, _, deeper = rest.partition("/")
        if deeper:
            entries[name] = True
        elif text is None:
            entries.pop(name, None)
        else:
            entries[name] = False


# ---------------------------------------------------------------- markdown parsing


def frontmatter(text: str) -> dict:
    """The `key: value` lines of a leading `---` block; quotes stripped, `null` -> None."""
    match = re.match(r"^---\n(.*?)\n---", text or "", re.DOTALL)
    fields: dict = {}
    if not match:
        return fields
    for line in match.group(1).splitlines():
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*(?:#.*)?$", line)
        if not pair:
            continue
        value = pair.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[pair.group(1)] = None if value in ("", "null", "~") else value
    return fields


def sections(text: str) -> dict[str, list[str]]:
    """Lines under each `## <heading>` (the heading itself excluded); later duplicates append."""
    result: dict[str, list[str]] = {}
    current = None
    for line in (text or "").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            result.setdefault(current, [])
            continue
        if current is not None:
            result[current].append(line)
    return result


def title_of(text: str) -> str | None:
    for line in (text or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_status(raw: str) -> dict:
    """`**in_progress** (plan, since 2026-10-01; …)` -> keyword, detail, stage, since."""
    text = raw.replace("**", "").strip()
    match = STATUS_RE.match(text)
    keyword = match.group(1) if match else (text.split(" ", 1)[0] if text else "unknown")
    detail = None
    paren = re.search(r"\((.*)\)\s*$", text)
    if paren:
        detail = paren.group(1).strip()
    stage = None
    if keyword == "in_progress" and detail:
        stage = re.split(r"[,;]", detail, maxsplit=1)[0].strip() or None
    since = None
    found = SINCE_RE.search(text) or DONE_CODE_DATE_RE.match(text)
    if found:
        since = found.group(1)
    return {"status": keyword, "detail": detail, "stage": stage, "since": since}


def roadmap_rows(text: str) -> list[dict]:
    """Table rows `| **ID** | `change-id` | outcome | depends on | mode | status |` (WORKFLOW §5)."""
    rows = []
    seen = set()
    for line in (text or "").splitlines():
        if not ROW_RE.match(line):
            continue
        parts = cells(line)
        if len(parts) < 3:
            continue
        rid = ID_RE.search(parts[0]).group(0)
        if rid in seen:
            continue
        seen.add(rid)
        change = parts[1].strip("` ") if len(parts) > 1 else None
        status = parse_status(parts[-1])
        rows.append({
            "id": rid,
            "change_id": change or None,
            "outcome": parts[2] if len(parts) > 3 else None,
            "prerequisites": ID_RE.findall(parts[3]) if len(parts) > 4 else [],
            "mode": parts[4] if len(parts) > 5 else None,
            **status,
        })
    return rows


def open_checkboxes(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        match = CHECKBOX_RE.match(line)
        if match and match.group("mark") == " ":
            out.append(match.group("text").strip())
    return out


# ---------------------------------------------------------------- state


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def _owner_entries(path: str, text: str, rows: list[dict], fallback_since: str,
                   archived: bool = False) -> list[dict]:
    """Every open entry of one live roadmap file that waits for the owner.

    With `archived` (only the newest closed roadmap whose `## Summary` records no release yet), just its
    open `## Before the next release` steps count: the close comes before the release (WORKFLOW §5.2).
    """
    entries: list[dict] = []
    parts = sections(text)
    ids_with_entry: set[str] = set()
    for line in ([] if archived else open_checkboxes(parts.get(OWNER_SECTION, []))):
        ref = ITEM_REF_RE.search(line)
        item = ref.group("id") if ref else None
        lowered = line.lower()
        if "owner step:" in lowered:
            kind = "secret" if SECRET_RE.search(line) else "step"
        elif re.search(r"\(Manual \d", line):
            kind = "step"
        else:
            kind = "decision"
        if item:
            ids_with_entry.add(item)
        entries.append({"kind": kind, "source": f"{path}#{OWNER_SECTION}", "item": item,
                        "since": _date_in(line) or fallback_since, "text": line})
    for line in open_checkboxes(parts.get(RELEASE_SECTION, [])):
        ref = ITEM_REF_RE.search(line)
        entries.append({"kind": "secret" if SECRET_RE.search(line) else "step",
                        "source": f"{path}#{RELEASE_SECTION}", "item": ref.group("id") if ref else None,
                        "since": _date_in(line) or fallback_since, "text": line})
    waiting_release = []
    for row in ([] if archived else rows):
        if row["status"] != "done_code":
            continue
        waiting = re.sub(r"^\d{4}-\d{2}-\d{2};\s*", "", row["detail"] or "")
        waiting = re.sub(r"^waiting:\s*", "", waiting)
        if "release" in waiting.lower():
            waiting_release.append(row)
        elif "owner" in waiting.lower() and row["id"] not in ids_with_entry:
            entries.append({"kind": "secret" if SECRET_RE.search(waiting) else "step",
                            "source": f"{path}#At a glance", "item": row["id"],
                            "since": row["since"] or fallback_since, "text": f"{row['id']}: {waiting}"})
    if waiting_release:
        ids = ", ".join(row["id"] for row in waiting_release)
        dates = [row["since"] for row in waiting_release if row["since"]]
        entries.append({"kind": "word", "source": f"{path}#At a glance", "item": None,
                        "since": min(dates) if dates else fallback_since,
                        "text": f"release: {ids} merged and waiting for a release"})
    return entries


def _package_update_entries(workflow: dict, fallback_since: str) -> list[dict]:
    """Owner work the package-update routine recorded in `routines.packageUpdates` (routines/package-updates.md).

    A `hold` entry with `owner` (a bump held until the owner decides, its issue in the project's repository) is a
    `decision`; a `hold` entry without it waits for a fix in SOFTURE, not for the owner. An `ownerSteps` entry (a
    merged bump whose owner step has no live roadmap to sit in) stays until it carries `confirmed`. Either is a
    `secret` when its text names one.
    """
    updates = ((workflow.get("routines") or {}) if isinstance(workflow.get("routines"), dict) else {})
    updates = updates.get("packageUpdates") if isinstance(updates.get("packageUpdates"), dict) else {}
    entries: list[dict] = []

    def listed(key: str) -> list[dict]:
        value = updates.get(key)
        return [entry for entry in value if isinstance(entry, dict) and isinstance(entry.get("package"), str)] \
            if isinstance(value, list) else []

    def ref(entry: dict) -> str:
        return f" ({entry['issue']})" if isinstance(entry.get("issue"), str) and entry["issue"] else ""

    def since(entry: dict) -> str:
        return entry["since"] if isinstance(entry.get("since"), str) and DATE_RE.fullmatch(entry["since"]) \
            else fallback_since

    for entry in listed("hold"):
        what = entry.get("owner")
        if not isinstance(what, str) or not what.strip():
            continue
        text = f"hold {entry['package']}: {what.strip()}{ref(entry)}"
        entries.append({"kind": "secret" if SECRET_RE.search(what) else "decision", "source": HOLD_SOURCE,
                        "item": None, "since": since(entry), "text": text})
    for entry in listed("ownerSteps"):
        step = entry.get("step")
        if entry.get("confirmed") or not isinstance(step, str) or not step.strip():
            continue
        version = f" {entry['version']}" if isinstance(entry.get("version"), str) and entry["version"] else ""
        text = f"{entry['package']}{version}: {step.strip()}{ref(entry)}"
        entries.append({"kind": "secret" if SECRET_RE.search(step) else "step", "source": OWNER_STEPS_SOURCE,
                        "item": None, "since": since(entry), "text": text})
    return entries


def released(text: str) -> bool:
    """Whether an archived roadmap's `## Summary` records the release that shipped it."""
    return any(RELEASE_LINE_RE.match(line.strip()) for line in sections(text).get("Summary", []))


def archived_roadmap_files(reader) -> list[str]:
    """Archived roadmaps (`<date>-roadmap*.md` in foundation/archive/), oldest first."""
    return _roadmap_files(reader, ARCHIVE_ROADMAPS_DIR, r"^\d{4}-\d{2}-\d{2}-roadmap.*\.md$")


def pending_release_roadmap(reader) -> str | None:
    """The newest archived roadmap when its release is not recorded yet: its pre-release steps are live."""
    paths = [path for path in archived_roadmap_files(reader) if roadmap_rows(reader.read(path) or "")]
    if not paths:
        return None
    newest = paths[-1]
    return None if released(reader.read(newest) or "") else newest


def _handoff_entries(path: str, text: str, item: str | None, since: str) -> list[dict]:
    """Owner steps and checks an open change records in its `## Roadmap handoff` (WORKFLOW §4)."""
    entries = []
    for line in sections(text).get(HANDOFF_SECTION, []):
        match = HANDOFF_OWNER_RE.match(line.strip())
        if match:
            body = match.group("text").strip()
            entries.append({"kind": "secret" if SECRET_RE.search(body) else "step",
                            "source": f"{path}#{HANDOFF_SECTION}", "item": item,
                            "since": _date_in(body) or since, "text": f"owner {match.group('what')}: {body}"})
    return entries


def _date_in(text: str) -> str | None:
    match = DATE_RE.search(text)
    return match.group(1) if match else None


def _summary(rows: list[dict]) -> tuple[int, int]:
    return sum(1 for row in rows if row["status"] in DONE_STATUSES), len(rows)


def _roadmap_files(reader, directory: str, pattern: str) -> list[str]:
    return [f"{directory}/{name}" for name, is_dir in reader.listdir(directory)
            if not is_dir and re.match(pattern, name)]


def _last_release(reader) -> dict | None:
    for path in reversed(archived_roadmap_files(reader)):
        text = reader.read(path) or ""
        for line in reversed(sections(text).get("Summary", [])):
            match = RELEASE_LINE_RE.match(line.strip())
            if match:
                return {"version": match.group("version"), "date": match.group("date"), "source": path}
    return None


def read_workflow(reader) -> dict:
    """`context/workflow.json` as a dict; {} when it is absent or not a JSON object."""
    raw = reader.read(WORKFLOW_PATH)
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def resolve_project(reader, workflow: dict | None = None, roadmap_text: str | None = None,
                    prior: dict | None = None) -> tuple[str, bool]:
    """`(project, from_repository)`: workflow.json `project`, else the active roadmap's, else the repository name.

    `from_repository` is True for the last fallback. Its letter case depends on the clone, so when `prior` (the
    state.json already written) holds the same name in another case, that spelling is kept.
    """
    workflow = read_workflow(reader) if workflow is None else workflow
    if workflow.get("project"):
        return workflow["project"], False
    if roadmap_text is None:
        roadmap_text = reader.read(ROADMAP_PATH)
    if roadmap_text and frontmatter(roadmap_text).get("project"):
        return frontmatter(roadmap_text)["project"], False
    name = repository_name(reader)
    previous = (prior or {}).get("project")
    if isinstance(previous, str) and previous.casefold() == name.casefold():
        name = previous
    return name, True


def build_state(reader, prior: dict | None = None, now: str | None = None) -> dict:
    """The state of the project that `reader` sees. `prior` keeps the `since` of entries still present."""
    today = _today()
    workflow = read_workflow(reader)

    owner_queue: list[dict] = []
    active = None
    roadmap_text = reader.read(ROADMAP_PATH)
    rows_by_change: dict[str, dict] = {}
    if roadmap_text is not None and not is_idle_placeholder(roadmap_text):
        meta = frontmatter(roadmap_text)
        rows = roadmap_rows(roadmap_text)
        done, total = _summary(rows)
        rows_by_change = {row["change_id"]: row for row in rows if row["change_id"]}
        active = {
            "slug": meta.get("roadmap"),
            "title": title_of(roadmap_text),
            "status": meta.get("status"),
            "version": meta.get("version"),
            "path": ROADMAP_PATH,
            "done": done,
            "total": total,
            "items": [{key: row[key] for key in ("id", "change_id", "outcome", "status", "stage", "since",
                                                  "detail", "prerequisites", "mode")}
                      for row in rows if row["status"] not in DONE_STATUSES],
        }
        owner_queue += _owner_entries(ROADMAP_PATH, roadmap_text, rows, meta.get("updated") or today)
    elif roadmap_text is not None:
        # The idle placeholder is no active roadmap, but a project between roadmaps still has owner steps:
        # its open `## Owner decisions and checks` and `## Before the next release` entries stay in the queue.
        meta = frontmatter(roadmap_text)
        owner_queue += _owner_entries(ROADMAP_PATH, roadmap_text, [], meta.get("updated") or today)

    queued = []
    for path in _roadmap_files(reader, QUEUED_DIR, r"^roadmap-.+\.md$"):
        text = reader.read(path) or ""
        meta = frontmatter(text)
        rows = roadmap_rows(text)
        done, total = _summary(rows)
        slug = meta.get("roadmap") or os.path.basename(path)[len("roadmap-"):-len(".md")]
        condition = meta.get("trigger") or _start_order(text)
        since = meta.get("created") or meta.get("updated") or today
        queued.append({
            "slug": slug,
            "title": title_of(text),
            "status": meta.get("status"),
            "path": path,
            "start_condition": condition,
            "done": done,
            "total": total,
            "items": [{key: row[key] for key in ("id", "change_id", "outcome", "status")} for row in rows],
        })
        owner_queue.append({"kind": "word", "source": path, "item": None, "since": since,
                            "text": f"start queued roadmap {slug}" + (f": {condition}" if condition else "")})
        owner_queue += _owner_entries(path, text, rows, meta.get("updated") or today)

    pending = pending_release_roadmap(reader)
    if pending:
        text = reader.read(pending) or ""
        meta = frontmatter(text)
        owner_queue += _owner_entries(pending, text, roadmap_rows(text),
                                      meta.get("updated") or pending.split("/")[-1][:10], archived=True)

    open_changes = []
    for name, is_dir in reader.listdir(CHANGES_DIR):
        if not is_dir:
            continue
        text = reader.read(f"{CHANGES_DIR}/{name}/change.md")
        if text is None:
            continue
        meta = frontmatter(text)
        change_id = meta.get("change_id") or name
        row = rows_by_change.get(change_id)
        open_changes.append({
            "change_id": change_id,
            "title": meta.get("title"),
            "status": meta.get("status"),
            "roadmap_item": meta.get("roadmap_item"),
            "updated": meta.get("updated"),
            "stage": (row["stage"] or row["status"]) if row else None,
        })
        owner_queue += _handoff_entries(f"{CHANGES_DIR}/{name}/change.md", text, meta.get("roadmap_item"),
                                        meta.get("updated") or today)

    owner_queue += _package_update_entries(workflow, today)

    owner_queue = carry_identity(owner_queue, (prior or {}).get("owner_queue") or [])
    owner_queue.sort(key=lambda entry: (entry["since"] or "", entry["source"], entry["text"]))

    state = {
        "schema_version": SCHEMA_VERSION,
        "project": resolve_project(reader, workflow, roadmap_text, prior)[0],
        "mode": workflow.get("mode") or "manual",
        "main_branch": workflow.get("mainBranch"),
        "updated_at": now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "active_roadmap": active,
        "queued": queued,
        "open_changes": open_changes,
        "owner_queue": owner_queue,
        "last_release": _last_release(reader),
    }
    return state


def is_idle_placeholder(text: str) -> bool:
    """A `roadmap.md` that only says there is no active roadmap (`status: idle` or `roadmap: none`)."""
    meta = frontmatter(text)
    return (meta.get("status") or "").lower() == "idle" or (meta.get("roadmap") or "").lower() == "none"


def repository_name(reader) -> str:
    """The repository's name: the last segment of `origin`'s URL, else the checkout's folder name.

    The last fallback for `project`, so a project between roadmaps without `project` in workflow.json still
    has a name. The URL comes first because a checkout's folder can be named anything (a worktree, a clone
    into a temporary folder). The URL's letter case is the clone's, not the forge's: in GitHub Actions the
    forge's spelling (`GITHUB_REPOSITORY`) wins when it names the same repository.
    """
    folder = getattr(reader, "root", None) or getattr(reader, "repo", None) or os.getcwd()
    url = subprocess.run(["git", "-C", folder, "remote", "get-url", "origin"], capture_output=True,
                         text=True).stdout.strip()
    name = re.split(r"[/:]", url.rstrip("/"))[-1] if url else os.path.basename(os.path.abspath(folder))
    name = re.sub(r"\.git$", "", name) or "unnamed"
    canonical = os.environ.get("GITHUB_REPOSITORY", "").rsplit("/", 1)[-1]
    return canonical if canonical and canonical.casefold() == name.casefold() else name


def pin_project(root: str, staged: bool = False) -> str | None:
    """Write the repository-derived `project` into `context/workflow.json`; the name written, else None.

    Nothing is written when `project` does not come from the repository name (workflow.json or the active
    roadmap names it). The spelling is the one `context/state.json` already holds when it matches, so the
    pin never flips a committed name. With `staged` the file is read from and added to the index; a
    workflow.json with unstaged edits is left alone, so nobody's uncommitted work is committed.
    """
    reader = IndexReader(root) if staged else FsReader(root)
    project, from_repository = resolve_project(reader, prior=load_prior(reader))
    if not from_repository:
        return None
    target = os.path.join(root, WORKFLOW_PATH)
    raw = reader.read(WORKFLOW_PATH)
    if staged:
        on_disk = None
        if os.path.exists(target):
            with open(target, encoding="utf-8") as fh:
                on_disk = fh.read()
        if on_disk != raw:
            return None
    workflow: dict = {}
    if raw:
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None  # a broken file is the doctor's to report, not ours to overwrite
        if not isinstance(loaded, dict):
            return None
        workflow = loaded
    workflow = {**workflow, "project": project} if "project" in workflow else {"project": project, **workflow}
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
    if staged:
        subprocess.run(["git", "-C", root, "add", "--", WORKFLOW_PATH], check=True)
    return project


def _start_order(text: str) -> str | None:
    """A run-wide order about starting the roadmap (`> - Start: …`), when the header has one."""
    for line in (text or "").splitlines():
        match = re.match(r"^>\s*-\s*(Start[^:]*):\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(2).strip()
    return None


def _entry_key(entry: dict) -> tuple:
    return (entry.get("kind"), entry.get("source"), entry.get("text"))


# Text of an unmatched entry this close to a prior entry's text (difflib ratio) is the same entry reworded.
REWORD_RATIO = 0.6
# The same, across headings of one file (a moved entry): stricter, because the section changed too.
MOVED_RATIO = 0.8


def entry_id(entry: dict) -> str:
    """A short id for a new owner-queue entry: a hash of its source, item and first line."""
    first_line = (entry.get("text") or "").strip().splitlines()[0] if (entry.get("text") or "").strip() else ""
    seed = "\n".join((entry.get("source") or "", entry.get("item") or "", first_line))
    return "oq-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]


def _file_of(source: str | None) -> str:
    return (source or "").split("#", 1)[0]


def _same_entry_score(new: dict, old: dict) -> float | None:
    """How surely `old` (prior file) is `new` reworded or moved; None when it is not."""
    if _file_of(new.get("source")) != _file_of(old.get("source")):
        return None
    same_section = new.get("source") == old.get("source")
    ratio = difflib.SequenceMatcher(None, new.get("text") or "", old.get("text") or "").ratio()
    if new.get("item") and new.get("item") == old.get("item") and new.get("kind") == old.get("kind"):
        return 1.0 + ratio + (1.0 if same_section else 0.0)
    if new.get("item") != old.get("item"):
        return None
    if ratio >= (REWORD_RATIO if same_section else MOVED_RATIO):
        return ratio + (1.0 if same_section else 0.0)
    return None


def carry_identity(entries: list[dict], prior: list[dict]) -> list[dict]:
    """Give every entry an `id` and keep `id` and `since` of the prior entry it continues.

    An entry with the same kind, source and text as a prior one continues it. Each remaining entry continues the
    prior one it matches best: the same file, and the same item and kind, or (without an item) text that is still
    close enough (`REWORD_RATIO` under the same heading, `MOVED_RATIO` under another). A prior entry is continued
    at most once. Anything else is new and gets a fresh id; ids stay unique within the queue.
    """
    unmatched = list(prior)
    exact: dict[tuple, list[dict]] = {}
    for old in unmatched:
        exact.setdefault(_entry_key(old), []).append(old)
    pending = []
    for entry in entries:
        candidates = exact.get(_entry_key(entry))
        if candidates:
            old = candidates.pop(0)
            unmatched.remove(old)
            _continue(entry, old)
        else:
            pending.append(entry)
    pairs = []
    for new_index, entry in enumerate(pending):
        for old_index, old in enumerate(unmatched):
            score = _same_entry_score(entry, old)
            if score is not None:
                pairs.append((score, new_index, old_index))
    taken_new: set[int] = set()
    taken_old: set[int] = set()
    for _score, new_index, old_index in sorted(pairs, key=lambda pair: (-pair[0], pair[1], pair[2])):
        if new_index in taken_new or old_index in taken_old:
            continue
        taken_new.add(new_index)
        taken_old.add(old_index)
        _continue(pending[new_index], unmatched[old_index])
    used: set[str] = set()
    result = []
    for entry in entries:
        ident = entry.get("id") if entry.get("id") not in used else None
        if not ident:
            base = entry_id(entry)
            ident, suffix = base, 2
            while ident in used:
                ident, suffix = f"{base}-{suffix}", suffix + 1
        used.add(ident)
        result.append({"id": ident, **{key: value for key, value in entry.items() if key != "id"}})
    return result


def _continue(entry: dict, old: dict) -> None:
    if old.get("id"):
        entry["id"] = old["id"]
    entry["since"] = old.get("since") or entry["since"]


def comparable(state: dict | None) -> dict | None:
    """The state without what a rewrite may change on its own (VOLATILE_FIELDS, VOLATILE_SOURCES)."""
    if state is None:
        return None
    kept = {key: value for key, value in state.items() if key not in VOLATILE_FIELDS}
    kept["owner_queue"] = [entry for entry in kept.get("owner_queue") or []
                           if not str(entry.get("source", "")).startswith(VOLATILE_SOURCES)]
    return kept


def serialize(state: dict) -> str:
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def load_prior(reader) -> dict | None:
    raw = reader.read(STATE_PATH)
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def render_state(reader) -> str:
    """The text of `context/state.json` for what `reader` sees; the previous text when nothing changed."""
    prior = load_prior(reader)
    state = build_state(reader, prior)
    if prior is not None and prior.get("updated_at") and json.dumps(_stable(prior)) == json.dumps(_stable(state)):
        state["updated_at"] = prior["updated_at"]
    return serialize(state)


def _stable(state: dict) -> dict:
    return {key: value for key, value in state.items() if key != "updated_at"}


def staleness(reader) -> str | None:
    """None when `context/state.json` matches the markdown; otherwise why not."""
    prior = load_prior(reader)
    if prior is None:
        return "missing or not valid JSON" if reader.exists(STATE_PATH) else "missing"
    if prior.get("schema_version") != SCHEMA_VERSION:
        return f"schema_version {prior.get('schema_version')!r}, expected {SCHEMA_VERSION}"
    fresh = build_state(reader, prior)
    old, new = comparable(prior), comparable(fresh)
    if old == new:
        return None
    changed = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
    return "out of date with the markdown (" + ", ".join(changed) + ")"


# ---------------------------------------------------------------- command line


def repo_root(start: str) -> str:
    out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else os.path.abspath(start)


def quiet_broken_pipe(run) -> int:
    """Run a CLI entry point; when stdout is closed early (`doctor --sweep | head`), stop quietly with 141.

    141 is what a shell reports for a process ended by SIGPIPE; no traceback, no "Exception ignored".
    """
    try:
        code = run()
        sys.stdout.flush()
        return code
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())  # the interpreter's final flush must not fail again
        return 141


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = None
    if "--root" in args:
        k = args.index("--root")
        root = args[k + 1]
        del args[k:k + 2]
    staged = "--staged" in args
    args = [arg for arg in args if arg != "--staged"]
    if len(args) != 1 or args[0] not in ("write", "print", "check", "pin-project"):
        print(__doc__, file=sys.stderr)
        return 2
    root = os.path.abspath(root) if root else repo_root(os.getcwd())
    if not os.path.isdir(os.path.join(root, "context")):
        print(f"no context/ directory in {root}: nothing to do", file=sys.stderr)
        return 0 if args[0] != "check" else 1
    if args[0] == "pin-project":
        pinned = pin_project(root, staged)
        if pinned:
            print(f"wrote {WORKFLOW_PATH}: \"project\": {json.dumps(pinned, ensure_ascii=False)}"
                  + " (staged)" * staged)
        return 0
    if args[0] == "write":
        pinned = pin_project(root, staged)
        if pinned:
            print(f"wrote {WORKFLOW_PATH}: \"project\": {json.dumps(pinned, ensure_ascii=False)} "
                  "(the repository name, fixed so it no longer depends on the clone)" + " (staged)" * staged)
    reader = IndexReader(root) if staged else FsReader(root)
    if args[0] == "check":
        problem = staleness(FsReader(root))
        if problem:
            print(f"{STATE_PATH}: {problem}", file=sys.stderr)
            return 1
        print(f"{STATE_PATH}: up to date")
        return 0
    text = render_state(reader)
    if args[0] == "print":
        sys.stdout.write(text)
        return 0
    target = os.path.join(root, STATE_PATH)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text)
    if staged:
        subprocess.run(["git", "-C", root, "add", "--", STATE_PATH], check=True)
    print(f"wrote {STATE_PATH}" + (" (staged)" if staged else ""))
    return 0


if __name__ == "__main__":
    sys.exit(quiet_broken_pipe(main))
