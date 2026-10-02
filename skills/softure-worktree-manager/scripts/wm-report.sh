#!/usr/bin/env bash
# Print the last assistant text message of a session — for a worker, its READY report.
#
#   wm-report.sh <change-id | session-uuid>
#
# A change-id is resolved through `claude agents --json` (background sessions launched by
# wm-launch.sh are named after the change). Pasted/adopted sessions have other names — pass
# their sessionId (ListAgents / `claude agents --json`). Reads the transcript
# ~/.claude/projects/<repo-slug>/<sessionId>.jsonl, so it works for background and
# interactive sessions alike, and after they stop.
set -euo pipefail
KEY="${1:?change-id or session uuid}"
MAIN="$(git rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')"
SLUG="$(printf %s "$MAIN" | sed 's#[/_.]#-#g')"

if [[ "$KEY" =~ ^[0-9a-f]{8}-[0-9a-f]{4}- ]]; then
  SID="$KEY"
else
  SID=$(claude agents --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); d=d if isinstance(d,list) else d.get("agents",[])
m=sorted((x for x in d if x.get("name")==sys.argv[1]), key=lambda x:x.get("startedAt",0))
print(m[-1]["sessionId"] if m else "")' "$KEY")
fi
[ -n "$SID" ] || { echo "NO-SESSION $KEY" >&2; exit 4; }

F="$HOME/.claude/projects/$SLUG/$SID.jsonl"
[ -f "$F" ] || { echo "NO-TRANSCRIPT $F" >&2; exit 5; }

python3 - "$F" <<'PY'
import json, sys
last = ""
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        d = json.loads(line)
    except ValueError:
        continue
    if d.get("type") != "assistant":
        continue
    c = d.get("message", {}).get("content")
    t = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text") if isinstance(c, list) else str(c or "")
    if t.strip():
        last = t
print(last)
PY
