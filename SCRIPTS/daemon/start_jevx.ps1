# Start JEVX — Décideur typé LLM-local souverain
# Usage: .\start_jevx.ps1 [port] [host]
# Default port: 8080
# Default host: 127.0.0.1
# IMPORTANT: Ce script doit rester en premier plan (foreground)
# car DaemonManager suit le PID de ce processus.

param(
    [int]$Port = 8080,
    [string]$ListenHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$jevxPath = "D:\DO\WEB\TOOLS\L4-TOOLS\JEVX"
$envFile = Join-Path $jevxPath ".env"

Write-Output "[JEVX] Starting on http://${ListenHost}:${Port}"
Write-Output "[JEVX] Path: $jevxPath"

# Charger le fichier .env dans les variables d'environnement
if (Test-Path $envFile) {
    Write-Output "[JEVX] Loading environment from .env"
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line.Split("=", 2)
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                # Supprimer les guillemets si présents
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                Write-Output "[JEVX]   $key = $value"
            }
        }
    }
} else {
    Write-Output "[JEVX] WARNING: .env not found at $envFile"
}

# Vérifier que bun est disponible
$bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $bun) {
    Write-Output "[JEVX] ERROR: bun not found in PATH"
    exit 1
}

# Se placer dans le répertoire JEVX
Set-Location -LiteralPath $jevxPath
Write-Output "[JEVX] Working directory: $(Get-Location)"

Write-Output "[JEVX] Starting bun run src/index.ts..."
Write-Output "[JEVX] Press Ctrl+C to stop"

# Démarrer JEVX au premier plan
& bun run src/index.ts --port $Port --host $ListenHost

exit $LASTEXITCODE
