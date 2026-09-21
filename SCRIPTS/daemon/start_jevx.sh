#!/bin/bash
# Start JEVX — Décideur typé LLM-local souverain
# Usage: ./start_jevx.sh [port]
# Default port: 8080

set -e

PORT=${1:-8080}
HOST="127.0.0.1"
JEVX_PATH="D:/DO/WEB/TOOLS/L4-TOOLS/JEVX"

echo "[JEVX] Starting on http://$HOST:$PORT"
echo "[JEVX] Path: $JEVX_PATH"

# Vérifier que bun est disponible
if ! command -v bun &> /dev/null; then
    echo "[JEVX] ERROR: bun not found in PATH"
    exit 1
fi

# Démarrer JEVX
cd "$JEVX_PATH"
bun run src/index.ts --port $PORT --host $HOST
