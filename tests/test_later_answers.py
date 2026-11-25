"""Tests for a "later" answer to an owner-queue entry (WORKFLOW.md §8.6): the item moves to the later roadmap.

    python3 -m unittest discover -s tests

An answered entry leaves the owner queue whatever the answer. A "later" moves the item to
`context/foundation/roadmaps/roadmap-later.md` as a new item; that roadmap never adds a "start" word to the queue.
An open entry that still carries `(later: #N)`, the shape before 0.37.0, gets the `owner-entry-put-off` note.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_doctor import Project, context_state  # noqa: E402

PAYMENTS = "context/foundation/roadmaps/roadmap-payments.md"
LATER = "context/foundation/roadmaps/roadmap-later.md"

LATER_ROADMAP = """---
project: "Example clinic"
roadmap: later
version: 1
status: waiting
backlog: context/backlog/roadmap-later/
trigger: "the owner picks an item up"
created: 2026-11-24
updated: 2026-11-24
---

# Roadmap later: what the owner put off

## At a glance

| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **LT-1** | `pick-payment-provider` | the payment provider is chosen | — | owner | blocked (owner: put off, #12) |

## Items

### LT-1: Pick the payment provider
- **Status:** blocked (owner: put off, #12)
- **From:** PY-1 in roadmap-payments.md, cockpit #12
"""


class LaterAnswerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def tearDown(self) -> None:
        self.project.cleanup()

    def queue(self) -> list[dict]:
        self.project.state("write")
        return json.loads(self.project.read(context_state.STATE_PATH))["owner_queue"]

    def test_the_later_roadmap_adds_no_start_word(self) -> None:
        self.project.write(LATER, LATER_ROADMAP)
        queue = self.queue()
        self.assertFalse(any(entry["source"] == LATER for entry in queue), queue)
        self.assertTrue(any(entry["kind"] == "word" and "payments" in entry["text"] for entry in queue),
                        "another queued roadmap still asks for its start word")
        state = json.loads(self.project.read(context_state.STATE_PATH))
        self.assertIn("later", [roadmap["slug"] for roadmap in state["queued"]], "the later roadmap is still listed")

    def test_a_settled_later_answer_leaves_the_queue(self) -> None:
        before = [entry for entry in self.queue() if entry["item"] == "PY-1" and entry["kind"] == "decision"]
        self.assertEqual(len(before), 1)
        text = self.project.read(PAYMENTS)
        text = text.replace("| blocked (provider account) |", "| carried (to roadmaps/roadmap-later.md LT-1, #12) |")
        text = text.replace("- [ ] **PY-1**: pick the payment provider. Gates PY-1.",
                            "- [x] **PY-1**: pick the payment provider. Gates PY-1. — later: #12 → LT-1")
        self.project.write(PAYMENTS, text)
        self.project.write(LATER, LATER_ROADMAP)
        queue = self.queue()
        self.assertFalse(any(entry["item"] in ("PY-1", "LT-1") for entry in queue), queue)
        code, report = self.project.doctor()
        self.assertEqual((code, report["failures"], report["notes"]), (0, [], []), report)

    def test_an_entry_kept_open_with_later_is_noted(self) -> None:
        text = self.project.read(PAYMENTS).replace(
            "- [ ] **PY-1**: pick the payment provider.", "- [ ] **PY-1** (later: #12, some day): pick the payment provider.")
        self.project.write(PAYMENTS, text)
        self.project.state("write")
        code, report = self.project.doctor()
        self.assertEqual(code, 0, report)
        self.assertEqual([(note["code"], note["path"]) for note in report["notes"]], [("owner-entry-put-off", PAYMENTS)])
        self.assertIn("roadmap-later.md", report["notes"][0]["message"])


if __name__ == "__main__":
    unittest.main()
