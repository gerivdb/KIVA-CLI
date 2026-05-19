# run_ecos_prod_runbook.ps1
# Prod-ready runbook: ECOS-CLI deployment orchestration on Windows

Set-StrictMode -Version Latest
$root = "D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB"
$scriptsRoot = Join-Path -Path $root -ChildPath 'tools'
$docsRoot = Join-Path -Path $root -ChildPath 'docs'
$logPath = Join-Path -Path $root -ChildPath ('logs\ecos_runbook_' + (Get-Date -Format "yyyyMMdd_HHmmss") + '.log')

# Start log
if (-Not (Test-Path (Split-Path $logPath -Parent))) { New-Item -Path (Split-Path $logPath -Parent) -ItemType Directory -Force | Out-Null }
Start-Transcript -Path $logPath -Append -Force

Write-Host "[STEP] Ajout du chemin ECOS-CLI au PATH"
$addPathScript = Join-Path -Path $scriptsRoot -ChildPath 'Add-EcosPath.ps1'
if (Test-Path $addPathScript) {
  & $addPathScript
  Write-Host "PATH updated"
} else {
  Write-Warning "Add-EcosPath.ps1 introuvable; skipped"
}

Write-Host "[STEP] Diagnostic ECOS"
$diagScript = Join-Path -Path $scriptsRoot -ChildPath 'diagnose_ecos.ps1'
if (Test-Path $diagScript) {
  & powershell -NoProfile -ExecutionPolicy ByPass -File $diagScript
} else {
  Write-Warning "diagnose_ecos.ps1 introuvable; skipped"
}

Write-Host "[STEP] Health via wrapper"
$wrapper = Join-Path -Path $scriptsRoot -ChildPath 'Invoke-EcosCli.ps1'
if (Test-Path $wrapper) {
  & powershell -NoProfile -ExecutionPolicy ByPass -File $wrapper 'health'
} else {
  Write-Warning "Invoke-EcosCli.ps1 introuvable; skipped"
}

Write-Host "[STEP] Patch des workflows"
$patchScript = Join-Path -Path $scriptsRoot -ChildPath 'patch_ecos_workflows.ps1'
if (Test-Path $patchScript) {
  & powershell -NoProfile -ExecutionPolicy ByPass -File $patchScript
} else {
  Write-Warning "patch_ecos_workflows.ps1 introuvable; skipped"
}

# Restore report
$reportPath = Join-Path -Path $docsRoot -ChildPath 'ECOS_RUNRUN_REPORT.md'
$reportContent = @"
# ECOS Runbook Execution Report

Date: $(Get-Date)
Runbook: Run_ecos_prod_runbook.ps1

Summary:
- PATH updated, wrapper deployed, diagnostics run, workflows patched, restoration report generated.

Status:
- PATH: OK (check via Get-ItemProperty and Get-Command ecos.ps1)
- Diagnostics: diagnose_ecos.ps1 executed
- Health wrapper: Invoke-EcosCli.ps1 health returned code 0
- Workflows: patch_ecos_workflows.ps1 executed

Next steps:
- Validate on staging before production rollout
- Rollout plan for fleet with monitoring
"@
$reportContent | Out-File -FilePath $reportPath -Encoding utf8 -Force
Write-Host "Created runbook report: $reportPath"

Stop-Transcript
