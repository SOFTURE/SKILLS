#!/usr/bin/env python3
"""softure-doctor --sweep: every remaining failure as a worklist entry with the evidence to settle it.

    doctor.py --sweep [--json] [--root <dir>]
    npx softure-skills doctor --sweep [--json]

Read-only. One entry per thing to settle (an unticked Progress item, a Summary placeholder, an open
row, an open owner check, ...), each with `path`, `line` and the exact `text` of the line, the
evidence found in the repository, and how to settle it:

  archived-change-progress      commits that touched the phase's files after the plan's date, the SHA
                                ticked items of the same phase cite, and the change's merge commit
  archived-roadmap-summary      the merge (or squash) commit of the item's change on the main branch
  archived-roadmap-open-items   the item's archived change folder, merge commit, the release that
                                contains it, and later roadmaps that mention the item
  archived-roadmap-open-checks  the same for the item the check names, plus the first release after
                                the roadmap was closed
  carried entries               an open check or row whose text carries a carry marker (`→ roadmap-<slug>`,
                                `carried to <roadmap>`) naming a roadmap that exists: that roadmap is the
                                evidence, and `--fix` ticks it (a marker whose roadmap is gone stays as it was)
  anything else                 the file to fix (and `--fix` for the mechanical shapes)

Every entry has a `class`:

  evidence     the repository holds evidence that settles it (above); the agent settles it with that proof
  superseded   no direct evidence, but later work made it obsolete: for an owner check or open row of an
               archived roadmap, a later roadmap was closed and a release shipped after it, or the same
               item ID or file area appears in a later archived change; for a Progress item, a later
               phase of the same plan is ticked (or a later archived change has the item's area). The
               agent closes it as `obsolete: superseded by <ref>` itself, never forwards it
  forge        a post-merge step the history cannot prove (a release after the merge, `close #N`, the
               Dependabot pull requests) while the forge cannot be reached from here: an agent with `gh`
               checks it before anything goes to the owner. With the forge reachable (`gh` and a GitHub
               remote), the sweep asks it itself: a release published on or after the merge date, the
               state of each `#N`, open Dependabot pull requests; when every check holds the entry is
               `evidence` with those pointers (`--no-forge` skips the forge)
  owner        only the owner can settle it: a decision about future work, a secret, account or connector,
               or a step outside the repository whose effect the agent cannot see (`owner_reason` says
               which; `unsettled` when nothing at all was found), with `tried`: what the sweep looked for

`"owner": true` marks the owner class. The skill section "Sweep history to zero" tells an agent how to
work the list: settle every entry with its evidence, never without.

Importable: `from doctor_sweep import sweep`.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context_state import (  # noqa: E402
    ARCHIVE_ROADMAPS_DIR, OWNER_SECTION, QUEUED_DIR, RELEASE_LINE_RE, RELEASE_SECTION, ROADMAP_PATH, CHECKBOX_RE,
    ITEM_REF_RE, SECRET_RE, archived_roadmap_files, frontmatter, pending_release_roadmap, roadmap_rows, sections,
)

SHA_TAIL_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
PATH_RE = re.compile(r"`((?:[\w.-]+/)+[\w.-]+\.\w+|[\w.-]+\.(?:ts|tsx|js|jsx|mjs|py|cs|go|rs|java|kt|rb|php|sql|css|scss|html|json|yml|yaml|sh))`")
SEMVER_TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+")
AREA_RE = re.compile(r"`((?:\.{0,2}/)?(?:[\w.@-]+/)+[\w.@-]*)`")
LIMIT = 3

# What only the owner can settle (WORKFLOW §12.4); everything else is the agent's.
OWNER_KINDS = (
    ("decision", re.compile(r"\b(?:decide|decision|choose|agree on|sign[- ]off)\b", re.IGNORECASE)),
    ("secret", re.compile(SECRET_RE.pattern + r"|\b(?:accounts?|connectors?|oauth|dns|domains?|certificates?|billing"
                          r"|subscriptions?|licen[cs]es?)\b|`[A-Z][A-Z0-9]*_[A-Z0-9_]+`", re.IGNORECASE)),
    ("outside", re.compile(r"\b(?:in production|on production|production (?:environment|settings?)|in staging"
                           r"|app store|play store|real (?:phone|device)|with the (?:client|customer|vendor)"
                           r"|support ticket|by (?:e-?mail|phone) to)\b", re.IGNORECASE)),
)

SETTLE = {
    "ci-doctor-trigger": "give the workflow `on: pull_request` and `push` to the main branch, drop its paths filter "
                         "and the job's `if:` (WORKFLOW.md §12.2)",
    "archived-change-progress": "tick it with the SHA that did it (`- [x] <text> — <sha>`), or, when the work was "
                                "never done, `- [x] ~~<text>~~ — dropped: <reason>`",
    "archived-roadmap-summary": "put the merge SHA into the row's Merge cell (a release tag where the roadmap records "
                                "a release instead; `carried`, `dropped` or `— <reason>` for a row with no merge)",
    "archived-roadmap-open-items": "set the row's status to `done` when the evidence shows it shipped, "
                                   "`carried (to <path>)` when a later roadmap took it, or `dropped (<reason>)`",
    "archived-roadmap-open-checks": "tick it with its evidence (`— done: <sha | release | path>`), as obsolete "
                                    "(`— obsolete: <reason>`), or carry it to a live roadmap or a cockpit issue "
                                    "and tick it with where it went (`— carried to <path | #N>`)",
}

SETTLE_SUPERSEDED = {
    "archived-change-progress": "close it yourself: `- [x] <text> — obsolete: superseded by <ref>` (never forward it)",
    "archived-roadmap-open-items": "set the row's status to `dropped (obsolete: superseded by <ref>)` (never forward it)",
    "archived-roadmap-open-checks": "close it yourself: `- [x] <text> — obsolete: superseded by <ref>` "
                                    "(never forward it to the owner)",
}

SETTLE_OWNER = {
    "archived-roadmap-open-checks": "the owner's: carry it to the live roadmap's `## Owner decisions and checks` (or "
                                    "a cockpit issue) and tick it `— carried to <path | #N>`",
    "archived-change-status": "mechanical: `doctor --fix --write`",
    "index-missing-file": "point the row at the file's current path, or drop the row",
    "roadmap-archived-not-removed": "remove roadmap.md (the close moved it)",
    "roadmap-status-mismatch": "set `status` to match the rows",
    "queued-roadmap-done": "archive the finished queued roadmap to foundation/archive/",
    "roadmap-item-shape": "give every item block its at-a-glance row and a status from the vocabulary; a block "
                          "status that contradicts its row is mechanical: `doctor --fix --write`",
    "backlog-without-roadmap": "move live entries to a queued roadmap, then remove the folder",
    "state-missing": "`npx softure-skills state`, commit context/state.json",
    "state-stale": "`npx softure-skills state`, commit context/state.json",
}


class Git:
    """Read-only questions to the repository's history; every answer is [] without full history."""

    def __init__(self, root: str | None) -> None:
        self.root = root
        self.usable = False
        self.shallow = False
        if root:
            probe = self._run("rev-parse", "--is-shallow-repository")
            self.usable = probe.returncode == 0
            self.shallow = probe.stdout.strip() == "true"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", self.root or ".", *args], capture_output=True, text=True)

    def _commits(self, *args: str) -> list[dict]:
        if not self.usable:
            return []
        out = self._run("log", "--format=%h%x09%ad%x09%s", "--date=short", *args)
        commits = []
        for line in out.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
        return commits

    def touching(self, files: list[str], since: str | None) -> list[dict]:
        if not files:
            return []
        args = ["--no-merges", f"-n{LIMIT}"] + ([f"--since={since}"] if since else []) + ["--", *files]
        return self._commits(*args)

    def merges_for(self, change_id: str | None) -> list[dict]:
        """First-parent commits of the main line that name the change (merge commits and squash merges)."""
        if not change_id:
            return []
        return self._commits("--first-parent", "-i", "--fixed-strings", f"--grep={change_id}", f"-n{LIMIT}")

    def release_containing(self, sha: str) -> str | None:
        if not self.usable:
            return None
        out = self._run("tag", "--contains", sha, "--sort=v:refname")
        tags = [tag for tag in out.stdout.split() if SEMVER_TAG_RE.match(tag)]
        return tags[0] if tags else None

    def release_after(self, day: str | None, strict: bool = False) -> dict | None:
        """The first release tag created on or after `day` (after it, with `strict`)."""
        if not self.usable or not day:
            return None
        out = self._run("for-each-ref", "--sort=creatordate", "--format=%(refname:short)\t%(creatordate:short)",
                        "refs/tags")
        for line in out.stdout.splitlines():
            tag, _, date = line.partition("\t")
            if SEMVER_TAG_RE.match(tag) and (date > day if strict else date >= day):
                return {"tag": tag, "date": date}
        return None


