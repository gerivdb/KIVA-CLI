# ============================================================
# apply-gitignore.ps1 — Applique un template .gitignore par strate
# REPO-STANDARDS / scripts / apply-gitignore.ps1
# IntentHash: 0xAPPLY_GITIGNORE_PS1_20260626
# ============================================================
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [Parameter(Mandatory=$true)][ValidateSet('L1','L2','L3')][string]$Strate
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TemplateDir = Join-Path (Split-Path -Parent $ScriptDir) "templates"
$TemplateFile = Join-Path $TemplateDir "gitignore.$Strate.template"

if (-not (Test-Path $TemplateFile)) {
    Write-Error "Template introuvable: $TemplateFile"
    exit 1
}

if (-not (Test-Path $RepoPath)) {
    Write-Error "Repo introuvable: $RepoPath"
    exit 1
}

$Gitignore = Join-Path $RepoPath ".gitignore"

# Lire le template
$TemplateContent = Get-Content $TemplateFile -Encoding UTF8

# Lire le gitignore existant
$Existing = @()
if (Test-Path $Gitignore) {
    $Existing = Get-Content $Gitignore -Encoding UTF8
}

# Calculer les patterns a ajouter
$Added = 0
$Skipped = 0
$NewPatterns = @()

foreach ($line in $TemplateContent) {
    $trimmed = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith('#')) {
        continue
    }
    if ($Existing -contains $trimmed) {
        $Skipped++
    } else {
        $NewPatterns += $trimmed
        $Added++
    }
}

# Fusionner
if ($Added -gt 0) {
    $header = "# ---- Ajoute par apply-gitignore.ps1 (strate $Strate) ----"
    $existingContent = if (Test-Path $Gitignore) { Get-Content $Gitignore -Encoding UTF8 -Raw } else { "" }
    $newBlock = $header, "", ($NewPatterns -join "`n")
    $merged = $existingContent, "", $newBlock -join "`n"
    Set-Content -Path $Gitignore -Value $merged -Encoding UTF8
}

# Rapport
Write-Output "============================================================"
Write-Output "apply-gitignore.ps1 — Rapport"
Write-Output "============================================================"
Write-Output "Repo        : $RepoPath"
Write-Output "Strate      : $Strate"
Write-Output "Template    : $TemplateFile"
Write-Output "Ajoutes     : $Added"
Write-Output "Ignores     : $Skipped (deja presents)"
Write-Output "============================================================"

# Verification critique : fichiers secrets trackes
$SecretFiles = git -C $RepoPath ls-files 2>$null | Select-String '\.env|\.key|\.pem'
if ($SecretFiles) {
    Write-Output ""
    Write-Warning "Fichiers secrets trackes detectes :"
    $SecretFiles | ForEach-Object { Write-Output "  $_" }
    Write-Output "=> Executer: git -C $RepoPath rm --cached <fichier>"
}
