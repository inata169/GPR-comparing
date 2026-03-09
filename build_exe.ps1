# scripts/build_exe.ps1
# Build standalone executables for rtgamma

$ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
python -m pip install pyinstaller

Write-Host "Building rtgamma_cli..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm rtgamma_cli.spec

Write-Host "Building gamma_viewer..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm gamma_viewer.spec

Write-Host "Build complete! Check the 'dist' folder." -ForegroundColor Green
Write-Host "Note: run_gui.ps1 will automatically use these executables if present in the dist folder." -ForegroundColor Yellow
