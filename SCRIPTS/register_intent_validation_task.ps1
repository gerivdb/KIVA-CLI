$cmd = "cd 'D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI'; python -m kiva_cli.kiva pipeline run intent-validation-pipeline"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command $cmd"
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "KIVA-CLI intent-validation-pipeline" -Action $action -Trigger $trigger -Settings $settings -Description "Daily 03:00 UTC - Validate INTENT frontmatter, hash uniqueness, cross-repo refs (ADR-019)" -Force
Write-Host "Task 'KIVA-CLI intent-validation-pipeline' registered."