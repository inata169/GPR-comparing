# Repository Guidelines

This guide helps contributors and agents work efficiently in this repository.

## Project Structure & Module Organization
- `rtgamma/` – core Python package for DICOM RTDOSE gamma analysis (I/O, resampling, gamma, optimize, CLI in `main.py`).
- `dicom/` – sample anonymized DICOM RT files for local testing.
- `phits-linac-validation/` – auxiliary 1D profile comparison project and default output folder `phits-linac-validation/output/rtgamma/`.
- Top-level artifacts: `README.md`, logs (`rtgamma.log`), prompts.

## Build, Test, and Development Commands
- Install deps (Python 3.9+):
  - `pip install pydicom numpy scipy matplotlib numba`
- Run 3D analysis:
  - `python -m rtgamma.main --ref dicom/PHITS_Iris_10_rtdose.dcm --eval dicom/RTD.deposit-3D-Lung16Beams-1.5-10-8.dcm --mode 3d --report phits-linac-validation/output/rtgamma/run3d`
- Run 2D analysis (axial slice 50) and save images:
  - `python -m rtgamma.main --mode 2d --plane axial --plane-index 50 --ref <ref.dcm> --eval <eval.dcm> --save-gamma-map out/gamma.png --save-dose-diff out/diff.png --report out/axial`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, type hints where practical.
- Naming: modules/files/functions use `snake_case`; classes use `CapWords`.
- Logging over prints; keep messages concise and actionable.
- Keep changes minimal and focused; prefer small, well-scoped patches.

## Testing Guidelines
- No formal test suite is present. When adding features/bugfixes, prefer lightweight `pytest`-style tests under `tests/` if explicitly requested.
- For manual checks, reuse fixtures in `dicom/` and write outputs to `phits-linac-validation/output/rtgamma/`.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `fix(rtgamma): …`, `feat(main): …`, `docs: …`).
- Commits should describe motivation + change scope; keep them atomic.
- PRs must include: summary, rationale, before/after evidence (e.g., pass rate, image paths), and any limitations.

## Security & Configuration Tips
- Do not commit PHI. Use anonymized test DICOM only.
- Avoid committing large binaries and generated outputs; prefer paths under `phits-linac-validation/output/rtgamma/` which are typically git-ignored.
- Coordinate systems: always respect DICOM `ImagePositionPatient`, `ImageOrientationPatient`, `PixelSpacing`, and `GridFrameOffsetVector`. Ingest frames in ascending GFOV and align dose arrays accordingly.

## Operational Notes (2025-10-16)
- 2D plane slicing: sagittal/coronal world-coordinate grids were corrected to align with array axis order `(z,y,x)` using a singleton axis for the fixed dimension. This resolves shape mismatches when saving 2D dose diff images.
- GUI auto-open: after runs, the GUI now prefers `run3d.md` (Action=3D), `<plane>.md` (Action=2D), or `header_compare.md` (Action=Header). Falls back to the most recent `*.md` if none found.
- Coronal GPR investigation: recent coronal pass rate (~82%) may differ from prior (~93%) due to stricter normalization behavior and corrected plane geometry. See `TODO.md` follow-up (2025-10-16) for concrete reproduction steps (plane-index 100/101/102 sweep, `--norm` sensitivity, and 2D vs 3D slice consistency check).
- Reproduction settings: use clinical presets (e.g., `clinical_rel`), `--opt-shift off`, `--interp linear`, `--cutoff 10`, and write outputs under `phits-linac-validation/output/rtgamma/`. Save GUI logs (`run_log_*.txt`) for traceability.
- Encoding tip: prefer UTF-8 (no BOM) for Markdown to avoid mojibake on Windows.
