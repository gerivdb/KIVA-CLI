#!/usr/bin/env bash
# ============================================================
# install-hooks.sh — Deploy REPO-STANDARDS hooks to target repo
# REPO-STANDARDS / scripts / install-hooks.sh
# IntentHash: 0xINSTALL_HOOKS_SCRIPT_20260626
# ============================================================
set -euo pipefail

USAGE="Usage: $0 <target-repo-path> [--force]

Installs REPO-STANDARDS .githooks/ into a target repository.

Options:
  --force    Overwrite existing hooks in target

Example:
  $0 D:/DO/WEB/TOOLS/L4-TOOLS/CTULU
  $0 D:/DO/WEB/TOOLS/L2-PLATFORM/TRIX --force"

if [ $# -lt 1 ]; then
    echo "${USAGE}"
    exit 1
fi

TARGET="${1}"
FORCE="${2:-}"

if [ ! -d "${TARGET}/.git" ] && [ ! -f "${TARGET}/.git" ]; then
    echo "ERREUR: '${TARGET}' n'est pas un dépôt Git."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_SRC="${SCRIPT_DIR}/../.githooks"
HOOKS_DST="${TARGET}/.githooks"

if [ ! -d "${HOOKS_SRC}" ]; then
    echo "ERREUR: Source hooks '${HOOKS_SRC}' introuvable."
    exit 1
fi

# Créer le répertoire .githooks dans le repo cible
mkdir -p "${HOOKS_DST}"

# Copier les hooks
INSTALLED=0
SKIPPED=0
OVERWRITTEN=0

for hook in "${HOOKS_SRC}"/*; do
    hook_name=$(basename "${hook}")

    # Ignorer les fichiers non-hook (README, etc.)
    case "${hook_name}" in
        README*|*.md|*.txt) continue ;;
    esac

    target_hook="${HOOKS_DST}/${hook_name}"

    if [ -f "${target_hook}" ]; then
        if [ "${FORCE}" = "--force" ]; then
            cp "${hook}" "${target_hook}"
            OVERWRITTEN=$((OVERWRITTEN + 1))
        else
            echo "  SKIP: ${hook_name} (exists, use --force to overwrite)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    else
        cp "${hook}" "${target_hook}"
        INSTALLED=$((INSTALLED + 1))
    fi

    # Rendre exécutable
    chmod +x "${target_hook}" 2>/dev/null || true
done

# Configurer le hooksPath
git -C "${TARGET}" config core.hooksPath .githooks

# Rapport
echo "============================================================"
echo "install-hooks.sh — Report"
echo "============================================================"
echo "Target       : ${TARGET}"
echo "Source       : ${HOOKS_SRC}"
echo "Installed    : ${INSTALLED}"
echo "Overwritten  : ${OVERWRITTEN}"
echo "Skipped      : ${SKIPPED}"
echo "hooksPath    : $(git -C "${TARGET}" config core.hooksPath)"
echo "============================================================"

# Vérification
if [ "${INSTALLED}" -gt 0 ] || [ "${OVERWRITTEN}" -gt 0 ]; then
    echo "Hooks actifs dans ${TARGET}:"
    ls -la "${HOOKS_DST}/" 2>/dev/null | grep -v total | grep -v '^d'
fi
