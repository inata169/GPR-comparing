# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- ROI/RTSTRUCT-based masking (planned)
- Local search (Nelder–Mead) option (planned)
- Optional GPU (CuPy) backend (investigating)

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
