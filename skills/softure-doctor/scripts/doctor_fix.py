#!/usr/bin/env python3
"""softure-doctor --fix: the mechanical repairs of history, as a dry run unless `--write` is given.

    doctor.py --fix [--write] [--json] [--root <dir>]
    npx softure-skills doctor --fix [--write]

Only two kinds of failure are mechanical, and only files under `context/` are edited:

  archived-change-status   an archived change.md gets `status: archived`; the old value is kept as
                           `legacy_status` in its front matter (a missing status gets none)
  index-missing-file       a row of an index inside an archive folder (`context/archive/`,
                           `context/foundation/archive/`) that links a missing file is rewritten to the
                           file's current path when git history shows where it moved (rename detection,
                           followed across several moves); a file that was deleted, not moved, is marked
                           `(moved, not found; last seen in <sha>: <path>)` with the last commit that had it

Everything else (and an index row whose target was never in git history, or any row when the
checkout has no full history) is a judgement case: `doctor.py --sweep` lists it with evidence.
Every edit is printed; a second run after `--write` changes nothing.

Importable: `from doctor_fix import plan_fixes, apply_fixes`.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context_state import frontmatter  # noqa: E402

ARCHIVE_PREFIXES = ("context/archive/", "context/foundation/archive/")
GONE_MARK = "moved, not found"
MAX_HOPS = 10


# ---------------------------------------------------------------- git history


class History:
    """Where files under a git checkout went. `usable` is False without git or with a shallow clone."""

    def __init__(self, root: str | None) -> None:
        self.root = root
        self.usable = False
        if root:
            probe = self._git("rev-parse", "--is-shallow-repository")
            self.usable = probe.returncode == 0 and probe.stdout.strip() == "false"

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", self.root or ".", *args], capture_output=True, text=True)

    def short(self, sha: str) -> str:
        out = self._git("rev-parse", "--short", sha)
        return out.stdout.strip() if out.returncode == 0 else sha[:7]

    def exists_now(self, rel: str) -> bool:
        return os.path.exists(os.path.join(self.root or ".", rel))

    def trace(self, rel: str) -> tuple[str, str] | None:
        """("moved", <current path>) or ("gone", <short sha of the last commit that had it>); None when
        the path was never in history (or history is not usable)."""
        if not self.usable:
            return None
        current = rel.rstrip("/")
        last_having = None
        for _ in range(MAX_HOPS):
            if current != rel.rstrip("/") and self.exists_now(current):
                return "moved", current
            log = self._git("log", "-1", "--no-merges", "--format=%H", "--", current)
            sha = log.stdout.strip()
            if log.returncode != 0 or not sha:
                break
            parent = self._git("rev-parse", "-q", "--verify", f"{sha}^")
            last_having = parent.stdout.strip() if parent.returncode == 0 else sha
            moved_to = self._renamed_in(sha, current)
            if not moved_to or moved_to == current:
                break
            current = moved_to
        if last_having is None:
            return None
        if current != rel.rstrip("/") and self.exists_now(current):
            return "moved", current
        return "gone", self.short(last_having)

    def _renamed_in(self, sha: str, path: str) -> str | None:
        shown = self._git("show", "-M", "--name-status", "--format=", sha)
        moves: dict[str, int] = {}
        for line in shown.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or not parts[0].startswith("R"):
                continue
            old, new = parts[1], parts[2]
            if old == path:
                return new
            if old.startswith(path + "/"):  # a folder: where most of its files went
                rest = old[len(path):]
                if new.endswith(rest):
                    target = new[: len(new) - len(rest)]
                    moves[target] = moves.get(target, 0) + 1
        return max(moves, key=moves.get) if moves else None


# ---------------------------------------------------------------- the edits


def fix_change_status(text: str) -> tuple[str, str] | None:
    """The change.md text with `status: archived` (and `legacy_status`), and what changed; None when fine."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return "---\nstatus: archived\n---\n\n" + text, "status missing -> archived (front matter added)"
    lines = match.group(1).split("\n")
    meta = frontmatter(text)
    old = meta.get("status")
    if old == "archived":
        return None
    index = next((i for i, line in enumerate(lines) if re.match(r"^status:", line)), None)
    if index is None:
        lines.append("status: archived")
        what = "status missing -> archived"
    else:
        raw = re.sub(r"^status:\s*", "", lines[index]).split(" #", 1)[0].strip()
        lines[index] = "status: archived"
        if "legacy_status" not in meta and raw:
            lines.insert(index + 1, f"legacy_status: {raw}")
        what = f"status {old or 'empty'} -> archived" + (f" (legacy_status: {raw})" if raw else "")
    body = "---\n" + "\n".join(lines) + "\n---" + text[match.end():]
    return body, what


