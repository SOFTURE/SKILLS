"""Tests for owner-queue entries whose roadmap checkbox wraps onto indented lines (SOFTURE/SKILLS#90).

    python3 -m unittest discover -s tests

A roadmap wraps long items at a fixed width. `owner_queue[].text` holds the whole item: the checkbox line joined
with its indented continuation lines, up to the next list item, heading or blank line, whitespace collapsed.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_doctor import Project, context_state  # noqa: E402

ROADMAP = "context/foundation/roadmap.md"

WRAPPED_RELEASE = (
    "- [ ] Set `SEARCH_INDEX_URL` in production and delete the old index key in the `production` Environment\n"
    "      before the deploy (**SR-1**)\n"
)
WRAPPED_OWNER = (
    "- [ ] **SR-5**: choose the ranking provider and open the account, then close the trial accounts\n"
    "  `ranking-a` and `ranking-b`. Gates SR-5.\n"
)


class WrappedEntryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def tearDown(self) -> None:
        self.project.cleanup()

    def queue(self) -> list[dict]:
        self.project.state("write")
        return json.loads(self.project.read(context_state.STATE_PATH))["owner_queue"]

    def wrap(self) -> None:
        text = self.project.read(ROADMAP)
        text = text.replace("- [ ] Set `SEARCH_INDEX_URL` in production (**SR-1**)\n", WRAPPED_RELEASE)
        text = text.replace("- [ ] **SR-5**: choose the ranking provider and open the account. Gates SR-5.\n",
                            WRAPPED_OWNER)
        self.project.write(ROADMAP, text)

    def test_wrapped_entries_keep_their_full_text(self) -> None:
        self.wrap()
        texts = [entry["text"] for entry in self.queue()]
        self.assertIn("Set `SEARCH_INDEX_URL` in production and delete the old index key in the `production` "
                      "Environment before the deploy (**SR-1**)", texts)
        self.assertIn("**SR-5**: choose the ranking provider and open the account, then close the trial accounts "
                      "`ranking-a` and `ranking-b`. Gates SR-5.", texts)

    def test_continuation_stops_at_a_blank_line_a_list_item_or_a_ticked_box(self) -> None:
        lines = [
            "- [ ] first item that",
            "  wraps once",
            "  - a nested bullet is not part of it",
            "- [x] a ticked item",
            "  with its own wrapped line",
            "- [ ] second item",
            "",
            "  a paragraph after a blank line",
        ]
        self.assertEqual(context_state.open_checkboxes(lines), ["first item that wraps once", "second item"])

    def test_an_entry_that_never_wrapped_keeps_its_id(self) -> None:
        before = {entry["text"]: entry["id"] for entry in self.queue()}
        self.project.commit("state")
        self.wrap()
        after = {entry["text"]: entry["id"] for entry in self.queue()}
        unwrapped = [text for text in before if text in after]
        self.assertTrue(unwrapped)
        for text in unwrapped:
            self.assertEqual(after[text], before[text], text)

    def test_a_wrapped_entry_continues_the_id_of_its_cut_text(self) -> None:
        cut = {entry["item"]: entry["id"] for entry in self.queue() if entry["kind"] == "decision"}
        self.project.commit("state")
        self.wrap()
        full = {entry["item"]: entry["id"] for entry in self.queue() if entry["kind"] == "decision"}
        self.assertEqual(full["SR-5"], cut["SR-5"])


if __name__ == "__main__":
    unittest.main()
