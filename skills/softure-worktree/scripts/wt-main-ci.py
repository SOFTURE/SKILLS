#!/usr/bin/env python3
"""Read the main branch's CI result for one commit: the merge a thread just made, or the main branch's head.

    wt-main-ci.py [<sha>] [--json] [--no-fetch]

Without `<sha>` it reads `origin/<main>` (fetched first unless `--no-fetch`). It asks the forge through `gh`
(read-only; `$SOFTURE_GH` names another binary) for the GitHub Actions runs on that commit started by a `push`,
and prints one verdict line, then one line per run:

    MAIN-CI  green | red | flaky | running | none | superseded  <sha7>
    RUN      <workflow>  <conclusion | status>  attempt <n>  <url>

- `green`: every run finished with success (or was skipped), each on its first attempt.
- `red`: a run failed (failure, timed out, startup failure, action required). The thread that made the merge
  owns it: a new change fixes it, never the next item (AGENTS.md → Operating mode: autonomous).
- `flaky`: every run is green now, but one of them passed only on a re-run (an earlier attempt failed). A test
  that fails once and passes on a re-run is a bug, never a timing failure: it is fixed like a red.
- `running`: a run is queued or in progress. Look again later (a scheduled wake-up, never a sleep in the turn).
- `none`: no push-triggered run on that commit yet (it has not started, or CI does not run on pushes to <main>).
- `superseded`: every run was cancelled, as `concurrency` does when a newer push arrives; the newer commit's
  run answers for this one.

Exit codes: 0 green or superseded, 1 red or flaky, 75 running or none, 2 when the forge cannot be reached.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wt_config import main_branch  # noqa: E402

RED = {"failure", "timed_out", "startup_failure", "action_required"}
PASSED = {"success", "skipped", "neutral"}
EXIT = {"green": 0, "superseded": 0, "red": 1, "flaky": 1, "running": 75, "none": 75}


def gh_api(path: str):
    try:
        out = subprocess.run([os.environ.get("SOFTURE_GH", "gh"), "api", path], capture_output=True, text=True,
                             timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def latest_runs(runs: list[dict]) -> list[dict]:
    """One run per workflow: the newest (a re-run of the whole workflow is a new attempt of the same run)."""
    newest: dict = {}
    for run in runs:
        key = run.get("workflow_id") or run.get("name")
        if key not in newest or (run.get("run_number") or 0, run.get("id") or 0) > (
                newest[key].get("run_number") or 0, newest[key].get("id") or 0):
            newest[key] = run
    return list(newest.values())


def verdict(runs: list[dict], failed_before: set) -> str:
    """The commit's CI verdict. `failed_before` holds the ids of runs with a failed earlier attempt."""
    if not runs:
        return "none"
    if any(run.get("status") != "completed" for run in runs):
        return "running"
    conclusions = [run.get("conclusion") for run in runs]
    if any(conclusion in RED for conclusion in conclusions):
        return "red"
    if all(conclusion == "cancelled" for conclusion in conclusions):
        return "superseded"
    if any(conclusion not in PASSED and conclusion != "cancelled" for conclusion in conclusions):
        return "red"
    if any(run.get("id") in failed_before for run in runs):
        return "flaky"
    return "green"


def read(sha: str, api=gh_api) -> dict | None:
    data = api(f"repos/{{owner}}/{{repo}}/actions/runs?head_sha={sha}&event=push&per_page=100")
    if not isinstance(data, dict):
        return None
    runs = latest_runs([run for run in data.get("workflow_runs") or [] if isinstance(run, dict)])
    failed_before = set()
    for run in runs:
        for attempt in range(1, int(run.get("run_attempt") or 1)):
            earlier = api(f"repos/{{owner}}/{{repo}}/actions/runs/{run.get('id')}/attempts/{attempt}")
            if isinstance(earlier, dict) and earlier.get("conclusion") in RED:
                failed_before.add(run.get("id"))
                break
    return {"sha": sha, "verdict": verdict(runs, failed_before),
            "runs": [{"workflow": run.get("name"), "status": run.get("status"), "conclusion": run.get("conclusion"),
                      "attempt": run.get("run_attempt") or 1, "url": run.get("html_url"),
                      "failed_before": run.get("id") in failed_before} for run in runs]}


def resolve(ref: str) -> str | None:
    out = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], capture_output=True,
                         text=True)
    return out.stdout.strip() or None if out.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    as_json = "--json" in args
    no_fetch = "--no-fetch" in args
    rest = [arg for arg in args if arg not in ("--json", "--no-fetch")]
    if len(rest) > 1 or any(arg.startswith("-") for arg in rest):
        print(__doc__, file=sys.stderr)
        return 2
    if rest:
        sha = resolve(rest[0]) or rest[0]
    else:
        branch = main_branch()
        if not no_fetch:
            subprocess.run(["git", "fetch", "-q", "origin", branch], capture_output=True)
        sha = resolve(f"origin/{branch}")
        if not sha:
            print(f"wt-main-ci: origin/{branch} not found", file=sys.stderr)
            return 2
    result = read(sha)
    if result is None:
        print("wt-main-ci: the forge cannot be reached from here (no `gh`, no GitHub remote or no credentials)",
              file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"MAIN-CI  {result['verdict']}  {sha[:7]}")
        for run in result["runs"]:
            state = run["conclusion"] or run["status"]
            note = "  (an earlier attempt failed)" if run["failed_before"] else ""
            print(f"RUN      {run['workflow']}  {state}  attempt {run['attempt']}  {run['url']}{note}")
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
