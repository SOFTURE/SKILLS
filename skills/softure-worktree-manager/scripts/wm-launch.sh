#!/usr/bin/env bash
# Start one /softure-worktree session in the background.
#
#   wm-launch.sh <roadmap-id> <change-id> [coordinator-name]
#
# Prints: SESSION <change-id> <short-id> <session-uuid>
# Exit:   3 a live session with this name already exists · 4 the session did not register
#
# Why this shape:
# - `claude --bg "<prompt>"` starts a full session that SUBMITS the prompt by itself —
#   no keystrokes, no OS permissions.
# - `--bg` ignores `--session-id`, so the id is read back from `claude agents --json` by name.
# - Background sessions also appear in IDE session panels. Some IDE extensions cannot
#   reattach PTY-backed background sessions and show an exit error when opened as a tab;
#   the worker keeps running regardless. Live view: `claude attach <short-id>`.
set -euo pipefail

ID="${1:?roadmap id}"
CID="${2:?change id}"
COORD="${3:-coordinator}"
MAIN="$(git rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')"
cd "$MAIN"

if claude agents --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); d=d if isinstance(d,list) else d.get("agents",[])
sys.exit(0 if any(x.get("name")==sys.argv[1] and x.get("state")!="done" for x in d) else 1)' "$CID"; then
  echo "ALREADY-RUNNING $CID" >&2; exit 3
fi

# The literal "coordinator-session <name>" is parsed back by wm-resume.sh — keep it.
PROMPT="/softure-worktree $ID

Launched by coordinator-session $COORD (/softure-worktree-manager). The coordinator merges into the main branch: carry the change to READY (roadmap row \`ready_to_merge\` via wt-roadmap.py ready) and stop. Do not merge, do not remove the worktree. Before archiving, run the full integration suite (wt-integration.sh <change-id>, A3.8) — fix every new red and put the result into the READY report. Do not ask the owner — decide (Prime Directive in /softure-worktree); a question the material cannot settle goes to $COORD via SendMessage. A deploy is a release the owner publishes: no tags, no releases, no edits of release workflows. Pre-release steps (migration, production secret, scheduled job, one-off command) go into the roadmap section \`## Before the next release\` and into the READY report."

claude --bg -n "$CID" "$PROMPT" >/dev/null

SID=""
for _ in $(seq 1 20); do
  SID=$(claude agents --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); d=d if isinstance(d,list) else d.get("agents",[])
m=[x for x in d if x.get("name")==sys.argv[1] and x.get("kind")=="background"]
m.sort(key=lambda x:x.get("startedAt",0))
print((m[-1].get("id","") + " " + m[-1]["sessionId"]) if m else "")' "$CID")
  [ -n "$SID" ] && break
  sleep 1
done
[ -n "$SID" ] || { echo "NO-SESSION $CID — claude --bg did not register" >&2; exit 4; }

set -- $SID
echo "SESSION $CID $1 $2"
