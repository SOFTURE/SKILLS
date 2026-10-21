#!/usr/bin/env python3
"""Print the startable set of the roadmap on the main branch, so the coordinator's check is mechanical.

    wt-startable.py [--ref <git-ref>] [--file <path>] [--no-fetch]

Reads `context/foundation/roadmap.md` from `origin/<main>` (fetched first; `--ref` picks another ref,
`--file` a file on disk) and prints one line per item that is not done yet:

    START     FC-3  pricing-one-section        no prerequisites
    START     FC-5  checkout-summary           prerequisites on main: FC-1, FC-2
    PROPOSED  FC-9  dark-mode                  prerequisites on main (start when no START item can take a slot)
    WAIT      FC-6  invoice-pdf                waiting for FC-5 (in_progress), FC-7 (ready)
    FLIGHT    FC-4  password-reset             in_progress (implement 2/3, since 2026-10-20; ...)
    BLOCKED   FC-8  sso-login                  blocked (SOFTURE/AI#301)
    OWNER     FC-10 release                    Mode: owner

START = `ready`, `Mode` is `autonomous`, every prerequisite `done` or `done_code` on the main branch (or
none). Every START item that has no thread yet gets one now (`rules/AGENTS.md` → Coordinator duties).
WAIT always names the missing prerequisite IDs with their status; use them verbatim in the report's
Stage (`waiting for FC-5, FC-7`). FLIGHT rows are `in_progress` or `ready_to_merge`: they should have a
thread; one without a thread is adopted (`softure-worktree-manager` M0.1).

The script cannot see threads: it lists what the roadmap allows, the coordinator matches it against
its thread list. Parsing follows WORKFLOW.md §5; a prerequisite ID that is not in the table counts as
done only when `## Done` names it. Only the `## At a glance` table is read.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wt_config import main_branch, main_root  # noqa: E402

ROADMAP = "context/foundation/roadmap.md"
ID_RE = re.compile(r"[A-Z]+-\d+")
ROW_RE = re.compile(r"^\| \*\*(?P<id>[A-Z]+-\d+)\*\* \| `(?P<change>[^`]+)` \|")
DONE_STATUSES = ("done", "done_code")
FLIGHT_STATUSES = ("in_progress", "ready_to_merge")


def read_roadmap(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            return fh.read()
    root = main_root()
    ref = args.ref
    if not ref:
        branch = main_branch(root)
        ref = f"origin/{branch}"
        if not args.no_fetch:
            subprocess.run(["git", "-C", root, "fetch", "-q", "origin", branch], capture_output=True)
    shown = subprocess.run(["git", "-C", root, "show", f"{ref}:{ROADMAP}"], capture_output=True, text=True)
    if shown.returncode != 0:
        sys.exit(f"cannot read {ROADMAP} at {ref}: {shown.stderr.strip()}")
    return shown.stdout


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def status_word(status: str) -> str:
    return status.replace("*", "").strip().split(" ", 1)[0].split("(", 1)[0]


def parse(text: str) -> tuple[list[dict], set[str]]:
    items: list[dict] = []
    done_section: set[str] = set()
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if section == "done":
            done_section.update(ID_RE.findall(line))
            continue
        if section != "at a glance" or not ROW_RE.match(line):
            continue
        row = cells(line)
        if len(row) < 6:
            continue
        items.append({
            "id": row[0].strip("*"),
            "change": row[1].strip("`"),
            "deps": ID_RE.findall(row[3]),
            "mode": row[4].strip().lower(),
            "status": row[-1].replace("*", "").strip(),
        })
    return items, done_section


def classify(items: list[dict], done_section: set[str]) -> list[tuple[str, dict, str]]:
    status_of = {item["id"]: status_word(item["status"]) for item in items}
    rows = []
    for item in items:
        word = status_word(item["status"])
        if word in DONE_STATUSES:
            continue
        if word in FLIGHT_STATUSES:
            rows.append(("FLIGHT", item, item["status"]))
            continue
        if word == "blocked":
            rows.append(("BLOCKED", item, item["status"]))
            continue
        if item["mode"] == "owner":
            rows.append(("OWNER", item, "Mode: owner"))
            continue
        missing = [
            dep for dep in item["deps"]
            if status_of.get(dep) not in DONE_STATUSES and not (dep not in status_of and dep in done_section)
        ]
        if missing:
            named = ", ".join(f"{dep} ({status_of.get(dep, 'not on the roadmap')})" for dep in missing)
            rows.append(("WAIT", item, f"waiting for {named}"))
            continue
        reason = f"prerequisites on main: {', '.join(item['deps'])}" if item["deps"] else "no prerequisites"
        if word == "ready":
            rows.append(("START", item, reason))
        elif word == "proposed":
            rows.append(("PROPOSED", item, f"{reason} (start when no START item can take a slot)"))
        else:
            rows.append(("UNKNOWN", item, f"unrecognised status: {item['status']}"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", help="git ref to read the roadmap from (default: origin/<main>)")
    parser.add_argument("--file", help="read this roadmap file instead of a git ref")
    parser.add_argument("--no-fetch", action="store_true", help="do not fetch origin/<main> first")
    args = parser.parse_args()

    items, done_section = parse(read_roadmap(args))
    if not items:
        sys.exit(f"no roadmap rows found in {ROADMAP} (WORKFLOW.md §5 table format)")
    rows = classify(items, done_section)
    order = ["START", "PROPOSED", "WAIT", "FLIGHT", "BLOCKED", "OWNER", "UNKNOWN"]
    rows.sort(key=lambda row: order.index(row[0]))
    id_width = max((len(item["id"]) for _, item, _ in rows), default=0)
    change_width = max((len(item["change"]) for _, item, _ in rows), default=0)
    for kind, item, detail in rows:
        print(f"{kind:<9} {item['id']:<{id_width}} {item['change']:<{change_width}}  {detail}")
    if not rows:
        print("nothing left: every roadmap item is done or done_code")


if __name__ == "__main__":
    main()