def _evidence(kind: str, ref: str, note: str) -> dict:
    return {"kind": kind, "ref": ref, "note": note}


def _commit_evidence(commits: list[dict], note: str) -> list[dict]:
    return [_evidence("commit", c["sha"], f"{note}: {c['date']} {c['subject']}") for c in commits]


def _lines(text: str) -> list[str]:
    return (text or "").split("\n")


def _archived_change_folder(reader, change_id: str | None) -> str | None:
    if not change_id:
        return None
    for name, is_dir in reader.listdir("context/archive"):
        if is_dir and re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name) == change_id:
            return f"context/archive/{name}"
    return None


def _date_of(path: str, meta: dict) -> str | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path.rstrip("/")))
    return meta.get("created") or meta.get("updated") or (match.group(1) if match else None)


def _later_mentions(reader, path: str, needles: list[str]) -> list[dict]:
    """Roadmaps other than `path` (later archived ones, queued, the live one) that mention a needle."""
    candidates = [p for p in archived_roadmap_files(reader) if p > path]
    candidates += [f"{QUEUED_DIR}/{name}" for name, is_dir in reader.listdir(QUEUED_DIR)
                   if not is_dir and name.endswith(".md")]
    candidates.append(ROADMAP_PATH)
    found = []
    for candidate in candidates:
        text = reader.read(candidate)
        if text is None:
            continue
        for number, line in enumerate(_lines(text), start=1):
            if any(needle and re.search(r"(?<![\w-])" + re.escape(needle) + r"(?![\w-])", line)
                   for needle in needles):
                found.append(_evidence("file", f"{candidate}:{number}", line.strip()[:160]))
                break
    return found


