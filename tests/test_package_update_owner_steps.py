"""A package bump that needs an owner-only step reaches the owner (issue #86).

    python3 -m unittest discover -s tests

The package-update routine merges a bump with its owner step recorded (`## Before the next release` of the live
roadmap, else a cockpit issue listed in `routines.packageUpdates.ownerSteps`) or holds it with such an issue
(`routines.packageUpdates.hold`, `owner`). `context_state.py` turns each into an `owner_queue` entry, classifies an
environment variable name such as `SOFTURE_EMAIL_KEY_SECRET` as a secret, and drops a step once the owner confirms it.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_doctor import Project, SCHEMA, validate  # noqa: E402
import context_state  # noqa: E402

HOLD_SOURCE = f"{context_state.WORKFLOW_PATH}#routines.packageUpdates.hold"
STEPS_SOURCE = f"{context_state.WORKFLOW_PATH}#routines.packageUpdates.ownerSteps"


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


class SecretKindTest(unittest.TestCase):
    def test_environment_variable_names_are_secrets(self) -> None:
        for text in ("Set SOFTURE_EMAIL_KEY_SECRET in production", "add `STRIPE_API_KEY` to the deploy",
                     "set GITHUB_TOKEN", "DB_PASSWORD for the new database", "set the mailing secret"):
            with self.subTest(text=text):
                self.assertRegex(text, context_state.SECRET_RE)
        for text in ("Set `STORAGE_URL` in production", "watch the migration", "SECRETARY_NAME is shown"):
            with self.subTest(text=text):
                self.assertNotRegex(text, context_state.SECRET_RE)


class OwnerQueueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def tearDown(self) -> None:
        self.project.cleanup()

    def set_package_updates(self, package_updates: dict) -> None:
        workflow = json.loads(self.project.read(context_state.WORKFLOW_PATH))
        workflow["routines"] = {"packageUpdates": package_updates}
        self.project.write(context_state.WORKFLOW_PATH, json.dumps(workflow, indent=2) + "\n")

    def queue(self) -> list[dict]:
        result = self.project.state("write")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.project.read(context_state.STATE_PATH))
        with open(SCHEMA, encoding="utf-8") as fh:
            self.assertEqual(validate(state, json.load(fh)), [])
        return state["owner_queue"]

    def test_before_the_next_release_secret_step_is_a_secret(self) -> None:
        rel = context_state.ROADMAP_PATH
        self.project.write(rel, self.project.read(rel) + (
            "\n## Before the next release\n\n"
            "- [ ] Set SOFTURE_EMAIL_KEY_SECRET in production (@softure-ai/mailing 0.3.0, 2026-11-24)\n"))
        entry = next(entry for entry in self.queue() if "SOFTURE_EMAIL_KEY_SECRET" in entry["text"])
        self.assertEqual(entry["kind"], "secret")
        self.assertEqual(entry["source"], f"{rel}#{context_state.RELEASE_SECTION}")
        self.assertEqual(entry["since"], "2026-11-24")

    def test_a_hold_for_the_owner_is_owner_work_and_a_defect_hold_is_not(self) -> None:
        self.set_package_updates({"hold": [
            {"package": "@softure-ai/auth", "issue": "SOFTURE/AI#123", "since": "2026-11-20"},
            {"package": "@softure-ai/billing", "issue": "#41", "since": "2026-11-22",
             "owner": "choose how existing invoices are treated by billing 0.4.0"},
        ]})
        entries = [entry for entry in self.queue() if entry["source"] == HOLD_SOURCE]
        self.assertEqual(len(entries), 1, "a package defect waits for SOFTURE, not for the owner")
        entry = entries[0]
        self.assertEqual(entry["kind"], "decision")
        self.assertEqual(entry["since"], "2026-11-22")
        self.assertIsNone(entry["item"])
        self.assertIn("@softure-ai/billing", entry["text"])
        self.assertIn("#41", entry["text"])
        self.assertIn("existing invoices", entry["text"])

    def test_a_merged_bump_without_a_live_roadmap_lists_its_issue_until_the_owner_confirms(self) -> None:
        step = {"package": "@softure-ai/mailing", "version": "0.3.0", "issue": "#42", "since": "2026-11-24",
                "step": "set the production secret SOFTURE_EMAIL_KEY_SECRET"}
        self.set_package_updates({"ownerSteps": [step]})
        entries = [entry for entry in self.queue() if entry["source"] == STEPS_SOURCE]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "secret")
        self.assertEqual(entries[0]["since"], "2026-11-24")
        for part in ("@softure-ai/mailing 0.3.0", "SOFTURE_EMAIL_KEY_SECRET", "#42"):
            self.assertIn(part, entries[0]["text"])
        self.set_package_updates({"ownerSteps": [{**step, "confirmed": "#43"}]})
        self.assertFalse([entry for entry in self.queue() if entry["source"] == STEPS_SOURCE],
                         "a confirmed step is settled")

    def test_a_changed_hold_list_makes_the_state_stale(self) -> None:
        self.project.state("write")
        self.set_package_updates({"ownerSteps": [{"package": "@softure-ai/mailing", "version": "0.3.0",
                                                  "issue": "#42", "since": "2026-11-24",
                                                  "step": "set SOFTURE_EMAIL_KEY_SECRET"}]})
        self.assertIn("state-stale", self.project.codes())

    def test_malformed_entries_are_ignored(self) -> None:
        self.set_package_updates({"hold": ["x", {"issue": "#1", "owner": "no package"}], "ownerSteps": {"a": 1}})
        sources = {entry["source"] for entry in self.queue()}
        self.assertFalse(sources & {HOLD_SOURCE, STEPS_SOURCE})


class RoutineTextTest(unittest.TestCase):
    routine = read("routines/package-updates.md")

    def test_owner_steps_are_recorded_or_held(self) -> None:
        self.assertIn("### 5. A step only the owner can take", self.routine)
        for part in ("## Before the next release", "routines.packageUpdates.ownerSteps", "\"owner\"",
                     "cockpit", "only the secret is missing", "how existing data is treated", "confirmed"):
            self.assertIn(part, self.routine)

    def test_report_names_the_step_on_its_decision_line(self) -> None:
        report = self.routine[self.routine.index("### 7. Report"):]
        self.assertRegex(report, r"Decision: .*SOFTURE_EMAIL_KEY_SECRET")
        self.assertRegex(report, r"(?s)`Decision` names .*owner step")

    def test_workflow_documents_both_shapes(self) -> None:
        workflow = read("WORKFLOW.md")
        self.assertIn('"ownerSteps"', workflow)
        self.assertRegex(workflow, r'"hold": \[[^\]]*"owner":')
        self.assertTrue(re.search(r"routines\.packageUpdates", workflow[workflow.index("### 12.1"):]))


if __name__ == "__main__":
    unittest.main()
