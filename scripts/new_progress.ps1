Param(
  [string]$Date = $(Get-Date -Format 'yyyy-MM-dd')
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $root

$dst = Join-Path $root ("docs/PROGRESS_" + $Date + ".md")
$tpl = Join-Path $root 'docs/PROGRESS_TEMPLATE.md'
if (Test-Path $dst) {
  Write-Output "Exists: $dst"
  exit 0
}
$content = Get-Content -Raw -Path $tpl -Encoding utf8
$content = $content -replace '{{DATE}}', $Date
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
Set-Content -Path $dst -Encoding utf8 -Value $content
Write-Output "Created: $dst"

