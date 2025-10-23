#+ rtgamma — DICOM RTDOSE Gamma Analysis (2D/3D)

Fast and reproducible gamma analysis for DICOM RTDOSE pairs with robust geometry handling, CLI/GUI, and lightweight docs/specs.

This README is normalized to UTF-8 (no BOM). For prior details, see CHANGELOG and docs under docs/openspec/.

## Features
- 2D/3D gamma with shift optimization (coarse→fine, early stop) and 2D fast path
- DICOM geometry fidelity (IPP/IOP/PixelSpacing/GFOV; GFOV-order alignment)
- Global and Local gamma selection
- CLI and Windows GUI (PowerShell/WinForms)
- Reports (CSV/JSON/MD), optional NPZ saves, and schema validation
- OpenSpec docs with examples and helper scripts

## Install
- Python 3.9+
- Dependencies:
  - `pip install pydicom numpy scipy matplotlib numba`

## Quick Start (CLI)
- 3D analysis (report only)
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/run3d`
- 2D axial (central slice, save images)
  - `python -m rtgamma.main --mode 2d --plane axial --plane-index auto --ref <ref.dcm> --eval <eval.dcm> --save-gamma-map out/gamma.png --save-dose-diff out/diff.png --report out/axial`

## Clinical Presets and Threads
- Presets: `--profile {clinical_abs,clinical_rel,clinical_2x2,clinical_3x3}` (shift OFF)
- Threads: `--threads <N>` to control Numba parallelism (0=auto)

## Global vs Local Gamma
- Select with `--gamma-type {global,local}` (default: global)
- GUI toggle: Local gamma (default OFF)
- Guide and examples: see `GPR_Global_vs_Local.md`

## Geometry and Coordinates
- Obeys DICOM IPP/IOP/PixelSpacing/GFOV; frames sorted by ascending GFOV
- 2D plane grids align to array order (z,y,x) with a singleton axis for the fixed dimension

## Outputs
- 2D images: PNG/TIFF (`--save-gamma-map`, `--save-dose-diff`)
- 3D arrays: NPZ (`--save-gamma-map`, `--save-dose-diff`)
- Reports: CSV/JSON/MD (`--report <basepath>`) with geometry sanity fields

## GUI
- Launch: double-click `run_gui.bat` (or run `scripts/run_gui.ps1`)
- Pick Ref/Eval RTDOSE, select output folder, choose Action (Header/3D/2D), preset, plane, threads
- Comfort: live log, status, elapsed, auto-open summary, save log; Local gamma toggle
- Details: `docs/openspec/GUI_RUN.md`

## OpenSpec and Validation
- Docs/specs: `docs/openspec/` (README, TEMPLATE, `report.schema.json`, examples, `rtgamma_openspec.md`)
- Validate a report JSON:
  - `python scripts/validate_report.py --sanitize-nan phits-linac-validation/output/rtgamma/spec_check/axial.json`
- Compare a 3D gamma slice vs a 2D report:
  - `python scripts/compare_slice_gpr.py <gamma3d.npz> --plane coronal --index 101 --report2d <coronal_101.json>`

## Testing
- Lightweight tests: `pytest -q`
- Includes gamma local vs global checks and I/O/header utilities

## Notes
- Prefer UTF-8 (no BOM) for Markdown on Windows
- Do not commit PHI; use anonymized test DICOM only
- Write outputs under `phits-linac-validation/output/rtgamma/`

## Recent Updates (2025-10-23)
- Local gamma support (`--gamma-type local`); GUI toggle added
- OpenSpec initialized; report schema and validators included
- Slice consistency helper script added
- Reproducible 2D/3D commands and validation steps documented
