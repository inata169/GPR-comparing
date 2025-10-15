<#
Wide-range best-shift search for Test02 (PHITS vs Multiplan) and 2D re-evaluation.

Phase 1: 3D best-shift search over a wide range (e.g., x: -150..150 mm, step 5 mm).
Phase 2: Re-run 2D (axial/coronal/sagittal) central slices with the fixed best shift.

Outputs go to: phits-linac-validation/output/rtgamma/Test02/
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ref  = "dicom/Test02/PHITS_Iris_10_rtdose.dcm"
$eval = "dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm"

$outDir  = "phits-linac-validation/output/rtgamma"
$testDir = Join-Path $outDir "Test02"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

# Wide search ranges (adjust here if needed)
$xStart = -150; $xEnd = 150; $xStep = 5
$yStart =  -50; $yEnd =  50; $yStep = 5
$zStart =  -50; $zEnd =  50; $zStep = 5
$shiftSpec = "x:$xStart:$xEnd:$xStep,y:$yStart:$yEnd:$yStep,z:$zStart:$zEnd:$zStep"

# Common gamma settings
$dd = 3; $dta = 2; $cut = 10

Write-Host "[Wide 3D Search] shift-range: $shiftSpec" -ForegroundColor Cyan
$wide3d = Join-Path $testDir "wide_best_3d"
python -m rtgamma.main --mode 3d --opt-shift on --shift-range $shiftSpec --refine coarse2fine `
  --norm none --dd $dd --dta $dta --cutoff $cut --ref $ref --eval $eval --report $wide3d

$bestJsonPath = "$wide3d.json"
if (-not (Test-Path $bestJsonPath)) { throw "Wide best 3D JSON not found: $bestJsonPath" }
$best = Get-Content -Raw -Path $bestJsonPath | ConvertFrom-Json
[double]$dx = $best.best_shift_mm[0]
[double]$dy = $best.best_shift_mm[1]
[double]$dz = $best.best_shift_mm[2]
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$dxS = $dx.ToString("0.###", $culture)
$dyS = $dy.ToString("0.###", $culture)
$dzS = $dz.ToString("0.###", $culture)
$fixedSpec = ("x:{0}:{0}:1,y:{1}:{1}:1,z:{2}:{2}:1" -f $dxS, $dyS, $dzS)
Write-Host ("[Best Shift] ({0}, {1}, {2}) mm" -f $dxS, $dyS, $dzS) -ForegroundColor Green
Write-Host ("3D best pass_rate_percent: {0:F1}%" -f [double]$best.pass_rate_percent)

# Re-run 2D with the fixed best shift
$planes = @("axial","coronal","sagittal")
$fixed2dResults = @()
foreach ($p in $planes) {
  $base = Join-Path $testDir ("wide_best_" + $p)
  Write-Host ("[2D] $p with fixed best shift...") -ForegroundColor Cyan
  python -m rtgamma.main --mode 2d --plane $p --plane-index auto `
    --opt-shift on --shift-range $fixedSpec --refine none `
    --norm none --dd $dd --dta $dta --cutoff $cut `
    --ref $ref --eval $eval --save-gamma-map ("{0}_gamma.png" -f $base) `
    --save-dose-diff ("{0}_diff.png" -f $base) --report $base

  $jsonPath = "$base.json"
  if (Test-Path $jsonPath) {
    $s = Get-Content -Raw -Path $jsonPath | ConvertFrom-Json
    $fixed2dResults += [PSCustomObject]@{
      plane         = $s.plane
      plane_index   = $s.plane_index
      pass_rate_pct = [double]$s.pass_rate_percent
    }
  }
}

# Consolidated summary
$sum = @()
$sum += "RTDOSE Gamma Wide-Range Search (Test02)"
$sum += ""
$sum += "Inputs"
$sum += "- ref: $ref"
$sum += "- eval: $eval"
$sum += ""
$sum += "3D Wide Search"
$sum += "- shift-range: $shiftSpec"
$sum += ("- best_shift_mm: ({0}, {1}, {2})" -f $dxS, $dyS, $dzS)
$sum += ("- best pass_rate_percent: {0:F1}%" -f [double]$best.pass_rate_percent)
$sum += ""
$sum += "2D Central Slices (fixed best shift)"
foreach ($r in $fixed2dResults) {
  $sum += ("- {0} (index={1}) pass_rate_percent: {2:F1}%" -f $r.plane, $r.plane_index, $r.pass_rate_pct)
}

$sumPath = Join-Path $testDir "wide_best_summary.txt"
$sum | Out-File -FilePath $sumPath -Encoding UTF8 -Force

Write-Host ""
Write-Host ("Summary written to: {0}" -f $sumPath) -ForegroundColor Green
Write-Host ("Reports and images under: {0}" -f $testDir)
