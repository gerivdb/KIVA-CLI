<#
.SYNOPSIS
  Contexte validation ATOM avant commande Git critique.
.DESCRIPTION
  Vérifie que le dépôt courant correspond au contexte attendu.
  Utilisation : .\context-check.ps1 -ExpectedRepo SPIDX
.PARAMETER ExpectedRepo
  Nom attendu du dépôt (ex: SPIDX, TRIX, PLIX).
#>
param(
    [string]$ExpectedRepo = ""
)

$currentPath = (Get-Location).Path
$repoName = (Get-Item $currentPath).Name

if ($ExpectedRepo -and ($repoName -ne $ExpectedRepo)) {
    Write-Error "ERREUR : dépôt courant '$repoName' ne correspond pas à '$ExpectedRepo'"
    exit 1
}

Write-Host "Contexte OK : $repoName"
exit 0