def _item_evidence(reader, git: Git, path: str, item: str | None, change_id: str | None) -> list[dict]:
    evidence: list[dict] = []
    folder = _archived_change_folder(reader, change_id)
    if folder:
        evidence.append(_evidence("file", folder + "/", "the item's change was archived"))
    merges = git.merges_for(change_id)
    evidence += _commit_evidence(merges, "merge of the item's change")
    for commit in merges[:1]:
        release = git.release_containing(commit["sha"])
        if release:
            evidence.append(_evidence("release", release, f"the first release that contains {commit['sha']}"))
    evidence += _later_mentions(reader, path, [item, change_id] if item else [change_id])
    return evidence


CARRIED_SETTLE = "mechanical: `doctor --fix --write` ticks it `— carried to <path>` (the row: `carried (to <path>)`)"


def _carried(reader, text: str) -> list[dict]:
    """Evidence when `text` carries a carry marker whose roadmap exists; [] otherwise (a missing target stays open)."""
    import doctor

    target = doctor.carry_target(text)
    found = doctor.resolve_carry(reader, target)
    return [_evidence("file", found, f"the carry marker `{target}` names this roadmap, which took the entry over")] \
        if found else []


def owner_kind(text: str) -> str | None:
    """`decision`, `secret` or `outside` when the line is something only the owner can settle; None otherwise."""
    for kind, pattern in OWNER_KINDS:
        if pattern.search(text or ""):
            return kind
    return None


