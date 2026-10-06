#!/usr/bin/env bash
# Run the project's full integration suite for the current HEAD, as configured in
# context/workflow.json (`integration.remote`, else `integration.local`).
#
#   wt-integration.sh <name> [--wait <minutes>] [--fresh]     # wait default 30
#
# Run it from inside the tree to test (cd <WT> && bash …/wt-integration.sh <change-id>).
#
# `integration.lookup` (optional) — a project command that prints the stored result for
# INTEGRATION_SHA (same stdout lines as below) and exits 0 green · 1 red · 3 no result.
# A stored green result for the very commit is reused: no new run (the same commit is the
# same code). `--fresh` skips the lookup — for a run that died or could not start.
#
# `integration.remote` — a project command that runs the suite elsewhere (CI) for the
# committed HEAD and waits for the result. It receives INTEGRATION_NAME, INTEGRATION_SHA and
# INTEGRATION_WAIT_MINUTES in the environment and must follow this contract:
#   exit 0 green · 1 red (or the run could not start) · 75 no result in time
#   stdout lines (optional, used by the READY report):
#     integration: green|red   counts: <passed>/<total>   run: <url>
#     flaky: <test>   red: <test>   new-red: <test>   (new-red = red and absent from the
#     latest result on the main branch; when the command cannot tell, it prints none and
#     every red counts as new)
# `integration.local` — runs in this tree; exit 0 green, anything else red (mapped to 1).
#
# Exit codes: 0 green · 1 red · 75 no result in time (retry later, never bypass) ·
#             78 not configured · 2 bad call.
set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
CFG() { python3 "$SCRIPTS/wt_config.py" "$@"; }

NAME="${1:-}"
[ -n "$NAME" ] || { sed -n '2,26p' "$0"; exit 2; }
shift
WAIT=30
FRESH=0
while [ $# -gt 0 ]; do
  case "$1" in
    --wait) WAIT="${2:-}"; shift 2 ;;
    --fresh) FRESH=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$WAIT" in ''|*[!0-9]*) echo "--wait: minutes as a number" >&2; exit 2 ;; esac
case "$NAME" in *[!a-zA-Z0-9._/-]*) echo "name: letters, digits, . _ - / only" >&2; exit 2 ;; esac

ROOT="$(git rev-parse --show-toplevel)"
SHA="$(git rev-parse HEAD)"
REMOTE="$(CFG integration.remote)"
LOCAL="$(CFG integration.local)"
LOOKUP="$(CFG integration.lookup)"

[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || echo "⚠ uncommitted changes are NOT part of the run — commit ${SHA:0:8} is what gets tested" >&2

if [ -n "$LOOKUP" ] && [ "$FRESH" = 0 ] && { [ -n "$REMOTE" ] || [ -n "$LOCAL" ]; }; then
  STORED="$( cd "$ROOT" && INTEGRATION_NAME="$NAME" INTEGRATION_SHA="$SHA" bash -c "$LOOKUP" 2>/dev/null )"
  if [ $? = 0 ]; then
    echo "▸ integration for ${SHA:0:8}: stored green result reused, no new run (integration.lookup)"
    printf '%s\n' "$STORED"
    echo "commit: $SHA"
    exit 0
  fi
fi

if [ -n "$REMOTE" ]; then
  echo "▸ integration (remote) for ${SHA:0:8} as '$NAME': $REMOTE"
  ( cd "$ROOT" && INTEGRATION_NAME="$NAME" INTEGRATION_SHA="$SHA" INTEGRATION_WAIT_MINUTES="$WAIT" bash -c "$REMOTE" )
  RC=$?
  echo "commit: $SHA"
  case "$RC" in 0|1|75) exit "$RC" ;; *) echo "✗ remote integration command exited $RC — treated as red" >&2; exit 1 ;; esac
fi

if [ -n "$LOCAL" ]; then
  echo "▸ integration (local) for ${SHA:0:8}: $LOCAL"
  if ( cd "$ROOT" && bash -c "$LOCAL" ); then
    echo "integration: green"; echo "commit: $SHA"; exit 0
  fi
  echo "integration: red"; echo "commit: $SHA"; exit 1
fi

echo "integration: not configured (context/workflow.json → integration.local / integration.remote)" >&2
exit 78
