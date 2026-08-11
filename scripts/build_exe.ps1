param(
    [switch]$FastViewer,
    [string]$Version = 'unreleased'
)

# scripts/build_exe.ps1
# Build standalone executables for rtgamma

# $ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

function Invoke-Checked([string]$FilePath, [string[]]$Arguments) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function New-ApplicationIdentity {
    $commit = $null
    $commitOutput = & git -C $ROOT rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0) { $commit = ([string]$commitOutput).Trim() }
    $statusOutput = & git -C $ROOT status --porcelain --untracked-files=no 2>$null
    $dirty = if ($LASTEXITCODE -eq 0) { -not [string]::IsNullOrWhiteSpace(($statusOutput -join "`n")) } else { $null }
    return [ordered]@{
        schema_version = 1
        version = $Version
        git_commit = $commit
        git_dirty = $dirty
    }
}

function Write-ApplicationIdentity([string]$DistDir) {
    if (-not (Test-Path $DistDir -PathType Container)) {
        throw "Distribution directory not found: $DistDir"
    }
    $identityPath = Join-Path $DistDir 'application_identity.json'
    New-ApplicationIdentity | ConvertTo-Json | Set-Content -LiteralPath $identityPath -Encoding UTF8
}

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
Invoke-Checked python @('-m', 'pip', 'install', 'pyinstaller')

Write-Host "Building rtgamma.main..." -ForegroundColor Cyan
# rtgamma.main relies on config/presets.json and config/3dvh_reference.json
# We add the config directory to the build
$cliArgs = @(
    '-m', 'PyInstaller', '-y', '--name', 'rtgamma_cli', '--onedir', '--console',
    '--add-data', 'config;config',
    '--hidden-import', 'numba',
    '--copy-metadata', 'numba',
    '--collect-all', 'pymedphys',
    '--copy-metadata', 'pymedphys',
    '--hidden-import', 'pydicom',
    '--hidden-import', 'reportlab',
    '--hidden-import', 'rtgamma.gamma',
    '--hidden-import', 'rtgamma.io_dicom',
    '--hidden-import', 'rtgamma.mask',
    '--hidden-import', 'rtgamma.optimize',
    '--hidden-import', 'rtgamma.report',
    '--hidden-import', 'rtgamma.resample',
    '--hidden-import', 'rtgamma.dvh',
    '--hidden-import', 'rtgamma.pdf_report',
    '--collect-submodules', 'scipy',
    '--collect-all', 'reportlab',
    '--clean',
    'scripts/run_cli.py'
)
Invoke-Checked python $cliArgs
Write-ApplicationIdentity (Join-Path $ROOT 'dist\rtgamma_cli')

Write-Host "Building gamma_viewer..." -ForegroundColor Cyan
$viewerArgs = @(
    '-m', 'PyInstaller', '-y', '--name', 'gamma_viewer', '--onedir', '--noconsole',
    '--hidden-import', 'matplotlib',
    '--hidden-import', 'numba',
    '--copy-metadata', 'numba',
    '--collect-all', 'pymedphys',
    '--copy-metadata', 'pymedphys',
    '--hidden-import', 'pydicom',
    '--collect-submodules', 'scipy',
    '--clean',
    'scripts/gamma_viewer.py'
)
Invoke-Checked python $viewerArgs
Write-ApplicationIdentity (Join-Path $ROOT 'dist\gamma_viewer')

if ($FastViewer) {
    Write-Host "Building gamma_viewer_fast..." -ForegroundColor Cyan
    Invoke-Checked python @('-m', 'PyInstaller', '-y', '--clean', 'gamma_viewer_fast.spec')
    Write-ApplicationIdentity (Join-Path $ROOT 'dist\gamma_viewer_fast')
}

Write-Host "Build complete! Check the 'dist' folder." -ForegroundColor Green
Write-Host "Note: run_gui_exe.ps1 uses gamma_viewer_fast only when built and launched with -DistributionMode FastZip." -ForegroundColor Yellow
