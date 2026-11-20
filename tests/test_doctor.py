"""Tests for skills/softure-doctor/scripts (doctor.py and context_state.py).

    python3 -m unittest discover -s tests

`tests/fixtures/doctor/clean/` is a project whose context/ follows the contract. Every folder in
`tests/fixtures/doctor/cases/<code>/` is one drift case: files laid over the clean tree (`_remove` lists
paths to delete, `_keep_state` keeps the clean state.json instead of regenerating it). The doctor must
fail with exactly that code on the case and pass on the clean tree.

`tests/fixtures/doctor/fix/<case>/` holds one historical shape that `doctor --fix` repairs. Its optional
`_history` file is replayed as commits before the overlay lands (`add <path>`, `mv <from> <to>`, `rm <path>`),
so rename detection has a real history to read.

`tests/fixtures/doctor/sweep/<case>/` holds one judgement case for `doctor --sweep`, with the history its
evidence comes from (`commit <path> <message>` writes the file and commits it with that message, `tag <name>`;
`add` and `rm` take an optional commit message after the path).

`tests/fixtures/doctor/state/<case>/` holds one shape of `context/` that an outside reader of `state.json` must get
right (a project between roadmaps, an idle placeholder roadmap); `StateTest` checks what `write` produces from it.

`tests/fixtures/doctor/measure/adopter/` mirrors the shapes adopting repositories hold (mentions in index cells,
targets deleted on purpose, cancelled Progress items, non-SHA Summary cells, owner checks of a roadmap that later
roadmaps and releases superseded). `MeasureTest` pins its numbers before and after `--fix` and per sweep class.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "softure-doctor", "scripts")
SCHEMA = os.path.join(ROOT, "skills", "softure-doctor", "references", "state.schema.json")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "doctor")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
sys.dont_write_bytecode = True  # the package ships skills/, so no __pycache__ may land there
sys.path.insert(0, SCRIPTS)
import context_state  # noqa: E402

CASES = sorted(os.listdir(os.path.join(FIXTURES, "cases")))
FIX_CASES = sorted(os.listdir(os.path.join(FIXTURES, "fix")))
SWEEP_CASES = sorted(os.listdir(os.path.join(FIXTURES, "sweep")))


def validate(value, schema: dict, path: str = "$") -> list[str]:
    """A small JSON Schema subset (type, enum, required, properties, additionalProperties, items)."""
    errors: list[str] = []
    types = schema.get("type")
    if types:
        names = types if isinstance(types, list) else [types]
        checks = {"object": dict, "array": list, "string": str, "integer": int, "null": type(None), "boolean": bool}
        if not any(isinstance(value, checks[name]) and not (name == "integer" and isinstance(value, bool))
                   for name in names):
            return [f"{path}: {type(value).__name__} is not {names}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing {key}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errors += validate(item, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected {key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors += validate(item, schema["items"], f"{path}[{index}]")
    return errors


class Project:
    """A throwaway git repository holding a copy of the clean fixture."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        shutil.copytree(os.path.join(FIXTURES, "clean", "context"), os.path.join(self.root, "context"))
        self.git("init", "-q", "-b", "main")
        self.commit("clean project")

    def cleanup(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env={**os.environ, **GIT_ENV}, check=True,
                              capture_output=True, text=True).stdout

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def path(self, rel: str) -> str:
        return os.path.join(self.root, rel)

    def read(self, rel: str) -> str:
        with open(self.path(rel), encoding="utf-8") as fh:
            return fh.read()

    def write(self, rel: str, text: str) -> None:
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), "w", encoding="utf-8") as fh:
            fh.write(text)

    def replay_history(self, source: str) -> None:
        history = os.path.join(source, "_history")
        if not os.path.exists(history):
            return
        with open(history, encoding="utf-8") as fh:
            steps = [line.split() for line in fh.read().splitlines() if line.strip()]
        for step in steps:
            message = " ".join(step)
            if step[0] == "add":
                self.write(step[1], f"# {os.path.basename(step[1])}\n\nContent of {step[1]}.\n")
                message = " ".join(step[2:]) or message
            elif step[0] == "mv":
                os.makedirs(os.path.dirname(self.path(step[2])), exist_ok=True)
                self.git("mv", step[1], step[2])
            elif step[0] == "rm":
                self.git("rm", "-q", step[1])
                message = " ".join(step[2:]) or message
            elif step[0] == "commit":
                existing = self.read(step[1]) if os.path.exists(self.path(step[1])) else ""
                self.write(step[1], existing + f"// {' '.join(step[2:])}\n")
                self.commit(" ".join(step[2:]))
                continue
            elif step[0] == "tag":
                self.git("tag", step[1])
                continue
            self.commit(message)

    def apply_case(self, case: str, group: str = "cases") -> None:
        source = os.path.join(FIXTURES, group, case)
        self.replay_history(source)
        for folder, _, files in os.walk(source):
            for name in files:
                if name.startswith("_"):
                    continue
                rel = os.path.relpath(os.path.join(folder, name), source)
                os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
                shutil.copyfile(os.path.join(folder, name), self.path(rel))
        removals = os.path.join(source, "_remove")
        if os.path.exists(removals):
            with open(removals, encoding="utf-8") as fh:
                for rel in fh.read().split():
                    os.remove(self.path(rel))
        if not os.path.exists(os.path.join(source, "_keep_state")) and os.path.exists(self.path(context_state.STATE_PATH)):
            self.state("write")

    def state(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "context_state.py"), *args, "--root", self.root],
                              env={**os.environ, **GIT_ENV}, capture_output=True, text=True)

    def doctor(self, *args: str) -> tuple[int, dict]:
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "doctor.py"), "--root", self.root, "--json",
                                 *args], env={**os.environ, **GIT_ENV}, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def codes(self) -> set[str]:
        return {failure["code"] for failure in self.doctor()[1]["failures"]}


class DoctorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def tearDown(self) -> None:
        self.project.cleanup()

    def test_clean_fixture_passes(self) -> None:
        code, report = self.project.doctor()
        self.assertEqual(report["failures"], [])
        self.assertEqual(code, 0)

    def test_each_case_fails_with_its_code(self) -> None:
        self.assertEqual(len(CASES), 12)
        for case in CASES:
            with self.subTest(case=case):
                project = Project()
                try:
                    project.apply_case(case)
                    code, report = project.doctor()
                    self.assertEqual(code, 1, report)
                    self.assertEqual({failure["code"] for failure in report["failures"]}, {case}, report)
                finally:
                    project.cleanup()

    def test_state_never_written_is_a_note(self) -> None:
        os.remove(self.project.path(context_state.STATE_PATH))
        self.project.git("rm", "-q", "--cached", context_state.STATE_PATH)
        self.project.git("commit", "-q", "--amend", "-m", "project before state.json")
        code, report = self.project.doctor()
        self.assertEqual(code, 0, report)
        self.assertEqual([note["code"] for note in report["notes"]], ["state-missing"])

    def test_change_branch_editing_its_change_keeps_the_state_fresh(self) -> None:
        rel = "context/changes/search-titles/change.md"
        self.project.write(rel, self.project.read(rel).replace("status: implementing", "status: implemented"))
        self.project.write("context/changes/new-thing/change.md", "---\nchange_id: new-thing\nstatus: new\n---\n")
        code, report = self.project.doctor()
        self.assertEqual(code, 0, report)

    def test_no_context_directory_passes(self) -> None:
        shutil.rmtree(self.project.path("context"))
        code, _ = self.project.doctor()
        self.assertEqual(code, 0)


class FixTest(unittest.TestCase):
    """`doctor --fix`: the mechanical repairs, dry run by default, idempotent after `--write`."""

    def test_each_fix_case_is_repaired_and_a_second_run_changes_nothing(self) -> None:
        for case in FIX_CASES:
            with self.subTest(case=case):
                project = Project()
                try:
                    project.apply_case(case, "fix")
                    project.commit(case)
                    self.assertTrue(project.codes(), "the case must fail before the fix")
                    before = project.git("status", "--porcelain")
                    code, dry = project.doctor("--fix")
                    self.assertEqual(code, 0)
                    self.assertFalse(dry["written"])
                    self.assertTrue(dry["edits"], dry)
                    self.assertEqual(dry["remaining"], [], dry)
                    self.assertEqual(project.git("status", "--porcelain"), before, "a dry run writes nothing")
                    code, applied = project.doctor("--fix", "--write")
                    self.assertEqual(applied["edits"], dry["edits"])
                    self.assertEqual(project.codes(), set())
                    changed = project.git("status", "--porcelain").split()
                    self.assertTrue(all(path.startswith("context/") for path in changed if "/" in path), changed)
                    _, again = project.doctor("--fix", "--write")
                    self.assertEqual(again["edits"], [])
                finally:
                    project.cleanup()

    def test_legacy_status_is_kept(self) -> None:
        project = Project()
        try:
            project.apply_case("legacy-status", "fix")
            project.doctor("--fix", "--write")
            root = "context/archive"
            for name in os.listdir(project.path(root)):
                meta = context_state.frontmatter(project.read(f"{root}/{name}/change.md"))
                self.assertEqual(meta["status"], "archived")
                if name.endswith("-no-status"):
                    self.assertNotIn("legacy_status", meta)
                elif name.startswith("2026-08"):
                    self.assertEqual(meta["legacy_status"], name.split("-old-", 1)[1])
        finally:
            project.cleanup()

    def test_moved_links_follow_git_history(self) -> None:
        project = Project()
        try:
            project.apply_case("index-moved", "fix")
            project.commit("index")
            project.doctor("--fix", "--write")
            index = project.read("context/archive/2026-09-01-staff-day-view/INDEX.md")
            self.assertIn("| [research](research.md) |", index)
            self.assertIn("| `frame.md` |", index)
        finally:
            project.cleanup()

    def test_deleted_file_is_marked_with_the_commit_that_removed_it(self) -> None:
        project = Project()
        try:
            project.apply_case("index-gone", "fix")
            project.commit("index")
            removed = project.git("rev-parse", "--short", "HEAD~1").strip()  # the `rm` commit
            project.doctor("--fix", "--write")
            index = project.read("context/archive/2026-09-01-staff-day-view/INDEX.md")
            self.assertIn(f"draft (removed in {removed}: ../../changes/staff-day-view/draft.md)", index)
        finally:
            project.cleanup()

    def test_judgement_cases_and_live_indexes_are_left_alone(self) -> None:
        project = Project()
        try:
            for case in ("archived-change-progress", "archived-roadmap-open-items", "index-missing-file"):
                project.apply_case(case)
            project.apply_case("legacy-status", "fix")
            project.commit("history")
            code, report = project.doctor("--fix", "--write")
            self.assertEqual({failure["code"] for failure in report["remaining"]},
                             {"archived-change-progress", "archived-roadmap-open-items", "index-missing-file"})
            self.assertTrue(any(skip["path"] == "context/foundation/roadmaps/README.md" for skip in report["skipped"]))
            self.assertEqual(project.codes(), {"archived-change-progress", "archived-roadmap-open-items",
                                               "index-missing-file"})
        finally:
            project.cleanup()


