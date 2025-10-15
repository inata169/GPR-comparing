<#
Runs 2D gamma for Test02 with zero fixed shift on axial, coronal, sagittal (central slice),
then writes a concise summary text under phits-linac-validation/output/rtgamma/Test02/.

Ref/Eval:
- ref  = dicom/Test02/PHITS_Iris_10_rtdose.dcm
- eval = dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm

Settings:
- shift fixed (dx,dy,dz) = (0,0,0) mm, refine none
- DD=3%, DTA=2 mm, Cutoff=10%, norm=none (absolute dose), global gamma
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ref  = "dicom/Test02/PHITS_Iris_10_rtdose.dcm"
$eval = "dicom/Test02/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm"

$outDir = "phits-linac-validation/output/rtgamma"
$testDir = Join-Path $outDir "Test02"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$commonArgs = @(
  "--opt-shift","on",
  "--shift-range","x:0:0:1,y:0:0:1,z:0:0:1",
  "--refine","none",
  "--dd","3","--dta","2","--cutoff","10",
  "--norm","none",
  "--log-level","INFO"
)

function Run-Plane {
  param(
    [Parameter(Mandatory=$true)][string]$Plane,
    [Parameter(Mandatory=$true)][string]$ReportBase,
    [Parameter(Mandatory=$true)][string]$GammaOut,
    [Parameter(Mandatory=$true)][string]$DiffOut
  )

  Write-Host "[$Plane] Running central slice with zero shift..."
  python -m rtgamma.main --mode 2d --plane $Plane --plane-index auto --ref $ref --eval $eval @commonArgs `
    --save-gamma-map $GammaOut `
    --save-dose-diff $DiffOut `
    --report $ReportBase

  $jsonPath = "$ReportBase.json"
  if (Test-Path $jsonPath) {
    $summary = Get-Content -Raw -Path $jsonPath | ConvertFrom-Json
    $obj = [PSCustomObject]@{
      plane         = $summary.plane
      plane_index   = $summary.plane_index
      pass_rate_pct = [double]$summary.pass_rate_percent
      best_shift_mm = $summary.best_shift_mm
      gamma_mean    = [double]$summary.gamma_mean
      gamma_median  = [double]$summary.gamma_median
      gamma_max     = [double]$summary.gamma_max
    }
    return $obj
  } else {
    Write-Warning "Summary JSON not found: $jsonPath"
    return $null
  }
}

$results = @()
$results += Run-Plane -Plane axial    -ReportBase (Join-Path $outDir "Test02_axial")    -GammaOut (Join-Path $outDir "Test02_axial_gamma.png")    -DiffOut (Join-Path $outDir "Test02_axial_diff.png")
$results += Run-Plane -Plane coronal  -ReportBase (Join-Path $outDir "Test02_coronal")  -GammaOut (Join-Path $outDir "Test02_coronal_gamma.png")  -DiffOut (Join-Path $outDir "Test02_coronal_diff.png")
$results += Run-Plane -Plane sagittal -ReportBase (Join-Path $outDir "Test02_sagittal") -GammaOut (Join-Path $outDir "Test02_sagittal_gamma.png") -DiffOut (Join-Path $outDir "Test02_sagittal_diff.png")

Write-Host ""
Write-Host "Summary (central slices, zero shift):" -ForegroundColor Cyan
$results | Format-Table -AutoSize

# Write consolidated summary.txt
$first = $results | Where-Object { $_ -ne $null } | Select-Object -First 1
$summaryText = @()
$summaryText += "RTDOSE Gamma Summary (Test02, PHITS vs CyberKnife)"
$summaryText += ""
$summaryText += "Inputs"
$summaryText += "- ref: $ref"
$summaryText += "- eval: $eval"
$summaryText += ""
$summaryText += "Settings"
$summaryText += "- mode: 2d (central slice auto)"
$summaryText += "- fixed shift (dx,dy,dz) [mm]: (0, 0, 0)"
$summaryText += "- DD / DTA / Cutoff: 3% / 2 mm / 10%"
$summaryText += "- gamma_type: global"
$summaryText += "- norm: none (absolute dose)"
$summaryText += ""
$summaryText += "Results (pass_rate_percent)"
foreach ($r in $results) {
  if ($r -ne $null) {
    $summaryText += "- $($r.plane) (plane_index=$($r.plane_index)): $([string]::Format('{0:F1}%', $r.pass_rate_pct))"
  }
}
if ($first -ne $null) {
  $summaryText += ""
  $summaryText += "Extra (from first plane)"
  $summaryText += ("- gamma_mean:   {0:F4}" -f $first.gamma_mean)
  $summaryText += ("- gamma_median: {0:F4}" -f $first.gamma_median)
  $summaryText += ("- gamma_max:   {0:F4}" -f $first.gamma_max)
}

$summaryPath = Join-Path $testDir "summary.txt"
$summaryText | Out-File -FilePath $summaryPath -Encoding UTF8 -Force

Write-Host ""
Write-Host "Summary written to: $summaryPath" -ForegroundColor Green
Write-Host "Reports and images: $outDir"

