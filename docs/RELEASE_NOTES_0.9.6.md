# GPR-comparing v0.9.6 release notes

Date: 2026-08-27

## Purpose

Version 0.9.6 packages the post-v0.9.5 ROI/DVH reliability correction merged through PR #34. The published `v0.9.4` and `v0.9.5` tags and assets remain unchanged and must not be replaced or renamed.

## User-visible changes

- A completed 2D or 3D Gamma calculation is no longer discarded when an evaluation-dose ROI contains only non-finite or spatially unavailable values.
- Reference and evaluation DVHs use the same paired finite-voxel support. This prevents apparently paired DVH statistics from describing different voxel populations when evaluation coverage is partial.
- An ROI with no paired finite dose values is retained in the report with an empty DVH and unavailable statistics rather than causing histogram calculation to fail.
- Fast 2D RTSTRUCT analysis slices the reference dose, evaluation dose, and mask consistently for axial, sagittal, and coronal planes.

These changes do not extrapolate missing evaluation dose, expand the evaluation grid, or convert unavailable values into zero dose.

## Source-workflow verification

The complete test suite passed with 172 tests, Ruff passed, and all six CI jobs passed on Windows and Ubuntu with Python 3.10, 3.11, and 3.12. Review findings about paired finite support and 2D plane slicing were corrected before PR #34 was merged.

A fixed-condition source run using a corrected evaluation RTDOSE was completed from commit `765a1485f7e9b440af295235146302f3533ca7f8`:

| Purpose | Engine | Interpolation fraction | Elapsed time | GPR | Evaluated points |
| --- | --- | ---: | ---: | ---: | ---: |
| Reference calculation | PyMedPhys 0.41.0 | 1 | 19.918 s | 62.6431% | 178,136 |
| Practical fast GPR | Numba 0.65.1 | 4 | 23.297 s | 92.4833% | 178,136 |

Both runs used 3% dose difference, 2 mm distance to agreement, 10% cutoff, global/global-max normalization, and shift optimization off. The Frame of Reference mismatch permission was disabled. The engine results are recorded separately and are not treated as numerically equivalent.

JSON, CSV, Markdown, PDF, charts, SQLite, `gamma3d.npz`, and `diff3d.npz` were generated. Ref Dose, Eval Dose, Dose Diff, Dose Ratio, Gamma, and Pass/Fail were renderable from the validated cache. Dose-only fallback kept the four dose overlays usable without a Gamma cache, and invalid Viewer input produced a nonzero exit with captured error logging.

This evidence verifies the source workflow. It is not clinical QA, patient-dose approval, commissioning, a medical-device claim, or an engine-equivalence result. No clinical GPR pass threshold is defined by this release.

## Distribution and TPS-PC execution scope

The project owner approved preparing v0.9.6 EXE and Python 3.12 offline ZIP candidates. Build them only from the exact approved v0.9.6 tag, with a clean source identity, and verify ZIP integrity, SHA-256, bundled identity, third-party notices, offline-only dependency installation, and synthetic PyMedPhys/Numba execution before transfer.

The TPS-PC follow-up is intentionally described as a **release-candidate EXE operational check**, not as a second formal packaged acceptance study. The fixed-condition source-workflow evidence above remains the formal software functional record. On the TPS PC, confirm only the distribution-specific boundary:

1. verify the transferred ZIP SHA-256;
2. start the packaged GUI/EXE without modifying external Python, global packages, PATH, or the registry;
3. execute one representative 3D Gamma workflow with the approved inputs and fixed settings;
4. open the resulting Viewer cache and confirm the expected overlays are available;
5. confirm reports and cache files are saved and no unexpected GUI or Viewer error is shown.

This reduced TPS-PC scope does not waive local package verification, authorize clinical use, or reinterpret the observed GPR as a patient-dose acceptance result.

## Release boundary

Preparing and building the candidates does not by itself publish a GitHub Release. Do not publish or replace Release assets without a separate publication decision. Do not add EXE files, ZIP files, DICOM data, workstation paths, GUI configuration, logs, NPZ, PDF, SQLite, or generated acceptance outputs to Git.
