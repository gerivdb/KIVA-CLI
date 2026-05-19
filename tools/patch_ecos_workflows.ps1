# patch_ecos_workflows.ps1 – Remplace les appels directs 'ecos health' par le wrapper
# Statut NEXUS: CONFORME_NEXUS | ENV1 / DEV_COMET
param(
  [string]$Root         = "D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB",
  [string]$WrapperPath  = "D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\tools\Invoke-EcosCli.ps1"
)

$extensions   = @("*.workflow", "*.yaml", "*.yml")
$replacements = 0

Get-ChildItem -Path $Root -Recurse -Include $extensions -File | ForEach-Object {
    $path = $_.FullName
    $text = Get-Content -Path $path -Raw -ErrorAction SilentlyContinue
    if ($text -match '\becos\s+health\b') {
        $new = [Regex]::Replace(
            $text,
            '\becos\s+health\b',
            "powershell -NoProfile -ExecutionPolicy Bypass -File `"$WrapperPath`" health",
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
        )
        $backup = $path + ".bak"
        Copy-Item -Path $path -Destination $backup -Force
        Set-Content -Path $path -Value $new -Force
        Write-Host "[OK] Remplacé dans : $path  → backup : $backup"
        $replacements++
    }
}

Write-Host "Remplacements effectués : $replacements"
