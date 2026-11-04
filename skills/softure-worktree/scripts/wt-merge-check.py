#!/usr/bin/env python3
"""Decide whether a change branch must merge the main branch in again before its merge, and which gates
that merge has to re-run.

    wt-merge-check.py [--base <ref>] [--no-fetch] [--not-mergeable]

Run in the change branch's checkout (worktree or cloud session), after the go and before merging the
pull request. Compares what `<main>` brought since the branch last merged it (merge-base..origin/<main>)
with what the branch changes (merge-base..HEAD) and prints:

    VERDICT  merge-as-is | remerge
    GATES    none | related | full
    <one line per finding: incoming, conflict, overlap, migrations, dependencies, test setup/config>
    RUN      <command>        (only with `remerge`: the gates to run on the merged tree, in order)

`conflict` is a local trial merge (`git merge-tree --write-tree`, nothing is written to the branch or the
working tree): `none`, `yes` with the conflicting files, or `unknown` when this git cannot run it (2.38+
needed). Pass `--not-mergeable` when the forge reports the pull request not mergeable; it counts as a
conflict under every policy.

`merge-as-is` — `<main>` has not moved, or `autonomy.remergeMain` finds no reason to merge it in:
- `"when-needed"` (the default): `<main>` brought no migration, no dependency change and no file the
  branch also changes (a conflict always comes with such a file);
- `"on-conflict"`: the merge does not conflict. Overlap, migrations and dependency changes are still
  printed (and still decide GATES when a remerge does happen), but they do not force a remerge. The
  merged result is then not tested before the merge: a change that is incompatible without conflicting
  surfaces on `<main>` or in the release gate instead of on the branch.
Merge the pull request as it is, provided the forge reports it mergeable and its checks were green at
READY. No push, no hook.

`remerge` — merge `origin/<main>` into the branch, resolve, run the RUN lines, push. GATES says what the
merge can break:
- `related`: every gate except `gates.test`, then `autonomy.relatedTests` with `{files}` replaced by
  the files the branch changes (on the merged tree);
- `full`: every gate — the incoming changes add a migration or touch dependencies, test setup or
  config (built-in patterns plus `autonomy.fullGatePaths`), or `autonomy.relatedTests` is not set.

`autonomy.remergeMain: "always"` keeps the old behaviour (always `remerge`; GATES is still computed).
The release gate runs the full suite once per roadmap either way (WORKFLOW.md §2).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wt_config import load_config  # noqa: E402

POLICIES = ("when-needed", "on-conflict", "always")
DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "pnpm-workspace.yaml",
    "yarn.lock", "bun.lock", "bun.lockb", ".npmrc", ".nvmrc", ".node-version",
    "requirements.txt", "pyproject.toml", "poetry.lock", "uv.lock", "Pipfile", "Pipfile.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock",
    "composer.json", "composer.lock", "Directory.Packages.props", "packages.lock.json",
}
FULL_GATE_PATTERNS = [
    "vitest.config.*", "vitest.setup.*", "vitest.workspace.*", "jest.config.*", "jest.setup.*",
    "playwright.config.*", "tsconfig*.json", "eslint.config.*", ".eslintrc*", "biome.json*",
    "babel.config.*", ".babelrc*", "lefthook.yml", "lefthook.yaml", ".husky/*", ".github/workflows/*",
    "test/setup*", "tests/setup*", "**/test-setup.*", "**/setupTests.*",
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed(rev_a: str, rev_b: str) -> list[str]:
    return [f for f in git("diff", "--name-only", "--no-renames", rev_a, rev_b).splitlines() if f]


def matches(path: str, patterns: list[str]) -> bool:
    name = os.path.basename(path)
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def listing(files: list[str], limit: int = 8) -> str:
    if not files:
        return "none"
    more = f" (+{len(files) - limit} more)" if len(files) > limit else ""
    return ", ".join(files[:limit]) + more


def trial_merge(merge_base: str, head: str, base_sha: str) -> tuple[str, list[str]]:
    """Merge `base_sha` into `head` in memory. Returns ("none" | "yes" | "unknown", conflicting files)."""
    result = subprocess.run(
        ["git", "merge-tree", "--write-tree", "--name-only", "--no-messages",
         f"--merge-base={merge_base}", head, base_sha],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return "none", []
    if result.returncode == 1:
        lines = [line for line in result.stdout.splitlines()[1:] if line]
        return "yes", sorted(set(lines))
    return "unknown", []


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", help="ref of the main branch to compare with (default: origin/<main>)")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--not-mergeable", action="store_true",
                        help="the forge reports the pull request not mergeable (a conflict with the main branch)")
    opts = parser.parse_args()

    config = load_config()
    main_ref = config["mainBranch"]
    autonomy = config.get("autonomy") or {}
    base = opts.base or f"origin/{main_ref}"
    if not opts.no_fetch and not opts.base:
        subprocess.run(["git", "fetch", "-q", "origin", main_ref], check=False)

    head = git("rev-parse", "HEAD").strip()
    base_sha = git("rev-parse", base).strip()
    merge_base = git("merge-base", head, base_sha).strip()
    incoming = changed(merge_base, base_sha)
    ours = changed(merge_base, head)
    overlap = sorted(set(incoming) & set(ours))

    migrations_dir = ((config.get("migrations") or {}).get("dir") or "").rstrip("/")
    migrations = [f for f in incoming if migrations_dir and f.startswith(migrations_dir + "/")]
    dependencies = [f for f in incoming if os.path.basename(f) in DEPENDENCY_FILES]
    setup = [f for f in incoming if matches(f, FULL_GATE_PATTERNS + list(autonomy.get("fullGatePaths") or []))]

    policy = autonomy.get("remergeMain") or "when-needed"
    if policy not in POLICIES:
        sys.exit(f"autonomy.remergeMain={policy!r} is not one of: {', '.join(POLICIES)}")
    moved = merge_base != base_sha
    conflict, conflicting = trial_merge(merge_base, head, base_sha) if moved else ("none", [])
    conflicts = opts.not_mergeable or conflict != "none"  # unknown counts as a conflict: never guess clean
    if policy == "always":
        needed = moved or opts.not_mergeable
    elif policy == "on-conflict":
        needed = conflicts
    else:
        # a textual conflict always shows up as an overlapping file
        needed = opts.not_mergeable or (moved and bool(overlap or migrations or dependencies))
    related_cmd = autonomy.get("relatedTests")
    full = bool(migrations or dependencies or setup) or not related_cmd

    print(f"VERDICT  {'remerge' if needed else 'merge-as-is'}")
    print(f"GATES    {'none' if not needed else ('full' if full else 'related')}")
    if not moved:
        print(f"incoming: none — {base} ({base_sha[:8]}) is already in the branch")
    else:
        count = int(git("rev-list", "--count", f"{merge_base}..{base_sha}").strip())
        print(f"incoming: {len(incoming)} files in {count} commits since {merge_base[:8]} ({base} {base_sha[:8]})")
    if conflict == "yes":
        print(f"conflict: yes — {listing(conflicting)}")
    elif conflict == "unknown":
        print("conflict: unknown — `git merge-tree --write-tree` failed (git 2.38+ needed); treated as a conflict")
    else:
        print("conflict: none")
    if opts.not_mergeable:
        print("forge: the pull request is not mergeable (--not-mergeable)")
    print(f"overlap: {listing(overlap)}")
    print(f"migrations: {listing(migrations)}")
    print(f"dependencies: {listing(dependencies)}")
    print(f"test setup/config: {listing(setup)}")
    print(f"policy: autonomy.remergeMain={policy}; relatedTests={'set' if related_cmd else 'not set'}")
    if not needed:
        return

    gates = config.get("gates") or {}
    if full:
        for name, cmd in gates.items():
            if cmd:
                print(f"RUN      {cmd}")
        return
    for name, cmd in gates.items():
        if cmd and name != "test":
            print(f"RUN      {cmd}")
    existing = set(git("ls-tree", "-r", "--name-only", head).splitlines())
    files = [f for f in ours if f in existing and not f.startswith("context/")]
    if files:
        print(f"RUN      {related_cmd.replace('{files}', ' '.join(shlex.quote(f) for f in files))}")


if __name__ == "__main__":
    main()
