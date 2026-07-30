#!/bin/bash
# wip-detector-cluster.sh — Détection branches WIP cross-repos + validation ADR-011
# SOT: gerivdb/REPO-STANDARDS/scripts/wip-detector-cluster.sh
# Ref: ADR-011 (branch naming convention), PRD-MAGISTRAL-004 (enforcement)
# Usage: bash scripts/wip-detector-cluster.sh [--orphans-only] [--ghosts-only] [--json] [--cleanup] [--audit-only]
# Version: 2.0.0 — 2026-06-30
# Exit code: 1 si ORPHAN ou GHOST détectés

set -euo pipefail

REPOS_FILE="${HOME}/.ecos/metacluster-repos.txt"
NOW=$(date +%s)
ORPHANS_ONLY=false
GHOSTS_ONLY=false
JSON_OUTPUT=false
CLEANUP_MERGED=false
AUDIT_ONLY=false
ADR_AUDIT=false
REPORT_DATE=$(date '+%Y-%m-%dT%H:%M')

# Compteurs globaux
TOTAL=0; ACTIVE=0; STALE=0; ORPHAN=0; GHOST=0; MERGED=0; VIOLATIONS=0; COMPLIANT=0

for arg in "$@"; do
  case $arg in
    --orphans-only)  ORPHANS_ONLY=true ;;
    --ghosts-only)   GHOSTS_ONLY=true ;;
    --json)          JSON_OUTPUT=true ;;
    --cleanup)       CLEANUP_MERGED=true ;;
    --audit-only)    AUDIT_ONLY=true; ADR_AUDIT=true ;;
    --adr-audit)     ADR_AUDIT=true ;;
  esac
done

# ────────────────────────────────────────────────────────────────
# ADR-011 VALIDATION ENGINE
# Pattern: <type>/epic{NNN}-{task}-{desc}
# Exceptions: main, master, release/vX.Y.Z, hotfix/*, dependabot/*
# ────────────────────────────────────────────────────────────────

# Regex du pattern ADR-011
ADR_PATTERN='^(feature|fix|refactor|adr|chore)/epic[0-9]{3}-[a-z0-9]{1,20}(-[a-z0-9]{1,30})?$'
# Regex des exceptions autorisées
ADR_EXCEPTIONS='^(main|master|develop|release/v[0-9]+\.[0-9]+\.[0-9]+|hotfix/[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+|dependabot/.*)$'

validate_branch_naming() {
  local branch="$1"
  local repo="$2"

  # Vérifier les exceptions d'abord
  if [[ "$branch" =~ $ADR_EXCEPTIONS ]]; then
    echo "COMPLIANT"
    return 0
  fi

  # Vérifier le pattern ADR-011
  if [[ "$branch" =~ $ADR_PATTERN ]]; then
    echo "COMPLIANT"
    return 0
  fi

  # Tenter de suggérer un pattern
  local suggested=""
  if [[ "$branch" =~ ^(feature|fix|refactor|chore)/(.+)$ ]]; then
    suggested="${BASH_REMATCH[1]}/epic000-$(echo "${BASH_REMATCH[2]}" | tr '_' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-20)"
  elif [[ "$branch" =~ ^([a-z]+)/(.+)$ ]]; then
    suggested="feature/epic000-$(echo "${BASH_REMATCH[2]}" | tr '_' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-20)"
  else
    suggested="feature/epic000-$(echo "$branch" | tr '_' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-20)"
  fi

  echo "VIOLATION:$suggested"
  return 1
}

emit_violation_event() {
  local repo="$1"
  local branch="$2"
  local suggested="$3"
  local epic_number=""
  local detected_at
  detected_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  # Extraire epic{NNN} si partiellement conforme
  if [[ "$branch" =~ epic([0-9]{3}) ]]; then
    epic_number="epic${BASH_REMATCH[1]}"
  fi

  # Emit event pour bus WAZAA (fichier JSONL)
  local event_dir="${HOME}/.ecos/events"
  mkdir -p "$event_dir"

  printf '{"event":"branch.naming.violation","detected_at":"%s","repo_name":"%s","branch_name":"%s","suggested_pattern":"%s","epic_number":"%s"}\n' \
    "$detected_at" "$repo" "$branch" "$suggested" "${epic_number:-null}" \
    >> "$event_dir/branch_violations.jsonl"

  if $JSON_OUTPUT; then
    printf '    {"event": "branch.naming.violation", "repo": "%s", "branch": "%s", "suggested": "%s", "detected_at": "%s"}' \
      "$repo" "$branch" "$suggested" "$detected_at"
  fi
}