def settle(project: Project, entry: dict) -> None:
    """What the skill's sweep tells an agent to do with one worklist entry, applied from its evidence alone."""
    lines = project.read(entry["path"]).split("\n")
    index = entry["line"] - 1
    assert lines[index] == entry["text"], (lines[index], entry["text"])
    text = entry["text"]
    commits = [evidence["ref"] for evidence in entry["evidence"] if evidence["kind"] == "commit"]
    if entry["class"] == "superseded" and entry["code"] == "archived-roadmap-open-items":
        lines[index] = text.replace(entry["status"], f"dropped (obsolete: superseded by {entry['evidence'][0]['ref']})")
    elif entry["class"] == "superseded":
        refs = " and ".join(evidence["ref"] for evidence in entry["evidence"])
        lines[index] = text.replace("- [ ] ", "- [x] ", 1) + f" — obsolete: superseded by {refs}"
    elif entry["code"] == "archived-change-progress":
        lines[index] = text.replace("- [ ] ", "- [x] ", 1) + f" — {commits[0]}"
    elif entry["code"] == "archived-roadmap-summary":
        lines[index] = text.replace(entry["cell"], commits[0])
    elif entry["code"] == "archived-roadmap-open-items":
        lines[index] = text.replace(entry["status"], f"done (merged {commits[0]})")
    elif entry["code"] == "archived-roadmap-open-checks" and entry["owner"]:
        live = "context/foundation/roadmap.md"
        roadmap = project.read(live).replace("## Owner decisions and checks\n",
                                             f"## Owner decisions and checks\n- [ ] {entry['subject']}\n", 1)
        project.write(live, roadmap)
        lines[index] = text.replace("- [ ] ", "- [x] ", 1) + f" — carried to {live}"
    elif entry["code"] == "archived-roadmap-open-checks":
        lines[index] = text.replace("- [ ] ", "- [x] ", 1) + f" — done: {entry['evidence'][0]['ref']}"
    else:
        raise AssertionError(f"no scripted settlement for {entry['code']}")
    project.write(entry["path"], "\n".join(lines))


