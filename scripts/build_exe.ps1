param(
    [switch]$FastViewer
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

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
Invoke-Checked python @('-m', 'pip', 'install', 'pyinstaller')

Write-Host "Building rtgamma.main..." -ForegroundColor Cyan
# rtgamma.main relies on config/presets.json and config/3dvh_reference.json
# We add the config directory to the build
$cliArgs = @(
    '-m', 'PyInstaller', '-y', '--name', 'rtgamma_cli', '--onedir', '--console',
    '--add-data', 'config;config',
    '--hidden-import', 'numba',
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

Write-Host "Building gamma_viewer..." -ForegroundColor Cyan
$viewerArgs = @(
    '-m', 'PyInstaller', '-y', '--name', 'gamma_viewer', '--onedir', '--noconsole',
    '--hidden-import', 'matplotlib',
    '--hidden-import', 'numba',
    '--hidden-import', 'pydicom',
    '--collect-submodules', 'scipy',
    '--clean',
    'scripts/gamma_viewer.py'
)
Invoke-Checked python $viewerArgs

if ($FastViewer) {
    Write-Host "Building gamma_viewer_fast..." -ForegroundColor Cyan
    Invoke-Checked python @('-m', 'PyInstaller', '-y', '--clean', 'gamma_viewer_fast.spec')
}

Write-Host "Build complete! Check the 'dist' folder." -ForegroundColor Green
Write-Host "Note: run_gui_exe.ps1 uses gamma_viewer_fast only when built and launched with -DistributionMode FastZip." -ForegroundColor Yellow
