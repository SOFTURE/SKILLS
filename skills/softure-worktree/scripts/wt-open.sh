#!/usr/bin/env bash
# Create a change worktree next to the main repo and prepare it for work.
#
#   wt-open.sh <change-id> [--base <ref>]
#
# Worktree: ../<repo>-<change-id>, branch <change-id>, base = the main branch from
# context/workflow.json (--base <branch> for a change that depends on another, unmerged one).
#
# Then runs every command from `worktree.setup` inside it ({repo} expands to the main repo's
# folder name, e.g. "cp ../{repo}/.env .env", "npm ci"). Ends with `git status --short`:
# an empty result is the condition for exit 0 — a fresh worktree holds nobody's work.
set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
CFG() { python3 "$SCRIPTS/wt_config.py" "$@"; }

CHANGE_ID="${1:-}"
[ -n "$CHANGE_ID" ] || { echo "usage: wt-open.sh <change-id> [--base <ref>]" >&2; exit 2; }
shift
MAIN="$(CFG --root)"
BASE="$(CFG mainBranch)"
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

REPO="$(basename "$MAIN")"
WT="$(dirname "$MAIN")/$REPO-$CHANGE_ID"

if git -C "$MAIN" show-ref --verify --quiet "refs/heads/$CHANGE_ID"; then
  echo "branch $CHANGE_ID already exists — this is a resume, not an open (wt-status.sh)" >&2; exit 3
fi
if [ -e "$WT" ]; then
  echo "directory $WT already exists — find out whose it is before doing anything" >&2; exit 3
fi

git -C "$MAIN" worktree add -q -b "$CHANGE_ID" "$WT" "$BASE"
echo "worktree: $WT (branch $CHANGE_ID from $BASE @ $(git -C "$WT" rev-parse --short HEAD))"

while IFS= read -r STEP; do
  [ -n "$STEP" ] || continue
  CMD="${STEP//\{repo\}/$REPO}"
  echo "setup: $CMD"
  ( cd "$WT" && bash -c "$CMD" ) 2>&1 | tail -5
done < <(CFG worktree.setup)

DIRTY="$(git -C "$WT" status --short)"
if [ -n "$DIRTY" ]; then
  echo "worktree is not clean after setup:" >&2
  echo "$DIRTY" >&2
  echo "A fresh worktree holds nobody's work — a setup step (an installer, a generator) wrote tracked files. Restore them (git -C \"$WT\" restore -- <paths>) and fix the setup step." >&2
  exit 4
fi
echo "ready — worktree clean"
echo "WT=$WT"
