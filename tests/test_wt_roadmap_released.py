"""Tests for `wt-roadmap.py released <tag>`: settle the context after a release and its deploy.

    python3 -m unittest discover -s tests

Each test builds a throwaway repository on its main branch: a roadmap whose rows wait for a release, the archived
changes behind them, and a tag that carries some of them. The script runs locally (not as a cloud session).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "softure-worktree", "scripts", "wt-roadmap.py")
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "skills", "softure-doctor", "scripts"))
import context_state  # noqa: E402
import doctor  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def roadmap(rows: list[tuple[str, str, str]], owner: list[str], release: list[str], archive_order: str = "at the end",
            done: list[str] | None = None) -> str:
    table = "".join(f"| **{rid}** | `{cid}` | {cid} works | — | autonomous | {status} |\n" for rid, cid, status in rows)
    blocks = "".join(f"### {rid}: {cid.title()}\n- **Change ID:** `{cid}`\n- **Status:** {status.replace('**', '')}\n\n"
                     for rid, cid, status in rows)
    return ("---\nproject: \"Shop\"\nroadmap: search\nversion: 1\nstatus: ready\nupdated: 2026-01-01\n---\n\n"
            "# Roadmap search: visitors find things\n\n"
            f"> - Archive roadmap: {archive_order}\n> - Release: at the end\n\n"
            "## At a glance\n\n| ID | Change | Outcome | Depends on | Mode | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + table + "\n## Items\n\n" + blocks
            + "## Before the next release\n" + "".join(f"{line}\n" for line in release)
            + "\n## Owner decisions and checks\n" + "".join(f"{line}\n" for line in owner)
            + "\n## Done\n" + "".join(f"{line}\n" for line in (done or [])))


class ReleasedTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self.git("init", "-q", "-b", "main")
        self.write("context/workflow.json", json.dumps({"mode": "autonomous", "mainBranch": "main"}) + "\n")
        self.write("context/changes/README.md", "# Changes\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, env={**os.environ, **GIT_ENV}, check=True,
                              capture_output=True, text=True).stdout

    def write(self, path: str, content: str) -> None:
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)

    def archive(self, change_id: str, date: str = "2026-01-02") -> None:
        self.write(f"context/archive/{date}-{change_id}/change.md",
                   f"---\nchange_id: {change_id}\nstatus: archived\n---\n# {change_id}\n\n## Notes\n"
                   f"Archived {date}: {change_id} works.\n")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, **GIT_ENV}
        env.pop("CLAUDE_CODE_REMOTE", None)
        return subprocess.run([sys.executable, SCRIPT, *args], cwd=self.repo, env=env, capture_output=True, text=True)

    def show(self, path: str) -> str:
        return self.git("show", f"HEAD:{path}")

    def state(self) -> dict:
        return json.loads(self.show("context/state.json"))

    def test_released_settles_the_rows_and_entries_the_tag_carries(self) -> None:
        self.write("context/foundation/roadmap.md", roadmap(
            [("WK-8", "search-titles", "done_code (2026-01-02; waiting: release)"),
             ("WK-9", "search-filters", "done_code (2026-01-03; waiting: release)"),
             ("WK-7", "search-index", "done_code (2026-01-02; waiting: release; owner step: set INDEX_KEY)")],
            owner=["- [ ] **WK-8**: run the release once the copy is final",
                   "- [ ] **WK-9**: deploy after the filters are reviewed",
                   "- [ ] **WK-5**: pick the ranking provider. Gates WK-5."],
            release=["- [ ] Set `SEARCH_URL` in production (**WK-8**)",
                     "- [ ] Rebuild the filter index (**WK-9**)"],
            done=["- **WK-8** `search-titles`: titles are found; archived in `archive/2026-01-02-search-titles/`"]))
        self.archive("search-titles")
        self.archive("search-index")
        self.commit("WK-8 and WK-7 merged")
        self.git("tag", "-a", "v1.2.0", "-m", "v1.2.0")
        self.archive("search-filters", "2026-01-03")
        self.commit("WK-9 merged after the release")

        result = self.run_script("released", "v1.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.show("context/foundation/roadmap.md")
        self.assertIn("| autonomous | done |", text.split("**WK-8**", 1)[1].splitlines()[0])
        self.assertRegex(text, r"\| \*\*WK-9\*\* .*\| done_code \(2026-01-03; waiting: release\) \|")
        self.assertRegex(text, r"\| \*\*WK-7\*\* .*\| done_code \(2026-01-02; waiting: owner step: set INDEX_KEY\) \|")
        self.assertIn("- **Change ID:** `search-titles`\n- **Status:** done\n", text)
        self.assertIn("titles are found; released: v1.2.0; archived in", text)
        self.assertIn("- [x] **WK-8**: run the release once the copy is final — done: v1.2.0", text)
        self.assertIn("- [x] Set `SEARCH_URL` in production (**WK-8**) — done: v1.2.0", text)
        self.assertIn("- [ ] **WK-9**: deploy after the filters are reviewed", text)
        self.assertIn("- [ ] Rebuild the filter index (**WK-9**)", text)
        self.assertIn("- [ ] **WK-5**: pick the ranking provider.", text)
        self.assertTrue(os.path.exists(os.path.join(self.repo, "context/foundation/roadmap.md")))  # WK-9 is open

        files = sorted(self.git("show", "--name-only", "--format=", "HEAD").split())
        self.assertEqual(files, ["context/foundation/roadmap.md", "context/state.json"])
        self.assertIsNone(context_state.staleness(context_state.GitReader(self.repo, "HEAD")))
        texts = [entry["text"] for entry in self.state()["owner_queue"]]
        self.assertIn("release: WK-9 merged and waiting for a release", texts)
        self.assertFalse(any("WK-8" in text for text in texts), texts)
        self.assertEqual(self.git("status", "--porcelain"), "")

        again = self.run_script("released", "v1.2.0")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("nothing to commit", again.stdout)

    def test_released_closes_a_finished_roadmap_ordered_to_be_archived(self) -> None:
        self.write("context/foundation/roadmap.md", roadmap(
            [("WK-1", "search-index", "done"),
             ("WK-8", "search-titles", "done_code (2026-01-02; waiting: release)")],
            owner=["- [x] **WK-1**: decided the engine.", "- [ ] **WK-8**: release word for the titles"],
            release=["- [ ] Set `SEARCH_URL` in production (**WK-8**)"]))
        self.archive("search-index", "2026-01-01")
        first = self.commit("WK-1 merged")
        self.archive("search-titles")
        second = self.commit("WK-8 merged")
        self.git("tag", "-a", "v1.2.0", "-m", "v1.2.0")

        result = self.run_script("released", "v1.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        tree = self.git("ls-tree", "-r", "--name-only", "HEAD", "context/foundation").split()
        self.assertNotIn("context/foundation/roadmap.md", tree)
        archived = [path for path in tree if re.match(r"context/foundation/archive/\d{4}-\d{2}-\d{2}-roadmap\.md$", path)]
        self.assertEqual(len(archived), 1, tree)
        text = self.show(archived[0])
        self.assertIn("## Summary", text)
        self.assertIn("| ID | Item | What changed | Merge |", text)
        self.assertIn(f"| **WK-1** | `search-index` | search-index works | {first[:8]} |", text)
        self.assertIn(f"| **WK-8** | `search-titles` | search-titles works | {second[:8]} |", text)
        self.assertRegex(text, r"(?m)^Release: v1\.2\.0 \(\d{4}-\d{2}-\d{2}\)$")
        self.assertNotIn("- [ ]", text)
        self.assertIn("docs(roadmap): close search", self.git("log", "-1", "--format=%s"))

        state = self.state()
        self.assertIsNone(state["active_roadmap"])
        self.assertEqual(state["last_release"]["version"], "v1.2.0")
        self.assertEqual(state["owner_queue"], [])
        reader = context_state.GitReader(self.repo, "HEAD")
        self.assertIsNone(context_state.staleness(reader))
        self.assertEqual([f.code for f in doctor.run_checks(reader, None) if f.severity == "fail"], [])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_released_leaves_a_roadmap_without_the_archive_order_open(self) -> None:
        self.write("context/foundation/roadmap.md", roadmap(
            [("WK-8", "search-titles", "done_code (2026-01-02; waiting: release)")], owner=[], release=[],
            archive_order="no"))
        self.archive("search-titles")
        self.commit("WK-8 merged")
        self.git("tag", "v1.2.0")
        result = self.run_script("released", "v1.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| autonomous | done |", self.show("context/foundation/roadmap.md"))

    def test_released_records_the_release_of_a_roadmap_closed_before_it(self) -> None:
        closed = roadmap([("WK-8", "search-titles", "done_code (2026-01-02; waiting: release)")], owner=[],
                         release=["- [ ] Set `SEARCH_URL` in production (**WK-8**)"])
        closed += ("\n## Summary\n\n| ID | Item | What changed | Merge |\n| --- | --- | --- | --- |\n"
                   "| **WK-8** | `search-titles` | titles are found | abc12345 |\n\nintegration: covered by the release\n")
        self.write("context/foundation/archive/2026-01-03-roadmap.md", closed)
        self.archive("search-titles")
        self.commit("closed before the release")
        self.git("tag", "-a", "v1.2.0", "-m", "v1.2.0")
        self.assertIn("SEARCH_URL", json.dumps(context_state.build_state(context_state.GitReader(self.repo, "HEAD"))))

        result = self.run_script("released", "v1.2.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.show("context/foundation/archive/2026-01-03-roadmap.md")
        self.assertRegex(text, r"\| \*\*WK-8\*\* .*\| done \|")
        self.assertIn("- [x] Set `SEARCH_URL` in production (**WK-8**) — done: v1.2.0", text)
        self.assertRegex(text, r"(?m)^Release: v1\.2\.0 \(\d{4}-\d{2}-\d{2}\)$")
        state = self.state()
        self.assertEqual(state["owner_queue"], [])
        self.assertEqual(state["last_release"]["version"], "v1.2.0")
        reader = context_state.GitReader(self.repo, "HEAD")
        self.assertEqual([f.code for f in doctor.run_checks(reader, None) if f.severity == "fail"], [])

    def test_released_refuses_an_unknown_tag(self) -> None:
        self.write("context/foundation/roadmap.md", roadmap(
            [("WK-8", "search-titles", "done_code (2026-01-02; waiting: release)")], owner=[], release=[]))
        self.archive("search-titles")
        head = self.commit("WK-8 merged")
        result = self.run_script("released", "v9.9.9")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("v9.9.9", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), head)


if __name__ == "__main__":
    unittest.main()
