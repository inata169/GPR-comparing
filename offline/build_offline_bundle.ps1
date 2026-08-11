[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [string]$PythonExe = 'python',
    [switch]$Force,
    [switch]$SkipArchive,
    [switch]$AllowDirty
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot 'dist\offline'
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$bundleName = 'GPR-comparing-offline-win64-py312'
$bundleRoot = Join-Path $OutputDirectory $bundleName
$archivePath = "$bundleRoot.zip"
$pythonVersion = '3.12.10'
$pythonInstallerSha256 = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb'

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Command)
    Write-Host "[RUN] $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK ] $Label"
}

function Remove-BuildTarget {
    param([string]$Path)
    $resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory).TrimEnd('\') + '\'
    $resolvedTarget = [IO.Path]::GetFullPath($Path)
    if (-not $resolvedTarget.StartsWith($resolvedOutput, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the output directory: $resolvedTarget"
    }
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'The Windows x64 offline bundle must be built on a 64-bit Windows PC.'
}

$versionProbe = & $PythonExe -c "import json,platform,struct,sys; print(json.dumps({'version': list(sys.version_info[:3]), 'bits': struct.calcsize('P')*8, 'os': platform.system()}))"
if ($LASTEXITCODE -ne 0) {
    throw "Could not run the requested Python executable: $PythonExe"
}
$pythonInfo = $versionProbe | ConvertFrom-Json
if ($pythonInfo.version[0] -ne 3 -or $pythonInfo.version[1] -ne 12) {
    throw "Bundle creation requires Python 3.12; found $($pythonInfo.version -join '.')."
}
if ($pythonInfo.bits -ne 64 -or $pythonInfo.os -ne 'Windows') {
    throw "Bundle creation requires 64-bit Windows Python; found $($pythonInfo.os) $($pythonInfo.bits)-bit."
}

Invoke-Checked 'check Git repository' {
    git -C $repoRoot rev-parse --is-inside-work-tree | Out-Null
}
$dirty = @(git -C $repoRoot status --porcelain --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Git worktree.' }
if ($dirty.Count -gt 0 -and -not $AllowDirty) {
    throw 'The worktree must be clean so the bundle exactly matches a Git commit.'
}
$commit = (git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not determine Git commit.' }
if ($dirty.Count -gt 0) {
    $commit = "$commit-dirty-validation-only"
    Write-Warning 'Building from a dirty worktree. Do not publish this validation bundle.'
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
if ((Test-Path -LiteralPath $bundleRoot) -or (Test-Path -LiteralPath $archivePath)) {
    if (-not $Force) {
        throw "Output already exists. Use -Force to replace it: $bundleRoot"
    }
    Remove-BuildTarget $bundleRoot
    Remove-BuildTarget $archivePath
}

$appDir = Join-Path $bundleRoot 'app'
$pythonDir = Join-Path $bundleRoot 'python'
$wheelhouseDir = Join-Path $bundleRoot 'wheelhouse'
New-Item -ItemType Directory -Path $appDir, $pythonDir, $wheelhouseDir -Force | Out-Null

Write-Host '[RUN] copy Git-tracked application files'
$trackedFiles = @(git -c core.quotepath=false -C $repoRoot ls-files)
if ($LASTEXITCODE -ne 0 -or $trackedFiles.Count -eq 0) {
    throw 'Could not list Git-tracked files.'
}
$excludedPrefixes = @(
    'config/gui_config.ini',
    'dicom/',
    'dist/',
    'output/',
    'phits-linac-validation/',
    'temp/',
    'tests/'
)
$trackedFiles = @($trackedFiles | Where-Object {
    $candidate = $_ -replace '\\', '/'
    -not ($excludedPrefixes | Where-Object {
        $candidate.Equals($_, [StringComparison]::OrdinalIgnoreCase) -or
        $candidate.StartsWith($_, [StringComparison]::OrdinalIgnoreCase)
    })
})
$trackedFiles = @($trackedFiles | Where-Object {
    $worktreePath = Join-Path $repoRoot ($_ -replace '/', '\')
    Test-Path -LiteralPath $worktreePath -PathType Leaf
})
if ($trackedFiles.Count -eq 0) {
    throw 'No application files remain after applying bundle exclusions.'
}
foreach ($relativePath in $trackedFiles) {
    $source = Join-Path $repoRoot ($relativePath -replace '/', '\')
    $destination = Join-Path $appDir ($relativePath -replace '/', '\')
    $parent = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $destination
}
Write-Host "[OK ] copied $($trackedFiles.Count) tracked files"

Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination (Join-Path $bundleRoot 'LICENSE')
Copy-Item -LiteralPath (Join-Path $repoRoot 'offline\NOTICE.txt') -Destination (Join-Path $bundleRoot 'NOTICE.txt')

$rootFiles = @(
    'INSTALL_OFFLINE.bat',
    'LAUNCH_GPR_COMPARING.bat',
    'RUN_SMOKE_TEST.bat',
    'check_existing_python.ps1',
    'verify_bundle.ps1'
)
foreach ($name in $rootFiles) {
    $source = Join-Path $appDir "offline\$name"
    $destinationName = if ($name -eq 'verify_bundle.ps1') {
        'VERIFY_BUNDLE.ps1'
    } elseif ($name -eq 'check_existing_python.ps1') {
        'CHECK_EXISTING_PYTHON.ps1'
    } else {
        $name
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $bundleRoot $destinationName)
}

$pythonInstallerName = "python-$PythonVersion-amd64.exe"
$pythonInstaller = Join-Path $pythonDir $pythonInstallerName
$pythonUri = "https://www.python.org/ftp/python/$PythonVersion/$pythonInstallerName"
$licenseRoot = Join-Path $bundleRoot 'THIRD_PARTY_LICENSES'
$licenseScript = Join-Path $repoRoot 'offline\license_compliance.py'
$licenseConfig = Join-Path $repoRoot 'offline\license_sources.json'
Invoke-Checked 'download and verify official license resources' {
    & $PythonExe $licenseScript fetch-resources --config $licenseConfig --output (Join-Path $licenseRoot '_official')
}
$spdxPath = Join-Path $licenseRoot "_official\Python-$PythonVersion\$pythonInstallerName.spdx.json"
$spdx = Get-Content -LiteralPath $spdxPath -Raw -Encoding UTF8 | ConvertFrom-Json
$cpython = @($spdx.packages | Where-Object {
    $_.name -eq 'CPython' -and $_.versionInfo -eq $pythonVersion -and
    $_.packageFileName -eq $pythonInstallerName
})
if ($cpython.Count -ne 1) {
    throw 'The official Python SPDX document has no unique matching CPython installer entry.'
}
$spdxSha = @($cpython[0].checksums | Where-Object { $_.algorithm -eq 'SHA256' })
if ($spdxSha.Count -ne 1 -or $spdxSha[0].checksumValue.ToLowerInvariant() -ne $pythonInstallerSha256) {
    throw 'The pinned Python installer SHA-256 does not match the official SPDX document.'
}
Write-Host "[RUN] download official CPython $PythonVersion x64 installer"
Invoke-WebRequest -Uri $pythonUri -OutFile $pythonInstaller -UseBasicParsing
$actualPythonHash = (Get-FileHash -LiteralPath $pythonInstaller -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualPythonHash -ne $pythonInstallerSha256) {
    throw "Python installer SHA-256 mismatch: expected $pythonInstallerSha256, got $actualPythonHash"
}
$signature = Get-AuthenticodeSignature -FilePath $pythonInstaller
if ($signature.Status -ne 'Valid') {
    throw "Python installer Authenticode signature is not valid: $($signature.Status)"
}
if ($signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
    throw "Unexpected Python installer signer: $($signature.SignerCertificate.Subject)"
}
Write-Host "[OK ] Python installer signature: $($signature.SignerCertificate.Subject)"

$requirements = Join-Path $repoRoot 'offline\requirements-offline.txt'
Invoke-Checked 'download resolved Windows x64 wheels' {
    & $PythonExe -m pip download --only-binary=:all: --dest $wheelhouseDir --requirement $requirements
}
$wheels = @(Get-ChildItem -LiteralPath $wheelhouseDir -Filter '*.whl' -File)
if ($wheels.Count -eq 0) {
    throw 'No wheel files were downloaded.'
}
$pysideProvenance = Join-Path $bundleRoot '_PYSIDE_FILTER_PROVENANCE.json'
Invoke-Checked 'remove unused GPL-only Qt modules from the Essentials wheel' {
    & $PythonExe $licenseScript filter-pyside --wheelhouse $wheelhouseDir --provenance $pysideProvenance
}
$thirdPartyManifest = Join-Path $bundleRoot 'THIRD_PARTY_MANIFEST.json'
Invoke-Checked 'collect wheel metadata and license materials' {
    & $PythonExe $licenseScript collect-wheels --wheelhouse $wheelhouseDir --output $licenseRoot --manifest $thirdPartyManifest --provenance $pysideProvenance
}
Remove-Item -LiteralPath $pysideProvenance -Force
$wheels = @(Get-ChildItem -LiteralPath $wheelhouseDir -Filter '*.whl' -File)

$verifyVenv = Join-Path $OutputDirectory '_verify_py312_venv'
Remove-BuildTarget $verifyVenv
try {
    Invoke-Checked 'create temporary verification environment' {
        & $PythonExe -m venv $verifyVenv
    }
    $verifyPython = Join-Path $verifyVenv 'Scripts\python.exe'
    $env:PIP_NO_INDEX = '1'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $env:PIP_CONFIG_FILE = 'NUL'
    Invoke-Checked 'offline-only wheel installation test' {
        & $verifyPython -m pip install --no-index --find-links $wheelhouseDir --requirement $requirements
    }
    Invoke-Checked 'runtime import test' {
        & $verifyPython -c "import os,struct,sys; assert sys.version_info[:2] == (3,12); assert struct.calcsize('P') == 8; os.environ['QT_QPA_PLATFORM']='offscreen'; import pydicom,numpy,scipy,numba,matplotlib,reportlab,pyqtgraph; from PySide6 import QtCore,QtGui,QtWidgets; app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); assert app; print('Runtime and offscreen Qt imports: OK')"
    }
}
finally {
    Remove-Item Env:PIP_NO_INDEX -ErrorAction SilentlyContinue
    Remove-Item Env:PIP_DISABLE_PIP_VERSION_CHECK -ErrorAction SilentlyContinue
    Remove-Item Env:PIP_CONFIG_FILE -ErrorAction SilentlyContinue
    Remove-BuildTarget $verifyVenv
}

$buildTime = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$bundleInfo = @"
GPR-comparing Windows offline bundle
Bundle format: 1
Git commit: $commit
Python: $PythonVersion (64-bit)
Platform: Windows x64
Built UTC: $buildTime
Python source: $pythonUri
Wheel count: $($wheels.Count)
Python installer SHA-256: $pythonInstallerSha256

Install: double-click INSTALL_OFFLINE.bat
Launch:  double-click LAUNCH_GPR_COMPARING.bat
Verify:  double-click RUN_SMOKE_TEST.bat
"@
Set-Content -LiteralPath (Join-Path $bundleRoot 'BUNDLE_INFO.txt') -Value $bundleInfo -Encoding UTF8

$manifestPath = Join-Path $bundleRoot 'SHA256SUMS.txt'
$mutableRelativePaths = @('app/config/gui_config.ini')
$hashLines = foreach ($file in Get-ChildItem -LiteralPath $bundleRoot -Recurse -File | Sort-Object FullName) {
    if ($file.FullName -eq $manifestPath) { continue }
    $relative = $file.FullName.Substring($bundleRoot.Length + 1) -replace '\\', '/'
    if ($relative -in $mutableRelativePaths) { continue }
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash *$relative"
}
Set-Content -LiteralPath $manifestPath -Value $hashLines -Encoding UTF8

& (Join-Path $bundleRoot 'VERIFY_BUNDLE.ps1') -BundleRoot $bundleRoot
if ($LASTEXITCODE -ne 0) { throw 'Final bundle verification failed.' }
Invoke-Checked 'verify licensing coverage and excluded content' {
    & $PythonExe (Join-Path $appDir 'offline\license_compliance.py') verify-bundle --bundle $bundleRoot
}

if (-not $SkipArchive) {
    Write-Host '[RUN] create USB transfer ZIP'
    Compress-Archive -Path $bundleRoot -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Host "[OK ] ZIP created: $archivePath"
}

Write-Host ''
Write-Host '[SUCCESS] Offline bundle is ready.'
Write-Host "Folder: $bundleRoot"
if (-not $SkipArchive) { Write-Host "ZIP:    $archivePath" }
