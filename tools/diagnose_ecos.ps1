# diagnose_ecos.ps1 - Localise ecos.ps1 et teste health
# Statut NEXUS: CONFORME_NEXUS | ENV1 / DEV_COMET
$ecos = Get-ChildItem -Path "D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI" -Recurse -Filter "ecos.ps1" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName

if ($ecos) {
    Write-Host "[OK] ecos.ps1 trouve : $ecos"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ecos "health"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] ECOS health : code retour 0 - operationnel"
    } else {
        Write-Warning "[WARN] ECOS health a retourne le code $LASTEXITCODE"
    }
} else {
    Write-Error "[FAIL] ecos.ps1 introuvable dans D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI"
    exit 1
}