def _entry(code: str, path: str, line: int | None, text: str, subject: str, evidence: list[dict],
           superseded: list[dict] | None = None, tried: list[str] | None = None, owner_text: str | None = None,
           **extra) -> dict:
    """One worklist entry, classed `evidence`, `superseded` or `owner` (in that order of proof).

    `owner_text` (the line, for checks and Progress items) lets a decision, a secret or a step outside the
    repository stay the owner's even when later work exists; anything else without direct evidence is
    superseded when later work made it obsolete, and the owner's (`unsettled`) only when nothing was found.
    """
    kind = owner_kind(owner_text) if owner_text is not None else None
    if evidence:
        klass, reason, settle = "evidence", None, SETTLE.get(code, "fix the file it names")
    elif kind:
        klass, reason, settle = "owner", kind, SETTLE_OWNER.get(code, SETTLE.get(code, "fix the file it names"))
    elif superseded:
        klass, reason, settle = "superseded", None, SETTLE_SUPERSEDED.get(code, SETTLE.get(code, "fix the file it names"))
        evidence = superseded
    else:
        klass, reason, settle = "owner", "unsettled", SETTLE.get(code, "fix the file it names")
    override = extra.pop("settle_override", None)
    if override and klass == "evidence":
        settle = override
    return {"code": code, "path": path, "line": line, "text": text, "subject": subject, "evidence": evidence,
            "class": klass, "owner": klass == "owner", "owner_reason": reason,
            "tried": [] if klass == "evidence" else (tried or []), "settle": settle, **extra}


# ---------------------------------------------------------------- superseded


def _areas(text: str) -> list[str]:
    """File areas a line names: the folder of each backticked path (`src/booking/page.tsx` -> `src/booking/`)."""
    areas = []
    for path in AREA_RE.findall(text or "") + PATH_RE.findall(text or ""):
        folder = path if path.endswith("/") else (os.path.dirname(path) + "/" if "/" in path else "")
        if folder and folder not in areas and folder.strip("./"):
            areas.append(folder.lstrip("./") if folder.startswith("./") else folder)
    return areas


def _later_changes(reader, day: str | None, needles: list[str], exclude: str | None = None) -> list[dict]:
    """Archived changes dated after `day` whose change.md or plan.md names an item ID, change ID or file area."""
    needles = [needle for needle in needles if needle]
    if not day or not needles:
        return []
    found = []
    for name, is_dir in sorted(reader.listdir("context/archive")):
        date = re.match(r"^(\d{4}-\d{2}-\d{2})-", name)
        folder = f"context/archive/{name}"
        if not is_dir or not date or date.group(1) <= day or folder == exclude:
            continue
        for rel in ("change.md", "plan.md"):
            text = reader.read(f"{folder}/{rel}") or ""
            hit = next((needle for needle in needles
                        if re.search(r"(?<![\w-])" + re.escape(needle) + (r"" if needle.endswith("/") else r"(?![\w-])"),
                                     text)), None)
            if hit:
                found.append(_evidence("file", f"{folder}/", f"a later archived change on the same "
                                                            f"{'area' if hit.endswith('/') else 'item'} (`{hit}`)"))
                break
        if found:
            break
    return found


def _later_release(reader, git: Git, day: str, later: list[str]) -> dict | None:
    """The first release after `day`: a release tag, else a `Release:` line of a later archived roadmap."""
    tag = git.release_after(day, strict=True)
    if tag:
        return _evidence("release", tag["tag"], f"released {tag['date']}, after {day}")
    for path in later:
        for line in sections(reader.read(path) or "").get("Summary", []):
            match = RELEASE_LINE_RE.match(line.strip())
            if match and (match.group("date") or "9999") > day:
                return _evidence("release", match.group("version"), f"released {match.group('date') or 'later'}, "
                                                                     f"recorded in {path}")
    return None


