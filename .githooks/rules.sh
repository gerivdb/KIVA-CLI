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

# Export for use in pre-push hook
export -f brgs_validate
export -f check_forbidden_paths
export -f check_branch_prefix
export -f check_redirect_map