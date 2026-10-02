#!/usr/bin/env python3
"""Mark one roadmap item on the main branch and commit ONLY that edit.

    wt-roadmap.py open  <change-id> [--note "…"] [--dry-run]
    wt-roadmap.py stage <change-id> "<stage>"      [--dry-run]
    wt-roadmap.py ready <change-id>                [--dry-run]
    (cloud sessions additionally: [--cloud] [--branch <branch>] — see below)

`open`  — status -> **in_progress** (research, since <today>; worktree `../<repo>-<id>`, branch `<id>`[; note])
`stage` — replaces only the stage inside the parentheses: research -> frame -> plan -> plan-review ->
          implement N/M -> impl-review -> integration -> archive (WORKFLOW.md §5)
`ready` — **in_progress** (<stage>, since …; <where>) -> **ready_to_merge** (since <today>; <where>)

Why a script instead of editing the file: sessions in worktrees used to edit the main tree's
roadmap without committing. Someone else's uncommitted rows then sat in `roadmap.md`, every
following session had to work around them, and merges conflicted. Here the commit is built
from HEAD plus one edit (hash-object -> update-index), so other sessions' uncommitted lines in
the working file never ride along; the same edit is applied to the working file too, so it does
not look like it reverts the commit.

Always works on the main worktree (first entry of `git worktree list`), whichever worktree
calls it. The main branch name comes from context/workflow.json (`mainBranch`).

**Cloud session** (`CLAUDE_CODE_REMOTE=true` or `--cloud`): there is no main tree on the main
branch and no other session in this container — the other sessions are other containers that
see only `origin`. The commit is then built directly on `origin/<main>` (fetch -> one edit ->
`commit-tree` on a temporary index) and **pushed at once**; the working tree and the current
branch stay untouched. A rejected push (someone pushed meanwhile) -> fetch and retry from the
fresh state. `--branch <name>` overrides the branch written into the row (default: current).
"""
from __future__ import annotations

import datetime as dt
import difflib
import os
import re
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wt_config import main_branch, main_root  # noqa: E402

ROADMAP = "context/foundation/roadmap.md"
COAUTHOR = "Co-Authored-By: Claude <noreply@anthropic.com>"

ROW_RE = re.compile(r"^(?P<head>\|.*\|\s*)(?P<status>[^|]*?)(?P<tail>\s*\|\s*)$")
ID_RE = re.compile(r"^\| \*\*([A-Z]+-\d+)\*\* \|")
STAGE_RE = re.compile(r"(in_progress\*{0,2} \()([^,;)]*)(, since )")
READY_RE = re.compile(r"(\*{0,2})in_progress(\*{0,2}) \([^,;)]*, since [0-9-]+; ")


