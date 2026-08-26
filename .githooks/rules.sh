#!/bin/bash
# rules.sh - BRGS (Branch Routing Governance System) rules
# Auto-generated from GOVERNANCE-HUB/multi-repo-governance.yaml
# Source of truth: GOVERNANCE-HUB/scripts/generate_rules.py

# IntentHash: 0xBRGS_RULES_20260712
# Generated: 2026-07-12

# ===== BRGS Guard 3: Forbidden Paths =====
# Paths that are forbidden for direct modification without ADR
export FORBIDDEN_PATHS="
EPICS/
PRD/
ADR/
INTENTS/
SPEC/
docs/architecture/
config/schemas/
.githooks/
.kilocode/
.github/workflows/
"

# ===== BRGS Guard 4: Allowed Branch Prefixes =====
# Valid branch name prefixes
export ALLOWED_PREFIXES="
feat/
fix/
docs/
chore/
refactor/
perf/
test/
hotfix/
emergency/
release/
experiment/
deploy/
rollback/
"

# ===== BRGS Redirect Map =====
# Maps forbidden paths to their canonical locations
export REDIRECT_MAP="
EPICS/ -> EPICS/
PRD/ -> PRD/
ADR/ -> ADR/
INTENTS/ -> INTENTS/
SPEC/ -> SPEC/
docs/architecture/ -> docs/architecture/
config/schemas/ -> config/schemas/
.githooks/ -> .githooks/
.kilocode/ -> .kilocode/
.github/workflows/ -> .github/workflows/
"

# ===== Guard Mode =====
# BLOCK = block push, WARN = warn only, AUDIT = log only
export GUARD_MODE="BLOCK"

# ===== Induration Metrics (ADR-2026-07-31-001) =====
# Gate manifests declare induration_risk and cost_obedience
# Bypass detection logs to WAL channel 'induration'
export BRGS_GATE_IDS="BRGS_FORBIDDEN_PATHS BRGS_BRANCH_PREFIX"
export BRGS_WAL_CHANNEL="induration"
export BRGS_BYPASS_DETECTION="true"

# ===== Helper Functions =====
check_forbidden_paths() {
    local changed_files="$1"
    local violations=0
    
    while IFS= read -r file; do
        for pattern in $FORBIDDEN_PATHS; do
            if [[ "$file" == $pattern* ]]; then
                echo "[BRGS VIOLATION] Forbidden path: $file (matches $pattern)"
                ((violations++))
            fi
        done
    done <<< "$changed_files"
    
    return $violations
}

check_branch_prefix() {
    local branch="$1"
    local valid=0
    
    for prefix in $ALLOWED_PREFIXES; do
        if [[ "$branch" == $prefix* ]]; then
            valid=1
            break
        fi
    done
    
    # Allow trunk branches
    if [[ "$branch" == "main" || "$branch" == "develop" ]]; then
        valid=1
    fi
    
    if [ $valid -eq 0 ]; then
        echo "[BRGS VIOLATION] Branch name '$branch' does not match allowed prefixes: $ALLOWED_PREFIXES"
        return 1
    fi
    
    return 0
}

check_redirect_map() {
    local changed_files="$1"
    local violations=0
    
    while IFS= read -r file; do
        for mapping in $REDIRECT_MAP; do
            from_path=$(echo "$mapping" | cut -d'>' -f1 | xargs)
            to_path=$(echo "$mapping" | cut -d'>' -f2 | xargs)
            
            if [[ "$file" == $from_path* ]]; then
                echo "[BRGS REDIRECT] $file should be in $to_path"
                ((violations++))
            fi
        done
    done <<< "$changed_files"
    
    return $violations
}

# Main validation function
brgs_validate() {
    local branch="$1"
    local changed_files="$2"
    
    local total_violations=0
    
    echo "[BRGS] Validating branch: $branch"
    echo "[BRGS] Changed files count: $(echo "$changed_files" | wc -l)"
    
    check_branch_prefix "$branch"
    total_violations=$((total_violations + $?))
    
    check_forbidden_paths "$changed_files"
    total_violations=$((total_violations + $?))
    
    check_redirect_map "$changed_files"
    total_violations=$((total_violations + $?))
    
    if [ $total_violations -gt 0 ]; then
        echo "[BRGS] FAIL: $total_violations violation(s) detected"
        return 1
    fi
    
    echo "[BRGS] OK: All checks passed"
    return 0
}

# ===== Induration: Bypass Detection & WAL Logging =====
# Detects if push used --no-verify and logs to WAL

log_induration_bypass() {
    local gate_id="$1"
    local repo="$2"
    local branch="$3"
    local method="$4"
    local reason="${5:-bypass detected}"
    local cost_obedience="${6:-600}"
    local bypass_cost="${7:-2}"
    
    local wal_dir=".wal"
    local wal_file="$wal_dir/induration.jsonl"
    
    # Ensure WAL directory exists
    mkdir -p "$wal_dir"
    
    # Calculate current I-score (simplified - uses static cost)
    local total_attempts=1
    local bypass_count=1
    local i_score=$(awk -v b="$bypass_count" -v t="$total_attempts" -v c="$cost_obedience" \
        'BEGIN { if (t==0) print 0; else print (b/t) * log(c) }')
    
    # Create JSON entry
    local entry=$(cat <<EOF
{
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gate_id": "$gate_id",
  "repo": "$repo",
  "branch": "$branch",
  "actor": "$(git config user.email || echo unknown)",
  "method": "$method",
  "reason": "$reason",
  "cost_obedience_sec": $cost_obedience,
  "bypass_cost_sec": $bypass_cost,
  "i_score_before": $i_score,
  "i_score_after": $i_score
}
EOF
)
    
    echo "$entry" >> "$wal_file"
    echo "[BRGS INDURATION] Bypass logged to WAL: $gate_id (I-score: $i_score)"
}

# Check if push was bypassed (--no-verify)
detect_bypass() {
    local gate_id="$1"
    local repo_name="$2"
    local branch_name="$3"
    
    # Check if --no-verify was used by looking at git config or env
    # This is a heuristic - in practice, the pre-push hook runs before push
    # so we detect via GIT_PUSH_OPTIONS or similar
    if [[ "${GIT_PUSH_OPTIONS:-}" == *"no-verify"* ]] || [[ "$*" == *"--no-verify"* ]]; then
        log_induration_bypass "$gate_id" "$repo_name" "$branch_name" "--no-verify" "explicit bypass" 600 2
        return 0
    fi
    
    # Also check for pre-push hook being skipped via core.hooksPath override
    local hooks_path=$(git config core.hooksPath 2>/dev/null || echo "")
    if [[ -n "$hooks_path" && "$hooks_path" != ".githooks" ]]; then
        log_induration_bypass "$gate_id" "$repo_name" "$branch_name" "core.hooksPath override" "hooks redirected" 600 2
        return 0
    fi
    
    return 1
}

# Export induration functions
export -f log_induration_bypass
export -f detect_bypass