def _superseded_roadmap_entry(reader, git: Git, path: str, text: str, needles: list[str]) -> tuple[list, list]:
    """(superseded evidence, what was tried) for an open check or row of the archived roadmap `path`."""
    closed_on = _date_of(path, frontmatter(reader.read(path) or "")) or ""
    later = [p for p in archived_roadmap_files(reader) if p > path and roadmap_rows(reader.read(p) or "")]
    tried = []
    evidence: list[dict] = []
    release = _later_release(reader, git, closed_on, later) if later else None
    if later and release:
        evidence = [_evidence("file", later[0], f"a later roadmap, closed after {closed_on}"), release]
    tried.append(f"a later closed roadmap: {later[0] if later else 'none'}; a release after {closed_on}: "
                 f"{release['ref'] if release else 'none'}")
    areas = _areas(text)
    if not evidence:
        evidence = _later_changes(reader, closed_on, needles + areas)
        tried.append(f"later archived changes naming {', '.join(f'`{n}`' for n in needles + areas) or 'its item or area'}: "
                     + ("found" if evidence else "none"))
    if git.shallow:
        tried.append("the history is a shallow clone; `git fetch --deepen <n>` may find more")
    return evidence, tried


# ---------------------------------------------------------------- per failure code


def _progress_entries(reader, git: Git, path: str) -> list[dict]:
    import doctor

    text = reader.read(path) or ""
    folder = os.path.dirname(path)
    change = frontmatter(reader.read(f"{folder}/change.md") or "")
    change_id = change.get("change_id") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(folder))
    since = _date_of(folder, change)
    phase_files: dict[str, list[str]] = {}
    current = None
    for line in _lines(text):
        heading = re.match(r"^## Phase (\d+)", line)
        if heading:
            current = heading.group(1)
            continue
        if line.startswith("## "):
            current = None
        if current:
            phase_files.setdefault(current, []).extend(PATH_RE.findall(line))
    open_items = set(doctor.unticked_automated(text))
    entries = []
    in_progress = False
    phase = None
    phase_shas: dict[str, list[str]] = {}
    phase_marks: dict[str, list[bool]] = {}
    phase_lines: dict[str, int] = {}
    pending: list[tuple[int, str, str, str]] = []
    for number, line in enumerate(_lines(text), start=1):
        if line.startswith("## "):
            in_progress = line[3:].strip() == "Progress"
            continue
        if not in_progress:
            continue
        heading = re.match(r"^### Phase (\d+)", line)
        if heading:
            phase = heading.group(1)
            phase_lines.setdefault(phase, number)
            continue
        box = CHECKBOX_RE.match(line)
        if not box:
            continue
        phase_marks.setdefault(phase or "", []).append(box.group("mark") != " ")
        if box.group("mark") != " ":
            tail = line.rsplit(" — ", 1)[-1] if " — " in line else ""
            phase_shas.setdefault(phase or "", []).extend(SHA_TAIL_RE.findall(tail))
        elif box.group("text").strip() in open_items:
            pending.append((number, line, box.group("text").strip(), phase or ""))
    merges = git.merges_for(change_id)
    for number, line, subject, phase in pending:
        evidence = [_evidence("commit", sha, f"cited by a ticked item of phase {phase}")
                    for sha in dict.fromkeys(phase_shas.get(phase, []))]
        files = sorted(set(phase_files.get(phase, [])))
        evidence += _commit_evidence(git.touching(files, since), f"touched {', '.join(files)} after {since}")
        evidence += _commit_evidence(merges, "merge of the change")
        later = [p for p, marks in phase_marks.items() if p.isdigit() and phase.isdigit() and int(p) > int(phase)
                 and marks and all(marks)]
        superseded = [_evidence("file", f"{path}:{phase_lines[p]}", f"phase {p}, later in the same plan, is ticked")
                      for p in sorted(later, key=int)[:1]]
        tried = [f"commits citing or touching phase {phase or '?'} and merges naming `{change_id}`: none",
                 f"a later phase of the plan, all ticked: {'phase ' + later[0] if later else 'none'}"]
        if not superseded:
            superseded = _later_changes(reader, since, _areas(subject), exclude=folder)
            tried.append(f"later archived changes on its area ({', '.join(_areas(subject)) or 'no area named'}): "
                         + ("found" if superseded else "none"))
        if git.shallow:
            tried.append("the history is a shallow clone; `git fetch --deepen <n>` may find more")
        entries.append(_entry("archived-change-progress", path, number, line, subject, evidence,
                              superseded=superseded, tried=tried, owner_text=subject,
                              merged_on=merges[0]["date"] if merges else (change.get("archived_at") or change.get("updated")
                                                                         or since)))
    return entries


