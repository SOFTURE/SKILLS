#!/usr/bin/env bash
# Event stream for Monitor: one line per change of a watched item.
#
#   wm-watch.sh <ID>:<change-id> [<ID>:<change-id> …]
#
# Emits, per item, whenever it changes:
#   STAGE <ID> <status cell of the roadmap row on the main branch's working copy>
#   READY <ID>                                       (row says ready_to_merge)
#   SESSION <change-id> <kind>/<status>/<state>      (background or peer session)
#   GONE <change-id>                                 (session vanished before READY)
#
# Covers the failure paths too (silence is not success): a session that ends or disappears
# without READY shows up as SESSION …/done or GONE. Polls every 60 s.
set -uo pipefail
MAIN="$(git rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')"
ROADMAP="$MAIN/context/foundation/roadmap.md"
ST="$(mktemp -d)"; trap 'rm -rf "$ST"' EXIT   # plain files instead of associative arrays: works on bash 3.2
get() { cat "$ST/$1" 2>/dev/null || true; }

while true; do
  for pair in "$@"; do
    ID="${pair%%:*}"; CID="${pair#*:}"
    row=$(python3 - "$ROADMAP" "$ID" <<'PY'
import sys
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith(f"| **{sys.argv[2]}** |"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        print(cells[-1])
        break
PY
)
    if [ "$(get "s$ID")" != "$row" ]; then
      printf %s "$row" > "$ST/s$ID"; echo "STAGE $ID $row"
      case "$row" in *ready_to_merge*) echo "READY $ID";; esac
    fi
    sess=$(claude agents --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); d=d if isinstance(d,list) else d.get("agents",[])
m=[x for x in d if x.get("name")==sys.argv[1]]
m.sort(key=lambda x:x.get("startedAt",0))
print("%s/%s/%s" % (m[-1].get("kind"), m[-1].get("status"), m[-1].get("state","-")) if m else "none")' "$CID" 2>/dev/null || echo "none")
    if [ "$(get "p$CID")" != "$sess" ]; then
      # adopted sessions (opened by hand) are not named after the change → "none" from the start, stay quiet
      if [ "$sess" = "none" ]; then [ -n "$(get "p$CID")" ] && echo "GONE $CID"; else echo "SESSION $CID $sess"; fi
      printf %s "$sess" > "$ST/p$CID"
    fi
  done
  sleep 60
done
