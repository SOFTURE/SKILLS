"""The rules name who settles the context after a release: the releasing session, never the package-update routine.

    python3 -m unittest discover -s tests
"""
from __future__ import annotations

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def paragraph(text: str, start: str) -> str:
    """The paragraph of `text` that begins with `start`."""
    at = text.index(start)
    end = text.find("\n\n", at)
    return text[at:end if end != -1 else len(text)]


def section(text: str, heading: str) -> str:
    at = text.index(heading)
    following = re.search(r"(?m)^#{2,3} ", text[at + len(heading):])
    return text[at:at + len(heading) + following.start()] if following else text[at:]


class ReleaseSettleRulesTest(unittest.TestCase):
    def test_agents_releases_paragraph_orders_the_settle_after_the_deploy(self) -> None:
        releases = paragraph(read("rules/AGENTS.md"), "**Releases.**")
        self.assertIn("wt-roadmap.py released <tag>", releases)
        self.assertRegex(releases, r"deploy's checks pass")
        self.assertRegex(releases, r"package-update routine never")

    def test_workflow_5_2_orders_the_settle_after_the_deploy(self) -> None:
        closing = section(read("WORKFLOW.md"), "### 5.2 Closing a roadmap")
        self.assertIn("wt-roadmap.py released <tag>", closing)
        self.assertRegex(closing, r"deploy's checks pass")
        self.assertRegex(closing, r"package-update routine never")

    def test_package_update_routine_never_settles_a_release(self) -> None:
        routine = read("routines/package-updates.md")
        self.assertIn("wt-roadmap.py released", routine)

    def test_worktree_skill_documents_the_released_mode(self) -> None:
        self.assertIn("wt-roadmap.py released <tag>", read("skills/softure-worktree/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
