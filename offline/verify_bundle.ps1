param(
    [string]$BundleRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $BundleRoot 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Checksum manifest not found: $manifestPath"
}

$checked = 0
foreach ($line in Get-Content -LiteralPath $manifestPath -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -notmatch '^([0-9A-Fa-f]{64}) \*(.+)$') {
        throw "Invalid checksum line: $line"
    }

    $expected = $Matches[1].ToUpperInvariant()
    $relative = $Matches[2] -replace '/', '\'
    $path = Join-Path $BundleRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Bundle file is missing: $relative"
    }

    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne $expected) {
        throw "SHA-256 mismatch: $relative"
    }
    $checked++
}

if ($checked -eq 0) {
    throw 'Checksum manifest contains no files.'
}

Write-Host "[OK] Verified $checked bundle files."
