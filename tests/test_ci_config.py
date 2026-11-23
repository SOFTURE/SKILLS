"""Tests for the `context-doctor` trigger check (skills/softure-doctor/scripts/ci_config.py), as the doctor reports
it (`ci-doctor-trigger`) and as the installer prints it.

    python3 -m unittest discover -s tests

The job must run on every push to the main branch, so the main branch's head carries a `context-doctor` check run
(WORKFLOW.md §12.2): a workflow with the job on `pull_request` only, with a `push` trigger that leaves the main
branch out, with a paths filter, or with an `if:` on the job is reported; a workflow without the job is not.
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
CLEAN = os.path.join(ROOT, "tests", "fixtures", "doctor", "clean")
INSTALL = os.path.join(ROOT, "scripts", "install.mjs")
sys.dont_write_bytecode = True
sys.path.insert(0, SCRIPTS)
import ci_config  # noqa: E402

JOB = """
jobs:
  context-doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Doctor
        run: |
          echo "on: push"
          npx --yes --package @softure-ai/skills@0.31.0 softure-skills doctor
        env:
          npm_config_ignore_scripts: "true"
"""

GOOD = "name: ci\non:\n  pull_request:\n  push:\n    branches: [main]\n" + JOB


def workflow(on: str, job: str = JOB) -> str:
    return f"name: ci\n{on}\n{job}"


class ProblemsTest(unittest.TestCase):
    def problems(self, text: str, branches=("main",)):
        return ci_config.problems(text, tuple(branches))

    def test_full_trigger_passes(self) -> None:
        self.assertEqual(self.problems(GOOD), [])

    def test_other_trigger_shapes_that_cover_the_main_branch_pass(self) -> None:
        for on in ("on: [push, pull_request]", "on: push", "on:\n  push:\n  pull_request:",
                   "on:\n  push:\n    branches:\n      - main\n      - 'release/**'\n  pull_request:\n    branches: [main]",
                   "on:\n  push:\n    branches-ignore: [gh-pages]", "on:\n  push:\n    branches: ['**']",
                   "'on':\n  push:\n    branches: [\"main\"]"):
            with self.subTest(on=on):
                self.assertEqual(self.problems(workflow(on)), [])

    def test_pull_request_only_is_reported(self) -> None:
        found = self.problems(workflow("on:\n  pull_request:\n    branches: [main]"))
        self.assertEqual(len(found), 1, found)
        self.assertIn("no `push` trigger", found[0])
        self.assertEqual(len(self.problems(workflow("on: pull_request"))), 1)
        self.assertEqual(len(self.problems(workflow("on: [pull_request, workflow_dispatch]"))), 1)

    def test_push_that_leaves_the_main_branch_out_is_reported(self) -> None:
        for on in ("on:\n  push:\n    branches: [develop]\n  pull_request:",
                   "on:\n  push:\n    branches-ignore: [main]\n  pull_request:",
                   "on:\n  push:\n    tags: ['v*']\n  pull_request:",
                   "on:\n  push:\n    branches: ['**', '!main']\n  pull_request:"):
            with self.subTest(on=on):
                found = self.problems(workflow(on))
                self.assertEqual(len(found), 1, found)
                self.assertIn("leaves out `main`", found[0])

    def test_main_branch_comes_from_the_project(self) -> None:
        on = "on:\n  push:\n    branches: [master]\n  pull_request:"
        self.assertEqual(len(self.problems(workflow(on), ("main",))), 1)
        self.assertEqual(self.problems(workflow(on), ("master",)), [])
        self.assertEqual(self.problems(workflow(on), ci_config.DEFAULT_MAIN_BRANCHES), [])

    def test_paths_filter_is_reported(self) -> None:
        for event, key in (("push", "paths"), ("push", "paths-ignore"), ("pull_request", "paths"),
                           ("pull_request", "paths-ignore")):
            with self.subTest(event=event, key=key):
                on = {"push": "  push:\n    branches: [main]\n", "pull_request": "  pull_request:\n"}
                on[event] += f"    {key}:\n      - 'src/**'\n"
                found = self.problems(workflow("on:\n" + on["push"] + on["pull_request"]))
                self.assertEqual(found, [f"a `{key}` filter on `{event}`"])

    def test_if_on_the_job_is_reported(self) -> None:
        job = JOB.replace("    runs-on:", "    if: github.event_name == 'pull_request'\n    runs-on:")
        self.assertEqual(self.problems(workflow("on:\n  pull_request:\n  push:\n    branches: [main]", job)),
                         ["an `if:` on the job `context-doctor`"])

    def test_job_found_by_its_name(self) -> None:
        job = JOB.replace("  context-doctor:", "  doctor:\n    name: context-doctor")
        self.assertEqual(len(self.problems(workflow("on: pull_request", job))), 1)

    def test_workflow_without_the_job_is_not_this_check(self) -> None:
        job = JOB.replace("  context-doctor:", "  build:")
        self.assertIsNone(self.problems(workflow("on: pull_request", job)))

    def test_every_problem_at_once(self) -> None:
        job = JOB.replace("    runs-on:", "    if: ${{ !github.event.pull_request.draft }}\n    runs-on:")
        found = self.problems(workflow("on:\n  pull_request:\n    paths: ['context/**']", job))
        self.assertEqual(len(found), 3, found)


class Tree:
    """A copy of the clean doctor fixture (context/ only, no git) with workflows laid over it."""

    def __init__(self, workflows: dict[str, str], main_branch: str | None = "main") -> None:
        self.root = tempfile.mkdtemp(prefix="ci-config-")
        shutil.copytree(os.path.join(CLEAN, "context"), os.path.join(self.root, "context"))
        config_path = os.path.join(self.root, "context", "workflow.json")
        with open(config_path, encoding="utf-8") as fh:
            config = json.load(fh)
        if main_branch is None:
            config.pop("mainBranch", None)
        else:
            config["mainBranch"] = main_branch
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh)
        for name, text in workflows.items():
            target = os.path.join(self.root, ".github", "workflows", name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text)

    def doctor(self) -> tuple[int, dict]:
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "doctor.py"), "--root", self.root, "--json"],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def install(self) -> str:
        result = subprocess.run(["node", INSTALL, "--target", self.root, "--dry-run"], capture_output=True,
                                text=True, env={**os.environ, "CI": "true"})
        return result.stdout + result.stderr

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class DoctorTest(unittest.TestCase):
    def run_doctor(self, workflows: dict[str, str], main_branch: str | None = "main") -> tuple[int, dict]:
        tree = Tree(workflows, main_branch)
        try:
            return tree.doctor()
        finally:
            tree.cleanup()

    def test_pull_request_only_fails_with_the_fix(self) -> None:
        code, report = self.run_doctor({"ci.yml": workflow("on: pull_request")})
        self.assertEqual(code, 1, report)
        failures = report["failures"]
        self.assertEqual([(f["code"], f["path"]) for f in failures], [("ci-doctor-trigger", ".github/workflows/ci.yml")])
        self.assertIn("no `push` trigger", failures[0]["message"])
        self.assertIn("`push` to `main`", failures[0]["message"])

    def test_paths_filter_and_if_fail(self) -> None:
        job = JOB.replace("    runs-on:", "    if: github.actor != 'dependabot[bot]'\n    runs-on:")
        code, report = self.run_doctor({"ci.yaml": workflow(
            "on:\n  pull_request:\n  push:\n    branches: [main]\n    paths-ignore: ['**.md']", job)})
        self.assertEqual(code, 1, report)
        message = report["failures"][0]["message"]
        self.assertIn("a `paths-ignore` filter on `push`", message)
        self.assertIn("an `if:` on the job `context-doctor`", message)

    def test_full_trigger_and_missing_job_pass(self) -> None:
        self.assertEqual(self.run_doctor({"ci.yml": GOOD})[0], 0)
        self.assertEqual(self.run_doctor({"build.yml": workflow("on: pull_request", JOB.replace("context-doctor", "build"))})[0], 0)
        self.assertEqual(self.run_doctor({})[0], 0)

    def test_main_branch_falls_back_to_main_or_master(self) -> None:
        on = "on:\n  pull_request:\n  push:\n    branches: [master]"
        codes = lambda report: {f["code"] for f in report["failures"]}  # noqa: E731
        self.assertNotIn("ci-doctor-trigger", codes(self.run_doctor({"ci.yml": workflow(on)}, main_branch=None)[1]))
        self.assertIn("ci-doctor-trigger", codes(self.run_doctor({"ci.yml": workflow(on)}, main_branch="main")[1]))

    def test_never_baselined(self) -> None:
        tree = Tree({"ci.yml": workflow("on: pull_request")})
        try:
            with open(os.path.join(tree.root, "context", "doctor-baseline.json"), "w", encoding="utf-8") as fh:
                json.dump({"note": "", "created": "2026-11-23", "entries": [
                    {"code": "ci-doctor-trigger", "path": ".github/workflows/ci.yml", "message": ""}]}, fh)
            code, report = tree.doctor()
            self.assertEqual(code, 1, report)
            self.assertIn("ci-doctor-trigger", {f["code"] for f in report["failures"]})
        finally:
            tree.cleanup()


@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class InstallerTest(unittest.TestCase):
    def install(self, workflows: dict[str, str], main_branch: str | None = "main") -> str:
        tree = Tree(workflows, main_branch)
        try:
            return tree.install()
        finally:
            tree.cleanup()

    def test_pull_request_only_prints_the_trigger(self) -> None:
        out = self.install({"ci.yml": workflow("on: pull_request")})
        self.assertIn("CI: the `context-doctor` job in .github/workflows/ci.yml does not run on every push to main", out)
        self.assertIn("no `push` trigger", out)
        self.assertIn("on:\n  pull_request:\n  push:\n    branches: [main]", out)

    def test_paths_filter_and_if_are_printed(self) -> None:
        job = JOB.replace("    runs-on:", "    if: github.event_name == 'push'\n    runs-on:")
        out = self.install({"ci.yml": workflow(
            "on:\n  pull_request:\n    paths: ['src/**']\n  push:\n    branches: [develop]", job)}, "develop")
        self.assertIn("a `paths` filter on `pull_request`", out)
        self.assertIn("an `if:` on the job `context-doctor`", out)
        self.assertIn("    branches: [develop]", out)

    def test_full_trigger_prints_no_ci_notice(self) -> None:
        self.assertNotIn("CI:", self.install({"ci.yml": GOOD}))

    def test_missing_job_prints_a_whole_workflow_with_its_trigger(self) -> None:
        out = self.install({}, "trunk")
        self.assertIn("on:\n  pull_request:\n  push:\n    branches: [trunk]\n\njobs:\n  context-doctor:", out)


if __name__ == "__main__":
    unittest.main()
