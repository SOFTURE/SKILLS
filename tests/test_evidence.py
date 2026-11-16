"""Tests for skills/softure-evidence/scripts/evidence.py.

    python3 -m unittest discover -s tests

Each test builds a throwaway repository with a context/workflow.json and an evidence store in a
temporary folder, then runs the script inside it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "softure-evidence", "scripts", "evidence.py")

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover - the conversion test is skipped without Pillow
    Image = None


class EvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self._tmp.name, "app")
        self.store = os.path.join(self._tmp.name, "store")
        self.home = os.path.join(self._tmp.name, "home")
        os.makedirs(self.repo)
        os.makedirs(self.home)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.configure({"store": "dir", "path": self.store})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def configure(self, evidence: dict | None) -> None:
        config = {"language": "en", "mainBranch": "main", "gates": {}}
        if evidence is not None:
            config["evidence"] = evidence
        self.write("context/workflow.json", json.dumps(config))

    def write(self, path: str, content: str | bytes) -> str:
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb" if isinstance(content, bytes) else "w") as fh:
            fh.write(content)
        return full

    def run_script(self, *args: str, expect: int = 0) -> str:
        env = {**os.environ, "HOME": self.home}
        result = subprocess.run([sys.executable, SCRIPT, *args], cwd=self.repo, env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def save(self, source: str, what: str = "map-panel", state: str = "after", *extra: str) -> dict:
        out = self.run_script("save", source, "--change", "add-side-map", "--what", what,
                              "--state", state, "--width", "390", "--theme", "dark", *extra)
        return json.loads(out.strip().splitlines()[-1])

    def test_name_follows_the_naming_rule(self) -> None:
        out = self.run_script("name", "--change", "add-side-map", "--nn", "1", "--what", "map-panel",
                              "--state", "after", "--width", "390", "--theme", "dark")
        self.assertEqual(out.strip(), "add-side-map/01-map-panel-after-390-dark.webp")

    def test_name_rejects_non_kebab_parts(self) -> None:
        out = self.run_script("name", "--change", "Add_Map", "--nn", "1", "--what", "map",
                              "--state", "after", "--width", "390", "--theme", "dark", expect=2)
        self.assertIn("invalid evidence name", out)

    def test_save_numbers_files_and_writes_the_page(self) -> None:
        source = self.write("shot.webp", b"RIFF0000WEBPVP8 ")
        first = self.save(source, "map-panel", "before")
        second = self.save(source, "map-panel", "after")
        self.assertEqual(first["key"], "add-side-map/01-map-panel-before-390-dark.webp")
        self.assertEqual(second["key"], "add-side-map/02-map-panel-after-390-dark.webp")
        self.assertTrue(os.path.exists(os.path.join(self.store, second["key"])))
        with open(os.path.join(self.store, "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn("add-side-map/01-map-panel-before-390-dark.webp", page)
        self.assertIn("add-side-map/02-map-panel-after-390-dark.webp", page)
        self.assertEqual(self.run_script("list", "--change", "add-side-map").split(),
                         [first["key"], second["key"]])

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_save_converts_png_to_webp(self) -> None:
        source = os.path.join(self.repo, "shot.png")
        Image.new("RGB", (390, 844), "white").save(source)
        saved = self.save(source)
        self.assertTrue(saved["key"].endswith(".webp"), saved)
        with Image.open(os.path.join(self.store, saved["key"])) as image:
            self.assertEqual(image.format, "WEBP")

    def test_save_without_a_store_is_reported_as_not_durable(self) -> None:
        self.configure(None)
        source = self.write("clip.mp4", b"\x00\x00\x00\x18ftypmp42")
        saved = self.save(source)
        self.assertFalse(saved["durable"])
        self.assertTrue(saved["file"].startswith(self.home))
        self.assertTrue(saved["key"].endswith(".mp4"))

    def test_save_through_an_upload_command_returns_its_link(self) -> None:
        self.configure({"store": "command", "upload": "echo uploading {file} >&2; echo https://cdn.example/{key}"})
        source = self.write("shot.webp", b"RIFF0000WEBPVP8 ")
        saved = self.save(source)
        self.assertEqual(saved["link"], "https://cdn.example/add-side-map/01-map-panel-after-390-dark.webp")

    def test_render_adds_entries_to_an_existing_page(self) -> None:
        page = os.path.join(self._tmp.name, "page.html")
        self.run_script("render", "--out", page, "--add",
                        "add-side-map/01-map-panel-before-390-dark.webp=https://a.example/1")
        self.run_script("render", "--from-page", page, "--out", page, "--add",
                        "add-side-map/02-map-panel-after-390-dark.webp=https://a.example/2")
        with open(page, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("https://a.example/1", content)
        self.assertIn("https://a.example/2", content)
        self.assertEqual(content.count("<figure>"), 1, "before and after share one row")

    def test_check_fails_on_binaries_in_a_change_folder(self) -> None:
        self.write("context/changes/add-side-map/plan.md", "# Plan\n")
        self.assertIn("no images", self.run_script("check", "context/changes/add-side-map"))
        self.write("context/changes/add-side-map/reviews/p2.png", b"\x89PNG")
        out = self.run_script("check", "context/changes/add-side-map", expect=1)
        self.assertIn("reviews/p2.png", out)

    def test_prune_deletes_only_changes_archived_long_enough_ago(self) -> None:
        for change, archived in (("old-change", "2026-01-10"), ("new-change", "2026-10-02")):
            self.write(f"context/archive/2026-01-01-{change}/change.md",
                       f"---\nchange_id: {change}\narchived_at: {archived}\n---\n")
            os.makedirs(os.path.join(self.store, change))
        os.makedirs(os.path.join(self.store, "in-flight"))
        dry = self.run_script("prune", "--months", "6", "--today", "2026-11-16")
        self.assertIn("would prune old-change", dry)
        self.assertTrue(os.path.isdir(os.path.join(self.store, "old-change")))
        self.run_script("prune", "--months", "6", "--today", "2026-11-16", "--apply")
        self.assertEqual(sorted(os.listdir(self.store)), ["in-flight", "new-change"])


if __name__ == "__main__":
    unittest.main()