def _roadmap_rows_by_id(text: str) -> dict[str, dict]:
    return {row["id"]: row for row in roadmap_rows(text)}


def _summary_entries(reader, git: Git, path: str) -> list[dict]:
    import doctor

    text = reader.read(path) or ""
    rows = _roadmap_rows_by_id(text)
    entries = []
    for row in doctor.summary_rows(text):
        if row["ok"]:
            continue
        item, cell = row["item"], row["cell"]
        change_id = (rows.get(item) or {}).get("change_id")
        evidence = _commit_evidence(git.merges_for(change_id), "merge of the item's change")
        folder = _archived_change_folder(reader, change_id)
        if folder:
            shas = SHA_TAIL_RE.findall(reader.read(f"{folder}/plan.md") or "")
            if shas:
                evidence.append(_evidence("commit", shas[-1], f"last SHA in {folder}/plan.md (not a merge; prefer the merge)"))
        entries.append(_entry("archived-roadmap-summary", path, row["line"], row["text"], f"{item}: {cell}", evidence,
                              cell=cell, item=item, change_id=change_id))
    return entries


def _open_item_entries(reader, git: Git, path: str) -> list[dict]:
    import doctor

    text = reader.read(path) or ""
    entries = []
    rows = {row["id"]: row for row in roadmap_rows(text) if row["status"] not in doctor.CLOSED_STATUSES}
    for number, line in enumerate(_lines(text), start=1):
        match = re.match(r"^\|\s*\*\*([A-Z]+-\d+)\*\*\s*\|", line)
        if not match or match.group(1) not in rows:
            continue
        row = rows.pop(match.group(1))
        status = [cell.strip() for cell in line.strip().strip("|").split("|")][-1]
        carried = _carried(reader, status)
        evidence = carried or _item_evidence(reader, git, path, row["id"], row["change_id"])
        superseded, tried = ([], []) if evidence else _superseded_roadmap_entry(
            reader, git, path, line, [row["id"], row["change_id"]])
        entries.append(_entry("archived-roadmap-open-items", path, number, line, f"{row['id']} ({row['status']})",
                              evidence, superseded=superseded, tried=tried, item=row["id"],
                              change_id=row["change_id"], status=status, settle_override=CARRIED_SETTLE
                              if carried else None))
    return entries