class SweepTest(unittest.TestCase):
    """`doctor --sweep`: a worklist with evidence for every judgement case, worked to doctor exit 0."""

    EXPECTED = {
        "progress": ("archived-change-progress", "src/day-view.ts"),
        "summary": ("archived-roadmap-summary", "staff-day-view"),
        "open-items": ("archived-roadmap-open-items", "v1.3.0"),
        "open-checks": ("archived-roadmap-open-checks", "reminder-sms"),
    }

    def test_each_case_lists_evidence_or_owner(self) -> None:
        self.assertEqual(set(SWEEP_CASES), set(self.EXPECTED))
        for case in SWEEP_CASES:
            with self.subTest(case=case):
                project = Project()
                try:
                    project.apply_case(case, "sweep")
                    project.commit(case)
                    code, expected = self.EXPECTED[case]
                    self.assertEqual(project.codes(), {code})
                    status, report = project.doctor("--sweep")
                    self.assertEqual(status, 1)
                    entries = report["entries"]
                    self.assertTrue(entries)
                    for entry in entries:
                        self.assertEqual(entry["code"], code)
                        self.assertTrue(entry["evidence"] or entry["owner"], entry)
                        self.assertEqual(project.read(entry["path"]).split("\n")[entry["line"] - 1], entry["text"])
                    notes = json.dumps([entry["evidence"] for entry in entries])
                    self.assertIn(expected, notes)
                finally:
                    project.cleanup()

    def test_open_checks_split_evidence_from_owner_items(self) -> None:
        project = Project()
        try:
            project.apply_case("open-checks", "sweep")
            project.commit("history")
            entries = project.doctor("--sweep")[1]["entries"]
            self.assertEqual(sorted((entry["item"], entry["section"], entry["owner"]) for entry in entries),
                             [("RM-1", "Before the next release", False), ("RM-1", "Owner decisions and checks", False),
                              ("RM-2", "Owner decisions and checks", True)])
            kinds = {evidence["kind"] for entry in entries for evidence in entry["evidence"]}
            self.assertEqual(kinds, {"commit", "release"})
        finally:
            project.cleanup()

    def test_scripted_sweep_ends_at_doctor_exit_0(self) -> None:
        project = Project()
        try:
            for case in SWEEP_CASES:
                project.apply_case(case, "sweep")
            project.commit("history")
            self.assertEqual(project.codes(), {code for code, _ in self.EXPECTED.values()})
            _, report = project.doctor("--sweep")
            for entry in report["entries"]:
                settle(project, entry)
            project.state("write")
            code, final = project.doctor()
            self.assertEqual((code, final["failures"]), (0, []))
            status, empty = project.doctor("--sweep")
            self.assertEqual((status, empty["entries"]), (0, []))
            queue = json.loads(project.read(context_state.STATE_PATH))["owner_queue"]
            self.assertTrue(any("RM-2" in entry["text"] and entry["source"].startswith("context/foundation/roadmap.md")
                                for entry in queue), "the owner item was carried to the live roadmap")
            self.assertFalse(any("/archive/" in entry["source"] for entry in queue))
        finally:
            project.cleanup()