def git(repo: str, *args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def find_row(lines: list[str], change_id: str) -> int:
    needle = f"| `{change_id}` |"
    hits = [i for i, line in enumerate(lines) if line.startswith("|") and needle in line]
    if len(hits) != 1:
        sys.exit(f"the roadmap table has {len(hits)} rows with `{change_id}` — expected exactly 1")
    return hits[0]


def set_row_status(line: str, new_status: str) -> str:
    match = ROW_RE.match(line.rstrip("\n"))
    if not match:
        sys.exit(f"cannot parse table row: {line[:120]}")
    return f"{match['head']}{new_status}{match['tail']}\n"


def row_status(line: str) -> str:
    match = ROW_RE.match(line.rstrip("\n"))
    return match["status"] if match else ""


def item_id(line: str, change_id: str) -> str:
    match = ID_RE.match(line)
    return match.group(1) if match else change_id


def edit(text: str, mode: str, change_id: str, arg: str | None, repo_name: str,
         cloud_branch: str | None = None) -> str:
    lines = text.splitlines(keepends=True)
    i = find_row(lines, change_id)
    today = dt.date.today().isoformat()
    body_status = None

    if mode == "open":
        current = row_status(lines[i])
        if any(word in current for word in ("in_progress", "ready_to_merge", "done")):
            sys.exit(f"item `{change_id}` already has status: {current.strip()[:100]}")
        note = f"; {arg}" if arg else ""
        if cloud_branch:
            where = f"cloud session, branch `{cloud_branch}` — do not take in another session"
        else:
            where = f"worktree `../{repo_name}-{change_id}`, branch `{change_id}`"
        lines[i] = set_row_status(lines[i], f"**in_progress** (research, since {today}; {where}{note})")
        body_status = f"- **Status:** in_progress (research, since {today}; {where}{note})\n"
    elif mode == "stage":
        new, count = STAGE_RE.subn(lambda m: f"{m[1]}{arg}{m[3]}", lines[i], count=1)
        if count != 1:
            sys.exit(f"row `{change_id}` has no `in_progress (<stage>, since …)` status — run `open` first")
        lines[i] = new
    else:  # ready
        new, count = READY_RE.subn(lambda m: f"{m[1]}ready_to_merge{m[2]} (since {today}; ", lines[i], count=1)
        if count != 1:
            sys.exit(f"row `{change_id}` is not `in_progress (<stage>, since …; …)` — nothing to mark ready")
        lines[i] = new

    # Item block (if present): the `- **Status:**` line under `- **Change ID:** `<id>``.
    cid = next((k for k, line in enumerate(lines) if line.strip() == f"- **Change ID:** `{change_id}`"), None)
    if cid is not None:
        end = next(
            (k for k in range(cid + 1, len(lines)) if lines[k].startswith(("#", "- **Change ID:**"))),
            len(lines),
        )
        sidx = next((k for k in range(cid + 1, end) if lines[k].startswith("- **Status:**")), None)
        if mode == "open":
            if sidx is None:
                lines.insert(cid + 1, body_status)
            else:
                lines[sidx] = body_status
        elif sidx is not None and mode == "stage":
            lines[sidx] = STAGE_RE.sub(lambda m: f"{m[1]}{arg}{m[3]}", lines[sidx], count=1)
        elif sidx is not None:
            lines[sidx] = READY_RE.sub(lambda m: f"{m[1]}ready_to_merge{m[2]} (since {today}; ", lines[sidx], count=1)

    out = "".join(lines)
    return re.sub(r"(?m)^updated: .*$", f"updated: {today}", out, count=1)


def commit_message(text: str, mode: str, change_id: str, arg: str | None, where: str) -> str:
    lines = text.splitlines(keepends=True)
    rid = item_id(lines[find_row(lines, change_id)], change_id)
    label = {"open": f"in_progress ({where})", "stage": arg or "", "ready": "ready_to_merge"}[mode]
    return f"docs(roadmap): {rid} {label}\n\n{COAUTHOR}"


def push_roadmap_commit(repo: str, sha: str, main: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Push `sha` to `origin/<main>` from a throwaway worktree, never from the session checkout.

    Pre-push hooks commonly compute the pushed files as `git diff HEAD @{push}` — from HEAD, not
    from the commit being sent. From the session checkout HEAD is a branch full of code, so the
    hook would run the whole test suite for a roadmap-only commit; from a detached HEAD
    `@{push}` does not resolve and hooks treat the push as "all files". Here HEAD = `sha`,
    upstream = `origin/<main>` and `push.default=upstream`, so the diff is the roadmap alone.
    Hooks stay enabled — nothing here uses `--no-verify`.
    """
    tmpdir = tempfile.mkdtemp(prefix="wt-roadmap-")
    branch = f"wt-roadmap-{os.getpid()}"
    try:
        git(repo, "worktree", "add", "-q", "-b", branch, tmpdir, sha)
        git(tmpdir, "branch", "-q", f"--set-upstream-to=origin/{main}")
        return subprocess.run(
            ["git", "-C", tmpdir, "-c", "push.default=upstream", "push", "-q", "origin", f"{branch}:{main}"],
            capture_output=True, text=True, env=env,
        )
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", tmpdir], capture_output=True)
        subprocess.run(["git", "-C", repo, "branch", "-D", branch], capture_output=True)


def run_cloud(mode: str, change_id: str, arg: str | None, branch: str | None, dry: bool) -> None:
    """Commit one roadmap edit directly on `origin/<main>` and push it — no working tree involved."""
    repo = git(".", "rev-parse", "--show-toplevel").strip()
    repo_name = os.path.basename(repo)
    main = main_branch(repo)
    if branch is None:
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    env = dict(os.environ)
    push = None
    for attempt in range(6):
        git(repo, "fetch", "-q", "origin", main)
        base = git(repo, "rev-parse", f"origin/{main}").strip()
        old = git(repo, "show", f"{base}:{ROADMAP}")
        new = edit(old, mode, change_id, arg, repo_name, cloud_branch=branch if mode == "open" else None)
        if dry:
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"origin/{main}", "commit"))
            return
        msg = commit_message(old, mode, change_id, arg, f"cloud session, branch {branch}")
        session = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "")
        if session.startswith("cse_"):
            msg += f"\nClaude-Session: https://claude.ai/code/session_{session[4:]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            index_env = {**env, "GIT_INDEX_FILE": os.path.join(tmpdir, "index")}
            blob_path = os.path.join(tmpdir, "roadmap.md")
            with open(blob_path, "w", encoding="utf-8") as fh:
                fh.write(new)
            git(repo, "read-tree", base, env=index_env)
            blob = git(repo, "hash-object", "-w", blob_path, env=index_env).strip()
            git(repo, "update-index", "--cacheinfo", f"100644,{blob},{ROADMAP}", env=index_env)
            tree = git(repo, "write-tree", env=index_env).strip()
            sha = git(repo, "commit-tree", tree, "-p", base, "-m", msg, env=index_env).strip()
        push = push_roadmap_commit(repo, sha, main, env)
        if push.returncode == 0:
            # Move the local main branch forward only when this session is not standing on it.
            if git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() != main:
                subprocess.run(["git", "-C", repo, "update-ref", f"refs/heads/{main}", sha], capture_output=True)
            subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", main], capture_output=True)
            print(f"{sha[:8]} {msg.splitlines()[0]} -> origin/{main}")
            return
        time.sleep(2 + attempt * 2)
    sys.exit(f"push to origin/{main} failed after 6 attempts: {push.stderr.strip()[:300] if push else ''}")


def run_local(mode: str, change_id: str, arg: str | None, dry: bool) -> None:
    main_wt = main_root()
    repo_name = os.path.basename(main_wt)
    main = main_branch(main_wt)
    current = git(main_wt, "symbolic-ref", "--short", "HEAD").strip()
    if current != main:
        sys.exit(f"the main tree is on `{current}`, not on `{main}` — not committing")

    work_path = os.path.join(main_wt, ROADMAP)
    if dry:
        head_text = git(main_wt, "show", f"HEAD:{ROADMAP}")
        new_head = edit(head_text, mode, change_id, arg, repo_name)
        sys.stdout.writelines(difflib.unified_diff(head_text.splitlines(True), new_head.splitlines(True), "HEAD", "commit"))
        return

    # Several sessions commit stages on the main branch at once. Every attempt re-reads HEAD,
    # checks right before committing that it did not move, and every failure removes its own
    # index entry (`reset -- ROADMAP`) before retrying or exiting — otherwise a lost race leaves
    # a blob staged on the main tree and every later call (of every session) refuses.
    for attempt in range(8):
        staged = subprocess.run(["git", "-C", main_wt, "diff", "--cached", "--quiet"])
        if staged.returncode != 0:
            if attempt < 7:
                time.sleep(3)
                continue
            sys.exit(f"the index on `{main}` holds someone else's staged changes — not committing under them; retry shortly")

        head_sha = git(main_wt, "rev-parse", "HEAD").strip()
        head_text = git(main_wt, "show", f"{head_sha}:{ROADMAP}")
        new_head = edit(head_text, mode, change_id, arg, repo_name)
        msg = commit_message(head_text, mode, change_id, arg, "separate worktree")
        with open(work_path, encoding="utf-8") as fh:
            work_text = fh.read()
        new_work = new_head if work_text == head_text else edit(work_text, mode, change_id, arg, repo_name)

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(new_head)
        blob = git(main_wt, "hash-object", "-w", tmp.name).strip()
        os.unlink(tmp.name)

        try:
            git(main_wt, "update-index", "--cacheinfo", f"100644,{blob},{ROADMAP}")
            if git(main_wt, "rev-parse", "HEAD").strip() != head_sha:
                raise subprocess.CalledProcessError(1, "rev-parse", stderr="HEAD moved")
            git(main_wt, "commit", "-q", "-m", msg)
            break
        except subprocess.CalledProcessError as exc:
            subprocess.run(["git", "-C", main_wt, "reset", "-q", "--", ROADMAP])
            if attempt < 7:
                time.sleep(2)
                continue
            sys.exit(f"commit failed (index restored): {exc.stderr}")
    with open(work_path, "w", encoding="utf-8") as fh:
        fh.write(new_work)
    sha = git(main_wt, "rev-parse", "--short", "HEAD").strip()
    print(f"{sha} {msg.splitlines()[0]}")
    if work_text != head_text:
        print(f"note: roadmap.md on `{main}` holds someone else's uncommitted edits — left untouched, outside the commit")


def main() -> None:
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    cloud = "--cloud" in argv or os.environ.get("CLAUDE_CODE_REMOTE") == "true"
    args = [a for a in argv if a not in ("--dry-run", "--cloud")]
    note = branch = None
    if "--note" in args:
        k = args.index("--note")
        note = args[k + 1]
        del args[k:k + 2]
    if "--branch" in args:
        k = args.index("--branch")
        branch = args[k + 1]
        del args[k:k + 2]
    valid = (
        len(args) >= 2 and args[0] in ("open", "stage", "ready")
        and (args[0] != "stage" or len(args) == 3)
        and (args[0] == "stage" or len(args) == 2)
    )
    if not valid:
        sys.exit(__doc__)
    mode, change_id = args[0], args[1]
    arg = note if mode == "open" else (args[2] if mode == "stage" else None)
    if cloud:
        run_cloud(mode, change_id, arg, branch, dry)
    else:
        run_local(mode, change_id, arg, dry)


if __name__ == "__main__":
    main()
