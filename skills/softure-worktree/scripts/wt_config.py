#!/usr/bin/env python3
"""Read the project's workflow configuration (context/workflow.json, see WORKFLOW.md §2).

    wt_config.py <dotted.key>        # scalar -> one line; list -> one item per line; missing/null -> nothing
    wt_config.py --root              # absolute path of the main worktree
    wt_config.py --json              # the whole resolved config as JSON

Always reads the config of the MAIN worktree (first entry of `git worktree list`), so every
worktree and every script sees the same values. `mainBranch` falls back to origin's HEAD, then
"main"; `worktree.maxParallel` to 4; `language` to "en".

Importable: `from wt_config import load_config, main_root, main_branch`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

CONFIG_PATH = os.path.join("context", "workflow.json")
DEFAULTS = {"language": "en", "worktree": {"maxParallel": 4, "setup": []}, "release": {"owner": True}}


def main_root() -> str:
    out = subprocess.run(
        ["git", "worktree", "list", "--porcelain"], check=True, capture_output=True, text=True
    ).stdout
    first = out.splitlines()[0] if out else ""
    if not first.startswith("worktree "):
        sys.exit("cannot read `git worktree list` output — run inside a git repository")
    return first[len("worktree "):]


def _detect_main_branch(root: str) -> str:
    ref = subprocess.run(
        ["git", "-C", root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        capture_output=True, text=True,
    )
    if ref.returncode == 0 and ref.stdout.strip().startswith("origin/"):
        return ref.stdout.strip()[len("origin/"):]
    return "main"


def _merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(root: str | None = None) -> dict:
    root = root or main_root()
    path = os.path.join(root, CONFIG_PATH)
    data: dict = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    config = _merge(DEFAULTS, data)
    if not config.get("mainBranch"):
        config["mainBranch"] = _detect_main_branch(root)
    return config


def main_branch(root: str | None = None) -> str:
    return load_config(root)["mainBranch"]


def lookup(config: dict, dotted: str):
    node = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--root":
        print(main_root())
        return
    config = load_config()
    if arg == "--json":
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return
    value = lookup(config, arg)
    if value is None:
        return
    if isinstance(value, list):
        for item in value:
            print(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if item is not None:
                print(f"{key}\t{item}")
    elif isinstance(value, bool):
        print("true" if value else "false")
    else:
        print(value)


if __name__ == "__main__":
    main()
