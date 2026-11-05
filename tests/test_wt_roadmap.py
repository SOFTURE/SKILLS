"""Tests for skills/softure-worktree/scripts/wt-roadmap.py `done` / `done_code`.

    python3 -m unittest discover -s tests

Each test builds a throwaway repository on its main branch with a roadmap, an archived change whose
`change.md` carries a `## Roadmap handoff`, and a `context/workflow.json` in manual or autonomous mode,
then runs the script locally (not as a cloud session).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "softure-worktree", "scripts", "wt-roadmap.py")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
ROADMAP = """---
updated: 2026-01-01
---
# Roadmap

| ID | Change | Outcome | Prerequisites | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **WK-8** | `search-titles` | a title search finds the page | — | autonomous | **ready_to_merge** (since 2026-01-01; cloud session) |

### WK-8: Search titles
- **Change ID:** `search-titles`
- **Status:** ready_to_merge (since 2026-01-01; cloud session)

## Owner decisions and checks

## Done
"""


def change_md(handoff: list[str]) -> str:
    return ("---\nchange_id: search-titles\ncreated: 2026-01-01\nstatus: archived\n---\n# search-titles\n\n"
            "## Notes\nArchived 2026-01-02: a title search finds the page.\n\n## Roadmap handoff\n"
            + "".join(f"{line}\n" for line in handoff))


class RoadmapDoneTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.git("init", "-q", "-b", "main")

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

    def setup_repo(self, mode: str, handoff: list[str]) -> None:
        self.write("context/workflow.json", json.dumps({"mode": mode, "mainBranch": "main"}) + "\n")
        self.write("context/foundation/roadmap.md", ROADMAP)
        self.write("context/archive/2026-01-01-search-titles/change.md", change_md(handoff))
        self.write("context/archive/2026-01-01-search-titles/plan.md", "# Plan\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "initial")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, **GIT_ENV}
        env.pop("CLAUDE_CODE_REMOTE", None)
        return subprocess.run([sys.executable, SCRIPT, *args], cwd=self.repo, env=env,
                              capture_output=True, text=True)

    def roadmap(self) -> str:
        return self.git("show", "HEAD:context/foundation/roadmap.md")

    def test_manual_mode_keeps_owner_checks(self) -> None:
        self.setup_repo("manual", ["- **Status:** done_code (waiting: owner check 2.4 on staging)",
                                   "- **Done:** a title search finds the page",
                                   "- **Owner check:** the results page reads well (Manual 2.4)"])
        result = self.run_script("done", "search-titles")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertIn("waiting: owner check 2.4 on staging", text)
        self.assertIn("- [ ] **WK-8**: the results page reads well (Manual 2.4).", text)

    def test_autonomous_refuses_owner_checks(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done_code (waiting: owner check 2.4 on staging)",
                                       "- **Owner check:** the results page reads well (Manual 2.4)"])
        result = self.run_script("done", "search-titles")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("autonomous mode", result.stderr)
        self.assertIn("Manual 2.4", result.stderr)
        self.assertIn("ready_to_merge", self.roadmap())

    def test_autonomous_verified_closes_without_owner_check(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done_code (waiting: owner check 2.4 on staging)",
                                       "- **Done:** a title search finds the page",
                                       "- **Owner check:** the results page reads well (Manual 2.4)"])
        result = self.run_script("done", "search-titles", "--verified", "screenshot 1280px checked, run 42 green")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertNotIn("owner check", text.lower())
        self.assertIn("| autonomous | done |", text)
        self.assertIn("- **Status:** done\n", text)
        self.assertIn("verified: screenshot 1280px checked, run 42 green", text)

    def test_autonomous_verified_keeps_release_wait(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done_code (waiting: release; owner check 2.4)",
                                       "- **Owner check:** the results page reads well (Manual 2.4)"])
        result = self.run_script("done", "search-titles", "--verified", "health check 200")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertRegex(text, r"done_code \(\d{4}-\d{2}-\d{2}; waiting: release\)")
        self.assertNotIn("owner check", text.lower())

    def test_autonomous_owner_step_is_tracked(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done_code (waiting: owner step: set STRIPE_KEY)",
                                       "- **Owner step:** set STRIPE_KEY in production (secret only the owner has)"])
        result = self.run_script("done", "search-titles")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertIn("- [ ] **WK-8**: owner step: set STRIPE_KEY in production (secret only the owner has).", text)
        self.assertIn("waiting: owner step: set STRIPE_KEY", text)

    def test_autonomous_done_code_refuses_owner_check_text(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done"])
        result = self.run_script("done_code", "search-titles", "--waiting", "owner check of the copy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("autonomous mode", result.stderr)

    def test_autonomous_clean_handoff_is_done(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done", "- **Done:** a title search finds the page"])
        result = self.run_script("done", "search-titles")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertIn("| autonomous | done |", text)
        self.assertIn("- **WK-8** `search-titles`: a title search finds the page; archived in", text)

    def test_verified_closes_a_done_code_row_and_its_old_checks(self) -> None:
        self.setup_repo("manual", ["- **Status:** done_code (waiting: owner check 2.4 on staging)",
                                   "- **Done:** a title search finds the page",
                                   "- **Owner check:** the results page reads well (Manual 2.4)"])
        self.assertEqual(self.run_script("done", "search-titles").returncode, 0)
        self.git("checkout", "-q", "--", ".")
        self.write("context/workflow.json", json.dumps({"mode": "autonomous", "mainBranch": "main"}) + "\n")
        self.git("commit", "-q", "-am", "switch to autonomous")
        result = self.run_script("done", "search-titles", "--verified", "health 200, deploy run 7 green")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertIn("| autonomous | done |", text)
        self.assertIn("- [x] **WK-8**: the results page reads well (Manual 2.4).", text)
        self.assertIn("— verified: health 200, deploy run 7 green", text)
        self.assertEqual(text.count("- **WK-8** `search-titles`:"), 1)
        self.assertIn("a title search finds the page; verified: health 200, deploy run 7 green", text)

    def test_verified_after_release_closes_the_row(self) -> None:
        self.setup_repo("autonomous", ["- **Status:** done_code (waiting: release)",
                                       "- **Done:** a title search finds the page"])
        self.assertEqual(self.run_script("done", "search-titles").returncode, 0)
        self.assertRegex(self.roadmap(), r"waiting: release\)")
        result = self.run_script("done", "search-titles", "--verified", "v1.2.0 deployed, health 200")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.roadmap()
        self.assertIn("| autonomous | done |", text)
        self.assertIn("- **Status:** done\n", text)


if __name__ == "__main__":
    unittest.main()
