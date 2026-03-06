param (
    [string]$Version = "0.7.0"
)

$ErrorActionPreference = 'Stop'

# Project root
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

$stagingDirName = "rtgamma_v$Version"
$stagingDirPath = Join-Path $ROOT "release_staging\$stagingDirName"
$zipFileName = "rtgamma_v$($Version)_windows_x64.zip"
$zipFilePath = Join-Path $ROOT "release_staging\$zipFileName"

Write-Host "Creating minimal distribution package for rtgamma v$Version..." -ForegroundColor Cyan

# 1. Prepare Staging Directory
if (Test-Path $stagingDirPath) {
    Remove-Item -Path $stagingDirPath -Recurse -Force
}
if (Test-Path $zipFilePath) {
    Remove-Item -Path $zipFilePath -Force
}
New-Item -ItemType Directory -Path $stagingDirPath -Force | Out-Null

# 2. Copy dist folder contents (EXE and dependencies)
$distCliDir = Join-Path $ROOT "dist\rtgamma_cli"
$distViewerDir = Join-Path $ROOT "dist\gamma_viewer"

if (-not (Test-Path $distCliDir) -or -not (Test-Path $distViewerDir)) {
    Write-Host "ERROR: Compiled executables not found in 'dist' folder. Please run 'scripts/build_exe.ps1' first." -ForegroundColor Red
    exit 1
}

Write-Host "Copying compiled executables..."
$targetDistDir = Join-Path $stagingDirPath "dist"
New-Item -ItemType Directory -Path $targetDistDir -Force | Out-Null
Copy-Item -Path $distCliDir -Destination $targetDistDir -Recurse -Force
Copy-Item -Path $distViewerDir -Destination $targetDistDir -Recurse -Force

# 3. Copy GUI scripts
Write-Host "Copying GUI scripts..."
$targetScriptsDir = Join-Path $stagingDirPath "scripts"
New-Item -ItemType Directory -Path $targetScriptsDir -Force | Out-Null
Copy-Item -Path (Join-Path $ROOT "scripts\run_gui.ps1") -Destination $targetScriptsDir -Force
Copy-Item -Path (Join-Path $ROOT "run_gui.bat") -Destination $stagingDirPath -Force

# 4. Copy config files
Write-Host "Copying configuration files..."
$targetConfigDir = Join-Path $stagingDirPath "config"
New-Item -ItemType Directory -Path $targetConfigDir -Force | Out-Null
$configFiles = Get-ChildItem -Path (Join-Path $ROOT "config") -File
foreach ($file in $configFiles) {
    Copy-Item -Path $file.FullName -Destination $targetConfigDir -Force
}

# 5. Copy Documentation
Write-Host "Copying documentation..."
Copy-Item -Path (Join-Path $ROOT "README_JA.md") -Destination $stagingDirPath -Force
Copy-Item -Path (Join-Path $ROOT "RUN_INSTRUCTIONS_JA.txt") -Destination $stagingDirPath -Force

# 6. Compress staging directory into ZIP
Write-Host "Compressing to $zipFileName..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($stagingDirPath, $zipFilePath)

# 7. Cleanup (Optional, keep staging dir for inspection if desired, but default is to keep zip and remove staging)
Write-Host "Cleaning up staging directory..."
Remove-Item -Path $stagingDirPath -Recurse -Force

Write-Host "Package created successfully: $zipFilePath" -ForegroundColor Green
