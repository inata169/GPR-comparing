# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- ROI/RTSTRUCT-based masking (planned)
- Local search (Nelder–Mead) option (planned)
- Optional GPU (CuPy) backend (investigating)

## [0.1.0] - 2025-10-23
### Added
- Local gamma support (`--gamma-type local`) with GUI toggle.
- OpenSpec documentation under `docs/openspec/` (README, TEMPLATE, report.schema.json, examples, GUI guide).
- Validators: `scripts/validate_report.py` (JSON schema), `scripts/compare_slice_gpr.py` (3D slice vs 2D).
- Synthetic, DICOM-free tests: `tests/test_cli_help.py`, `tests/test_gamma_synthetic.py`.
- Japanese README: `README_JA.md` and GUI screenshot reference.
- CI: GitHub Actions for Windows and Ubuntu with Python 3.10–3.12.

### Changed
- README normalized to UTF-8 (no BOM) and updated with latest guidance and CI badge.
- GUI script (`scripts/run_gui.ps1`): Local gamma checkbox; minor docs links.

### Fixed
- 2D fast path normalization aligned with 3D (use full-volume reference max for global/max_ref), fixing coronal slice GPR consistency.
- CI stability: DICOM-dependent tests now skip when sample data is absent.

### Notes
- Coronal GPR investigation notes updated in OpenSpec with post-fix behavior.

## [2025-10-15]
### Added
- Report fields: `ref_for_uid`, `eval_for_uid`, `same_for_uid`, `best_shift_mag_mm`, `absolute_geometry_only`, `orientation_min_dot`, `warnings`.
- Console warnings for FoR mismatch and large shifts; CLI `--warn-large-shift-mm`.
- PowerShell: `scripts/run_autofallback.ps1` (auto-fallback from absolute geometry to wide best-shift), `run_test02_abs_vs_bestshift.ps1`, `run_test02_wide_bestshift.ps1`.
- Utility: `scripts/compare_rtdose_headers.py` (Markdown diff of RTDOSE geometry/scale).

### Fixed
- PowerShell string interpolation with colons in shift spec (use `-f` formatting) to avoid parser errors.

### Notes
- Test04 (6MV vs 10MV) absolute geometry yields ~60% GPR (expected due to energy profile differences).
- Test01/03 (SSD=100 cm) vs Test02/04 (SCD=100 cm) suggest setup discrepancy as a primary cause of low GPR in earlier runs.

## [2025-10-10]
### Added
- Documentation overhaul: README streamlined; AGENTS.md (contributor guide).
- Troubleshooting, Test Plan, Decisions (ADR) docs.

### Changed
- DICOM Z-slice order handling: synchronize `GridFrameOffsetVector` (GFOV) with dose frames by reordering in ascending GFOV.
- Origin offset correction: project IPP delta onto reference row/col/slice directions for robust alignment across orientations.
- Shift application: convert axis shifts (dx,dy,dz along ref axes) to an LPS vector before resampling.
- Output directory handling: guard against empty dirname when creating folders.

### Fixed
- Occasional `FileNotFoundError` when output directory didn’t exist.
- Missing `TransferSyntaxUID` handled by defaulting to ImplicitVRLittleEndian when absent.
- Minor scoping/name issues in optimization flow.

### Notes
- Self-compare pass rate is 100% (expected). Cross-system pairs with different grid sizes/scales naturally yield low pass rates; this is data-driven, not a software defect.
