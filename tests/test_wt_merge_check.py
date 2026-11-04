"""Tests for skills/softure-worktree/scripts/wt-merge-check.py.

    python3 -m unittest discover -s tests

Each test builds a throwaway repository: a main branch, a change branch, and new commits on main,
then runs the script on the change branch with `--base main --no-fetch`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "softure-worktree", "scripts", "wt-merge-check.py")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


class MergeCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.git("init", "-q", "-b", "main")
        self.write("app.txt", "one\ntwo\nthree\nfour\nfive\nsix\nseven\n")
        self.write("package.json", '{"dependencies": {"left-pad": "1.0.0"}}\n')
        self.commit("initial")
        self.git("checkout", "-q", "-b", "change")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        env = {**os.environ, **GIT_ENV}
        return subprocess.run(["git", *args], cwd=self.repo, env=env, check=True,
                              capture_output=True, text=True).stdout

    def write(self, path: str, content: str) -> None:
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def on_main(self, path: str, content: str) -> None:
        self.git("checkout", "-q", "main")
        self.write(path, content)
        self.commit(f"main: {path}")
        self.git("checkout", "-q", "change")

    def configure(self, policy: str | None) -> None:
        # The config is read from the main worktree's working tree; keep it out of the commits.
        config = {"mainBranch": "main", "gates": {"test": "npm test", "lint": "npm run lint"}}
        if policy:
            config["autonomy"] = {"remergeMain": policy}
        self.write("context/workflow.json", json.dumps(config))
        self.write(".git/info/exclude", "context/\n")

    def run_check(self, policy: str | None, *extra: str) -> subprocess.CompletedProcess:
        self.configure(policy)
        env = {**os.environ, **GIT_ENV}
        return subprocess.run([sys.executable, SCRIPT, "--base", "main", "--no-fetch", *extra],
                              cwd=self.repo, env=env, capture_output=True, text=True)

    def verdict(self, policy: str | None, *extra: str) -> tuple[str, str]:
        result = self.run_check(policy, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = dict(line.split(None, 1) for line in result.stdout.splitlines() if line.startswith(("VERDICT", "GATES")))
        return lines["VERDICT"].strip(), result.stdout

    # --- on-conflict -------------------------------------------------------------------------------

    def test_on_conflict_dependency_change_without_conflict_merges_as_is(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        self.on_main("package.json", '{"dependencies": {"left-pad": "1.0.1"}}\n')
        verdict, out = self.verdict("on-conflict")
        self.assertEqual(verdict, "merge-as-is", out)
        self.assertIn("GATES    none", out)
        self.assertIn("conflict: none", out)
        self.assertIn("dependencies: package.json", out)

    def test_on_conflict_overlap_without_conflict_merges_as_is(self) -> None:
        self.write("app.txt", "ONE\ntwo\nthree\nfour\nfive\nsix\nseven\n")
        self.commit("change: first line")
        self.on_main("app.txt", "one\ntwo\nthree\nfour\nfive\nsix\nSEVEN\n")
        verdict, out = self.verdict("on-conflict")
        self.assertEqual(verdict, "merge-as-is", out)
        self.assertIn("overlap: app.txt", out)

    def test_on_conflict_textual_conflict_remerges(self) -> None:
        self.write("app.txt", "one\nTWO-branch\nthree\nfour\nfive\nsix\nseven\n")
        self.commit("change: second line")
        self.on_main("app.txt", "one\nTWO-main\nthree\nfour\nfive\nsix\nseven\n")
        verdict, out = self.verdict("on-conflict")
        self.assertEqual(verdict, "remerge", out)
        self.assertIn("conflict: yes", out)
        self.assertIn("app.txt", out)
        self.assertIn("RUN      npm test", out)

    def test_on_conflict_forge_not_mergeable_remerges(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        self.on_main("other.txt", "other\n")
        verdict, out = self.verdict("on-conflict", "--not-mergeable")
        self.assertEqual(verdict, "remerge", out)

    def test_on_conflict_conflict_with_dependency_change_runs_full_gates(self) -> None:
        self.write("package.json", '{"dependencies": {"left-pad": "2.0.0"}}\n')
        self.commit("change: bump")
        self.on_main("package.json", '{"dependencies": {"left-pad": "1.0.1"}}\n')
        verdict, out = self.verdict("on-conflict")
        self.assertEqual(verdict, "remerge", out)
        self.assertIn("GATES    full", out)

    # --- existing policies keep their meaning ------------------------------------------------------

    def test_when_needed_dependency_change_remerges(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        self.on_main("package.json", '{"dependencies": {"left-pad": "1.0.1"}}\n')
        self.assertEqual(self.verdict("when-needed")[0], "remerge")
        self.assertEqual(self.verdict(None)[0], "remerge")  # the default

    def test_when_needed_unrelated_change_merges_as_is(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        self.on_main("other.txt", "other\n")
        self.assertEqual(self.verdict("when-needed")[0], "merge-as-is")

    def test_always_remerges_when_main_moved(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        self.on_main("other.txt", "other\n")
        self.assertEqual(self.verdict("always")[0], "remerge")

    def test_main_not_moved_merges_as_is(self) -> None:
        self.write("feature.txt", "new\n")
        self.commit("change: feature")
        for policy in ("when-needed", "on-conflict", "always"):
            self.assertEqual(self.verdict(policy)[0], "merge-as-is", policy)

    def test_unknown_policy_fails(self) -> None:
        result = self.run_check("sometimes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("remergeMain", result.stderr)


if __name__ == "__main__":
    unittest.main()
