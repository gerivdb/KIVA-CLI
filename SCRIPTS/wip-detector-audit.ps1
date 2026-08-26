# wip-detector-audit.ps1 -- Wrapper PowerShell natif Windows pour audit ADR-011
# Complete wip-detector-cluster.sh quand bash/head ne sont pas dispo (PowerShell pur).
# Usage: .\scripts\wip-detector-audit.ps1 [-AuditOnly] [-RepoPath <path>]
# Exit code: 0 si OK, 1 si violations détectées
param(
    [switch]$AuditOnly,
    [string[]]$RepoPath
)

$ErrorActionPreference = 'SilentlyContinue'
$eventsDir = Join-Path $env:USERPROFILE '.ecos\events'
if (-not (Test-Path $eventsDir)) { New-Item -ItemType Directory -Force -Path $eventsDir | Out-Null }
$detectedLog   = Join-Path $eventsDir 'branch_detected.jsonl'
$violationsLog = Join-Path $eventsDir 'branch_violations.jsonl'
if (Test-Path $detectedLog)   { Remove-Item $detectedLog -Force }
if (Test-Path $violationsLog) { Remove-Item $violationsLog -Force }

$adrPattern    = '^(feature|fix|refactor|adr|chore)/epic(\d{3})-([a-z0-9]{1,20})(?:-([a-z0-9]{1,30}))?$'
$adrExceptions = '^(main|master|develop|HEAD|release/v\d+\.\d+\.\d+|hotfix/\d{4}-\d{2}-\d{2}-[a-z0-9-]+|dependabot/.*)$'

if (-not $RepoPath) {
    $RepoPath = @(
        'D:\DO\WEB\TOOLS\L4-TOOLS\WAZAA',
        'D:\DO\WEB\TOOLS\L4-TOOLS\REPO-STANDARDS',
        'D:\DO\WEB\TOOLS\L1-INFRA\NEXUS'
    )
}
$total = 0; $compliant = 0; $violations = 0
foreach ($r in $RepoPath) {
    $name = Split-Path $r -Leaf
    if (-not (Test-Path (Join-Path $r '.git'))) { continue }
    git -C $r fetch origin --prune --quiet 2>$null
    $branches = git -C $r for-each-ref refs/heads --format='%(refname:short)' 2>$null
    foreach ($b in ($branches -split "`n")) {
        $b = $b.Trim()
        if (-not $b -or $b -match '^(main|master|develop)$') { continue }
        $ts = (Get-Date -Format 'o')
        $total++
        if ($b -match $adrExceptions) {
            $line = '{"event":"branch.detected","detected_at":"'+$ts+'","repo_name":"'+$name+'","branch_name":"'+$b+'","compliant":true}'
            Add-Content $detectedLog $line -Encoding UTF8
            $compliant++
            if ($AuditOnly) { Write-Output "  OK        $b" }
            continue
        }
        if ($b -match $adrPattern) {
            $epicN  = 'epic' + $Matches[2]
            $taskId = $Matches[3]
            $line = '{"event":"branch.detected","detected_at":"'+$ts+'","repo_name":"'+$name+'","branch_name":"'+$b+'","epic_number":"'+$epicN+'","task":"'+$taskId+'","compliant":true}'
            Add-Content $detectedLog $line -Encoding UTF8
            $compliant++
            if ($AuditOnly) { Write-Output "  OK        $b -> $epicN / $taskId" }
            continue
        }
        # VIOLATION
        $base = $b -replace '[^a-z0-9-]', '-' -replace '-+', '-'
        if ($base.Length -gt 20) { $base = $base.Substring(0, 20) }
        $suggested = 'feature/epic000-' + $base.TrimEnd('-')
        Add-Content $violationsLog ('{"event":"branch.naming.violation","detected_at":"'+$ts+'","repo_name":"'+$name+'","branch_name":"'+$b+'","suggested_pattern":"'+$suggested+'","epic_number":null}') -Encoding UTF8
        Add-Content $detectedLog ('{"event":"branch.detected","detected_at":"'+$ts+'","repo_name":"'+$name+'","branch_name":"'+$b+'","compliant":false}') -Encoding UTF8
        $violations++
        if ($AuditOnly) { Write-Output "  VIOLATION $b -> suggested: $suggested" }
    }
}
$rate = if ($total -gt 0) { [math]::Round(($compliant / $total) * 100, 1) } else { 0 }
Write-Output ""
Write-Output "ADR-011 AUDIT -- $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
Write-Output "[OK] COMPLIANT: $compliant  [WARN] VIOLATIONS: $violations  [RATE] TAUX: ${rate}%"
Write-Output "Events ecrits: $detectedLog | $violationsLog"
exit ($violations -gt 0 ? 1 : 0)
