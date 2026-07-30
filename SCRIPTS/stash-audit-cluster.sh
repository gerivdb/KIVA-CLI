#!/bin/bash
# stash-audit-cluster.sh — Audit stash cross-repos metacluster
# SOT: gerivdb/REPO-STANDARDS/scripts/stash-audit-cluster.sh
# Usage: bash scripts/stash-audit-cluster.sh [--zombies-only] [--json]
# Version: 1.0.0 — 2026-06-29

set -euo pipefail

REPOS_FILE="${HOME}/.ecos/metacluster-repos.txt"
NOW=$(date +%s)
TOTAL=0
FRESH=0
STALE=0
ZOMBIE=0
ZOMBIES_ONLY=false
JSON_OUTPUT=false
REPORT_DATE=$(date '+%Y-%m-%dT%H:%M')

# Args
for arg in "$@"; do
  case $arg in
    --zombies-only) ZOMBIES_ONLY=true ;;
    --json) JSON_OUTPUT=true ;;
  esac
done

# Fallback si pas de fichier metacluster
if [ ! -f "$REPOS_FILE" ]; then
  echo "⚠️  $REPOS_FILE introuvable — audit repo courant uniquement"
  REPOS_FILE=$(mktemp)
  echo "$(pwd)" > "$REPOS_FILE"
fi

$JSON_OUTPUT || echo "=== STASH AUDIT METACLUSTER — $REPORT_DATE ==="
$JSON_OUTPUT && echo "{"
$JSON_OUTPUT && echo "  \"date\": \"$REPORT_DATE\","
$JSON_OUTPUT && echo "  \"repos\": ["

FIRST_REPO=true
while IFS= read -r repo_path; do
  [ -z "$repo_path" ] && continue
  [ -d "$repo_path/.git" ] || continue
  REPO_NAME=$(basename "$repo_path")

  STASH_LIST=$(git -C "$repo_path" stash list --format="%gd|%s|%ct" 2>/dev/null || echo "")
  [ -z "$STASH_LIST" ] && continue

  REPO_FRESH=0
  REPO_STALE=0
  REPO_ZOMBIE=0

  while IFS='|' read -r stash_id stash_msg stash_ts; do
    [ -z "$stash_ts" ] && continue
    AGE_HOURS=$(( (NOW - stash_ts) / 3600 ))

    if   [ $AGE_HOURS -lt 4  ]; then CLASS="FRESH";  REPO_FRESH=$((REPO_FRESH+1));   FRESH=$((FRESH+1))
    elif [ $AGE_HOURS -lt 24 ]; then CLASS="STALE";  REPO_STALE=$((REPO_STALE+1));   STALE=$((STALE+1))
    else                              CLASS="ZOMBIE"; REPO_ZOMBIE=$((REPO_ZOMBIE+1));  ZOMBIE=$((ZOMBIE+1))
    fi

    $ZOMBIES_ONLY && [ "$CLASS" != "ZOMBIE" ] && continue

    if $JSON_OUTPUT; then
      $FIRST_REPO || echo "    ,"
      echo "    {\"repo\": \"$REPO_NAME\", \"stash\": \"$stash_id\", \"msg\": \"$stash_msg\", \"age_hours\": $AGE_HOURS, \"class\": \"$CLASS\"}"
      FIRST_REPO=false
    else
      ICON="🟢"
      [ "$CLASS" = "STALE"  ] && ICON="🟡"
      [ "$CLASS" = "ZOMBIE" ] && ICON="🧟"
      echo "  $ICON [$CLASS ${AGE_HOURS}h] $REPO_NAME :: $stash_id — $stash_msg"
    fi
    TOTAL=$((TOTAL+1))
  done <<< "$STASH_LIST"
done < "$REPOS_FILE"

if $JSON_OUTPUT; then
  echo "  ],"
  echo "  \"summary\": {\"total\": $TOTAL, \"fresh\": $FRESH, \"stale\": $STALE, \"zombie\": $ZOMBIE}"
  echo "}"
else
  echo ""
  echo "─────────────────────────────────────"
  echo "TOTAL: $TOTAL  🟢 FRESH: $FRESH  🟡 STALE: $STALE  🧟 ZOMBIE: $ZOMBIE"
  [ $ZOMBIE -gt 0  ] && echo "🚨 ACTION REQUISE: $ZOMBIE ZOMBIE(s) — convertir avant push"
  [ $TOTAL  -gt 10 ] && echo "🚨 ALERTE METACLUSTER: seuil 10 dépassé ($TOTAL) — HITL requis"
  echo ""
  echo "Conversion zombie: git stash branch wip/recovery-\$(date +%Y%m%d)-<slug> stash@{N}"
  echo "Meta-tool complet: ecos run stash-lifecycle-manager"
fi

# Exit code non-zéro si ZOMBIEs détectés (utile en CI)
[ $ZOMBIE -gt 0 ] && exit 1
exit 0
