<#
Generic auto-fallback runner for RTDOSE gamma.

Phase A: Run absolute-geometry 3D (opt-shift=off, norm=none).
If pass rate < threshold OR warnings indicate geometry issues, then
Phase B: Run best-shift search with a wide range and re-evaluate 2D axial with the fixed best shift.

Usage examples:
  # Test02
  # powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_autofallback.ps1 -Name Test02_auto -Ref "dicom/Test02/PHITS_Iris_10_rtdose.dcm" -Eval "dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm"

Parameters:
  -Name   : subfolder name under output/rtgamma
  -Ref    : path to reference RTDOSE DICOM
  -Eval   : path to evaluation RTDOSE DICOM
  -Threshold : pass rate (%) below which to trigger fallback (default 85)
  -Range  : shift-range spec for fallback (default x:-150:150:5,y:-50:50:5,z:-50:50:5)
#>

param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$Ref,
  [Parameter(Mandatory=$true)][string]$Eval,
  [double]$Threshold = 85.0,
  [string]$Range = "x:-150:150:5,y:-50:50:5,z:-50:50:5"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$outDir  = "phits-linac-validation/output/rtgamma"
$testDir = Join-Path $outDir $Name
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

function Write-Line($s) { Write-Host $s }

Write-Line "[A] 3D absolute geometry (opt-shift=off, norm=none)"
$absBase = Join-Path $testDir "abs_3d"
python -m rtgamma.main --mode 3d --opt-shift off --norm none --dd 3 --dta 2 --cutoff 10 `
  --ref $Ref --eval $Eval --report $absBase

if (-not (Test-Path ("{0}.json" -f $absBase))) { throw "Missing JSON: $absBase.json" }
$absJson = Get-Content -Raw -Path ("{0}.json" -f $absBase) | ConvertFrom-Json
[double]$absPass = $absJson.pass_rate_percent
$warnings = [string]$absJson.warnings
$sameFor = [bool]$absJson.same_for_uid
$oriDot  = [double]$absJson.orientation_min_dot
Write-Line ("[A] pass={0:F1}%, same_for={1}, min_dot={2}, warnings='{3}'" -f $absPass, $sameFor, $oriDot, $warnings)

$doFallback = $false
if ($absPass -lt $Threshold) { $doFallback = $true }
if (-not [string]::IsNullOrWhiteSpace($warnings)) { $doFallback = $true }

$summary = @()
$summary += "Auto-Fallback Gamma Run ($Name)"
$summary += ""
$summary += "Inputs"
$summary += "- ref : $Ref"
$summary += "- eval: $Eval"
$summary += ""
$summary += "Phase A: Absolute geometry"
$summary += ("- pass_rate_percent: {0:F1}%" -f $absPass)
$summary += ("- same_for_uid: {0}" -f $sameFor)
if ($oriDot -is [double]) { $summary += ("- orientation_min_dot: {0}" -f $oriDot) }
if (-not [string]::IsNullOrWhiteSpace($warnings)) { $summary += ("- warnings: {0}" -f $warnings) }

if ($doFallback) {
  Write-Line "[B] Fallback: best-shift 3D search"
  $bestBase = Join-Path $testDir "best_3d"
  python -m rtgamma.main --mode 3d --opt-shift on --shift-range $Range --refine coarse2fine `
    --norm none --dd 3 --dta 2 --cutoff 10 --ref $Ref --eval $Eval --report $bestBase

  if (-not (Test-Path ("{0}.json" -f $bestBase))) { throw "Missing JSON: $bestBase.json" }
  $bestJson = Get-Content -Raw -Path ("{0}.json" -f $bestBase) | ConvertFrom-Json
  [double]$bestPass = $bestJson.pass_rate_percent
  $dx = [double]$bestJson.best_shift_mm[0]
  $dy = [double]$bestJson.best_shift_mm[1]
  $dz = [double]$bestJson.best_shift_mm[2]
  $culture = [System.Globalization.CultureInfo]::InvariantCulture
  $dxS = $dx.ToString("0.###", $culture)
  $dyS = $dy.ToString("0.###", $culture)
  $dzS = $dz.ToString("0.###", $culture)
  $fixSpec = ("x:{0}:{0}:1,y:{1}:{1}:1,z:{2}:{2}:1" -f $dxS, $dyS, $dzS)

  Write-Line ("[B] best_shift=({0},{1},{2}) mm, pass={3:F1}%" -f $dxS,$dyS,$dzS,$bestPass)

  Write-Line "[B] 2D axial re-eval with fixed best shift"
  $bestAx = Join-Path $testDir "best_axial"
  python -m rtgamma.main --mode 2d --plane axial --plane-index auto `
    --opt-shift on --shift-range $fixSpec --refine none `
    --norm none --dd 3 --dta 2 --cutoff 10 `
    --ref $Ref --eval $Eval --report $bestAx

  $summary += ""
  $summary += "Phase B: Best-shift search"
  $summary += ("- range: {0}" -f $Range)
  $summary += ("- best_shift_mm: ({0}, {1}, {2})" -f $dxS,$dyS,$dzS)
  $summary += ("- 3D pass_rate_percent: {0:F1}%" -f $bestPass)
  if (Test-Path ("{0}.json" -f $bestAx)) {
    $ax = Get-Content -Raw -Path ("{0}.json" -f $bestAx) | ConvertFrom-Json
    $summary += ("- 2D axial pass_rate_percent: {0:F1}%" -f [double]$ax.pass_rate_percent)
  }
} else {
  Write-Line "[B] Fallback skipped: Phase A met threshold and had no warnings"
  $summary += ""
  $summary += "Phase B: Skipped (threshold met; no warnings)"
}

$sumPath = Join-Path $testDir "autofallback_summary.txt"
$summary | Out-File -FilePath $sumPath -Encoding UTF8 -Force
Write-Line ("Summary written to: {0}" -f $sumPath)
