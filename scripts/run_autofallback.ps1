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
  [string]$CoarseRange = "x:-150:150:10,y:-30:30:10,z:-30:30:10"
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
  Write-Line "[B] Fallback Stage 1: Coarse 3D search"
  $coarseBase = Join-Path $testDir "coarse_3d"
  python -m rtgamma.main --mode 3d --opt-shift on --shift-range $CoarseRange --refine none `
    --norm none --dd 3 --dta 2 --cutoff 10 --ref $Ref --eval $Eval --report $coarseBase

  if (-not (Test-Path ("{0}.json" -f $coarseBase))) { throw "Missing JSON: $coarseBase.json" }
  $coarseJson = Get-Content -Raw -Path ("{0}.json" -f $coarseBase) | ConvertFrom-Json
  [double]$coarsePass = $coarseJson.pass_rate_percent
  $cx = [double]$coarseJson.best_shift_mm[0]
  $cy = [double]$coarseJson.best_shift_mm[1]
  $cz = [double]$coarseJson.best_shift_mm[2]
  $culture = [System.Globalization.CultureInfo]::InvariantCulture
  $c_x0 = ($cx - 10).ToString("0.###", $culture)
  $c_x1 = ($cx + 10).ToString("0.###", $culture)
  $c_y0 = ($cy - 10).ToString("0.###", $culture)
  $c_y1 = ($cy + 10).ToString("0.###", $culture)
  $c_z0 = ($cz - 10).ToString("0.###", $culture)
  $c_z1 = ($cz + 10).ToString("0.###", $culture)

  Write-Line ("[B] coarse best_shift=({0},{1},{2}) mm, pass={3:F1}%" -f $cx,$cy,$cz,$coarsePass)

  Write-Line "[C] Fallback Stage 2: Fine 3D search"
  $fineRange = ("x:{0}:{1}:1,y:{2}:{3}:1,z:{4}:{5}:1" -f $c_x0, $c_x1, $c_y0, $c_y1, $c_z0, $c_z1)
  $fineBase = Join-Path $testDir "fine_3d"
  python -m rtgamma.main --mode 3d --opt-shift on --shift-range $fineRange --refine none `
    --norm none --dd 3 --dta 2 --cutoff 10 --ref $Ref --eval $Eval --report $fineBase

  if (-not (Test-Path ("{0}.json" -f $fineBase))) { throw "Missing JSON: $fineBase.json" }
  $fineJson = Get-Content -Raw -Path ("{0}.json" -f $fineBase) | ConvertFrom-Json
  [double]$finePass = $fineJson.pass_rate_percent
  $fx = [double]$fineJson.best_shift_mm[0]
  $fy = [double]$fineJson.best_shift_mm[1]
  $fz = [double]$fineJson.best_shift_mm[2]
  $fxS = $fx.ToString("0.###", $culture)
  $fyS = $fy.ToString("0.###", $culture)
  $fzS = $fz.ToString("0.###", $culture)
  $fixSpec = ("x:{0}:{0}:1,y:{1}:{1}:1,z:{2}:{2}:1" -f $fxS, $fyS, $fzS)

  Write-Line ("[C] fine best_shift=({0},{1},{2}) mm, pass={3:F1}%" -f $fxS,$fyS,$fzS,$finePass)

  Write-Line "[D] 2D axial re-eval with fixed best shift"
  $bestAx = Join-Path $testDir "best_axial"
  python -m rtgamma.main --mode 2d --plane axial --plane-index auto `
    --opt-shift on --shift-range $fixSpec --refine none `
    --norm none --dd 3 --dta 2 --cutoff 10 `
    --ref $Ref --eval $Eval --report $bestAx

  $summary += ""
  $summary += "Phase B: Coarse-shift search"
  $summary += ("- range: {0}" -f $CoarseRange)
  $summary += ("- coarse_shift_mm: ({0}, {1}, {2})" -f $cx,$cy,$cz)
  $summary += ("- pass_rate_percent: {0:F1}%" -f $coarsePass)

  $summary += ""
  $summary += "Phase C: Fine-shift search"
  $summary += ("- range: {0}" -f $fineRange)
  $summary += ("- best_shift_mm: ({0}, {1}, {2})" -f $fxS,$fyS,$fzS)
  $summary += ("- pass_rate_percent: {0:F1}%" -f $finePass)
  
  $fineWarnings = [string]$fineJson.warnings
  if (-not [string]::IsNullOrWhiteSpace($fineWarnings)) { $summary += ("- warnings: {0}" -f $fineWarnings) }

  if (Test-Path ("{0}.json" -f $bestAx)) {
    $summary += ""
    $summary += "Phase D: 2D Axial Fixed-Shift"
    $ax = Get-Content -Raw -Path ("{0}.json" -f $bestAx) | ConvertFrom-Json
    $summary += ("- pass_rate_percent: {0:F1}%" -f [double]$ax.pass_rate_percent)
  }
} else {
  Write-Line "[B] Fallback skipped: Phase A met threshold and had no warnings"
  $summary += ""
  $summary += "Phase B/C: Skipped (threshold met; no warnings)"
}

$sumPath = Join-Path $testDir "autofallback_summary.txt"
$summary | Out-File -FilePath $sumPath -Encoding UTF8 -Force
Write-Line ("Summary written to: {0}" -f $sumPath)