class MeasureTest(unittest.TestCase):
    """`tests/fixtures/doctor/measure/adopter/`: the shapes adopting repositories hold (issue #41), measured.

    The numbers are what the release notes report: failures before `--fix`, its edits, failures after it,
    and the sweep's entries by class. The owner class is the one that must stay a handful.
    """

    EXPECTED = {
        "failures": 4,
        "fix_edits": 4,
        "after_fix": 2,
        "sweep": {"total": 5, "with_evidence": 0, "superseded": 3, "owner": 2},
    }

    def measure(self, project: Project) -> dict:
        _, before = project.doctor()
        _, fix = project.doctor("--fix", "--write")
        _, after = project.doctor()
        _, swept = project.doctor("--sweep")
        return {"failures": len(before["failures"]), "fix_edits": len(fix["edits"]),
                "after_fix": len(after["failures"]), "sweep": swept["summary"]}

    def test_adopter_numbers(self) -> None:
        project = Project()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            self.assertEqual(self.measure(project), self.EXPECTED)
        finally:
            project.cleanup()

    def test_mentions_are_not_links_and_removed_targets_are_marked(self) -> None:
        project = Project()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            _, report = project.doctor()
            missing = [failure["message"] for failure in report["failures"] if failure["code"] == "index-missing-file"]
            self.assertEqual(len(missing), 2, missing)
            self.assertFalse(any(name in " ".join(missing) for name in ("change.md", "research.md", "plan.md")))
            project.doctor("--fix", "--write")
            folder = "context/archive/2026-07-01-booking-page"
            removed = project.git("log", "-1", "--format=%h", "--diff-filter=D", "--",
                                  f"{folder}/old-notes.md").strip()
            self.assertIn(f"| old-notes.md (removed in {removed}) |", project.read(f"{folder}/INDEX.md"))
            self.assertIn("step 0 (removed in ", project.read(f"{folder}/screenshots/README.md"))
            self.assertNotIn("index-missing-file", project.codes())
        finally:
            project.cleanup()

    def test_dropped_progress_items_are_not_open_and_fix_normalises_them(self) -> None:
        project = Project()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            plan = "context/archive/2026-07-01-booking-page/plan.md"
            _, report = project.doctor()
            message = next(f["message"] for f in report["failures"] if f["code"] == "archived-change-progress")
            self.assertTrue(message.startswith("1 unticked"), message)
            project.doctor("--fix", "--write")
            text = project.read(plan)
            self.assertIn("- [x] ~~1.1 A one-column layout~~ — dropped: cancelled, replaced by 1.4\n", text)
            self.assertIn("- [x] ~~1.5 Inline field errors~~ — dropped: the redesign moved errors to a summary\n", text)
            self.assertIn("- [ ] 1.3 `npm test` green\n", text)
            _, again = project.doctor("--fix")
            self.assertFalse([e for e in again["edits"] if e["path"] == plan], again["edits"])
        finally:
            project.cleanup()

    def test_dropped_item_reads_only_explicit_notes(self) -> None:
        import doctor
        dropped = {
            "~~1.1 A one-column layout~~ — cancelled, replaced by 1.12": "~~1.1 A one-column layout~~ — dropped: cancelled, replaced by 1.12",
            "~~2.3 Export to CSV~~": "~~2.3 Export to CSV~~ — dropped: struck through, no reason recorded",
            "1.4 SMS fallback (not applicable)": "~~1.4 SMS fallback~~ — dropped: not applicable",
            "1.5 Inline errors - dropped: moved to a summary": "~~1.5 Inline errors~~ — dropped: moved to a summary",
        }
        for text, expected in dropped.items():
            self.assertEqual(doctor.dropped_line(text), expected)
        for text in ("1.3 Handle cancelled bookings", "1.6 `npm test` green", "1.7 Show dropped calls — 9b03e77x",
                     "1.8 Mark obsolete slots"):
            self.assertIsNone(doctor.dropped_item(text), text)

    def test_superseded_checks_carry_their_evidence_and_owner_keeps_only_its_kinds(self) -> None:
        project = Project()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            project.doctor("--fix", "--write")
            entries = project.doctor("--sweep")[1]["entries"]
            by_subject = {entry["subject"].split(" ", 2)[1] if entry["subject"].startswith("1.") else
                          entry["subject"].split(" ")[0]: entry for entry in entries}
            screenshots = by_subject["Review"]
            self.assertEqual(screenshots["class"], "superseded")
            self.assertEqual([(e["kind"], e["ref"]) for e in screenshots["evidence"]],
                             [("file", "context/foundation/archive/2026-08-20-roadmap.md"), ("release", "v1.0.0")])
            self.assertEqual(by_subject["After"]["class"], "superseded")
            self.assertEqual(by_subject["`npm"]["class"], "superseded")
            self.assertIn("phase 2", by_subject["`npm"]["evidence"][0]["note"])
            owner = sorted((entry["owner_reason"], entry["subject"]) for entry in entries if entry["owner"])
            self.assertEqual([reason for reason, _ in owner], ["decision", "secret"], owner)
            self.assertTrue(all(entry["tried"] for entry in entries if entry["owner"]))
            for entry in entries:
                settle(project, entry)
            project.state("write")
            self.assertEqual(project.codes(), set())
        finally:
            project.cleanup()

    def test_owner_kinds(self) -> None:
        import doctor_sweep
        cases = {
            "Decide whether reminders also go out by email.": "decision",
            "Set `SMS_SENDER` in production (**RM-1**)": "secret",
            "Connect the calendar connector for the clinic account": "secret",
            "Check that a reminder arrives on a real phone": "outside",
            "Review the screenshots of the booking page": None,
            "After the v1.0.0 release, re-run the booking smoke test.": None,
            "`npm test` green": None,
        }
        for text, kind in cases.items():
            self.assertEqual(doctor_sweep.owner_kind(text), kind, text)

    def test_summary_reads_only_the_item_tables_merge_column(self) -> None:
        import doctor
        text = "\n".join([
            "## Summary", "",
            "| ID | Item | What changed | Merge |", "| --- | --- | --- | --- |",
            "| A-1 | one | x | 4f2a9c1 |", "| A-2 | two | x | carried |", "| A-3 | three | x | v1.4.0 |",
            "| A-4 | four | x | — (done on main, no PR) |", "| A-5 | five | x | dropped (no longer wanted) |",
            "| A-6 | six | x | merge SHA after the PR |", "| A-7 | seven | x | TBD |", "",
            "| Finding | Severity |", "| --- | --- |", "| 1 | high |", "",
            "Release: v1.4.0 (2026-10-02)",
        ])
        self.assertEqual(doctor.summary_placeholders(text), ['A-6: "merge SHA after the PR"', 'A-7: "TBD"'])

    def test_shallow_clone_marks_what_it_can_see(self) -> None:
        project = Project()
        clone = tempfile.TemporaryDirectory()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            subprocess.run(["git", "clone", "-q", "--depth", "4", f"file://{project.root}", clone.name + "/s"],
                           check=True, env={**os.environ, **GIT_ENV})
            shallow = Project.__new__(Project)
            shallow.root = clone.name + "/s"
            _, fix = shallow.doctor("--fix")
            index_edits = [edit for edit in fix["edits"] if edit["code"] == "index-missing-file"]
            self.assertEqual([edit["what"].split(" marked")[0] for edit in index_edits], ["`old-notes.md`"])
            self.assertTrue(any("shallow" in skip["why"] for skip in fix["skipped"]), fix["skipped"])
        finally:
            clone.cleanup()
            project.cleanup()


