"""Tests for the owner-word wake declaration (WORKFLOW.md §8.6) as the installer prints it.

    python3 -m unittest discover -s tests

An autonomous project without `autonomy.ownerWordWake` in context/workflow.json gets the one-time setup steps of
routines/owner-word-wake.md; a project that declared the key, or a manual one, gets nothing. The steps declare
"routine" only once the task's GitHub trigger is verified, because a task created with a cron-or-one-shot tool has
no trigger and never fires. The release gate (scripts/validate.mjs) keeps the setup brief saying so. The doctor side
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

    def test_setup_steps_declare_routine_only_after_the_trigger_is_verified(self) -> None:
        out = install({**self.BASE, "mode": "autonomous"})
        self.assertIn("can be added only in claude.ai/code/routines", out)
        self.assertIn("once the task shows the GitHub trigger", out)
        self.assertIn('until then set "none"', out)
        self.assertIn("open one owner-word issue and check that the routine's run shows up", out)
        self.assertLess(out.index("once the task shows the GitHub trigger"), out.index('"ownerWordWake": "routine"'))

    def test_installer_creates_the_cockpit_label(self) -> None:
        out = install({**self.BASE, "mode": "autonomous"})
        self.assertIn("label cockpit (created on the forge when gh can)", out)
        self.assertNotIn("label owner-word", out)

    def test_declared_project_gets_no_notice(self) -> None:
        for value in ("routine", "heartbeat", "none"):
            with self.subTest(value=value):
                out = install({**self.BASE, "mode": "autonomous", "autonomy": {"ownerWordWake": value}})
                self.assertNotIn(NOTICE, out)

    def test_manual_project_gets_no_notice(self) -> None:
        self.assertNotIn(NOTICE, install({**self.BASE, "mode": "manual"}))
        self.assertNotIn(NOTICE, install(self.BASE))


def validate(edit: tuple[str, str, str] | None = None) -> subprocess.CompletedProcess:
    """Run scripts/validate.mjs on a copy of the package, optionally with one text replaced in one file."""
    root = tempfile.mkdtemp(prefix="owner-word-wake-validate-")
    try:
        copy = os.path.join(root, "pkg")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "tests"))
        if edit:
            rel, old, new = edit
            path = os.path.join(copy, rel)
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            if old not in content:
                raise AssertionError(f"{rel}: {old!r} not found")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content.replace(old, new))
        return subprocess.run(["node", os.path.join(copy, "scripts", "validate.mjs")], capture_output=True, text=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


class SetupBriefGateTest(unittest.TestCase):
    BRIEF = "routines/owner-word-wake.md"

    def test_shipped_brief_passes(self) -> None:
        result = validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_brief_without_each_trigger_rule_fails(self) -> None:
        cases = {
            "web UI": ("only in the routines web UI (claude.ai/code/routines) or with a tool that",
                       "with any tool or"),
            "UI steps": ("exact steps to finish it in claude.ai/code/routines", "steps"),
            "never working": ("never reports the routine as set up or working", "reports what it made"),
            "verify first": ("3. Verify the trigger:", "3. Look at the task:"),
            "none until verified": ('trigger is verified the value is "none"', 'task exists the value is "routine"'),
            "testing section": ("## Testing it", "## Afterwards"),
        }
        for name, (old, new) in cases.items():
            with self.subTest(name=name):
                result = validate((self.BRIEF, old, new))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("routines/owner-word-wake.md", result.stderr)

    def test_readme_without_the_test_steps_fails(self) -> None:
        result = validate(("routines/README.md", "To test it, open\none `cockpit` issue", "Then wait"))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("does not say how to test the owner-word wake routine", result.stderr)


if __name__ == "__main__":
    unittest.main()