emit_branch_detected() {
  local repo="$1"
  local branch="$2"
  local compliant="$3"
  local epic_number=""
  local task=""
  local detected_at
  detected_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  if [[ "$branch" =~ ^[a-z]+/epic([0-9]{3})-([a-z0-9-]+)$ ]]; then
    epic_number="epic${BASH_REMATCH[1]}"
    task="${BASH_REMATCH[2]}"
  elif $compliant; then
    epic_number="$branch"
  fi

  # Emit event pour bus WAZAA (fichier JSONL)
  local event_dir="${HOME}/.ecos/events"
  mkdir -p "$event_dir"

  printf '{"event":"branch.detected","detected_at":"%s","repo_name":"%s","branch_name":"%s","epic_number":"%s","task":"%s","compliant":%s}\n' \
    "$detected_at" "$repo" "$branch" "${epic_number:-null}" "${task:-null}" \
    "$([ "$compliant" = true ] && echo true || echo false)" \
    >> "$event_dir/branch_detected.jsonl"
}

# Fallback mono-repo
if [ ! -f "$REPOS_FILE" ]; then
  echo "⚠️  $REPOS_FILE introuvable — audit repo courant uniquement"
  REPOS_FILE=$(mktemp)
  echo "$(pwd)" > "$REPOS_FILE"
fi

classify_branch() {
  local repo_path="$1" branch="$2" age_seconds="$3"
  local age_hours=$(( age_seconds / 3600 ))
  local age_days=$(( age_seconds / 86400 ))

  # GHOST: locale uniquement (pas de remote)
  local has_remote
  has_remote=$(git -C "$repo_path" branch -r 2>/dev/null | grep -c "origin/$branch" || true)
  if [ "$has_remote" -eq 0 ] && [ "$age_hours" -gt 24 ]; then
    echo "GHOST"; return
  fi

  # Open PR check (nécessite gh CLI)
  local has_pr=0
  if command -v gh &>/dev/null; then
    has_pr=$(gh pr list --repo "$(git -C "$repo_path" remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]//' | sed 's/\.git$//')" \
      --head "$branch" --state open --json number --jq 'length' 2>/dev/null || echo 0)
  fi

  # Classification
  if   [ "$age_hours" -lt 24  ]; then echo "ACTIVE"
  elif [ "$age_days"  -lt 7   ] && [ "$has_pr" -gt 0 ]; then echo "STALE_PR"
  elif [ "$age_days"  -lt 7   ]; then echo "STALE"
  elif [ "$has_pr"    -gt 0   ]; then echo "STALE_PR"
  else echo "ORPHAN"
  fi
}

$JSON_OUTPUT || echo "=== WIP BRANCH DETECTOR — $REPORT_DATE ==="
$AUDIT_ONLY && ! $JSON_OUTPUT && echo "=== MODE AUDIT-ONLY (ADR-011) ==="
$JSON_OUTPUT && echo '{'
$JSON_OUTPUT && echo '  "date": "'"$REPORT_DATE"'",'
$JSON_OUTPUT && echo '  "repos": ['

FIRST=true

while IFS= read -r repo_path; do
  [ -z "$repo_path" ] && continue
  [ -d "$repo_path/.git" ] || continue
  REPO_NAME=$(basename "$repo_path")

  # Fetch remote silencieux
  git -C "$repo_path" fetch origin --prune --quiet 2>/dev/null || true

  # Branches locales (exclure main/develop/master)
  BRANCHES=$(git -C "$repo_path" for-each-ref refs/heads \
    --format='%(refname:short)|%(committerdate:unix)' 2>/dev/null \
    | grep -vE '^(main|master|develop)\|' || true)

  [ -z "$BRANCHES" ] && continue

  REPO_HAS_OUTPUT=false
  REPO_LINES=""

  while IFS='|' read -r branch ts; do
    [ -z "$ts" ] && continue
    AGE_SEC=$(( NOW - ts ))
    AGE_HOURS=$(( AGE_SEC / 3600 ))
    AGE_DAYS=$(( AGE_SEC / 86400 ))

     CLASS=$(classify_branch "$repo_path" "$branch" "$AGE_SEC")

     # ── ADR-011 Naming Validation ──
     ADR_RESULT=$(validate_branch_naming "$branch" "$REPO_NAME")
     ADR_COMPLIANT=true
     ADR_SUGGESTED=""
     if [[ "$ADR_RESULT" == VIOLATION:* ]]; then
       ADR_COMPLIANT=false
       ADR_SUGGESTED="${ADR_RESULT#VIOLATION:}"
       VIOLATIONS=$((VIOLATIONS+1))
       emit_violation_event "$REPO_NAME" "$branch" "$ADR_SUGGESTED"
     else
       COMPLIANT=$((COMPLIANT+1))
     fi
     emit_branch_detected "$REPO_NAME" "$branch" "$ADR_COMPLIANT"

     # Mode audit-only: afficher uniquement le rapport ADR
     if $AUDIT_ONLY; then
       ADR_ICON="✅"
       $ADR_COMPLIANT || ADR_ICON="⚠️"
       printf "%s [%-10s] %-50s → %s\n" "$ADR_ICON" \
         "$([ "$ADR_COMPLIANT" = true ] && echo "COMPLIANT" || echo "VIOLATION")" \
         "$branch" \
         "$([ "$ADR_COMPLIANT" = true ] && echo "" || echo "suggested: $ADR_SUGGESTED")"
       continue
     fi

    # Branches mergées
    IS_MERGED=$(git -C "$repo_path" branch --merged main 2>/dev/null | grep -c "^[[:space:]]*$branch$" || true)
    [ "$IS_MERGED" -gt 0 ] && CLASS="MERGED" && MERGED=$((MERGED+1))

    # Filtres
    $ORPHANS_ONLY && [[ "$CLASS" != "ORPHAN" ]] && continue
    $GHOSTS_ONLY  && [[ "$CLASS" != "GHOST"  ]] && continue

    # Compteurs
    case $CLASS in
      ACTIVE)   ACTIVE=$((ACTIVE+1)) ;;
      STALE|STALE_PR) STALE=$((STALE+1)) ;;
      ORPHAN)   ORPHAN=$((ORPHAN+1)) ;;
      GHOST)    GHOST=$((GHOST+1)) ;;
    esac
    TOTAL=$((TOTAL+1))

    # Cleanup mergées
    if $CLEANUP_MERGED && [ "$CLASS" = "MERGED" ]; then
      git -C "$repo_path" branch -d "$branch" 2>/dev/null && \
        echo "  🗑️  Supprimé (mergée): $REPO_NAME/$branch" || true
      continue
    fi

    REPO_HAS_OUTPUT=true

    if $JSON_OUTPUT; then
      $FIRST || echo ','
      printf '    {"repo": "%s", "branch": "%s", "age_hours": %d, "class": "%s"}' \
        "$REPO_NAME" "$branch" "$AGE_HOURS" "$CLASS"
      FIRST=false
    else
      ICON="🟢"
      [ "$CLASS" = "STALE"    ] || [ "$CLASS" = "STALE_PR" ] && ICON="🟡"
      [ "$CLASS" = "ORPHAN"   ] && ICON="🔴"
      [ "$CLASS" = "GHOST"    ] && ICON="👻"
      [ "$CLASS" = "MERGED"   ] && ICON="✅"
      LABEL="${AGE_HOURS}h"
      [ $AGE_DAYS -ge 1 ] && LABEL="${AGE_DAYS}j"
      REPO_LINES="$REPO_LINES\n  $ICON [$CLASS $LABEL] $branch"
    fi
  done <<< "$BRANCHES"

  if $REPO_HAS_OUTPUT && ! $JSON_OUTPUT && ! $AUDIT_ONLY; then
    echo ""
    echo "📁 $REPO_NAME"
    echo -e "$REPO_LINES"
  fi

