"""Tests for the main branch's CI after a merge (issue: autonomous runs never looked at it) and for the required-checks
check that keeps a red pull request from merging.

    python3 -m unittest discover -s tests

- `wt-main-ci.py` (skills/softure-worktree/scripts) reads the push-triggered runs on one commit and prints a verdict:
  a run that passed only on a re-run is `flaky`, a failure is `red`, cancelled-only runs are `superseded`.
- `ci_config.py --protection` / `doctor --protection` (skills/softure-doctor/scripts) asks the forge whether every
  pull-request job is a required check on the main branch and nobody bypasses them.
- The managed block, the heartbeat routine and WORKFLOW.md tell threads and the coordinator to act on both.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCTOR_SCRIPTS = os.path.join(ROOT, "skills", "softure-doctor", "scripts")
WT_SCRIPTS = os.path.join(ROOT, "skills", "softure-worktree", "scripts")
sys.dont_write_bytecode = True
sys.path.insert(0, DOCTOR_SCRIPTS)
sys.path.insert(0, WT_SCRIPTS)
import ci_config  # noqa: E402

_spec = importlib.util.spec_from_file_location("wt_main_ci", os.path.join(WT_SCRIPTS, "wt-main-ci.py"))
main_ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(main_ci)

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
answers = json.load(open(os.environ["FAKE_GH_ANSWERS"]))
path = sys.argv[2]
if path not in answers:
    sys.exit(1)
print(json.dumps(answers[path]))
"""


def run(run_id: int, conclusion: str | None, status: str = "completed", attempt: int = 1, name: str = "ci") -> dict:
    return {"id": run_id, "name": name, "workflow_id": name, "run_number": run_id, "status": status,
            "conclusion": conclusion, "run_attempt": attempt, "html_url": f"https://github.com/acme/shop/runs/{run_id}"}


class VerdictTest(unittest.TestCase):
    def read(self, runs: list[dict], attempts: dict | None = None) -> dict:
        answers = {"repos/{owner}/{repo}/actions/runs?head_sha=abc1234&event=push&per_page=100":
                   {"workflow_runs": runs}, **(attempts or {})}
        return main_ci.read("abc1234", api=answers.get)

    def test_green(self) -> None:
        self.assertEqual(self.read([run(1, "success"), run(2, "skipped", name="deploy")])["verdict"], "green")

    def test_a_failed_run_is_red(self) -> None:
        self.assertEqual(self.read([run(1, "success"), run(2, "failure", name="e2e")])["verdict"], "red")
        self.assertEqual(self.read([run(1, "timed_out")])["verdict"], "red")

    def test_a_run_that_passed_only_on_a_rerun_is_flaky(self) -> None:
        result = self.read([run(1, "success", attempt=2)],
                           {"repos/{owner}/{repo}/actions/runs/1/attempts/1": {"conclusion": "failure"}})
        self.assertEqual(result["verdict"], "flaky")
        self.assertTrue(result["runs"][0]["failed_before"])

    def test_a_rerun_after_a_cancelled_attempt_stays_green(self) -> None:
        result = self.read([run(1, "success", attempt=2)],
                           {"repos/{owner}/{repo}/actions/runs/1/attempts/1": {"conclusion": "cancelled"}})
        self.assertEqual(result["verdict"], "green")

    def test_running_none_and_superseded(self) -> None:
        self.assertEqual(self.read([run(1, None, status="in_progress")])["verdict"], "running")
        self.assertEqual(self.read([])["verdict"], "none")
        self.assertEqual(self.read([run(1, "cancelled")])["verdict"], "superseded")
        self.assertEqual(self.read([run(1, "cancelled"), run(2, "success", name="lint")])["verdict"], "green")

    def test_the_forge_out_of_reach_is_no_answer(self) -> None:
        self.assertIsNone(main_ci.read("abc1234", api=lambda path: None))


class MainCiCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.gh = os.path.join(self._tmp.name, "gh")
        with open(self.gh, "w", encoding="utf-8") as fh:
            fh.write(FAKE_GH)
        os.chmod(self.gh, 0o755)
        self.answers = os.path.join(self._tmp.name, "answers.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, runs: list[dict]) -> subprocess.CompletedProcess:
        with open(self.answers, "w", encoding="utf-8") as fh:
            json.dump({"repos/{owner}/{repo}/actions/runs?head_sha=abc1234&event=push&per_page=100":
                       {"workflow_runs": runs}}, fh)
        return subprocess.run([sys.executable, os.path.join(WT_SCRIPTS, "wt-main-ci.py"), "abc1234"],
                              env={**os.environ, "SOFTURE_GH": self.gh, "FAKE_GH_ANSWERS": self.answers},
                              cwd=self._tmp.name, capture_output=True, text=True)

    def test_exit_codes_follow_the_verdict(self) -> None:
        green = self.cli([run(1, "success")])
        self.assertEqual(green.returncode, 0, green.stderr)
        self.assertIn("MAIN-CI  green  abc1234", green.stdout)
        red = self.cli([run(1, "failure")])
        self.assertEqual(red.returncode, 1)
        self.assertIn("https://github.com/acme/shop/runs/1", red.stdout)
        self.assertEqual(self.cli([run(1, None, status="queued")]).returncode, 75)

    def test_no_forge_exits_2(self) -> None:
        out = subprocess.run([sys.executable, os.path.join(WT_SCRIPTS, "wt-main-ci.py"), "abc1234"],
                             env={**os.environ, "SOFTURE_GH": os.path.join(os.sep, "nonexistent", "gh")},
                             cwd=self._tmp.name, capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)


CI = """name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [{run: npm test}]
  e2e:
    name: End-to-end
    strategy:
      matrix:
        browser: [chromium, webkit]
    runs-on: ubuntu-latest
    steps: [{run: npm run e2e}]
  build:
    name: Build ${{ matrix.os }}
    runs-on: ubuntu-latest
    steps: [{run: npm run build}]
"""
DEPLOY = "name: deploy\non:\n  push:\n    branches: [main]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
REPO = {"full_name": "acme/shop", "default_branch": "main", "permissions": {"admin": True}}


class Reader:
    def __init__(self, files: dict) -> None:
        self.files = files

    def listdir(self, path: str):
        return [(name.rsplit("/", 1)[1], False) for name in self.files if name.startswith(path + "/")]

    def read(self, path: str):
        return self.files.get(path)


class ProtectionTest(unittest.TestCase):
    READER = Reader({".github/workflows/ci.yml": CI, ".github/workflows/deploy.yml": DEPLOY})

    def report(self, answers: dict, branch: str | None = "main") -> tuple[int, dict]:
        return ci_config.protection_report(self.READER, answers.get, branch)

    def test_pull_request_jobs_are_the_checks_to_require(self) -> None:
        self.assertEqual(ci_config.ci_jobs(self.READER), ["test", "End-to-end"],
                         "a push-only workflow and an expression name are left out")

    def test_no_protection_is_a_failure(self) -> None:
        code, report = self.report({"repos/{owner}/{repo}": REPO})
        self.assertEqual(code, 1)
        self.assertIn("requires no status checks", report["problems"][0])

    def test_a_missing_job_and_an_admin_bypass_are_named(self) -> None:
        code, report = self.report({"repos/{owner}/{repo}": REPO, "repos/{owner}/{repo}/branches/main/protection": {
            "required_status_checks": {"contexts": ["test"]}, "enforce_admins": {"enabled": False}}})
        self.assertEqual(code, 1)
        self.assertIn("`End-to-end`", report["problems"][0])
        self.assertIn("bypass", report["problems"][1])

    def test_every_job_required_with_admins_included_passes(self) -> None:
        code, report = self.report({"repos/{owner}/{repo}": REPO, "repos/{owner}/{repo}/branches/main/protection": {
            "required_status_checks": {"checks": [{"context": "test"}, {"context": "End-to-end (chromium)"},
                                                  {"context": "End-to-end (webkit)"}]},
            "enforce_admins": {"enabled": True}}})
        self.assertEqual((code, report["problems"]), (0, []))

    def test_a_ruleset_counts_and_its_bypass_list_is_read(self) -> None:
        rules = [{"type": "required_status_checks", "ruleset_id": 7, "parameters": {
            "required_status_checks": [{"context": "test"}, {"context": "End-to-end"}]}}]
        reader_only = {**REPO, "permissions": {"admin": False}}
        answers = {"repos/{owner}/{repo}": reader_only, "repos/{owner}/{repo}/rules/branches/main": rules,
                   "repos/{owner}/{repo}/rulesets/7": {"bypass_actors": []}}
        self.assertEqual(self.report(answers)[0], 0)
        answers["repos/{owner}/{repo}/rulesets/7"] = {"bypass_actors": [{"actor_type": "RepositoryRole"}]}
        self.assertEqual(self.report(answers)[0], 1)

    def test_unknown_when_the_token_cannot_read_protection(self) -> None:
        code, report = self.report({"repos/{owner}/{repo}": {**REPO, "permissions": {"admin": False}}})
        self.assertEqual(code, 75)
        self.assertIn("admin", report["unknown"])
        self.assertEqual(self.report({})[0], 75)

    def test_the_default_branch_comes_from_the_forge(self) -> None:
        code, report = self.report({"repos/{owner}/{repo}": {**REPO, "default_branch": "master"}}, branch=None)
        self.assertEqual(report["branch"], "master")

    def test_a_missing_cockpit_label_is_named_when_the_routine_is_declared(self) -> None:
        workflow = json.dumps({"autonomy": {"cockpitWake": "routine"}})
        reader = Reader({**self.READER.files, "context/workflow.json": workflow})
        protected = {"repos/{owner}/{repo}": REPO, "repos/{owner}/{repo}/branches/main/protection": {
            "required_status_checks": {"contexts": ["test", "End-to-end"]}, "enforce_admins": {"enabled": True}}}
        code, report = ci_config.protection_report(reader, protected.get, "main")
        self.assertEqual(code, 1)
        self.assertEqual(len(report["label_problems"]), 1)
        self.assertIn("`cockpit` does not exist", report["label_problems"][0])
        protected["repos/{owner}/{repo}/labels/cockpit"] = {"name": "cockpit"}
        self.assertEqual(ci_config.protection_report(reader, protected.get, "main")[0], 0)

    def test_doctor_protection_runs_without_a_context_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gh = os.path.join(tmp, "gh")
            with open(gh, "w", encoding="utf-8") as fh:
                fh.write(FAKE_GH)
            os.chmod(gh, 0o755)
            answers = os.path.join(tmp, "answers.json")
            with open(answers, "w", encoding="utf-8") as fh:
                json.dump({"repos/{owner}/{repo}": REPO}, fh)
            os.makedirs(os.path.join(tmp, ".github", "workflows"))
            with open(os.path.join(tmp, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as fh:
                fh.write(CI)
            out = subprocess.run([sys.executable, os.path.join(DOCTOR_SCRIPTS, "doctor.py"), "--root", tmp,
                                  "--protection"], env={**os.environ, "SOFTURE_GH": gh, "FAKE_GH_ANSWERS": answers},
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertIn("FAIL main-checks-not-required main:", out.stdout)


class InstructionsTest(unittest.TestCase):
    def read(self, *path: str) -> str:
        with open(os.path.join(ROOT, *path), encoding="utf-8") as fh:
            return fh.read()

    def test_threads_read_the_main_branch_ci_after_their_merge(self) -> None:
        rules = self.read("rules", "AGENTS.md")
        self.assertIn("wt-main-ci.py <merge SHA>", rules)
        self.assertIn("is a bug, never a timing failure", rules)
        self.assertIn("doctor --protection", rules)
        self.assertNotIn("The main branch is already tested", rules)
        self.assertIn("wt-main-ci.py", self.read("skills", "softure-worktree", "SKILL.md"))

    def test_the_heartbeat_reports_the_main_branch_ci(self) -> None:
        heartbeat = self.read("routines", "roadmap-heartbeat.md")
        self.assertIn("wt-main-ci.py", heartbeat)
        self.assertIn("main CI: <green|red|flaky|running|none|superseded>", heartbeat)
        self.assertIn("fix thread", heartbeat)


if __name__ == "__main__":
    unittest.main()
