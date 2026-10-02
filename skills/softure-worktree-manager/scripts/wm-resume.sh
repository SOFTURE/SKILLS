#!/usr/bin/env bash
# Read-only: what a freshly started coordinator must do with changes already in flight.
#
#   wm-resume.sh
#
# For every roadmap row in flight (`in_progress` or `ready_to_merge`) prints one line:
#
#   RESUME <ID> <change-id> action=<ACTION> stage="…" wt=yes|no branch=yes|no|merged
#          session=<short-id>|none proc=<status/state/pid|nopid> coord=<name>|? coord_alive=yes|no|?
#          last="<hint from the worker's last assistant message>"
#
# ACTION (the skill's M0.1 table says what to do with each):
#   MERGE     row says ready_to_merge → M5 now
#   ADOPT     worker process alive and working → take over its merge
#   NUDGE     worker process alive but blocked (usage limit, sleep, network) → SendMessage "continue"
#   RELAUNCH  no live worker process, worktree/branch still there → claude stop <id>; wm-launch.sh
#   FIX-ROW   the main branch already has the merge commit, row not updated → fix the row
#   REPORT    in flight on the roadmap but no branch and no worktree → tell the owner
#
# Why: the owner clears the coordinator session and runs the skill again; workers keep running
# as background processes, and a fresh coordinator must merge them and wake the stuck ones
# instead of treating them as someone else's.
#
# WM_AGENTS_JSON overrides the session list — only for testing the NUDGE/RELAUNCH paths
# without touching live workers.
set -uo pipefail
MAIN="$(git rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')"
cd "$MAIN"
WT_SCRIPTS="$(cd "$(dirname "$0")/../../softure-worktree/scripts" 2>/dev/null && pwd || echo "$MAIN/.claude/skills/softure-worktree/scripts")"
MAIN_BRANCH="$(python3 "$WT_SCRIPTS/wt_config.py" mainBranch)"
AGENTS_JSON="${WM_AGENTS_JSON:-$(claude agents --json 2>/dev/null || echo '[]')}"

python3 - "$MAIN" "$AGENTS_JSON" "$MAIN_BRANCH" <<'PY'
import json, os, re, subprocess, sys

main, agents_raw, main_branch = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    agents = json.loads(agents_raw)
    agents = agents if isinstance(agents, list) else agents.get("agents", [])
except ValueError:
    agents = []
slug = re.sub(r"[/_.]", "-", main)
proj = os.path.expanduser(f"~/.claude/projects/{slug}")

def git(*a):
    return subprocess.run(["git", "-C", main, *a], capture_output=True, text=True)

rows = []
for line in open(os.path.join(main, "context/foundation/roadmap.md"), encoding="utf-8"):
    m = re.match(r"\| \*\*([A-Z]+-\d+)\*\* \| `([^`]+)` \|", line)
    if not m:
        continue
    status = [c.strip() for c in line.strip().strip("|").split("|")][-1]
    if "ready_to_merge" in status:
        rows.append((m.group(1), m.group(2), "ready_to_merge"))
    elif "in_progress" in status:
        stage = re.search(r"\(([^,;)]+)", status)
        rows.append((m.group(1), m.group(2), stage.group(1).strip() if stage else status))

wts = git("worktree", "list", "--porcelain").stdout
live_names = {a.get("name") for a in agents if a.get("pid")}
# "Merged" = the main branch carries the merge commit ("Merge <change-id> (<ID>): …").
# Not "branch is an ancestor of main": a freshly opened branch with no commits is one too.
merge_subjects = git("log", "--first-parent", "--merges", "--format=%s", main_branch).stdout.splitlines()

def transcript_lines(sid):
    f = os.path.join(proj, f"{sid}.jsonl")
    if not os.path.exists(f):
        return []
    out = []
    for l in open(f, encoding="utf-8"):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out

def texts(d):
    c = d.get("message", {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""

if not rows:
    print("RESUME none — no roadmap row in flight")

for rid, cid, stage in rows:
    wt = "yes" if f"branch refs/heads/{cid}\n" in wts else "no"
    has_branch = git("rev-parse", "--verify", "-q", f"refs/heads/{cid}").returncode == 0
    merged = any(s.startswith((f"Merge {cid} ", f"Merge {cid}:", f"Merge branch '{cid}' into {main_branch}"))
                 for s in merge_subjects)
    branch = "merged" if merged else ("yes" if has_branch else "no")

    mine = sorted((a for a in agents if a.get("name") == cid), key=lambda a: a.get("startedAt", 0))
    a = mine[-1] if mine else None
    session = a.get("id", "?") if a else "none"
    proc = (f"{a.get('status')}/{a.get('state')}/" + ("pid" if a.get("pid") else "nopid")) if a else "-"

    coord, last = "?", ""
    if a and a.get("sessionId"):
        tl = transcript_lines(a["sessionId"])
        for d in tl:
            if d.get("type") == "user":
                m = re.search(r"coordinator-session (\S+)", texts(d))
                if m:
                    coord = m.group(1)
                    break
        for d in reversed(tl):
            if d.get("type") == "assistant" and texts(d).strip():
                last = texts(d).strip().replace("\n", " ")[:120]
                break
    coord_alive = "?" if coord == "?" else ("yes" if coord in live_names else "no")

    stuck = re.search(r"session limit|went to sleep|API Error|Can't reach|rate limit", last, re.I)
    if stage == "ready_to_merge":
        action = "MERGE"
    elif merged:
        action = "FIX-ROW"
    elif not has_branch and wt == "no":
        action = "REPORT"
    elif a and a.get("pid") and (a.get("state") in ("working",) or a.get("status") == "busy") and not stuck:
        action = "ADOPT"
    elif a and a.get("pid"):
        action = "NUDGE"
    else:
        action = "RELAUNCH"

    print(f'RESUME {rid} {cid} action={action} stage="{stage}" wt={wt} branch={branch} '
          f'session={session} proc={proc} coord={coord} coord_alive={coord_alive} last="{last}"')
PY
