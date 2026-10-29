#!/usr/bin/env python3
"""Mark one roadmap item on the main branch and commit ONLY that edit.

    wt-roadmap.py open  <change-id> [--note "…"] [--dry-run]
    wt-roadmap.py stage <change-id> "<stage>"      [--dry-run]
    wt-roadmap.py ready <change-id>                [--dry-run]
    wt-roadmap.py done  <change-id>                [--dry-run]
    wt-roadmap.py done_code <change-id> --waiting "<what>" [--dry-run]
    (cloud sessions additionally: [--cloud] [--branch <branch>] — see below)

`open`  — status -> **in_progress** (research, since <today>; worktree `../<repo>-<id>`, branch `<id>`[; note])
`stage` — replaces only the stage inside the parentheses: research -> frame -> plan -> plan-review ->
          implement N/M -> impl-review -> integration -> archive (WORKFLOW.md §5)
`ready` — **in_progress** (<stage>, since …; <where>) -> **ready_to_merge** (since <today>; <where>)
`done`  — run right after the change's merge: the row and the item block -> `done` (or
          `done_code (<today>; waiting: <what>)`), plus the `## Done`, `## Owner decisions and checks`
          and `## Before the next release` lines. All of it comes from the `## Roadmap handoff`
          section that `softure-archive --handoff` wrote into the archived change.md
          (`context/archive/<created>-<id>/change.md` on the main branch). `done` follows the
          handoff's status; `done_code --waiting "…"` forces `done_code` with that text. Lines
          already present are not added twice, so a re-run is safe.

Branches never edit roadmap.md (unless `worktree.cloudState` is "branch"): the roadmap state lives
on the main branch, written only by this script, so merging the main branch into a change branch
never conflicts on it.

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

With `worktree.cloudState: "branch"` in context/workflow.json, a cloud session instead commits
the edit **on its own branch** (the checkout) and pushes nothing: the branch carries the state
and `<main>` changes only through the merge. Every merge of `<main>` into such a branch then
conflicts on the roadmap, so prefer the default and give the project's pre-push hook a cheap path
for pushes that touch only `context/` (WORKFLOW.md §2, CI minutes). Use "branch" only when a
coordinator assigns the items (so nobody needs to see a claim on `<main>`) and a push to `<main>`
stays expensive or contended by many sessions.
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
from wt_config import load_config, main_branch, main_root  # noqa: E402

ROADMAP = "context/foundation/roadmap.md"
COAUTHOR = "Co-Authored-By: Claude <noreply@anthropic.com>"

ROW_RE = re.compile(r"^(?P<head>\|.*\|\s*)(?P<status>[^|]*?)(?P<tail>\s*\|\s*)$")
ID_RE = re.compile(r"^\| \*\*([A-Z]+-\d+)\*\* \|")
STAGE_RE = re.compile(r"(in_progress\*{0,2} \()([^,;)]*)(, since )")
READY_RE = re.compile(r"(\*{0,2})in_progress(\*{0,2}) \([^,;)]*, since [0-9-]+; ")
HANDOFF_RE = re.compile(r"^- \*\*(?P<key>[^*]+):\*\* ?(?P<value>.*)$")
ARCHIVED_RE = re.compile(r"^Archived [0-9-]+: (?P<outcome>.+?)\.?$")
DONE_CODE_RE = re.compile(r"^done_code \((?:[0-9-]+; )?waiting: (?P<waiting>.+)\)$")


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


def read_handoff(repo: str, rev: str, change_id: str) -> dict:
    """Read the archived change folder of `change_id` at `rev` and its `## Roadmap handoff` section.

    Returns {"archive", "status", "waiting", "outcome", "owner": [...], "release": [...]}. Without a
    handoff section (an archive written before it existed) the outcome falls back to the
    `Archived <date>: <outcome>.` line under `## Notes`, the status to `done`.
    """
    names = git(repo, "ls-tree", "-d", "--name-only", rev, "context/archive/").splitlines()
    pattern = re.compile(rf"^context/archive/[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}-{re.escape(change_id)}$")
    hits = [name for name in names if pattern.match(name)]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} archive folders for `{change_id}` on {rev} — expected exactly 1 "
                 f"(run `done` only after the change's merge, which carries its archive commit)")
    text = git(repo, "show", f"{rev}:{hits[0]}/change.md")
    handoff = {"archive": hits[0][len("context/"):] + "/", "status": "done", "waiting": None,
               "outcome": None, "owner": [], "release": [], "found": False}
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "Notes" and handoff["outcome"] is None:
            archived = ARCHIVED_RE.match(line.strip())
            if archived:
                handoff["outcome"] = archived["outcome"]
        if section != "Roadmap handoff":
            continue
        match = HANDOFF_RE.match(line.strip())
        if not match:
            continue
        handoff["found"] = True
        key, value = match["key"].strip().lower(), match["value"].strip()
        if key == "status":
            waiting = DONE_CODE_RE.match(value)
            handoff["status"] = "done_code" if waiting else "done"
            handoff["waiting"] = waiting["waiting"] if waiting else None
        elif key == "done":
            handoff["outcome"] = value
        elif key == "owner check":
            handoff["owner"].append(value)
        elif key == "before the next release":
            handoff["release"].append(value)
    return handoff


def append_to_section(lines: list[str], heading: str, entry: str, before: tuple[str, ...]) -> None:
    """Append `entry` at the end of `## <heading>`; create the section in front of the first of `before`
    that exists (else at the end of the file). An entry already present is not added again."""
    if any(line.rstrip("\n") == entry for line in lines):
        return
    start = next((k for k, line in enumerate(lines) if line.rstrip() == f"## {heading}"), None)
    if start is None:
        at = next((k for k, line in enumerate(lines) if line.rstrip() in {f"## {b}" for b in before}), None)
        block = [f"## {heading}\n", f"{entry}\n", "\n"]
        if at is None:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            if lines and lines[-1].strip():
                block.insert(0, "\n")
            lines.extend(block[:-1])
        else:
            lines[at:at] = block
        return
    end = next((k for k in range(start + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    if end == len(lines) and lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.insert(end, f"{entry}\n")


def done_status(handoff: dict, mode: str, arg: str | None, today: str) -> str:
    if mode == "done_code" or handoff["status"] == "done_code":
        return f"done_code ({today}; waiting: {arg or handoff['waiting']})"
    return "done"


def unchanged(old: str, new: str, target: str) -> bool:
    """A re-run (e.g. `done` after a retry) whose edit is already in place commits nothing."""
    if re.sub(r"(?m)^updated: .*$", "", old) != re.sub(r"(?m)^updated: .*$", "", new):
        return False
    print(f"roadmap on {target} already up to date — nothing to commit")
    return True


def edit(text: str, mode: str, change_id: str, arg: str | None, repo_name: str,
         cloud_branch: str | None = None, handoff: dict | None = None) -> str:
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
    elif mode in ("done", "done_code"):
        status = done_status(handoff, mode, arg, today)
        current = row_status(lines[i]).strip()
        if current.startswith(("done", "**done")):
            status = current.replace("**", "")  # a re-run keeps the recorded date and text
        lines[i] = set_row_status(lines[i], status)
        body_status = f"- **Status:** {status}\n"
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
        if mode in ("open", "done", "done_code"):
            if sidx is None:
                lines.insert(cid + 1, body_status)
            else:
                lines[sidx] = body_status
        elif sidx is not None and mode == "stage":
            lines[sidx] = STAGE_RE.sub(lambda m: f"{m[1]}{arg}{m[3]}", lines[sidx], count=1)
        elif sidx is not None:
            lines[sidx] = READY_RE.sub(lambda m: f"{m[1]}ready_to_merge{m[2]} (since {today}; ", lines[sidx], count=1)

    if mode in ("done", "done_code"):
        rid = item_id(lines[i], change_id)
        outcome = handoff["outcome"] or "delivered"
        for check in handoff["owner"]:
            append_to_section(lines, "Owner decisions and checks",
                              f"- [ ] **{rid}**: {check}. {handoff['archive']}plan.md", ("Done", "Decisions (auto)"))
        for step in handoff["release"]:
            append_to_section(lines, "Before the next release", f"- [ ] {step} (**{rid}**)",
                              ("Owner decisions and checks", "Done", "Decisions (auto)"))
        append_to_section(lines, "Done", f"- **{rid}** `{change_id}`: {outcome}; archived in `{handoff['archive']}`",
                          ("Decisions (auto)",))

    out = "".join(lines)
    return re.sub(r"(?m)^updated: .*$", f"updated: {today}", out, count=1)


def commit_message(text: str, mode: str, change_id: str, arg: str | None, where: str,
                   new_text: str | None = None) -> str:
    lines = text.splitlines(keepends=True)
    rid = item_id(lines[find_row(lines, change_id)], change_id)
    label = {"open": f"in_progress ({where})", "stage": arg or "", "ready": "ready_to_merge",
             "done": "done", "done_code": "done_code"}[mode]
    if mode in ("done", "done_code") and new_text is not None:
        new_lines = new_text.splitlines(keepends=True)
        label = row_status(new_lines[find_row(new_lines, change_id)]).strip().split(" ")[0]
    return f"docs(roadmap): {rid} {label}\n\n{COAUTHOR}"


def load_handoff(repo: str, rev: str, mode: str, change_id: str) -> dict | None:
    if mode not in ("done", "done_code"):
        return None
    handoff = read_handoff(repo, rev, change_id)
    if not handoff["found"]:
        print(f"note: {handoff['archive']}change.md has no `## Roadmap handoff` — status `done` unless forced, "
              f"no owner-check or release lines", file=sys.stderr)
    return handoff


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
        handoff = load_handoff(repo, base, mode, change_id)
        new = edit(old, mode, change_id, arg, repo_name, cloud_branch=branch if mode == "open" else None,
                   handoff=handoff)
        if dry:
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"origin/{main}", "commit"))
            return
        if unchanged(old, new, f"origin/{main}"):
            return
        msg = commit_message(old, mode, change_id, arg, f"cloud session, branch {branch}", new)
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


def run_cloud_branch(mode: str, change_id: str, arg: str | None, branch: str | None, dry: bool) -> None:
    """Commit one roadmap edit on the session's own branch (the checkout); push nothing."""
    repo = git(".", "rev-parse", "--show-toplevel").strip()
    repo_name = os.path.basename(repo)
    current = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if current == main_branch(repo):
        sys.exit(f"cloudState=branch: the session stands on `{current}` — switch to the change branch first")
    if branch is None:
        branch = current
    work_path = os.path.join(repo, ROADMAP)
    with open(work_path, encoding="utf-8") as fh:
        old = fh.read()
    handoff = load_handoff(repo, "HEAD", mode, change_id)
    new = edit(old, mode, change_id, arg, repo_name, cloud_branch=branch if mode == "open" else None,
               handoff=handoff)
    if dry:
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), current, "commit"))
        return
    if unchanged(old, new, current):
        return
    with open(work_path, "w", encoding="utf-8") as fh:
        fh.write(new)
    msg = commit_message(old, mode, change_id, arg, f"cloud session, branch {branch}", new)
    session = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "")
    if session.startswith("cse_"):
        msg += f"\nClaude-Session: https://claude.ai/code/session_{session[4:]}"
    git(repo, "commit", "-q", "-m", msg, "--", ROADMAP)
    sha = git(repo, "rev-parse", "--short", "HEAD").strip()
    print(f"{sha} {msg.splitlines()[0]} -> {current} (not pushed; the branch carries the state)")


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
        new_head = edit(head_text, mode, change_id, arg, repo_name, handoff=load_handoff(main_wt, "HEAD", mode, change_id))
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
        handoff = load_handoff(main_wt, head_sha, mode, change_id)
        new_head = edit(head_text, mode, change_id, arg, repo_name, handoff=handoff)
        if unchanged(head_text, new_head, main):
            return
        msg = commit_message(head_text, mode, change_id, arg, "separate worktree", new_head)
        with open(work_path, encoding="utf-8") as fh:
            work_text = fh.read()
        new_work = new_head if work_text == head_text else edit(work_text, mode, change_id, arg, repo_name,
                                                                handoff=handoff)

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
    note = branch = waiting = None
    if "--waiting" in args:
        k = args.index("--waiting")
        waiting = args[k + 1]
        del args[k:k + 2]
    if "--note" in args:
        k = args.index("--note")
        note = args[k + 1]
        del args[k:k + 2]
    if "--branch" in args:
        k = args.index("--branch")
        branch = args[k + 1]
        del args[k:k + 2]
    valid = (
        len(args) >= 2 and args[0] in ("open", "stage", "ready", "done", "done_code")
        and (args[0] != "stage" or len(args) == 3)
        and (args[0] == "stage" or len(args) == 2)
        and (args[0] != "done_code" or bool(waiting))
    )
    if not valid:
        sys.exit(__doc__)
    mode, change_id = args[0], args[1]
    arg = {"open": note, "stage": args[2] if mode == "stage" else None, "done_code": waiting}.get(mode)
    if cloud and (load_config().get("worktree") or {}).get("cloudState") == "branch":
        run_cloud_branch(mode, change_id, arg, branch, dry)
    elif cloud:
        run_cloud(mode, change_id, arg, branch, dry)
    else:
        run_local(mode, change_id, arg, dry)


if __name__ == "__main__":
    main()
