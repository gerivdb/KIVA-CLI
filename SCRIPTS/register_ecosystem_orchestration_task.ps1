$cmd = 'cd D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI; python -m kiva_cli.kiva pipeline run ecosystem-orchestration-pipeline'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$cmd`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::FromDays(3650))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "KIVA-CLI ecosystem-orchestration-pipeline" -Action $action -Trigger $trigger -Settings $settings -Description "Every 30 min - CTULU/TRIX/ECOS-CLI N+3 coherence check (ADR-020)" -Force
Write-Host "Task 'KIVA-CLI ecosystem-orchestration-pipeline' registered."