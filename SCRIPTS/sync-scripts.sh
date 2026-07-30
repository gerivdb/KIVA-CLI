#!/bin/bash
# Sync scripts and hooks from REPO-STANDARDS to all ecosystem repos
# Does not exit on individual repo errors

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$SOURCE_DIR/scripts/VERSION"
SCRIPT_VERSION="unknown"
if [[ -f "$VERSION_FILE" ]]; then
    SCRIPT_VERSION=$(cat "$VERSION_FILE")
fi

DRY_RUN=0
FORCE=0
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=1 ;;
        --force) FORCE=1 ;;
    esac
done

# List of target repos with local paths (relative to SOURCE_DIR/../..)
TARGETS=(
    # L0-CANON
    "$SOURCE_DIR/../../L0-CANON/GOVERNANCE-HUB"
    "$SOURCE_DIR/../../L0-CANON/unified-design"
    "$SOURCE_DIR/../../L0-CANON/ONTOLOGY"
    "$SOURCE_DIR/../../L0-CANON/BRAIN"
    "$SOURCE_DIR/../../L0-CANON/BLO"
    "$SOURCE_DIR/../../L0-CANON/FERMI-EVER"
    "$SOURCE_DIR/../../L0-CANON/GOST"
    "$SOURCE_DIR/../../L0-CANON/personae"
    "$SOURCE_DIR/../../L0-CANON/connard-design"
    "$SOURCE_DIR/../../L0-CANON/morphohdl-anamorphic-growth"
    "$SOURCE_DIR/../../L0-CANON/triadic-compound-eye"
    "$SOURCE_DIR/../../L0-CANON/sonar-driven-design"
    "$SOURCE_DIR/../../L0-CANON/ECOSYSTEM"
    "$SOURCE_DIR/../../L0-CANON/BRAIN-DOCS"
    "$SOURCE_DIR/../../L0-CANON/TOPOS"
    "$SOURCE_DIR/../../L0-CANON/TQL"
    
    # L1-CAUSALITY / L1-INFRA
    "$SOURCE_DIR/../../L1-INFRA/KIVA"
    "$SOURCE_DIR/../../L1-INFRA/KIVA-CLI"
    "$SOURCE_DIR/../../L1-INFRA/ECOS-CLI"
    "$SOURCE_DIR/../../L1-INFRA/GATEWAY-MANAGER"
    "$SOURCE_DIR/../../L1-INFRA/BOINC-LLM-P2P"
    "$SOURCE_DIR/../../L1-INFRA/ECOS-CLI"
    
    # L1b / L2 / L2b
    "$SOURCE_DIR/../../L1-INFRA/KIVA"
    "$SOURCE_DIR/../../L1-INFRA/KIVA-CLI"
    "$SOURCE_DIR/../../L1-INFRA/ECOS-CLI"
    "$SOURCE_DIR/../../L1-INFRA/GATEWAY-MANAGER"
    "$SOURCE_DIR/../../L1-INFRA/TOPOS"
    "$SOURCE_DIR/../../L1-INFRA/TQL"
    "$SOURCE_DIR/../../L1-INFRA/LARQL-243"
    "$SOURCE_DIR/../../L1-INFRA/KEEL"
    "$SOURCE_DIR/../../L1-INFRA/IRIS"
    
    # L2b_QUALIFIER
    "$SOURCE_DIR/../../L2b_QUALIFIER/KRONOS"
    
    # L3_EMERGENCE
    "$SOURCE_DIR/../../L3-EMERGENCE/FLUENCE"
    "$SOURCE_DIR/../../L3-EMERGENCE/CANDIDATOR"
    "$SOURCE_DIR/../../L3-EMERGENCE/STYX"
    "$SOURCE_DIR/../../L3-EMERGENCE/UAE"
    "$SOURCE_DIR/../../L3-EMERGENCE/BANK-BUSTER"
    "$SOURCE_DIR/../../L3-EMERGENCE/GERIBOOKING"
    "$SOURCE_DIR/../../L3-EMERGENCE/RACINES"
    "$SOURCE_DIR/../../L3-EMERGENCE/BRAIN"
    
    # L3-CITIZENS
    "$SOURCE_DIR/../../L3-CITIZENS/STYX"
    "$SOURCE_DIR/../../L3-CITIZENS/UAE"
    "$SOURCE_DIR/../../L3-CITIZENS/BANK-BUSTER"
    "$SOURCE_DIR/../../L3-CITIZENS/GERIBOOKING"
    "$SOURCE_DIR/../../L3-CITIZENS/RACINES"
    "$SOURCE_DIR/../../L3-CITIZENS/BRAIN"
    
    # L4-TOOLS
    "$SOURCE_DIR/../../L4-TOOLS/CTULU"
    "$SOURCE_DIR/../../L4-TOOLS/WAZAA"
    "$SOURCE_DIR/../../L4-TOOLS/TOOL-FACTORY-1"
    "$SOURCE_DIR/../../L4-TOOLS/VDB"
    "$SOURCE_DIR/../../L4-TOOLS/SKILLS"
    "$SOURCE_DIR/../../L4-TOOLS/BRAIN-DOCS"
    "$SOURCE_DIR/../../L4-TOOLS/vscode-lm-proxy"
    "$SOURCE_DIR/../../L4-TOOLS/vsix-ai-orchestrator"
    "$SOURCE_DIR/../../L4-TOOLS/cline"
    "$SOURCE_DIR/../../L4-TOOLS/BatMCP"
    "$SOURCE_DIR/../../L4-TOOLS/COMET-BOT"
    "$SOURCE_DIR/../../L4-TOOLS/ECIT-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/ECO-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/ecos-diff"
    "$SOURCE_DIR/../../L4-TOOLS/JOURNALISTE"
    "$SOURCE_DIR/../../L4-TOOLS/LUKAS-PRESTATIONS"
    "$SOURCE_DIR/../../L4-TOOLS/ONTOLOGY_MC"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0303-BRAIN"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0312-BRAIN2"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0402-DEEPSITE"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0902-optimiser-Perplexity"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0903-comparateur-IA-code"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0905-FRUSTRATION"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0906-JP-PETIT"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0909-DMR"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0920-BOOKING"
    "$SOURCE_DIR/../../L4-TOOLS/2025-1003-GERIBOOKING"
    "$SOURCE_DIR/../../L4-TOOLS/2025-1103-DOC-UNIV-DEV"
    "$SOURCE_DIR/../../L4-TOOLS/DATA-MINER"
    "$SOURCE_DIR/../../L4-TOOLS/PITCH-1"
    "$SOURCE_DIR/../../L4-TOOLS/GATEWAY-MANAGER"
    "$SOURCE_DIR/../../L4-TOOLS/strix"
    "$SOURCE_DIR/../../L4-TOOLS/ECOYSTEM"
    "$SOURCE_DIR/../../L4-TOOLS/ECOS-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/KIVA-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/BOINC-LLM-P2P"
    "$SOURCE_DIR/../../L4-TOOLS/DATA-MINER"
    "$SOURCE_DIR/../../L4-TOOLS/ECOS-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/JOURNALISTE"
    "$SOURCE_DIR/../../L4-TOOLS/LUKAS-PRESTATIONS"
    "$SOURCE_DIR/../../L4-TOOLS/ONTOLOGY_MC"
    "$SOURCE_DIR/../../L4-TOOLS/TOOL-FACTORY-1"
    "$SOURCE_DIR/../../L4-TOOLS/VDB"
    "$SOURCE_DIR/../../L4-TOOLS/WAZAA"
    "$SOURCE_DIR/../../L4-TOOLS/SKILLS"
    "$SOURCE_DIR/../../L4-TOOLS/BRAIN-DOCS"
    "$SOURCE_DIR/../../L4-TOOLS/vscode-lm-proxy"
    "$SOURCE_DIR/../../L4-TOOLS/vsix-ai-orchestrator"
    "$SOURCE_DIR/../../L4-TOOLS/cline"
    "$SOURCE_DIR/../../L4-TOOLS/BatMCP"
    "$SOURCE_DIR/../../L4-TOOLS/COMET-BOT"
    "$SOURCE_DIR/../../L4-TOOLS/ECIT-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/ECO-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/ecos-diff"
    "$SOURCE_DIR/../../L4-TOOLS/JOURNALISTE"
    "$SOURCE_DIR/../../L4-TOOLS/LUKAS-PRESTATIONS"
    "$SOURCE_DIR/../../L4-TOOLS/ONTOLOGY_MC"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0303-BRAIN"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0312-BRAIN2"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0402-DEEPSITE"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0902-optimiser-Perplexity"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0903-comparateur-IA-code"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0905-FRUSTRATION"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0906-JP-PETIT"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0909-DMR"
    "$SOURCE_DIR/../../L4-TOOLS/2025-0920-BOOKING"
    "$SOURCE_DIR/../../L4-TOOLS/2025-1003-GERIBOOKING"
    "$SOURCE_DIR/../../L4-TOOLS/2025-1103-DOC-UNIV-DEV"
    "$SOURCE_DIR/../../L4-TOOLS/ECOS-CLI"
    "$SOURCE_DIR/../../L4-TOOLS/ECOS-CLI"
)

