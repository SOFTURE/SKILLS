"""Tests for scripts/portfolio.py (`softure-skills portfolio`).

    python3 -m unittest discover -s tests

Projects are throwaway git repositories built from tests/fixtures/doctor: one local checkout read at its
main branch, one read through a clone of a bare "remote", one without state.json. Nothing in them may
change. `SOFTURE_GH` points at a fake `gh` that knows one GitHub repository, `acme/shop`, with a release.
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
SCRIPT = os.path.join(ROOT, "scripts", "portfolio.py")
CLEAN = os.path.join(ROOT, "tests", "fixtures", "doctor", "clean", "context")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_ALLOW_PROTOCOL": "file",
}


FAKE_GH = """#!/usr/bin/env python3
import os, sys
args = " ".join(sys.argv[1:])
path = sys.argv[-1]
if path.startswith("repos/acme/") and path.count("/") == 2:
    print('{"default_branch": "main"}')
elif "/commits/main/check-runs?check_name=context-doctor" in path:
    if os.path.exists(sys.argv[0] + ".private." + path.split("/")[2]):
        sys.stderr.write("gh: Resource not accessible by personal access token (HTTP 403)\\n")
        sys.exit(1)
    stub = sys.argv[0] + ".checks." + path.split("/")[2] + ".json"
    print(open(stub).read() if os.path.exists(stub) else '{"total_count": 0, "check_runs": []}')
elif path.startswith("repos/acme/") and path.endswith("/commits/main"):
    print('{"sha": "abc123"}')
elif "/actions/runs?head_sha=abc123" in path or ("/actions/runs/" in path and "/jobs?" in path) \\
        or ("/actions/jobs/" in path and path.endswith("/logs")):
    kind = "runs" if "head_sha" in path else "jobs" if "/jobs?" in path else "log." + path.split("/")[-2]
    stub = sys.argv[0] + "." + kind + "." + path.split("/")[2]
    if not os.path.exists(stub):
        sys.stderr.write("gh: Resource not accessible by personal access token (HTTP 403)\\n")
        sys.exit(1)
    print(open(stub).read())
elif "/check-runs/" in path and path.endswith("/annotations"):
    stub = sys.argv[0] + ".annotations." + path.split("/")[2] + ".json"
    print(open(stub).read() if os.path.exists(stub) else "[]")
elif "repos/acme/shop/releases/latest" in args:
    print('{"tag_name": "v1.6.0", "published_at": "2026-11-20T08:00:00Z"}')
elif "repos/acme/shop/contents/context/state.json" in args or "repos/acme/old/contents/context/state.json" in args:
    sys.stdout.write(open(sys.argv[0] + ".state.json").read())
else:
    sys.stderr.write("gh: Not Found (HTTP 404)\\n")
    sys.exit(1)
