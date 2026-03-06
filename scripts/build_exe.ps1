# scripts/build_exe.ps1
# Build standalone executables for rtgamma

$ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
python -m pip install pyinstaller

Write-Host "Building rtgamma.main..." -ForegroundColor Cyan
# rtgamma.main relies on config/presets.json and config/3dvh_reference.json
# We add the config directory to the build
python -m PyInstaller --name rtgamma_cli --onedir --noconsole `
    --add-data "config;config" `
    --hidden-import numba `
    --hidden-import pydicom `
    --hidden-import rtgamma.gamma `
    --hidden-import rtgamma.io_dicom `
    --hidden-import rtgamma.mask `
    --hidden-import rtgamma.optimize `
    --hidden-import rtgamma.report `
    --hidden-import rtgamma.resample `
    --clean `
    rtgamma/main.py

Write-Host "Building gamma_viewer..." -ForegroundColor Cyan
python -m PyInstaller --name gamma_viewer --onedir --noconsole `
    --hidden-import matplotlib `
    --hidden-import numba `
    --hidden-import pydicom `
    --clean `
    scripts/gamma_viewer.py

Write-Host "Build complete! Check the 'dist' folder." -ForegroundColor Green
Write-Host "Note: run_gui.ps1 will automatically use these executables if present in the dist folder." -ForegroundColor Yellow
