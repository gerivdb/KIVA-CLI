# .githooks/rules.sh — Auto-generated from multi-repo-governance.yaml
# DO NOT EDIT MANUALLY — Run: python .githooks/generate_rules.py
# Generated: 2026-05-27T20:29:16.492954
# BRGS Version: 3.0
# Repository: KIVA-CLI
# IntentHash: 0xBRG_GENERATE_RULES_20260526

BRGS_VERSION="3.0"
GUARD_MODE="BLOCK"
TARGET_REPO="KIVA-CLI"

# Forbidden paths (pipe-separated globs)
FORBIDDEN_PATHS="src/ecos/|src/devtools/"

# Allowed branch prefixes (pipe-separated)
ALLOWED_PREFIXES="kiva-cli/|feat/|fix/|chore/"

# Redirect map (format: source_path:target_repo|...)
REDIRECT_MAP="src/ecos/:gerivdb/ECOS-CLI|src/devtools/:gerivdb/DevTools"
