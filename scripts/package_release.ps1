param (
    [string]$Version = "0.7.0",
    [ValidateSet('Legacy','Fast')]
    [string]$DistributionMode = 'Legacy'
)

$ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

$suffix = if ($DistributionMode -eq 'Fast') { 'fast_windows_x64' } else { 'windows_x64' }
$stagingDirName = "rtgamma_v$Version"
if ($DistributionMode -eq 'Fast') { $stagingDirName = "rtgamma_v$($Version)_fast" }
$stagingDirPath = Join-Path $ROOT "release_staging\$stagingDirName"
$zipFileName = "rtgamma_v$($Version)_$suffix.zip"
$zipFilePath = Join-Path $ROOT "release_staging\$zipFileName"

function Copy-IfExists([string]$src, [string]$dst) {
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
    }
}

function Write-FastNotice([string]$targetDir) {
    $notice = @'
rtgamma Fast Viewer distribution notice

The rtgamma application source code is distributed under the MIT license.

Bundled third-party components remain under their own licenses. In particular:
- PySide6/Qt are not MIT licensed. Community wheels are distributed under LGPLv3/GPLv3 terms.
- pyqtgraph is MIT licensed.
- NumPy, pydicom, matplotlib, scipy, numba, and other bundled dependencies retain their own licenses.
- PyInstaller-generated bundles must still comply with all dependency licenses.
- GPL-only Qt modules/plugins are intentionally not bundled.

Qt/PySide6 binaries are bundled unmodified in onedir form. Review bundled_manifest.txt
for the exact file list included in this ZIP.
'@
    $notice | Out-File -FilePath (Join-Path $targetDir 'NOTICE.txt') -Encoding utf8
}

