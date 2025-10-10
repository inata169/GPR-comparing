# Test Plan (Manual Regression)

## Scope
Covers core gamma workflows: DICOM I/O, resampling, shift optimization, gamma computation, and reporting.

## Test Matrix
1) Self-compare (sanity)
- Command: `python -m rtgamma.main --ref dicom/RTDOSE_...7605.1.dcm --eval dicom/RTDOSE_...7605.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/self_check`
- Expected: pass rate ~100%, best shift (0,0,0).

2) Cross-pair 3D (default 3%/2mm/10%)
- Command: `python -m rtgamma.main --ref dicom/RTDOSE_...7605.1.dcm --eval dicom/RTDOSE_...9109.1.dcm --mode 3d --report phits-linac-validation/output/rtgamma/pair_3d`
- Expected (reference run): pass ~0.43% ±0.2%; small negative dx best shift.

3) Cross-pair 3D (3%/3mm/10%)
- Command: `python -m rtgamma.main --dd 3 --dta 3 --cutoff 10 --ref <ref> --eval <eval> --mode 3d --report .../pair_3d_3by3`
- Expected (reference run): pass ~1.1% ±0.3%.

4) 2D visuals (axial/sagittal/coronal)
- Commands: use `--mode 2d --plane <axis> --plane-index <n> --save-gamma-map ... --save-dose-diff ...`
- Expected: images generated, gamma high in mismatch regions; diff shows spatial pattern.

5) PHITS vs RTD.deposit sample
- Command: `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report .../phits_vs_rtd`
- Expected (reference run): pass ~0.16%.

## Acceptance Criteria
- Commands complete without exceptions.
- Reports written (CSV/JSON/MD) with plausible stats and search logs.
- Self-compare meets 100%; cross-pairs within expected bands.
