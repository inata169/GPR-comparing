[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BundledPythonDir,
    [Parameter(Mandatory = $true)]
    [string]$SelectedPythonPathFile,
    [string]$VenvDir,
    [string[]]$CandidatePath = @(),
    [switch]$SkipSystemDiscovery
)

$ErrorActionPreference = 'Stop'
$bundledRoot = [IO.Path]::GetFullPath($BundledPythonDir).TrimEnd('\')
$selectedPathFile = [IO.Path]::GetFullPath($SelectedPythonPathFile)
$candidatePaths = New-Object 'System.Collections.Generic.List[string]'
$installedProducts = New-Object 'System.Collections.Generic.List[string]'

if (Test-Path -LiteralPath $selectedPathFile) {
    Remove-Item -LiteralPath $selectedPathFile -Force
}

function Add-PythonCandidate {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim().Trim('"'))
    if (Test-Path -LiteralPath $expanded -PathType Container) {
        $expanded = Join-Path $expanded 'python.exe'
    }
    if (-not (Test-Path -LiteralPath $expanded -PathType Leaf)) { return }

    try {
        $resolved = [IO.Path]::GetFullPath($expanded)
    }
    catch {
        return
    }
    if (-not $candidatePaths.Contains($resolved)) {
        $candidatePaths.Add($resolved)
    }
}

function Get-PythonInfo {
    param([string]$PythonPath)

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $PythonPath
    $psi.Arguments = '-I -c "import json,struct,sys;print(json.dumps({''implementation'':sys.implementation.name,''version'':list(sys.version_info[:3]),''bits'':struct.calcsize(''P'')*8}))"'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    try {
        $process = [System.Diagnostics.Process]::Start($psi)
        if (-not $process.WaitForExit(5000)) {
            $process.Kill()
            return $null
        }
        if ($process.ExitCode -ne 0) { return $null }
        $output = $process.StandardOutput.ReadToEnd().Trim()
        if ([string]::IsNullOrWhiteSpace($output)) { return $null }
        return $output | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

foreach ($path in $CandidatePath) {
    Add-PythonCandidate $path
}

if (-not $SkipSystemDiscovery) {
    foreach ($command in Get-Command python.exe -All -ErrorAction SilentlyContinue) {
        Add-PythonCandidate $command.Source
    }

    try {
        foreach ($path in & where.exe python.exe 2>$null) {
            Add-PythonCandidate $path
        }
    }
    catch {}

    $pythonRegistryRoots = @(
        'HKCU:\Software\Python\PythonCore',
        'HKLM:\Software\Python\PythonCore',
        'HKLM:\Software\WOW6432Node\Python\PythonCore'
    )
    foreach ($root in $pythonRegistryRoots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        foreach ($versionKey in Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue) {
            if ($versionKey.PSChildName -notmatch '^3\.12(?:\.|$)') { continue }
            $installKey = Join-Path $versionKey.PSPath 'InstallPath'
            if (-not (Test-Path -LiteralPath $installKey)) { continue }
            try {
                $key = Get-Item -LiteralPath $installKey -ErrorAction Stop
                Add-PythonCandidate ([string]$key.GetValue('ExecutablePath', $null))
                Add-PythonCandidate ([string]$key.GetValue('', $null))
            }
            catch {}
        }
    }

    $uninstallRoots = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $uninstallRoots) {
        foreach ($product in Get-ItemProperty -Path $root -ErrorAction SilentlyContinue) {
            $displayName = [string]$product.DisplayName
            if ($displayName -match '^Python 3\.12(?:\.\d+)?(?:\s|$)' -and -not $installedProducts.Contains($displayName)) {
                $installedProducts.Add($displayName)
            }
        }
    }
}

$compatiblePythons = New-Object 'System.Collections.Generic.List[object]'
foreach ($path in $candidatePaths) {
    $normalized = [IO.Path]::GetFullPath($path)
    if ($normalized.StartsWith($bundledRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        continue
    }
    $info = Get-PythonInfo $normalized
    if ($null -eq $info) { continue }
    if ($info.implementation -eq 'cpython' -and $info.version[0] -eq 3 -and $info.version[1] -eq 12 -and $info.bits -eq 64) {
        $compatiblePythons.Add([PSCustomObject]@{
            Path = $normalized
            Version = ($info.version -join '.')
            Patch = [int]$info.version[2]
        })
    }
}

if ($compatiblePythons.Count -gt 0) {
    $selected = @($compatiblePythons | Sort-Object `
        @{ Expression = { if ($_.Patch -eq 10) { 0 } else { 1 } } }, `
        @{ Expression = { $_.Path } })[0]
    $selectedParent = Split-Path -Parent $selectedPathFile
    if (-not (Test-Path -LiteralPath $selectedParent)) {
        New-Item -ItemType Directory -Path $selectedParent -Force | Out-Null
    }
    [IO.File]::WriteAllText(
        $selectedPathFile,
        $selected.Path,
        (New-Object Text.UTF8Encoding($false))
    )
    if (-not [string]::IsNullOrWhiteSpace($VenvDir)) {
        $resolvedVenvDir = [IO.Path]::GetFullPath($VenvDir)
        Write-Host '[RUN] Creating the dedicated application environment with the selected Python.'
        & $selected.Path -m venv $resolvedVenvDir
        if ($LASTEXITCODE -ne 0) {
            Remove-Item -LiteralPath $selectedPathFile -Force -ErrorAction SilentlyContinue
            Write-Error "The selected external Python could not create the dedicated environment (exit $LASTEXITCODE)."
            exit 13
        }
        $venvPython = Join-Path $resolvedVenvDir 'Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            Remove-Item -LiteralPath $selectedPathFile -Force -ErrorAction SilentlyContinue
            Write-Error "The selected external Python did not create: $venvPython"
            exit 13
        }
        Write-Host '[OK] Dedicated application environment created.'
    }
    Write-Host '[OK] Compatible external Python 3.12 x64 installation detected.'
    Write-Host "  Executable: $($selected.Path) (Python $($selected.Version), 64-bit)"
    Write-Host 'It will only create the dedicated app virtual environment; the external installation and global packages will not be changed.'
    exit 0
}

if ($installedProducts.Count -gt 0) {
    Write-Host '[SAFETY STOP] An existing external Python 3.12 installation was detected.'
    foreach ($product in $installedProducts) {
        Write-Host "  Registered product: $product"
    }
    Write-Host 'No runnable compatible CPython 3.12 x64 executable was found.'
    Write-Host 'The bundled Python installer was not started, so the registered Python installation was not changed.'
    exit 12
}

Write-Host '[OK] No external Python 3.12 x64 installation was detected.'
exit 0
