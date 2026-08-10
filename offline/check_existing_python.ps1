[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BundledPythonDir,
    [string[]]$CandidatePath = @(),
    [switch]$SkipSystemDiscovery
)

$ErrorActionPreference = 'Stop'
$bundledRoot = [IO.Path]::GetFullPath($BundledPythonDir).TrimEnd('\')
$candidatePaths = New-Object 'System.Collections.Generic.List[string]'
$installedProducts = New-Object 'System.Collections.Generic.List[string]'

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

$conflicts = New-Object 'System.Collections.Generic.List[string]'
foreach ($path in $candidatePaths) {
    $normalized = [IO.Path]::GetFullPath($path)
    if ($normalized.StartsWith($bundledRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        continue
    }
    $info = Get-PythonInfo $normalized
    if ($null -eq $info) { continue }
    if ($info.implementation -eq 'cpython' -and $info.version[0] -eq 3 -and $info.version[1] -eq 12 -and $info.bits -eq 64) {
        $conflicts.Add("$normalized (Python $($info.version -join '.'), 64-bit)")
    }
}

if ($conflicts.Count -gt 0 -or $installedProducts.Count -gt 0) {
    Write-Host '[SAFETY STOP] An existing external Python 3.12 installation was detected.'
    foreach ($conflict in $conflicts) {
        Write-Host "  Executable: $conflict"
    }
    foreach ($product in $installedProducts) {
        Write-Host "  Registered product: $product"
    }
    Write-Host 'The bundled Python installer was not started, so the existing Python installation was not changed.'
    Write-Host 'Use a clean Windows PC without Python 3.12 for the full offline acceptance test.'
    exit 12
}

Write-Host '[OK] No external Python 3.12 x64 installation was detected.'
exit 0
