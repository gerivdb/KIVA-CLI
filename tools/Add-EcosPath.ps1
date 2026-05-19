$ErrorActionPreference = "Stop"

try {
param(
    [Parameter(Mandatory=$false)]
    [string]$ParamName = ""
)

$ecosPath = "D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI"
$pathKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
$existing = (Get-ItemProperty -Path $pathKey -Name Path -ErrorAction SilentlyContinue).Path
if ($existing -and $existing.Split(';') -contains $ecosPath) {
  Write-Output "ECOS-CLI already in PATH"
} else {
  $newPath = if ([string]::IsNullOrEmpty($existing)) { $ecosPath } else { $existing + ";" + $ecosPath }
  Set-ItemProperty -Path $pathKey -Name Path -Value $newPath -Force
  [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
  [Environment]::SetEnvironmentVariable("Path", $newPath, "Process")
  Write-Output "PATH systeme mis a jour pour inclure ECOS-CLI: $ecosPath"
}

} catch {
    Write-Error $_.Exception.Message
    exit 1
}