class BrokenPipeTest(unittest.TestCase):
    """Piping into `head` closes stdout early; the scripts stop quietly instead of printing a traceback."""

    def test_closed_stdout_is_quiet(self) -> None:
        project = Project()
        try:
            project.apply_case("adopter", "measure")
            project.commit("adopter")
            commands = [[os.path.join(SCRIPTS, "doctor.py"), "--root", project.root],
                        [os.path.join(SCRIPTS, "doctor.py"), "--sweep", "--root", project.root],
                        [os.path.join(SCRIPTS, "doctor.py"), "--fix", "--root", project.root],
                        [os.path.join(SCRIPTS, "context_state.py"), "print", "--root", project.root]]
            for command in commands:
                with self.subTest(command=command[1:2]):
                    proc = subprocess.Popen([sys.executable, *command], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, env={**os.environ, **GIT_ENV})
                    proc.stdout.close()  # the reader is gone before the first line
                    _, err = proc.communicate()
                    self.assertEqual(err.decode(), "")
                    self.assertEqual(proc.returncode, 141)
        finally:
            project.cleanup()


class BaselineTest(unittest.TestCase):
    """`doctor --baseline`: a last resort that accepts today's failures and only ever shrinks."""

    def setUp(self) -> None:
        self.project = Project()
        for case in ("archived-change-progress", "index-missing-file"):
            self.project.apply_case(case)
        self.project.commit("history")

    def tearDown(self) -> None:
        self.project.cleanup()

    def baseline(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "doctor.py"), "--root", self.project.root,
                               "--baseline"], env={**os.environ, **GIT_ENV}, capture_output=True, text=True)

    def entries(self) -> list[tuple[str, str]]:
        data = json.loads(self.project.read("context/doctor-baseline.json"))
        return [(entry["code"], entry["path"]) for entry in data["entries"]]

    def test_unchanged_tree_passes(self) -> None:
        self.assertEqual(self.baseline().returncode, 0)
        self.assertEqual({code for code, _ in self.entries()}, {"archived-change-progress", "index-missing-file"})
        code, report = self.project.doctor()
        self.assertEqual((code, report["failures"]), (0, []))
        self.assertEqual({note["severity"] for note in report["notes"]}, {"baselined"})

    def test_new_drift_fails(self) -> None:
        self.baseline()
        self.project.apply_case("archived-change-status")
        self.assertEqual(self.project.codes(), {"archived-change-status"})
        result = self.baseline()
        self.assertEqual(result.returncode, 1, "the baseline never grows")
        self.assertIn("not added", result.stdout)
        self.assertNotIn("archived-change-status", {code for code, _ in self.entries()})
        self.assertEqual(self.project.codes(), {"archived-change-status"})

    def test_fixed_entry_must_be_removed(self) -> None:
        self.baseline()
        plan = "context/archive/2026-09-01-staff-day-view/plan.md"
        shutil.copyfile(os.path.join(FIXTURES, "clean", plan), self.project.path(plan))
        self.assertEqual(self.project.codes(), {"baseline-stale"})
        result = self.baseline()
        self.assertEqual(result.returncode, 0)
        self.assertIn("dropped (fixed): archived-change-progress", result.stdout)
        self.assertEqual(self.entries(), [("index-missing-file", "context/foundation/roadmaps/README.md")])
        self.assertEqual(self.project.codes(), set())

    def test_empty_baseline_is_removed_and_state_is_never_baselined(self) -> None:
        self.baseline()
        for case in ("archived-change-progress", "index-missing-file"):
            for folder, _, files in os.walk(os.path.join(FIXTURES, "cases", case)):
                for name in files:
                    rel = os.path.relpath(os.path.join(folder, name), os.path.join(FIXTURES, "cases", case))
                    shutil.copyfile(os.path.join(FIXTURES, "clean", rel), self.project.path(rel))
        self.assertEqual(self.baseline().returncode, 0)
        self.assertFalse(os.path.exists(self.project.path("context/doctor-baseline.json")))
        self.project.apply_case("state-stale")
        self.assertEqual(self.baseline().returncode, 0)
        self.assertFalse(os.path.exists(self.project.path("context/doctor-baseline.json")))
        self.assertEqual(self.project.codes(), {"state-stale"})

    def test_sweep_ignores_the_baseline(self) -> None:
        self.baseline()
        status, report = self.project.doctor("--sweep")
        self.assertEqual(status, 1)
        self.assertEqual({entry["code"] for entry in report["entries"]}, {"archived-change-progress", "index-missing-file"})


class StateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def tearDown(self) -> None:
        self.project.cleanup()

    def state(self) -> dict:
        return json.loads(self.project.read(context_state.STATE_PATH))

    def test_state_matches_the_schema(self) -> None:
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertEqual(validate(self.state(), schema), [])
        self.project.write("context/foundation/roadmap.md", "# nothing parsable\n")
        self.project.state("write")
        self.assertEqual(validate(self.state(), schema), [])

    def test_project_between_roadmaps_comes_from_workflow_json(self) -> None:
        self.project.apply_case("between-roadmaps", "state")
        state = self.state()
        self.assertIsNone(state["active_roadmap"])
        self.assertEqual(state["project"], "Example clinic")

    def test_project_between_roadmaps_falls_back_to_the_repository_name(self) -> None:
        self.project.apply_case("between-roadmaps", "state")
        workflow = json.loads(self.project.read(context_state.WORKFLOW_PATH))
        del workflow["project"]
        self.project.write(context_state.WORKFLOW_PATH, json.dumps(workflow, indent=2) + "\n")
        self.project.git("remote", "add", "origin", "https://github.com/acme/clinic-site.git")
        self.project.state("write")
        self.assertEqual(self.state()["project"], "clinic-site")
        self.project.git("remote", "remove", "origin")
        self.project.state("write")
        self.assertEqual(self.state()["project"], os.path.basename(self.project.root))
        with open(SCHEMA, encoding="utf-8") as fh:
            self.assertEqual(validate(self.state(), json.load(fh)), [])

    def test_idle_placeholder_roadmap_is_no_active_roadmap(self) -> None:
        self.project.apply_case("idle-roadmap", "state")
        state = self.state()
        self.assertIsNone(state["active_roadmap"])
        self.assertEqual(state["project"], "Example clinic")
        self.assertFalse(any(entry["source"].startswith(context_state.ROADMAP_PATH) for entry in state["owner_queue"]))
        rel = "context/foundation/roadmap.md"
        for line in ("status: idle\n", "roadmap: none\n"):
            with self.subTest(dropped=line.strip()):
                self.project.write(rel, self.project.read(rel).replace(line, ""))
                self.project.state("write")
                self.assertIsNone(self.state()["active_roadmap"])
                self.project.apply_case("idle-roadmap", "state")

    def test_owner_queue_lists_what_waits_for_the_owner(self) -> None:
        queue = self.state()["owner_queue"]
        kinds = {(entry["kind"], entry["item"]) for entry in queue}
        self.assertIn(("decision", "SR-5"), kinds)
        self.assertIn(("secret", "SR-4"), kinds)
        self.assertIn(("step", "SR-1"), kinds)
        self.assertIn(("decision", "PY-1"), kinds)
        self.assertNotIn(("decision", "BK-2"), kinds, "a ticked entry of an archived roadmap is not waiting")
        self.assertFalse(any("/archive/" in entry["source"] for entry in queue))
        self.assertTrue(any(entry["kind"] == "word" and entry["text"].startswith("release: SR-4") for entry in queue))
        self.assertTrue(any(entry["kind"] == "word" and "payments" in entry["text"] for entry in queue))
        self.assertFalse(any("Run the reindex" in entry["text"] for entry in queue), "ticked lines are not waiting")
        self.assertEqual([entry["since"] for entry in queue], sorted(entry["since"] for entry in queue))

    def test_active_roadmap_counts_and_items(self) -> None:
        active = self.state()["active_roadmap"]
        self.assertEqual((active["slug"], active["done"], active["total"]), ("search", 2, 5))
        self.assertEqual([item["id"] for item in active["items"]], ["SR-2", "SR-3", "SR-5"])
        self.assertEqual(active["items"][0]["stage"], "implement 2/3")
        self.assertEqual(self.state()["last_release"]["version"], "v1.4.0")

    def test_since_is_kept_and_updated_at_is_stable(self) -> None:
        state = self.state()
        state["owner_queue"][0]["since"] = "2026-01-01"
        state["updated_at"] = "2026-01-01T00:00:00Z"
        self.project.write(context_state.STATE_PATH, json.dumps(state, indent=2) + "\n")
        self.project.state("write")
        rewritten = self.state()
        self.assertEqual(rewritten["owner_queue"][0]["since"], "2026-01-01")
        self.assertEqual(rewritten["updated_at"], "2026-01-01T00:00:00Z")

    def test_staged_reads_only_the_index(self) -> None:
        rel = "context/foundation/roadmap.md"
        self.project.write(rel, self.project.read(rel).replace("| autonomous | ready |", "| autonomous | blocked (x) |"))
        result = self.project.state("write", "--staged")
        self.assertEqual(result.returncode, 0, result.stderr)
        items = {item["id"]: item["status"] for item in self.state()["active_roadmap"]["items"]}
        self.assertEqual(items["SR-3"], "ready")
        self.assertIn(context_state.STATE_PATH, self.project.git("diff", "--cached", "--name-only")
                      or context_state.STATE_PATH)

    def test_state_matches_after_a_roadmap_close(self) -> None:
        roadmap = self.project.read("context/foundation/roadmap.md")
        closed = (roadmap.replace("status: ready", "status: done")
                  .replace("| autonomous | ready |", "| autonomous | done |")
                  .replace("(implement 2/3, since 2026-11-08; cloud session, branch `claude/x` — do not take in "
                           "another session)", "done")
                  .replace("**in_progress** done", "done")
                  .replace("| owner | blocked (provider account) |", "| owner | carried (to roadmaps/roadmap-payments.md) |")
                  .replace("- [ ] **SR-5**: choose the ranking provider and open the account. Gates SR-5.",
                           "- [x] **SR-5**: choose the ranking provider and open the account. Gates SR-5. "
                           "Carried to roadmaps/roadmap-payments.md.")
                  .replace("- [ ] **SR-4**: owner step:", "- [x] **SR-4**: owner step:"))
        closed += ("\n## Summary\n\n| ID | Item | What changed | Merge |\n| --- | --- | --- | --- |\n"
                   "| SR-1 | Index | indexed | 1a2b3c4 |\n| SR-2 | Titles | titles | 2b3c4d5 |\n"
                   "| SR-3 | Filters | filters | 3c4d5e6 |\n| SR-4 | Synonyms | synonyms | 4d5e6f7 |\n"
                   "| SR-5 | Paid API | carried | — |\n")
        os.remove(self.project.path("context/foundation/roadmap.md"))
        shutil.rmtree(self.project.path("context/changes/search-titles"))
        self.project.write("context/foundation/archive/2026-11-20-roadmap.md", closed)
        self.project.state("write")
        code, report = self.project.doctor()
        self.assertEqual(code, 0, report)
        state = self.state()
        self.assertIsNone(state["active_roadmap"])
        self.assertEqual(state["open_changes"], [])
        pending = [entry for entry in state["owner_queue"]
                   if entry["source"].startswith("context/foundation/archive/2026-11-20-roadmap.md")]
        self.assertEqual([entry["source"].split("#")[1] for entry in pending], ["Before the next release"],
                         "until its release is recorded, the closed roadmap's pre-release steps wait for the owner")
        # Once the release is recorded, an unticked pre-release step is history to settle, not a queue entry.
        self.project.write("context/foundation/archive/2026-11-20-roadmap.md", closed + "Release: v1.5.0 (2026-11-21)\n")
        self.project.state("write")
        self.assertFalse(any("/archive/" in entry["source"] for entry in self.state()["owner_queue"]))
        self.assertEqual(self.project.codes(), {"archived-roadmap-open-checks"})

    def test_close_with_open_checks_fails_and_queues_nothing(self) -> None:
        """An archived roadmap with unticked checks is a doctor failure and never an owner-queue entry."""
        self.project.apply_case("archived-roadmap-open-checks")
        for rel in ("context/foundation/roadmap.md", "context/foundation/roadmaps/roadmap-payments.md",
                    "context/foundation/roadmaps/README.md"):
            os.remove(self.project.path(rel))
        shutil.rmtree(self.project.path("context/changes/search-titles"))
        shutil.rmtree(self.project.path("context/backlog"))
        self.project.state("write")
        self.assertEqual(self.state()["owner_queue"], [])
        self.assertEqual(self.project.codes(), {"archived-roadmap-open-checks"})

    def test_roadmap_close_refuses_open_checks(self) -> None:
        with open(os.path.join(ROOT, "skills", "softure-roadmap", "SKILL.md"), encoding="utf-8") as fh:
            skill = fh.read()
        close = skill[skill.index("- **`--close`**"):skill.index("## Existing roadmap")]
        self.assertIn("archived-roadmap-open-checks", close)
        self.assertIn("refuses", close)

    def test_open_change_handoff_steps_are_queued_but_never_stale(self) -> None:
        rel = "context/changes/search-titles/change.md"
        self.project.write(rel, self.project.read(rel) + "\n## Roadmap handoff\n- **Status:** done\n"
                           "- **Owner step:** rotate the search api key (secret only the owner has)\n")
        self.assertEqual(self.project.codes(), set(), "a change branch writing its handoff stays green")
        self.project.state("write")
        entries = [entry for entry in self.state()["owner_queue"] if entry["source"].startswith(rel)]
        self.assertEqual([(entry["kind"], entry["item"]) for entry in entries], [("secret", "SR-2")])

    def test_git_reader_sees_the_commit_plus_overrides(self) -> None:
        reader = context_state.GitReader(self.project.root, "HEAD",
                                         {"context/foundation/roadmap.md": "---\nroadmap: other\n---\n"})
        state = context_state.build_state(reader)
        self.assertEqual(state["active_roadmap"]["slug"], "other")
        self.assertEqual(len(state["queued"]), 1)
        self.assertIsNone(context_state.staleness(context_state.GitReader(self.project.root, "HEAD")))


if __name__ == "__main__":
    unittest.main()
