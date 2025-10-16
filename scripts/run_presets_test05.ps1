Param(
  [string]$OutDir = "phits-linac-validation/output/rtgamma"
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $here)

# Ensure PYTHONPATH points to project root
$env:PYTHONPATH = (Get-Location).Path

$ref = 'dicom/Test05/AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
$eval = 'dicom/Test05/AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host '== Header compare (Test05) =='
python scripts/compare_rtdose_headers.py --a $ref --b $eval --out (Join-Path $OutDir 'Test05_dose_compare.md')

Write-Host '== 3D absolute geometry baseline (opt-shift off, norm none) =='
python -m rtgamma.main --ref $ref --eval $eval --mode 3d --opt-shift off --norm none --dd 3 --dta 2 --cutoff 10 --report (Join-Path $OutDir 'Test05_abs')

Write-Host '== 3D optimized (2-stage with prescan + early stop) =='
python -m rtgamma.main --ref $ref --eval $eval --mode 3d --shift-range "x:-10:10:2,y:-10:10:2,z:-10:10:2" --fine-range-mm 5 --fine-step-mm 1 --early-stop-patience 200 --report (Join-Path $OutDir 'Test05_3d')

Write-Host '== 2D central-slice images (axial/sagittal/coronal; opt-shift off) =='
python -m rtgamma.main --ref $ref --eval $eval --mode 2d --plane axial --plane-index auto --opt-shift off --norm global_max --dd 3 --dta 2 --cutoff 10 --save-gamma-map (Join-Path $OutDir 'Test05_axial_gamma.png') --save-dose-diff (Join-Path $OutDir 'Test05_axial_diff.png') --report (Join-Path $OutDir 'Test05_axial')
python -m rtgamma.main --ref $ref --eval $eval --mode 2d --plane sagittal --plane-index auto --opt-shift off --norm global_max --dd 3 --dta 2 --cutoff 10 --save-gamma-map (Join-Path $OutDir 'Test05_sagittal_gamma.png') --save-dose-diff (Join-Path $OutDir 'Test05_sagittal_diff.png') --report (Join-Path $OutDir 'Test05_sagittal')
python -m rtgamma.main --ref $ref --eval $eval --mode 2d --plane coronal --plane-index auto --opt-shift off --norm global_max --dd 3 --dta 2 --cutoff 10 --save-gamma-map (Join-Path $OutDir 'Test05_coronal_gamma.png') --save-dose-diff (Join-Path $OutDir 'Test05_coronal_diff.png') --report (Join-Path $OutDir 'Test05_coronal')

Write-Host '== Summary (Markdown + PDF) =='
python scripts/make_summary.py --case Test05 --out-dir $OutDir

Write-Host 'Done.'