def _relative(new_path: str, missing: dict, original_candidate: str) -> str:
    """`new_path` written the way the row wrote the old one (relative to the index, context/ or the root)."""
    target = missing["target"]
    anchor = ""
    if missing["kind"] == "link" and "#" in target:
        anchor = "#" + target.split("#", 1)[1]
    trailing = "/" if target.split("#", 1)[0].endswith("/") else ""
    if missing["kind"] == "link":
        start = missing["base"]
    else:
        base = missing["base"]
        joined = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/").rstrip("/")
        context_joined = os.path.normpath(os.path.join("context", target)).replace(os.sep, "/").rstrip("/")
        start = base if joined == original_candidate else ("context" if context_joined == original_candidate else ".")
    rel = os.path.relpath(new_path, start).replace(os.sep, "/") if start != "." else new_path
    return rel + trailing + anchor


def _replace_target(line: str, missing: dict, replacement: str | None, gone_note: str | None) -> str:
    target = missing["target"]
    if missing["kind"] == "link":
        pattern = re.compile(r"\[([^\]]*)\]\(" + re.escape(target) + r"((?:\s+\"[^\"]*\")?)\)")
        if replacement is not None:
            return pattern.sub(lambda m: f"[{m.group(1)}]({replacement}{m.group(2)})", line, count=1)
        return pattern.sub(lambda m: f"{m.group(1)} ({gone_note}: {target})", line, count=1)
    if replacement is not None:
        return line.replace(f"`{target}`", f"`{replacement}`", 1)
    return line.replace(f"`{target}`", f"{target} ({gone_note})", 1)


def plan_fixes(reader, root: str | None) -> dict:
    """The edits `--fix` would make: {"edits": [...], "skipped": [...], "files": {path: new text}}."""
    import doctor  # noqa: E402  (doctor imports this module lazily too)

    edits: list[dict] = []
    skipped: list[dict] = []
    files: dict[str, str] = {}

    for name, is_dir in reader.listdir(doctor.ARCHIVE_DIR):
        if not is_dir:
            continue
        rel = f"{doctor.ARCHIVE_DIR}/{name}/change.md"
        text = reader.read(rel)
        if text is None:
            continue
        fixed = fix_change_status(text)
        if fixed:
            files[rel] = fixed[0]
            edits.append({"code": "archived-change-status", "path": rel, "what": fixed[1]})

    history = History(root)
    for missing in doctor.missing_index_targets(reader):
        if not missing["path"].startswith(ARCHIVE_PREFIXES):
            skipped.append({"code": "index-missing-file", "path": missing["path"], "target": missing["target"],
                            "why": "a live index: fix or drop the row by hand (--sweep)"})
            continue
        if not history.usable:
            skipped.append({"code": "index-missing-file", "path": missing["path"], "target": missing["target"],
                            "why": "no full git history in this checkout"})
            continue
        found = None
        for candidate in missing["candidates"]:
            traced = history.trace(candidate)
            if traced:
                found = (candidate, traced)
                break
        if not found:
            skipped.append({"code": "index-missing-file", "path": missing["path"], "target": missing["target"],
                            "why": "never in git history: fix or drop the row (--sweep)"})
            continue
        candidate, (kind, value) = found
        text = files.get(missing["path"], reader.read(missing["path"]) or "")
        lines = text.split("\n")
        index = missing["line"] - 1
        if index >= len(lines):
            continue
        if kind == "moved":
            new_target = _relative(value, missing, candidate)
            lines[index] = _replace_target(lines[index], missing, new_target, None)
            what = f"`{missing['target']}` -> `{new_target}` (moved to {value})"
        else:
            note = f"{GONE_MARK}; last seen in {value}"
            lines[index] = _replace_target(lines[index], missing, None, note)
            what = f"`{missing['target']}` marked ({note})"
        files[missing["path"]] = "\n".join(lines)
        edits.append({"code": "index-missing-file", "path": missing["path"], "line": missing["line"], "what": what})
    return {"edits": edits, "skipped": skipped, "files": files}


def apply_fixes(root: str, files: dict[str, str]) -> None:
    for rel, text in files.items():
        if not rel.startswith("context/"):
            raise ValueError(f"--fix writes only under context/, not {rel}")
        with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
