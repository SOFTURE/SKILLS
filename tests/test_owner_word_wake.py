"""Tests for the owner-word wake declaration (WORKFLOW.md §8.6) as the installer prints it.

    python3 -m unittest discover -s tests

An autonomous project without `autonomy.ownerWordWake` in context/workflow.json gets the one-time setup steps of
routines/owner-word-wake.md; a project that declared the key, or a manual one, gets nothing. The doctor side
(`owner-word-wake-undeclared` note, `owner-word-wake-invalid` failure) is covered in test_doctor.py.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(ROOT, "scripts", "install.mjs")
NOTICE = "autonomy.ownerWordWake is not set"


def install(config: dict) -> str:
    root = tempfile.mkdtemp(prefix="owner-word-wake-")
    try:
        os.makedirs(os.path.join(root, "context"))
        with open(os.path.join(root, "context", "workflow.json"), "w", encoding="utf-8") as fh:
            json.dump(config, fh)
        result = subprocess.run(["node", INSTALL, "--target", root, "--dry-run"], capture_output=True, text=True,
                                env={**os.environ, "CI": "true"})
        return result.stdout + result.stderr
    finally:
        shutil.rmtree(root, ignore_errors=True)


class InstallerNoticeTest(unittest.TestCase):
    BASE = {"project": "Example clinic", "language": "en", "mainBranch": "main", "gates": {}}

    def test_autonomous_project_without_the_key_gets_the_setup_steps(self) -> None:
        out = install({**self.BASE, "mode": "autonomous"})
        self.assertIn(NOTICE, out)
        self.assertIn("routines/owner-word-wake.md", out)
        self.assertIn("GitHub trigger on issues (opened, labeled)", out)
        self.assertIn('"autonomy": { "ownerWordWake": "routine" }', out)

    def test_declared_project_gets_no_notice(self) -> None:
        for value in ("routine", "heartbeat", "none"):
            with self.subTest(value=value):
                out = install({**self.BASE, "mode": "autonomous", "autonomy": {"ownerWordWake": value}})
                self.assertNotIn(NOTICE, out)

    def test_manual_project_gets_no_notice(self) -> None:
        self.assertNotIn(NOTICE, install({**self.BASE, "mode": "manual"}))
        self.assertNotIn(NOTICE, install(self.BASE))


if __name__ == "__main__":
    unittest.main()