sync_repo() {
    local target="$1"
    local dry_run="$2"
    local force="$3"
    
    if [[ ! -d "$target" ]]; then
        echo "Skipping $target (not found)"
        return 0
    fi
    
    # Check for local modifications if not forced
    if [[ $force -eq 0 && -d "$target/scripts" ]]; then
        # Check if there are uncommitted changes in scripts directory
        if cd "$target" && git status --porcelain scripts/ 2>/dev/null | grep -q '^'; then
            echo "[WARN]  $target has local modifications in scripts/ - use --force to overwrite"
            return 0
        fi
    fi
    
    echo "Syncing to $target (v$SCRIPT_VERSION)"
    
    # Create .githooks directory if it doesn't exist
    mkdir -p "$target/.githooks" 2>/dev/null || true
    
    # Sync scripts directory
    if [[ $dry_run -eq 1 ]]; then
        rsync -avn --delete "$SOURCE_DIR/scripts/" "$target/scripts/" 2>/dev/null || true
        rsync -avn "$SOURCE_DIR/.githooks/" "$target/.githooks/" 2>/dev/null || true
    else
        rsync -av --delete "$SOURCE_DIR/scripts/" "$target/scripts/" 2>/dev/null || true
        rsync -av "$SOURCE_DIR/.githooks/" "$target/.githooks/" 2>/dev/null || true
        
        # Update checkpoint with sync timestamp
        timestamp=$(date -Iseconds)
        mkdir -p "$target/.mdu" 2>/dev/null || true
        echo "{\"last_sync\": \"$timestamp\", \"source\": \"REPO-STANDARDS\", \"version\": \"$SCRIPT_VERSION\"}" > "$target/.mdu/checkpoint_sync.json" 2>/dev/null || true
    fi
}

DRY_RUN=0
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=1
fi

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

for target in "${TARGETS[@]}"; do
    sync_repo "$target" "$DRY_RUN" "$FORCE"
done

if [[ $DRY_RUN -eq 1 ]]; then
    echo "Dry run complete. Use no argument to perform actual sync."
else
    echo "Sync complete."
fi