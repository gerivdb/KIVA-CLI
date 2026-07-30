#!/usr/bin/env bash
# ============================================================
# apply-gitignore.sh — Applique un template .gitignore par strate
# REPO-STANDARDS / scripts / apply-gitignore.sh
# IntentHash: 0xAPPLY_GITIGNORE_SCRIPT_20260626
# ============================================================
set -euo pipefail

USAGE="Usage: $0 <repo-path> <strate>

Strates valides: L1 (ontologies), L2 (cognition), L3 (automation)

Exemple:
  $0 D:/DO/WEB/ONTOLOGY L1
  $0 D:/DO/WEB/TOOLS/L4-TOOLS/CTULU L3"

REPO_PATH="${1:?${USAGE}}"
STRATE="${2:?${USAGE}}"

# Déterminer le template
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/../templates"

case "${STRATE}" in
    L1) TEMPLATE="${TEMPLATE_DIR}/gitignore.L1.template" ;;
    L2) TEMPLATE="${TEMPLATE_DIR}/gitignore.L2.template" ;;
    L3) TEMPLATE="${TEMPLATE_DIR}/gitignore.L3.template" ;;
    *)  echo "ERREUR: Strate '${STRATE}' invalide. Utiliser L1, L2 ou L3."
        echo "${USAGE}"
        exit 1 ;;
esac

if [ ! -f "${TEMPLATE}" ]; then
    echo "ERREUR: Template '${TEMPLATE}' introuvable."
    exit 1
fi

GITIGNORE="${REPO_PATH}/.gitignore"

# Compter les patterns existants
EXISTING_COUNT=0
if [ -f "${GITIGNORE}" ]; then
    EXISTING_COUNT=$(grep -cve '^\s*$' -e '^\s*#' "${GITIGNORE}" 2>/dev/null || echo 0)
fi

# Calculer les nouveaux patterns à ajouter
ADDED=0
SKIPPED=0
TMPFILE=$(mktemp)

while IFS= read -r pattern; do
    # Ignorer lignes vides et commentaires
    [[ -z "${pattern}" || "${pattern}" =~ ^[[:space:]]*# ]] && continue
    # Nettoyer le pattern
    pattern=$(echo "${pattern}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -z "${pattern}" ] && continue

    # Vérifier si le pattern existe déjà
    if [ -f "${GITIGNORE}" ] && grep -qF "${pattern}" "${GITIGNORE}"; then
        SKIPPED=$((SKIPPED + 1))
    else
        echo "${pattern}" >> "${TMPFILE}"
        ADDED=$((ADDED + 1))
    fi
done < "${TEMPLATE}"

# Fusionner les nouveaux patterns
if [ "${ADDED}" -gt 0 ]; then
    echo "" >> "${GITIGNORE}"
    echo "# ---- Ajouté par apply-gitignore.sh (strate ${STRATE}) ----" >> "${GITIGNORE}"
    cat "${TMPFILE}" >> "${GITIGNORE}"
fi

rm -f "${TMPFILE}"

# Rapport
echo "============================================================"
echo "apply-gitignore.sh — Rapport"
echo "============================================================"
echo "Repo      : ${REPO_PATH}"
echo "Strate    : ${STRATE}"
echo "Template  : ${TEMPLATE}"
echo "Patterns existants : ${EXISTING_COUNT}"
echo "Patterns ajoutés   : ${ADDED}"
echo "Patterns ignorés   : ${SKIPPED} (déjà présents)"
echo "============================================================"

# Vérification critique : fichiers secrets trackés
SECRET_FILES=$(git -C "${REPO_PATH}" ls-files 2>/dev/null | grep -E '\.env|\.key|\.pem' || true)
if [ -n "${SECRET_FILES}" ]; then
    echo ""
    echo "⚠️  ALERTE: Fichiers secrets trackés détectés :"
    echo "${SECRET_FILES}"
    echo "→ Exécuter: git -C ${REPO_PATH} rm --cached <fichier>"
fi
