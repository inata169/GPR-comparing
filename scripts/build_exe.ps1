# scripts/build_exe.ps1
# Build standalone executables for rtgamma (LIGHTWEIGHT VERSION)
# This uses optimized .spec files to reduce size (MKL/unused modules excluded)

$ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

# Update pip and pyinstaller just in case
Write-Host "Checking for PyInstaller..." -ForegroundColor Cyan
python -m pip install -U pyinstaller

Write-Host "Building rtgamma_cli from optimized .spec..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm rtgamma_cli.spec

Write-Host "Building gamma_viewer from optimized .spec..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm gamma_viewer.spec

Write-Host "`nBuild complete! Check the 'dist' folder." -ForegroundColor Green
Write-Host "Note: Verification of size reduction in progress..." -ForegroundColor Yellow

# Measure sizes
$cli_size = (Get-ChildItem -Recurse -Path "dist/rtgamma_cli" | Measure-Object -Property Length -Sum).Sum / 1MB
$viewer_size = (Get-ChildItem -Recurse -Path "dist/gamma_viewer" | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "Dist size (rtgamma_cli):   $([math]::Round($cli_size, 1)) MB" -ForegroundColor Cyan
Write-Host "Dist size (gamma_viewer): $([math]::Round($viewer_size, 1)) MB" -ForegroundColor Cyan
