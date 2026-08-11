# Release-readiness checkpoint — 2026-08-11

## Decision recorded

The project owner approved the current PyMedPhys-standardization validation scope and known limitations on 2026-08-11. This approval permits release preparation; it is not approval to create a version, tag, GitHub Release, clinical claim, or offline clean-machine claim.

The approved scope is software verification for research and education:

- CPython 3.12 and PyMedPhys 0.41.0 are the fixed source baseline;
- PyMedPhys is the standard Gamma engine;
- Numba remains an explicitly selected legacy/experimental engine;
- analytical/synthetic tests, controlled non-patient RTDOSE characterization, provenance, GUI execution, and Fast 3D Viewer operation are in scope;
- no silent fallback to Numba is permitted;
- a Sun Nuclear 3DVH comparison is not required for standardization;
- clinical validation, patient QA, commissioning, treatment decisions, medical-device status, and vendor approval are out of scope.

## Evidence currently available

- Versioned report schema 2 and privacy-conscious provenance across JSON, CSV, Markdown, PDF, SQLite, and batch summaries.
- Exact and analytical PyMedPhys tests plus explicit Numba regression coverage.
- Controlled 3 x 3 cm and 5 x 5 cm local characterization without distributing DICOM or numerical arrays.
- Full-volume 5 x 5 cm +2% and +1 mm source-GUI/Fast-Viewer checks documented in the [controlled RTDOSE verification record](PYMEDPHYS_CONTROLLED_RTDOSE_VERIFICATION_2026-08-11.md).
- Local Windows/Python 3.12 `tests/` result: `99 passed, 7 skipped, 8 warnings`; Ruff passed.
- A Python 3.12 x64 offline candidate bundle with a complete wheelhouse, SHA-256 manifest, third-party licensing manifest, local `--no-index` installation verification, and source-tree smoke checks. See the [2026-08-11 progress record](PROGRESS_2026-08-11.md).

## Gates requiring completion or an explicit disposition

### Source and numerical policy

- Decide the dependency update policy and whether future PyMedPhys versions use an exact pin, a reviewed compatibility range, or a new validation cycle.
- Approve the current fail-closed handling of `norm=none` for PyMedPhys or specify a separately validated mapping.
- Decide whether numerical PyMedPhys-versus-Numba thresholds are required for release. Numba agreement must not define PyMedPhys correctness.
- Decide when the internal legacy boolean engine switch and legacy-report compatibility path may be removed.
- Complete or explicitly defer peak-memory characterization.

### Verification and CI

- Re-run the release candidate from a clean Git revision so reports no longer record `git_dirty=true`.
- Confirm the complete supported Python/operating-system CI matrix on that revision.
- Verify schema handling for any retained legacy, ROI, and DVH report paths selected for the release scope.
- Review any failed acceptance threshold without case-specific parameter tuning.

### Offline delivery

- Perform a physically network-isolated installation check if that claim is desired.
- Perform the first-install test on a Windows x64 PC without Python when a suitable machine becomes available. This is currently an explicitly accepted pending item.
- Do not describe the current candidate ZIP as clean-machine verified.

### Repository and publication hygiene

- Commit only the intended source and public-documentation changes.
- Exclude the locally modified `config/gui_config.ini`, which currently contains workstation-specific DICOM paths.
- Preserve the user's unrelated `AGENTS.md` change without staging it as part of the release work.
- Confirm that `test_data_local/`, `dist/`, DICOM, NPZ, reports, logs, databases, and local absolute paths are absent from the publication diff.
- Choose the release version and approve the version change, tag, and GitHub Release as separate actions.

## Current disposition

Release preparation may continue. No version, tag, push, pull request, or GitHub Release was created at this checkpoint. The next safe technical step is to resolve or explicitly defer the source/numerical policy items, then create a clean release-candidate revision and run the final CI/reproducibility checks from it.
