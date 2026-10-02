#!/usr/bin/env bash
# State of every change worktree at once — for picking an item and for numbering.
#
#   wt-status.sh            # table + next free numbers
#   wt-status.sh --files    # also the files each branch changed against the main branch
#
# Why: parallel sessions collide on three things that only show at merge time — the same
# files, lesson numbers and migration numbers. This prints all three before anyone starts.
set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
CFG() { python3 "$SCRIPTS/wt_config.py" "$@"; }

SHOW_FILES=0
[ "${1:-}" = "--files" ] && SHOW_FILES=1

MAIN="$(CFG --root)"
MAIN_BRANCH="$(CFG mainBranch)"
MIG_DIR="$(CFG migrations.dir)"
MIG_PATTERN="$(CFG migrations.pattern)"
[ -n "$MIG_PATTERN" ] || MIG_PATTERN='^[0-9]+_.*'
LESSONS="context/foundation/lessons.md"

max_lesson() { grep -oE '^#+ *L-[0-9]+' "$1" 2>/dev/null | grep -oE '[0-9]+' | sort -n | tail -1; }
max_migration() {
  [ -n "$MIG_DIR" ] && [ -d "$1/$MIG_DIR" ] || return 0
  ls "$1/$MIG_DIR" 2>/dev/null | grep -E "$MIG_PATTERN" | grep -oE '^[0-9]+' | sort -n | tail -1
}

L_MAX="$(max_lesson "$MAIN/$LESSONS")"; L_MAX=${L_MAX:-0}
M_MAX="$(max_migration "$MAIN")"; M_MAX=${M_MAX:-0}
L_WHO="$MAIN_BRANCH"; M_WHO="$MAIN_BRANCH"

printf '%-44s %-32s %-9s %-16s %-6s %s\n' WORKTREE BRANCH "+/-main" "change status" lesson migrations
git worktree list --porcelain | awk '/^worktree /{w=substr($0,10)} /^branch /{sub("refs/heads/","",$2); print w"\t"$2} /^detached/{print w"\t(detached)"}' |
while IFS=$'\t' read -r WT BR; do
  [ "$WT" = "$MAIN" ] && continue
  if [ "$BR" = "(detached)" ]; then
    printf '%-44s %-32s %s\n' "$(basename "$WT")" "$BR" "baseline/helper — not a change"
    continue
  fi
  AB="$(git -C "$MAIN" rev-list --left-right --count "$MAIN_BRANCH...$BR" 2>/dev/null | awk '{print "+"$2"/-"$1}')"
  STATUS="$(sed -n 's/^status: *//p' "$WT/context/changes/$BR/change.md" 2>/dev/null | head -1)"
  [ -z "$STATUS" ] && [ -d "$WT/context/archive" ] && ls -d "$WT"/context/archive/*-"$BR" >/dev/null 2>&1 && STATUS="archived"
  L="$(max_lesson "$WT/$LESSONS")"
  MIG="—"
  if [ -n "$MIG_DIR" ]; then
    MIG="$(git -C "$MAIN" diff --name-only --diff-filter=A "$MAIN_BRANCH...$BR" -- "$MIG_DIR" 2>/dev/null \
      | xargs -n1 basename 2>/dev/null | grep -E "$MIG_PATTERN" | tr '\n' ' ')"
    MIG="${MIG:-—}"
  fi
  printf '%-44s %-32s %-9s %-16s %-6s %s\n' "$(basename "$WT")" "$BR" "$AB" "${STATUS:-?}" "L-${L:-?}" "$MIG"
  if [ "$SHOW_FILES" = 1 ]; then
    git -C "$MAIN" diff --name-only "$MAIN_BRANCH...$BR" 2>/dev/null | grep -v '^context/' | sed 's/^/      /'
  fi
done

# Next free numbers: maximum over the main branch and every worktree, plus one.
while IFS= read -r WT; do
  L="$(max_lesson "$WT/$LESSONS")"; [ -n "$L" ] && [ "$((10#$L))" -gt "$((10#$L_MAX))" ] && L_MAX=$L && L_WHO="$(basename "$WT")"
  M="$(max_migration "$WT")"; [ -n "$M" ] && [ "$((10#$M))" -gt "$((10#$M_MAX))" ] && M_MAX=$M && M_WHO="$(basename "$WT")"
done < <(git worktree list --porcelain | awk '/^worktree /{print substr($0,10)}')
echo
printf 'highest lesson:    L-%03d (%s)  -> next free: L-%03d\n' "$((10#$L_MAX))" "$L_WHO" "$((10#$L_MAX + 1))"
if [ -n "$MIG_DIR" ]; then
  echo "highest migration: $M_MAX ($M_WHO)  -> whoever merges second renumbers theirs"
else
  echo "migrations: not configured (context/workflow.json → migrations)"
fi
echo "integration: wt-integration.sh <name> — the full suite as configured in context/workflow.json"