function Collect-ThirdPartyLicenses([string]$targetDir) {
    $licenseRoot = Join-Path $targetDir 'THIRD_PARTY_LICENSES'
    $manualRoot = Join-Path $licenseRoot 'manual'
    New-Item -ItemType Directory -Path $manualRoot -Force | Out-Null

    $packages = @(
        'PySide6',
        'shiboken6',
        'PySide6_Essentials',
        'PySide6_Addons',
        'PySide6-Essentials',
        'PySide6-Addons',
        'pyqtgraph',
        'numpy',
        'pydicom',
        'matplotlib',
        'scipy',
        'numba',
        'PyInstaller'
    )

    foreach ($pkg in $packages) {
        $outDir = Join-Path $licenseRoot $pkg
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        $summaryPath = Join-Path $outDir 'METADATA_LICENSE_SUMMARY.txt'
        $script = @"
import importlib.metadata as md
import pathlib
import shutil
name = "$pkg"
out = pathlib.Path(r"$outDir")
try:
    dist = md.distribution(name)
except md.PackageNotFoundError:
    (out / "NOT_BUNDLED_OR_NOT_INSTALLED.txt").write_text(f"{name} was not found in this build environment.\n", encoding="utf-8")
    raise SystemExit(0)
lines = [
    f"Name: {dist.metadata.get('Name', name)}",
    f"Version: {dist.version}",
    f"License: {dist.metadata.get('License', 'see package metadata/classifiers')}",
]
for key in ("Classifier",):
    for value in dist.metadata.get_all(key) or []:
        if "License" in value:
            lines.append(value)
(out / "METADATA_LICENSE_SUMMARY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
for file in dist.files or []:
    text = str(file).replace("\\", "/").lower()
    if any(part in text for part in ("license", "copying", "notice")):
        src = dist.locate_file(file)
        if src.is_file():
            dst = out / pathlib.Path(str(file)).name
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
"@
        try {
            $script | python -
        } catch {
            "Automatic license collection failed for $pkg. Verify manually." | Out-File -FilePath $summaryPath -Encoding utf8
        }
    }

    @'
Manual verification notes

If automatic collection above is incomplete, add manually verified license text or
URLs here before publishing the Fast ZIP. Required coverage includes PySide6,
shiboken6, PySide6_Essentials, PySide6_Addons, Qt, pyqtgraph, numpy, pydicom,
matplotlib if bundled, and PyInstaller runtime components if applicable.
'@ | Out-File -FilePath (Join-Path $manualRoot 'README.txt') -Encoding utf8

    @'
Qt manual notice

Qt/PySide6 components bundled with the Fast ZIP are not MIT licensed.
Community Qt for Python/PySide6 packages are provided under LGPLv3/GPLv3 terms
unless a commercial Qt license is used. This distribution intentionally avoids
GPL-only Qt modules/plugins and keeps Qt/PySide6 binaries unmodified.

Verify against the Qt documentation for the exact PySide6/Qt version included:
https://doc.qt.io/qtforpython-6/
https://doc.qt.io/qt-6/licensing.html
'@ | Out-File -FilePath (Join-Path $manualRoot 'Qt_NOTICE.txt') -Encoding utf8
}

function Write-BundledManifest([string]$targetDir) {
    $manifestPath = Join-Path $targetDir 'bundled_manifest.txt'
    $basePath = (Resolve-Path $targetDir).Path.TrimEnd('\') + '\'
    $baseUri = New-Object System.Uri($basePath)
    Get-ChildItem -Path $targetDir -Recurse -File |
        ForEach-Object {
            $fileUri = New-Object System.Uri($_.FullName)
            [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($fileUri).ToString()).Replace('\','/')
        } |
        Sort-Object |
        Out-File -FilePath $manifestPath -Encoding utf8
    return $manifestPath
}

function Remove-FastUnneededQtPlugins([string]$targetDir) {
    $patterns = @(
        '*qtvirtualkeyboardplugin.dll',
        '*Qt6VirtualKeyboard*',
        '*QtVirtualKeyboard*'
    )
    foreach ($pattern in $patterns) {
        Get-ChildItem -Path $targetDir -Recurse -Force -ErrorAction SilentlyContinue -Filter $pattern |
            ForEach-Object {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force
            }
    }
}

function Remove-NonFastQtComponents([string]$targetDir) {
    $distRoot = Join-Path $targetDir 'dist'
    if (-not (Test-Path $distRoot)) { return }
    $targetDirs = @(
        (Join-Path $distRoot 'rtgamma_cli'),
        (Join-Path $distRoot 'gamma_viewer')
    )
    $patterns = @(
        'PySide6',
        'shiboken6',
        'Qt6*.dll',
        'qwindows.dll'
    )
    foreach ($dir in $targetDirs) {
        if (-not (Test-Path $dir)) { continue }
        foreach ($pattern in $patterns) {
            Get-ChildItem -Path $dir -Recurse -Force -ErrorAction SilentlyContinue -Filter $pattern |
                ForEach-Object {
                    Remove-Item -LiteralPath $_.FullName -Recurse -Force
                }
        }
    }
}

function Test-FastManifest([string]$targetDir, [string]$manifestPath) {
    $manifest = Get-Content -Path $manifestPath -Encoding UTF8
    $qwindows = $manifest | Where-Object { $_ -match '(^|/)platforms/qwindows\.dll$' }
    if (-not $qwindows) {
        throw "Fast ZIP manifest does not show qwindows.dll under a Qt platforms/ path."
    }

    $gplOnlyPatterns = @(
        'QtGraphs',
        'QtHttpServer',
        'QtLocation',
        'QtNetworkAuth',
        'QtQuick3D',
        'QtVirtualKeyboard'
    )
    $unexpected = @()
    foreach ($pattern in $gplOnlyPatterns) {
        $unexpected += $manifest | Where-Object { $_ -match $pattern }
    }
    if ($unexpected.Count -gt 0) {
        throw "Fast ZIP manifest contains Qt modules/plugins that require review: $($unexpected -join ', ')"
    }

    $legacyQt = @()
    foreach ($nonFastDist in @((Join-Path $targetDir 'dist\rtgamma_cli'), (Join-Path $targetDir 'dist\gamma_viewer'))) {
      if (Test-Path $nonFastDist) {
        $legacyQt += Get-ChildItem -Path $nonFastDist -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match 'PySide6|shiboken6|qwindows\.dll|Qt6' }
      }
    }
    if ($legacyQt.Count -gt 0) {
        throw "PySide6/Qt components were found in non-Fast dist folders inside Fast ZIP staging."
    }
}

Write-Host "Creating $DistributionMode distribution package for rtgamma v$Version..." -ForegroundColor Cyan

if (Test-Path $stagingDirPath) {
    Remove-Item -Path $stagingDirPath -Recurse -Force
}
if (Test-Path $zipFilePath) {
    Remove-Item -Path $zipFilePath -Force
}
New-Item -ItemType Directory -Path $stagingDirPath -Force | Out-Null

$distCliDir = Join-Path $ROOT 'dist\rtgamma_cli'
$distViewerDir = Join-Path $ROOT 'dist\gamma_viewer'
$distFastViewerDir = Join-Path $ROOT 'dist\gamma_viewer_fast'

if (-not (Test-Path $distCliDir) -or -not (Test-Path $distViewerDir)) {
    Write-Host "ERROR: Compiled rtgamma_cli/gamma_viewer executables not found. Run scripts/build_exe.ps1 first." -ForegroundColor Red
    exit 1
}
if ($DistributionMode -eq 'Fast' -and -not (Test-Path $distFastViewerDir)) {
    Write-Host "ERROR: Fast viewer executable not found. Run scripts/build_exe.ps1 -FastViewer first." -ForegroundColor Red
    exit 1
}

Write-Host "Copying compiled executables..."
$targetDistDir = Join-Path $stagingDirPath 'dist'
New-Item -ItemType Directory -Path $targetDistDir -Force | Out-Null
Copy-Item -Path $distCliDir -Destination $targetDistDir -Recurse -Force
Copy-Item -Path $distViewerDir -Destination $targetDistDir -Recurse -Force
if ($DistributionMode -eq 'Fast') {
    Copy-Item -Path $distFastViewerDir -Destination $targetDistDir -Recurse -Force
}

Write-Host "Copying GUI scripts..."
$targetScriptsDir = Join-Path $stagingDirPath 'scripts'
New-Item -ItemType Directory -Path $targetScriptsDir -Force | Out-Null
Copy-Item -Path (Join-Path $ROOT 'scripts\run_gui_exe.ps1') -Destination $targetScriptsDir -Force
Copy-Item -Path (Join-Path $ROOT 'scripts\gui_config_common.ps1') -Destination $targetScriptsDir -Force
if ($DistributionMode -eq 'Fast') {
    Copy-Item -Path (Join-Path $ROOT 'run_gui_fast_exe.bat') -Destination $stagingDirPath -Force
} else {
    Copy-Item -Path (Join-Path $ROOT 'run_gui_exe.bat') -Destination $stagingDirPath -Force
}

Write-Host "Copying configuration files..."
$targetConfigDir = Join-Path $stagingDirPath 'config'
New-Item -ItemType Directory -Path $targetConfigDir -Force | Out-Null
Get-ChildItem -Path (Join-Path $ROOT 'config') -File |
Where-Object { $_.Name -ne 'gui_config.ini' } |
ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $targetConfigDir -Force
}

Write-Host "Copying documentation..."
Copy-IfExists (Join-Path $ROOT 'README_JA.md') $stagingDirPath
Copy-IfExists (Join-Path $ROOT 'README.md') $stagingDirPath
Copy-IfExists (Join-Path $ROOT 'RUN_INSTRUCTIONS_JA.txt') $stagingDirPath

if ($DistributionMode -eq 'Fast') {
    Write-FastNotice $stagingDirPath
    Collect-ThirdPartyLicenses $stagingDirPath
    Remove-FastUnneededQtPlugins $stagingDirPath
}
Remove-NonFastQtComponents $stagingDirPath

$manifestPath = Write-BundledManifest $stagingDirPath
if ($DistributionMode -eq 'Fast') {
    Test-FastManifest $stagingDirPath $manifestPath
}

Write-Host "Compressing to $zipFileName..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($stagingDirPath, $zipFilePath)

Write-Host "Cleaning up staging directory..."
Remove-Item -Path $stagingDirPath -Recurse -Force

Write-Host "Package created successfully: $zipFilePath" -ForegroundColor Green
