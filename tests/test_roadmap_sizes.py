"""Optional relative sizes and slices in a roadmap (WORKFLOW §5, "Sizes and slices").

    python3 -m unittest discover -s tests

A roadmap with `- **Size:** S | M | L` per item, a `**Sizes:**` line and a `### Slices` block under `## Order` must
read exactly like the same roadmap without them: the orchestrators' parser (`wt-startable.py`), the state builder
(`context_state.py`) and the doctor never read a size.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True  # the package ships skills/, so no __pycache__ may land there
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "softure-doctor", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "skills", "softure-worktree", "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import context_state  # noqa: E402
from test_doctor import Project  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "wt_startable", os.path.join(ROOT, "skills", "softure-worktree", "scripts", "wt-startable.py"))
wt_startable = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wt_startable)

SIZES = {"SR-1": "M", "SR-2": "S", "SR-3": "S", "SR-4": "S", "SR-5": "L"}
ORDER_BLOCK = """
**Sizes:** relative to each other, never hours or dates. S: one or two phases, no migration. M: up to four
phases or one migration. L: a migration and open unknowns.

### Slices
| Slice | Items | Size |
| --- | --- | --- |
| **1. First usable: a title search** | SR-1, SR-2 | 1 S, 1 M |
| 2. Filters and synonyms | SR-3, SR-4 | 2 S |
| 3. Paid ranking | SR-5 | 1 L |
"""


def sized(text: str) -> str:
    """`text` with a Size line in every item block, the Sizes line and the Slices block under `## Order`."""
    text = text.replace("## Order\nSR-1 first.\n", "## Order\nSR-1 first.\n" + ORDER_BLOCK, 1)
    lines = []
    current = None
    for line in text.splitlines():
        heading = re.match(r"^### ([A-Z]+-\d+):", line)
        if heading:
            current = heading.group(1)
        lines.append(line)
        if current and line.startswith("- **Status:**"):
            lines.append(f"- **Size:** {SIZES[current]}")
            current = None
    return "\n".join(lines) + "\n"


class RoadmapSizesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.plain = self.project.read(context_state.ROADMAP_PATH)
        self.sized = sized(self.plain)

    def tearDown(self) -> None:
        self.project.cleanup()

    def test_the_fixture_really_carries_sizes_and_slices(self) -> None:
        self.assertIn("### Slices", self.sized)
        self.assertGreaterEqual(self.sized.count("- **Size:** "), 2)

    def test_the_orchestrators_parser_ignores_sizes(self) -> None:
        self.assertEqual(wt_startable.parse(self.sized), wt_startable.parse(self.plain))
        self.assertEqual(wt_startable.classify(*wt_startable.parse(self.sized)),
                         wt_startable.classify(*wt_startable.parse(self.plain)))

    def test_the_state_and_the_doctor_ignore_sizes(self) -> None:
        self.assertEqual(context_state.roadmap_rows(self.sized), context_state.roadmap_rows(self.plain))
        before = json.loads(self.project.read(context_state.STATE_PATH))
        self.project.write(context_state.ROADMAP_PATH, self.sized)
        self.project.state("write")
        after = json.loads(self.project.read(context_state.STATE_PATH))
        self.assertEqual(after["active_roadmap"], before["active_roadmap"])
        self.assertEqual(after["owner_queue"], before["owner_queue"])
        self.assertEqual(self.project.codes(), set())


if __name__ == "__main__":
    unittest.main()
