#!/usr/bin/env python3
"""softure-doctor: check the `context/` contract of a project (WORKFLOW.md §12) and exit non-zero on drift.

    doctor.py [--root <dir>] [--json]
    npx softure-skills doctor            (the same, from the installed package)

Adopting projects run it in their CI check, documentation-only changes included (that is where the
drift happens). `softure-archive` and `softure-roadmap --close` run it before their commit and fix
what they own. Each problem is one line `FAIL <code> <path>: <what>`; the codes:

  roadmap-archived-not-removed    roadmap.md is still there although the same roadmap is in foundation/archive/
  roadmap-status-mismatch         roadmap.md `status` contradicts its rows (done with open rows; waiting)
  archived-change-status          an archived change.md whose status is not `archived`
  archived-change-progress        an archived plan.md with unticked Automated items in `## Progress`
  archived-roadmap-open-items     an archived roadmap with rows that are not done, done_code, dropped or carried
  archived-roadmap-summary        an archived roadmap whose `## Summary` merge column holds placeholders, not SHAs
  queued-roadmap-done             a queued roadmap in foundation/roadmaps/ whose rows are all done
  backlog-without-roadmap         a backlog/roadmap-<slug>/ folder without its queued (or promoted) roadmap
  index-missing-file              an index row (README.md / INDEX.md table under context/) links a missing file
  state-missing                   context/state.json is missing although the project has written it before
  state-stale                     context/state.json does not match the markdown

A project that has never written `context/state.json` (it adopted the package before the file existed)
gets a note, not a failure: the first run of `wt-roadmap.py`, `softure-archive` or `softure-roadmap`
creates it. Fix a stale or missing file with `npx softure-skills state` (or
`python3 .claude/skills/softure-doctor/scripts/context_state.py write`) and commit it.

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
from context_state import (  # noqa: E402
    ARCHIVE_ROADMAPS_DIR, CHANGES_DIR, QUEUED_DIR, ROADMAP_PATH, STATE_PATH, FsReader, frontmatter,
    roadmap_rows, sections, staleness,
)

ARCHIVE_DIR = "context/archive"
BACKLOG_DIR = "context/backlog"
CLOSED_STATUSES = ("done", "done_code", "dropped", "carried")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
EMPTY_MERGE = {"—", "-", "–", "n/a", "none", "no merge", "not merged"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INDEX_NAMES = ("README.md", "INDEX.md")
CODE_PATH_RE = re.compile(r"`((?:\.{1,2}/)?(?:[\w.-]+/)*[\w.-]+\.md|(?:\.{1,2}/)?(?:[\w.-]+/)+)`")


class Finding:
    def __init__(self, code: str, path: str, message: str, severity: str = "fail") -> None:
        self.code, self.path, self.message, self.severity = code, path, message, severity

    def as_dict(self) -> dict:
        return {"code": self.code, "path": self.path, "message": self.message, "severity": self.severity}

    def __str__(self) -> str:
        label = "FAIL" if self.severity == "fail" else "note"
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


def unticked_automated(plan: str) -> list[str]:
    """Open `- [ ]` items of `## Progress` that are not under a `#### Manual` heading.

    Open Manual items are legitimate in an archived plan (manual mode carries them to the owner).
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
        if match and not manual:
            open_items.append(match.group(1).strip())
    return open_items


def check_archived_roadmaps(reader) -> list[Finding]:
    findings: list[Finding] = []
    for path in _archived_roadmaps(reader):
        text = reader.read(path) or ""
        open_rows = [f"{row['id']} ({row['status']})" for row in roadmap_rows(text)
                     if row["status"] not in CLOSED_STATUSES]
        if open_rows:
            findings.append(Finding("archived-roadmap-open-items", path,
                                    f"rows not done, done_code, dropped or carried: {', '.join(open_rows)}"))
        bad = summary_placeholders(text)
        if bad:
            findings.append(Finding("archived-roadmap-summary", path,
                                    "## Summary merge column holds placeholders instead of merge SHAs: "
                                    + "; ".join(bad[:4])))
    return findings


def summary_placeholders(text: str) -> list[str]:
    """Rows of the `## Summary` table whose `Merge` cell holds no SHA (and is not an explicit dash)."""
    lines = sections(text).get("Summary", [])
    header = None
    bad = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        parts = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = [cell.lower() for cell in parts]
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in parts if cell):
            continue
        index = header.index("merge") if "merge" in header else len(parts) - 1
        cell = parts[index] if index < len(parts) else ""
        if SHA_RE.search(cell) or cell.strip("`* ").lower() in EMPTY_MERGE:
            continue
        bad.append(f"{parts[0]}: \"{cell}\"")
    return bad


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


def check_indexes(reader) -> list[Finding]:
    findings: list[Finding] = []
    for path in _walk(reader, "context"):
        if os.path.basename(path) not in INDEX_NAMES:
            continue
        base = os.path.dirname(path)
        for line in (reader.read(path) or "").splitlines():
            if not line.strip().startswith("|"):
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
                    findings.append(Finding("index-missing-file", path, f"row links `{target}`, which does not exist"))
            for target in CODE_PATH_RE.findall(line):
                # A path in backticks: relative to the index, to context/ or to the repository root.
                candidates = [os.path.normpath(os.path.join(prefix, target)).replace(os.sep, "/").rstrip("/")
                              for prefix in (base, "context", ".")]
                inside = [c for c in candidates if c.startswith("context/")]
                if inside and not any(reader.exists(c) for c in inside):
                    findings.append(Finding("index-missing-file", path, f"row names `{target}`, which does not exist"))
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


def run_checks(reader, root: str | None = None) -> list[Finding]:
    """Every finding for the project `reader` sees. `root` (a git checkout) enables the history check."""
    if not reader.exists("context"):
        return []
    findings: list[Finding] = []
    for check in (check_main_roadmap, check_archived_changes, check_archived_roadmaps,
                  check_queued_and_backlog, check_indexes):
        findings += check(reader)
    findings += check_state(reader, root)
    return findings


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    as_json = "--json" in args
    args = [arg for arg in args if arg != "--json"]
    root = None
    if "--root" in args:
        k = args.index("--root")
        root = os.path.abspath(args[k + 1])
        del args[k:k + 2]
    if args:
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
    findings = run_checks(reader, git_root)
    failures = [f for f in findings if f.severity == "fail"]
    if as_json:
        print(json.dumps({"root": root, "failures": [f.as_dict() for f in failures],
                          "notes": [f.as_dict() for f in findings if f.severity != "fail"]}, indent=2))
        return 1 if failures else 0
    for finding in findings:
        print(finding)
    if failures:
        print(f"softure-doctor: {len(failures)} problem(s) in the context/ contract (WORKFLOW.md §12)")
        return 1
    print("softure-doctor: context/ contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
