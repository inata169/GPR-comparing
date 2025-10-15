<#
Runs Test02 in two phases and writes a consolidated summary:
  A) Absolute geometry only (opt-shift=off, norm=none), 3D + 2D central axial/coronal/sagittal
  B) Best-shift search (±3 mm, 1 mm step, coarse→fine) for 3D, then 2D axial with that fixed shift

Outputs under phits-linac-validation/output/rtgamma/Test02/.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ref  = "dicom/Test02/PHITS_Iris_10_rtdose.dcm"
$eval = "dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm"

$outDir  = "phits-linac-validation/output/rtgamma"
$testDir = Join-Path $outDir "Test02"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

# -------------------------
# Phase A: Absolute geometry
# -------------------------
Write-Host "[A] Absolute geometry (3D)" -ForegroundColor Cyan
$abs3d = Join-Path $testDir "abs_3d"
python -m rtgamma.main --mode 3d --opt-shift off --norm none --dd 3 --dta 2 --cutoff 10 `
  --ref $ref --eval $eval --report $abs3d

Write-Host "[A] Absolute geometry (2D central slices)" -ForegroundColor Cyan
$planes = @("axial","coronal","sagittal")
$abs2dResults = @()
foreach ($p in $planes) {
  $base = Join-Path $testDir ("abs_" + $p)
  python -m rtgamma.main --mode 2d --plane $p --plane-index auto --opt-shift off --norm none --dd 3 --dta 2 --cutoff 10 `
    --ref $ref --eval $eval --save-gamma-map ("{0}_gamma.png" -f $base) --save-dose-diff ("{0}_diff.png" -f $base) --report $base
  if (Test-Path ("{0}.json" -f $base)) {
    $s = Get-Content -Raw -Path ("{0}.json" -f $base) | ConvertFrom-Json
    $abs2dResults += [PSCustomObject]@{
      plane         = $s.plane
      plane_index   = $s.plane_index
      pass_rate_pct = [double]$s.pass_rate_percent
    }
  }
}

# -------------------------
# Phase B: Best-shift search
# -------------------------
Write-Host "[B] Best-shift search (3D, ±3 mm)" -ForegroundColor Cyan
$best3d = Join-Path $testDir "best_3d"
python -m rtgamma.main --mode 3d --opt-shift on --shift-range "x:-3:3:1,y:-3:3:1,z:-3:3:1" --refine coarse2fine `
  --norm none --dd 3 --dta 2 --cutoff 10 --ref $ref --eval $eval --report $best3d

$bestJsonPath = "$best3d.json"
if (-not (Test-Path $bestJsonPath)) { throw "Best 3D JSON not found: $bestJsonPath" }
$best = Get-Content -Raw -Path $bestJsonPath | ConvertFrom-Json
[double]$dx = $best.best_shift_mm[0]
[double]$dy = $best.best_shift_mm[1]
[double]$dz = $best.best_shift_mm[2]
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$dxS = $dx.ToString("0.###", $culture)
$dyS = $dy.ToString("0.###", $culture)
$dzS = $dz.ToString("0.###", $culture)
$shiftSpec = ("x:{0}:{0}:1,y:{1}:{1}:1,z:{2}:{2}:1" -f $dxS, $dyS, $dzS)

Write-Host ("[B] Re-running 2D axial with fixed best shift: ({0}, {1}, {2}) mm" -f $dxS, $dyS, $dzS) -ForegroundColor Cyan
$bestAx = Join-Path $testDir "best_axial"
python -m rtgamma.main --mode 2d --plane axial --plane-index auto --opt-shift on --shift-range $shiftSpec --refine none `
  --norm none --dd 3 --dta 2 --cutoff 10 --ref $ref --eval $eval --save-gamma-map ("{0}_gamma.png" -f $bestAx) `
  --save-dose-diff ("{0}_diff.png" -f $bestAx) --report $bestAx

# -------------------------
# Consolidated summary
# -------------------------
$abs3dJson = Get-Content -Raw -Path ("{0}.json" -f $abs3d) | ConvertFrom-Json
$best3dJson = $best

$summary = @()
$summary += "RTDOSE Gamma Summary (Test02)"
$summary += ""
$summary += "Inputs"
$summary += "- ref: $ref"
$summary += "- eval: $eval"
$summary += ""
$summary += "Phase A: Absolute geometry only (opt-shift=off, norm=none, dd=3, dta=2, cutoff=10)"
$summary += ("- 3D pass_rate_percent: {0:F1}%" -f [double]$abs3dJson.pass_rate_percent)
foreach ($r in $abs2dResults) {
  $summary += ("- 2D {0} (index={1}) pass_rate_percent: {2:F1}%" -f $r.plane, $r.plane_index, $r.pass_rate_pct)
}
$summary += ""
$summary += "Phase B: Best-shift search (±3 mm, coarse→fine, norm=none)"
$summary += ("- 3D best pass_rate_percent: {0:F1}%" -f [double]$best3dJson.pass_rate_percent)
$summary += ("- best_shift_mm: ({0}, {1}, {2})" -f $dxS, $dyS, $dzS)
if (Test-Path ("{0}.json" -f $bestAx)) {
  $bax = Get-Content -Raw -Path ("{0}.json" -f $bestAx) | ConvertFrom-Json
  $summary += ("- 2D axial (with best shift) pass_rate_percent: {0:F1}%" -f [double]$bax.pass_rate_percent)
}

$cmpPath = Join-Path $testDir "compare_abs_vs_bestshift.txt"
$summary | Out-File -FilePath $cmpPath -Encoding UTF8 -Force

Write-Host ""
Write-Host ("Summary written to: {0}" -f $cmpPath) -ForegroundColor Green
Write-Host "Reports and images under: $testDir"
