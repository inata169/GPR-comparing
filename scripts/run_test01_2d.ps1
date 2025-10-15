<#
Runs 2D gamma for Test01 with x = -114 mm fixed shift on axial, coronal, sagittal (central slice).
Outputs reports (CSV/JSON/MD) and 2D images (gamma/diff) under phits-linac-validation/output/rtgamma/.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ref = "dicom/Test01/RTDOSE_2.16.840.1.114337.1.2604.1760077605.3.dcm"
$eval = "dicom/Test01/RTDOSE_2.16.840.1.114337.1.2604.1760079109.3.dcm"

# Absolute dose comparison (no normalization), DD=3%, DTA=2mm, cutoff=10%
$commonArgs = @(
    "--opt-shift","on",
    "--shift-range","x:-114:-114:1,y:0:0:1,z:0:0:1",
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

  Write-Host "[$Plane] Running central slice with x=-114 mm..."
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
    }
    return $obj
  } else {
    Write-Warning "Summary JSON not found: $jsonPath"
    return $null
  }
}

$results = @()
$results += Run-Plane -Plane axial    -ReportBase "phits-linac-validation/output/rtgamma/Test01_axial"    -GammaOut "phits-linac-validation/output/rtgamma/Test01_axial_gamma.png"    -DiffOut "phits-linac-validation/output/rtgamma/Test01_axial_diff.png"
$results += Run-Plane -Plane coronal  -ReportBase "phits-linac-validation/output/rtgamma/Test01_coronal"  -GammaOut "phits-linac-validation/output/rtgamma/Test01_coronal_gamma.png"  -DiffOut "phits-linac-validation/output/rtgamma/Test01_coronal_diff.png"
$results += Run-Plane -Plane sagittal -ReportBase "phits-linac-validation/output/rtgamma/Test01_sagittal" -GammaOut "phits-linac-validation/output/rtgamma/Test01_sagittal_gamma.png" -DiffOut "phits-linac-validation/output/rtgamma/Test01_sagittal_diff.png"

Write-Host ""
Write-Host "Summary (central slices, x=-114 mm):" -ForegroundColor Cyan
$results | Format-Table -AutoSize

Write-Host ""
Write-Host "Reports and images: phits-linac-validation/output/rtgamma/"
