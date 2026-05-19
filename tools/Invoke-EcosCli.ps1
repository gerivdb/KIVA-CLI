# Invoke-EcosCli.ps1 - Wrapper pour ECOS CLI avec fallback
# Statut NEXUS: CONFORME_NEXUS | ENV1 / DEV_COMET
param([string]$Command)

$ecosPath = (Get-Command ecos.ps1 -ErrorAction SilentlyContinue).Source
if (-not $ecosPath) {
    Write-Warning "ECOS CLI introuvable dans PATH, tentative de localisation manuelle"
    $ecosPath = Get-ChildItem -Path "D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI" -Filter "ecos.ps1" -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1 -ExpandProperty FullName
}

if ($ecosPath) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ecosPath $Command
    exit $LASTEXITCODE
}

# Fallback Python si ecos.ps1 totalement absent
$pyPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pyPath) {
    $possibleMain = "D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI\ecos\cli\__main__.py"
    if (Test-Path $possibleMain) {
        & $pyPath -u $possibleMain $Command
        exit $LASTEXITCODE
    }
    & $pyPath -m ecos.cli $Command
    exit $LASTEXITCODE
}

Write-Error "ECOS CLI manquant (ecos.ps1 introuvable, fallback Python indisponible) - commande '$Command' annulee"
exit 1