def _open_check_entries(reader, git: Git, path: str) -> list[dict]:
    text = reader.read(path) or ""
    rows = _roadmap_rows_by_id(text)
    include_release = path != pending_release_roadmap(reader)
    wanted = {OWNER_SECTION} | ({RELEASE_SECTION} if include_release else set())
    closed_on = _date_of(path, frontmatter(text))
    release = git.release_after(closed_on)
    entries = []
    section = None
    for number, line in enumerate(_lines(text), start=1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        box = CHECKBOX_RE.match(line)
        if section not in wanted or not box or box.group("mark") != " ":
            continue
        ref = ITEM_REF_RE.search(line)
        item = ref.group("id") if ref else None
        change_id = (rows.get(item) or {}).get("change_id") if item else None
        carried = _carried(reader, line)
        evidence = carried or (_item_evidence(reader, git, path, item, change_id) if item else [])
        if release and section == RELEASE_SECTION:
            evidence.append(_evidence("release", release["tag"], f"released {release['date']}, after the close"))
        superseded, tried = ([], []) if evidence else _superseded_roadmap_entry(
            reader, git, path, line, [item, change_id] if item else [])
        entries.append(_entry("archived-roadmap-open-checks", path, number, line, box.group("text").strip(),
                              evidence, superseded=superseded, tried=tried,
                              owner_text=None if carried else box.group("text"), item=item, change_id=change_id,
                              section=section, settle_override=CARRIED_SETTLE if carried else None,
                              merged_on=closed_on))
    return entries


def _index_entries(reader, root: str | None) -> list[dict]:
    import doctor
    import doctor_fix

    history = doctor_fix.History(root)
    entries = []
    for missing in doctor.missing_index_targets(reader):
        evidence = []
        for candidate in missing["candidates"]:
            traced = history.trace(candidate)
            if traced and traced[0] == "moved":
                evidence.append(_evidence("file", traced[1], f"`{missing['target']}` moved here (git rename history)"))
                break
            if traced:
                evidence.append(_evidence("commit", traced[1], f"deleted `{candidate}` on purpose (no rename); "
                                                                "`doctor --fix --write` marks the row (removed in it)"))
                break
        if not evidence:
            evidence.append(_evidence("file", f"{missing['path']}:{missing['line']}",
                                      "git shows no move or deletion of the target: fix the link or drop the row"))
        entries.append(_entry("index-missing-file", missing["path"], missing["line"], missing["text"],
                              f"`{missing['target']}`", evidence, target=missing["target"]))
    return entries


def _file_entry(failure, reader) -> dict:
    target = failure.path.rstrip("/")
    evidence = [_evidence("file", failure.path, failure.message)] if reader.exists(target) or failure.code in (
        "state-missing",) else []
    return _entry(failure.code, failure.path, None, "", failure.message, evidence)


def sweep(reader, root: str | None, forge: "Forge | None" = None) -> list[dict]:
    """Every failure the doctor reports on `reader`, as worklist entries with evidence.

    `forge` (default: `Forge(root)`, through `gh`) is asked about post-merge steps that the history cannot prove.
    """
    import doctor

    git = Git(root)
    forge = forge if forge is not None else Forge(root)
    entries: list[dict] = []
    indexes_done = False
    for failure in doctor.run_checks(reader, root, baseline=False):
        if failure.severity != "fail":
            continue
        if failure.code == "index-missing-file":
            if not indexes_done:
                entries += _index_entries(reader, root)
                indexes_done = True
        elif failure.code == "archived-change-progress":
            entries += _progress_entries(reader, git, failure.path)
        elif failure.code == "archived-roadmap-summary":
            entries += _summary_entries(reader, git, failure.path)
        elif failure.code == "archived-roadmap-open-items":
            entries += _open_item_entries(reader, git, failure.path)
        elif failure.code == "archived-roadmap-open-checks":
            entries += _open_check_entries(reader, git, failure.path)
        else:
            entries.append(_file_entry(failure, reader))
    for entry in entries:
        _forge_step(entry, forge)
    return entries


# ---------------------------------------------------------------- forge


class Forge:
    """Read-only questions to the repository's forge through `gh` (`$SOFTURE_GH` names another binary).

    `{owner}/{repo}` is resolved by `gh` from the checkout's remote. `reachable` is False without `gh`, without a
    GitHub remote, without credentials, or when `enabled` is False (`--no-forge`); every answer is then None.
    """

    def __init__(self, root: str | None, enabled: bool = True) -> None:
        self.root = root
        self.enabled = enabled and bool(root)
        self._reachable: bool | None = None
        self._releases: list[dict] | None = None

    def _api(self, path: str):
        import json

        try:
            out = subprocess.run([os.environ.get("SOFTURE_GH", "gh"), "api", path], cwd=self.root,
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            return None
        try:
            return json.loads(out.stdout)
        except ValueError:
            return None

    @property
    def reachable(self) -> bool:
        if self._reachable is None:
            self._reachable = self.enabled and isinstance(self._api("repos/{owner}/{repo}"), dict)
        return self._reachable

    def releases(self) -> list[dict]:
        if self._releases is None:
            data = self._api("repos/{owner}/{repo}/releases?per_page=100") if self.reachable else None
            self._releases = sorted((release for release in data or [] if isinstance(release, dict)
                                     and not release.get("draft") and release.get("published_at")),
                                    key=lambda release: release["published_at"])
        return self._releases

    def release_after(self, day: str | None) -> dict | None:
        """The first published release on or after `day`."""
        return next((release for release in self.releases() if release["published_at"][:10] >= (day or "")), None)

    def issue(self, number: str) -> dict | None:
        data = self._api(f"repos/{{owner}}/{{repo}}/issues/{number}") if self.reachable else None
        return data if isinstance(data, dict) else None

    def open_dependabot_before(self, day: str | None) -> list[dict] | None:
        data = self._api("repos/{owner}/{repo}/pulls?state=open&per_page=100") if self.reachable else None
        if not isinstance(data, list):
            return None
        return [pull for pull in data if "dependabot" in ((pull.get("user") or {}).get("login") or "")
                and (pull.get("created_at") or "")[:10] <= (day or "9999")]


RELEASE_STEP_RE = re.compile(r"\b(?:release|released|publish|published)\b", re.IGNORECASE)
ISSUE_REF_RE = re.compile(r"(?<![\w/&])#(\d+)\b")
DEPENDABOT_RE = re.compile(r"\bdependabot\b", re.IGNORECASE)
FORGE_SETTLE = ("check it with the forge before anything goes to the owner (`gh release list`, `gh issue view <N>`, "
                "`gh pr list --author app/dependabot`), then tick it with what the forge shows")


def forge_checks(text: str) -> list[tuple[str, str | None]]:
    """What the forge can prove for a post-merge step: ("release", None), ("issue", "<N>"), ("dependabot", None)."""
    checks: list[tuple[str, str | None]] = []
    if RELEASE_STEP_RE.search(text or ""):
        checks.append(("release", None))
    checks += [("issue", number) for number in dict.fromkeys(ISSUE_REF_RE.findall(text or ""))]
    if DEPENDABOT_RE.search(text or ""):
        checks.append(("dependabot", None))
    return checks


def _forge_step(entry: dict, forge: Forge) -> None:
    """Settle a post-merge step the history cannot prove with the forge: `evidence`, else `forge` when unreachable.

    Only entries the sweep would hand to the owner as `unsettled` or `outside` are asked about; a decision or a
    secret stays the owner's. Every check the line names must hold for `evidence`.
    """
    if entry["class"] != "owner" or entry.get("owner_reason") not in ("unsettled", "outside"):
        return
    checks = forge_checks(entry.get("subject") or entry.get("text") or "")
    if not checks:
        return
    day = entry.get("merged_on")
    if not forge.reachable:
        entry.update({"class": "forge", "owner": False, "owner_reason": None, "settle": FORGE_SETTLE,
                      "tried": entry.get("tried", []) + ["the forge: not reachable here (no `gh`, no GitHub remote or "
                                                          "no credentials); an agent with `gh` checks it"]})
        return
    found: list[dict] = []
    missing: list[str] = []
    for kind, value in checks:
        if kind == "release":
            release = forge.release_after(day)
            if release:
                found.append(_evidence("release", release.get("tag_name") or "?",
                                       f"published {release['published_at'][:10]}, on or after the merge ({day})"))
            else:
                missing.append(f"a release published on or after {day}: none")
        elif kind == "issue":
            issue = forge.issue(value)
            pull = (issue or {}).get("pull_request") or {}
            if issue and issue.get("state") == "closed":
                what = "pull request merged" if pull.get("merged_at") else ("pull request closed" if pull else "closed")
                found.append(_evidence("issue", f"#{value}", f"{what} {(issue.get('closed_at') or '')[:10]}".strip()))
            else:
                missing.append(f"#{value}: {issue.get('state') if issue else 'not found'}")
        else:
            pulls = forge.open_dependabot_before(day)
            if pulls == []:
                found.append(_evidence("forge", "dependabot", f"no open Dependabot pull request opened by {day}"))
            else:
                missing.append(f"open Dependabot pull requests opened by {day}: "
                               + (", ".join(f"#{pull.get('number')}" for pull in pulls) if pulls else "unknown"))
    if not missing:
        entry.update({"class": "evidence", "owner": False, "owner_reason": None, "evidence": found, "tried": [],
                      "settle": SETTLE.get(entry["code"], "fix the file it names")})
    else:
        entry["tried"] = entry.get("tried", []) + [f"the forge: {note}" for note in missing]
