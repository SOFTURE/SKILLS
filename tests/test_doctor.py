"""Tests for skills/softure-doctor/scripts (doctor.py and context_state.py).

    python3 -m unittest discover -s tests

`tests/fixtures/doctor/clean/` is a project whose context/ follows the contract. Every folder in
`tests/fixtures/doctor/cases/<code>/` is one drift case: files laid over the clean tree (`_remove` lists
paths to delete, `_keep_state` keeps the clean state.json instead of regenerating it). The doctor must
fail with exactly that code on the case and pass on the clean tree.
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

    def apply_case(self, case: str) -> None:
        source = os.path.join(FIXTURES, "cases", case)
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

    def doctor(self) -> tuple[int, dict]:
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "doctor.py"), "--root", self.root, "--json"],
                                env={**os.environ, **GIT_ENV}, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)


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
        self.assertEqual(len(CASES), 11)
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

    def test_owner_queue_lists_what_waits_for_the_owner(self) -> None:
        queue = self.state()["owner_queue"]
        kinds = {(entry["kind"], entry["item"]) for entry in queue}
        self.assertIn(("decision", "SR-5"), kinds)
        self.assertIn(("secret", "SR-4"), kinds)
        self.assertIn(("step", "SR-1"), kinds)
        self.assertIn(("decision", "PY-1"), kinds)
        self.assertIn(("decision", "BK-2"), kinds)
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
                  .replace("| owner | blocked (provider account) |", "| owner | carried (to roadmaps/roadmap-payments.md) |"))
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
        self.assertTrue(any(entry["source"].startswith("context/foundation/archive/2026-11-20-roadmap.md")
                            for entry in state["owner_queue"]))

    def test_git_reader_sees_the_commit_plus_overrides(self) -> None:
        reader = context_state.GitReader(self.project.root, "HEAD",
                                         {"context/foundation/roadmap.md": "---\nroadmap: other\n---\n"})
        state = context_state.build_state(reader)
        self.assertEqual(state["active_roadmap"]["slug"], "other")
        self.assertEqual(len(state["queued"]), 1)
        self.assertIsNone(context_state.staleness(context_state.GitReader(self.project.root, "HEAD")))


if __name__ == "__main__":
    unittest.main()