"""


def git(cwd: str, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **GIT_ENV}, check=True,
                          capture_output=True, text=True).stdout


def snapshot(path: str) -> str:
    return git(path, "status", "--porcelain", "--ignored") + git(path, "rev-parse", "HEAD")


class PortfolioTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.gh = os.path.join(base, "gh")
        with open(self.gh, "w", encoding="utf-8") as fh:
            fh.write(FAKE_GH)
        os.chmod(self.gh, 0o755)
        shutil.copyfile(os.path.join(CLEAN, "state.json"), self.gh + ".state.json")
        self.alpha = self.make_repo(os.path.join(base, "alpha"))
        self.beta = self.make_repo(os.path.join(base, "beta"), drop_state=True, drift=True)
        self.remote = os.path.join(base, "gamma.git")
        source = self.make_repo(os.path.join(base, "gamma-src"))
        git(base, "clone", "-q", "--bare", source, self.remote)
        git(source, "tag", "v1.2.0")
        git(source, "push", "-q", self.remote, "v1.2.0")
        # A work-in-progress edit in a checkout must not be read: the main branch is.
        with open(os.path.join(self.alpha, "context", "foundation", "roadmap.md"), "a", encoding="utf-8") as fh:
            fh.write("\n| **SR-9** | `wip` | uncommitted | — | autonomous | ready |\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def make_repo(self, path: str, drop_state: bool = False, drift: bool = False) -> str:
        os.makedirs(path)
        shutil.copytree(CLEAN, os.path.join(path, "context"))
        if drop_state:
            os.remove(os.path.join(path, "context", "state.json"))
        if drift:
            change = os.path.join(path, "context", "archive", "2026-09-01-staff-day-view", "change.md")
            with open(change, encoding="utf-8") as fh:
                text = fh.read()
            with open(change, "w", encoding="utf-8") as fh:
                fh.write(text.replace("status: archived", "status: implemented"))
        git(path, "init", "-q", "-b", "main")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "init")
        return path

    def run_portfolio(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, SCRIPT, *args], env={**os.environ, **GIT_ENV, "SOFTURE_GH": self.gh},
                              capture_output=True, text=True)

    def test_table_has_one_row_per_project(self) -> None:
        before = snapshot(self.alpha)
        result = self.run_portfolio(self.alpha, self.beta, f"file://{self.remote}")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "| project | active roadmap X/N | queued | open changes | owner queue | "
                                   "last release | doctor |")
        self.assertIn("| alpha | search 2/5 | 1 | 1 | 6 | v1.4.0 (roadmap, 2026-10-02) | ok |", lines)
        self.assertIn("| beta* | search 2/5 | 1 | 1 | 6 | v1.4.0 (roadmap, 2026-10-02) | 1 failing |", lines)
        self.assertIn("| gamma | search 2/5 | 1 | 1 | 6 | v1.2.0 | ok |", lines, "a tag beats the roadmap value")
        self.assertIn("no context/state.json", result.stdout)
        self.assertEqual(snapshot(self.alpha), before)

    def test_owner_lists_every_project_oldest_first(self) -> None:
        result = self.run_portfolio(self.alpha, self.beta, "--owner", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        queue = json.loads(result.stdout)["owner_queue"]
        self.assertEqual(len(queue), 12)
        self.assertEqual({entry["project"] for entry in queue}, {"alpha", "beta"})
        self.assertEqual([entry["since"] for entry in queue], sorted(entry["since"] for entry in queue))
        text = self.run_portfolio(self.alpha, "--owner").stdout
        self.assertTrue(text.startswith("| since | project | kind | what | source | id |"))
        self.assertTrue(all(entry["id"].startswith("oq-") for entry in queue), "an owner-word issue names an entry by id")
        self.assertIn("| oq-", text)

    def test_json_and_config_file(self) -> None:
        config = os.path.join(self._tmp.name, "portfolio.json")
        with open(config, "w", encoding="utf-8") as fh:
            json.dump({"projects": [{"name": "shop", "repo": self.alpha, "branch": "main"},
                                    {"repo": os.path.join(self._tmp.name, "missing")}]}, fh)
        result = self.run_portfolio("--config", config, "--json")
        self.assertEqual(result.returncode, 1)  # the missing project is reported, the rest still printed
        projects = json.loads(result.stdout)["projects"]
        self.assertEqual(projects[0]["name"], "shop")
        self.assertEqual(projects[0]["state"]["active_roadmap"]["total"], 5)
        self.assertEqual(projects[0]["doctor"], [])
        self.assertTrue(projects[1]["error"])


    def test_last_release_comes_from_the_forge(self) -> None:
        git(self.alpha, "remote", "add", "origin", "https://github.com/acme/shop.git")
        result = self.run_portfolio(self.alpha, "--json")
        row = json.loads(result.stdout)["projects"][0]
        self.assertEqual((row["last_release"], row["last_release_date"], row["last_release_source"]),
                         ("v1.6.0", "2026-11-20", "release"))
        self.assertIn("| v1.6.0 (2026-11-20), drift: SR-4 waits for a release since 2026-11-09 |",
                      self.run_portfolio(self.alpha).stdout)

    def test_api_source_reads_the_release_and_labels_the_roadmap_value(self) -> None:
        result = self.run_portfolio("acme/shop", "acme/old", "--source", "api", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row["name"]: row for row in json.loads(result.stdout)["projects"]}
        self.assertEqual((rows["shop"]["last_release"], rows["shop"]["last_release_source"]), ("v1.6.0", "release"))
        self.assertEqual((rows["old"]["last_release"], rows["old"]["last_release_source"]), ("v1.4.0", "roadmap"))
        table = self.run_portfolio("acme/old", "--source", "api").stdout
        self.assertIn("| v1.4.0 (roadmap, 2026-10-02) | missing |", table)

    def test_api_source_flags_a_release_newer_than_rows_waiting_for_one(self) -> None:
        """The forge released after SR-4 merged, yet SR-4 still waits: `wt-roadmap.py released` did not run."""
        result = self.run_portfolio("acme/shop", "acme/old", "--source", "api", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row["name"]: row for row in json.loads(result.stdout)["projects"]}
        self.assertEqual(rows["shop"]["release_drift"],
                         {"release": "v1.6.0", "release_date": "2026-11-20", "items": ["SR-4"],
                          "waiting_since": "2026-11-09", "settle": "wt-roadmap.py released v1.6.0"})
        self.assertIsNone(rows["old"]["release_drift"])  # the release is the roadmap's own record, not the forge's
        table = self.run_portfolio("acme/shop", "--source", "api").stdout
        self.assertIn("v1.6.0 (2026-11-20), drift: SR-4 waits for a release since 2026-11-09", table)

    def test_a_release_older_than_the_waiting_rows_is_no_drift(self) -> None:
        state = json.load(open(self.gh + ".state.json", encoding="utf-8"))
        for entry in state["owner_queue"]:
            if entry["text"].startswith("release: "):
                entry["since"] = "2026-11-21"
        with open(self.gh + ".state.json", "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        result = self.run_portfolio("acme/shop", "--source", "api", "--json")
        self.assertIsNone(json.loads(result.stdout)["projects"][0]["release_drift"])

    def test_api_source_reads_the_context_doctor_check_run(self) -> None:
        def stub(name: str, *runs: dict) -> None:
            with open(f"{self.gh}.checks.{name}.json", "w", encoding="utf-8") as fh:
                json.dump({"total_count": len(runs), "check_runs": [
                    {"id": index, "name": "context-doctor", "started_at": f"2026-11-20T0{index}:00:00Z",
                     "html_url": f"https://github.com/acme/{name}/runs/{index}", **run}
                    for index, run in enumerate(runs, 1)]}, fh)
        stub("shop", {"status": "completed", "conclusion": "failure"}, {"status": "completed", "conclusion": "success"})
        stub("red", {"status": "completed", "conclusion": "failure"})
        stub("wip", {"status": "in_progress", "conclusion": None})
        with open(f"{self.gh}.annotations.red.json", "w", encoding="utf-8") as fh:
            json.dump([{"title": "context-doctor failure codes", "annotation_level": "failure",
                        "message": "archived-change-progress (3), state-stale (1)"},
                       {"title": "state-stale", "path": "context/state.json", "message": "out of date"}], fh)
        result = self.run_portfolio("acme/shop", "acme/red", "acme/wip", "acme/old", "--source", "api", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row["name"]: row for row in json.loads(result.stdout)["projects"]}
        self.assertEqual({name: row["doctor_check"] for name, row in rows.items()},
                         {"shop": "ok", "red": "failing", "wip": "pending", "old": "missing"})
        self.assertEqual(rows["shop"]["doctor_check_url"], "https://github.com/acme/shop/runs/2")
        self.assertEqual(rows["red"]["doctor_check_codes"], ["archived-change-progress", "state-stale"])
        self.assertEqual(rows["shop"]["doctor_check_codes"], [])
        lines = self.run_portfolio("acme/shop", "acme/red", "acme/old", "--source", "api").stdout.splitlines()
        self.assertIn("| shop | search 2/5 | 1 | 1 | 6 | v1.6.0 (2026-11-20), drift: SR-4 waits for a release since "
                      "2026-11-09 | ok |", lines)
        self.assertIn("| red | no state.json | — | — | — | — | failing: archived-change-progress, state-stale |", lines)
        self.assertIn("| old | search 2/5 | 1 | 1 | 6 | v1.4.0 (roadmap, 2026-10-02) | missing |", lines)

    def test_api_source_falls_back_to_the_actions_api_when_checks_are_forbidden(self) -> None:
        """A fine-grained token cannot read check runs (403); the job and its log need only Actions: read."""
        def private(name: str, jobs: list[dict] | None, log: str = "") -> None:
            open(f"{self.gh}.private.{name}", "w").close()
            if jobs is None:
                return
            with open(f"{self.gh}.runs.{name}", "w", encoding="utf-8") as fh:
                json.dump({"total_count": 1, "workflow_runs": [{"id": 7}]}, fh)
            with open(f"{self.gh}.jobs.{name}", "w", encoding="utf-8") as fh:
                json.dump({"total_count": len(jobs), "jobs": [
                    {"id": index, "name": "context-doctor", "started_at": f"2026-11-20T0{index}:00:00Z",
                     "html_url": f"https://github.com/acme/{name}/actions/runs/7/job/{index}", **job}
                    for index, job in enumerate(jobs, 1)] + [
                    {"id": 99, "name": "build", "status": "completed", "conclusion": "failure"}]}, fh)
            for index in range(1, len(jobs) + 1):
                with open(f"{self.gh}.log.{index}.{name}", "w", encoding="utf-8") as fh:
                    fh.write(log)
        log = ("2026-11-20T02:00:01.0000000Z ##[group]Run npx softure-skills doctor\n"
               "2026-11-20T02:00:05.0000000Z ##[error]archived-change-progress (3), state-stale (1)\n"
               "2026-11-20T02:00:05.0000000Z context-doctor failure codes: archived-change-progress (3), "
               "state-stale (1)\n")
        private("red", [{"status": "completed", "conclusion": "success"},
                        {"status": "completed", "conclusion": "failure"}], log)
        private("shop", [{"status": "completed", "conclusion": "success"}])
        private("wip", [{"status": "queued", "conclusion": None}])
        private("old", [])
        private("gone", None)  # Actions: read missing too: the forge cannot be asked
        result = self.run_portfolio("acme/red", "acme/shop", "acme/wip", "acme/old", "acme/gone",
                                    "--source", "api", "--json")
        rows = {row["name"]: row for row in json.loads(result.stdout)["projects"]}
        self.assertEqual({name: row["doctor_check"] for name, row in rows.items()},
                         {"red": "failing", "shop": "ok", "wip": "pending", "old": "missing", "gone": "unknown"})
        self.assertEqual(rows["red"]["doctor_check_codes"], ["archived-change-progress", "state-stale"])
        self.assertEqual(rows["red"]["doctor_check_url"], "https://github.com/acme/red/actions/runs/7/job/2")
        self.assertEqual(rows["shop"]["doctor_check_codes"], [])
        lines = self.run_portfolio("acme/red", "--source", "api").stdout.splitlines()
        self.assertIn("| red | no state.json | — | — | — | — | failing: archived-change-progress, state-stale |", lines)


if __name__ == "__main__":
    unittest.main()