done < "$REPOS_FILE"

# ── ADR-011 Compliance Summary ──
ADR_TOTAL=$((COMPLIANT + VIOLATIONS))
if [ "$ADR_TOTAL" -gt 0 ]; then
  ADR_RATE=$(( (COMPLIANT * 100) / ADR_TOTAL ))
else
  ADR_RATE=100
fi

if $JSON_OUTPUT; then
  echo ''
  echo '  ],'
  printf '  "summary": {"total": %d, "active": %d, "stale": %d, "orphan": %d, "ghost": %d, "merged_not_cleaned": %d},\n' \
    "$TOTAL" "$ACTIVE" "$STALE" "$ORPHAN" "$GHOST" "$MERGED"
  printf '  "adr_011": {"compliant": %d, "violations": %d, "rate_pct": %d}\n' \
    "$COMPLIANT" "$VIOLATIONS" "$ADR_RATE"
  echo '}'
else
  echo ""
  echo "───────────────────────────────────────"
  if $AUDIT_ONLY; then
    echo "ADR-011 AUDIT — $REPORT_DATE"
    echo "✅ COMPLIANT: $COMPLIANT  ⚠️ VIOLATIONS: $VIOLATIONS  📊 TAUX: ${ADR_RATE}%"
    [ $VIOLATIONS -gt 0 ] && echo "⚠️  $VIOLATIONS branche(s) hors-convention ADR-011 — events émis dans ~/.ecos/events/"
  else
    echo "TOTAL: $TOTAL  🟢 ACTIVE: $ACTIVE  🟡 STALE: $STALE  🔴 ORPHAN: $ORPHAN  👻 GHOST: $GHOST  ✅ MERGED_NON_NETTOYÉ: $MERGED"
    [ $ORPHAN -gt 0 ] && echo "🚨 $ORPHAN ORPHAN(s): décision HITL requise — merger, archiver ou dropper"
    [ $GHOST  -gt 0 ] && echo "👻 $GHOST GHOST(s): branches locales non pushées > 24h — push ou drop"
    [ $MERGED -gt 0 ] && echo "⚠️  $MERGED branch(es) mergée(s) non nettoyée(s) — lancer avec --cleanup"
    echo ""
    echo "ADR-011 COMPLIANCE: $COMPLIANT ✅ | $VIOLATIONS ⚠️ | ${ADR_RATE}%"
    [ $VIOLATIONS -gt 0 ] && echo "⚠️  Events branch.naming.violation émis dans ~/.ecos/events/branch_violations.jsonl"
    echo ""
    echo "Meta-tool complet: ecos run wip-branch-detector"
  fi
fi

# Exit non-zéro si problèmes détectés
[ $((ORPHAN + GHOST)) -gt 0 ] && exit 1
exit 0
