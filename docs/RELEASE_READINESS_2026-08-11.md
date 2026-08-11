# Release-readiness checkpoint — 2026-08-11

## Decision recorded

The project owner approved the current PyMedPhys-standardization validation scope and known limitations on 2026-08-11, then explicitly approved version v0.9.3, its tag, and a source-only GitHub Release. This is not approval for clinical use or an offline clean-machine claim.

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
- Local Windows/Python 3.12 `tests/` result: `134 passed, 7 skipped, 13 warnings`; Ruff and the report-schema example passed.
- PR #26 completed the Codex review/fix loop with no major issue and no unresolved review thread; its Windows/Ubuntu, Python 3.10/3.11/3.12 CI matrix passed.
- A Python 3.12 x64 offline candidate bundle with a complete wheelhouse, SHA-256 manifest, third-party licensing manifest, local `--no-index` installation verification, and source-tree smoke checks. See the [2026-08-11 progress record](PROGRESS_2026-08-11.md).

## Gates requiring completion or an explicit disposition

### Source and numerical policy

- Resolved 2026-08-11: keep the exact PyMedPhys 0.41.0 pin; any engine-version change requires a separately reviewed validation cycle and rebuilt dependency, integrity, licensing, test, controlled-verification, and offline-bundle evidence.
- Resolved 2026-08-11: reject `norm=none` fail-closed for PyMedPhys. No absolute-dose mapping is inferred; a future mapping requires a separate specification and validation cycle.
- Resolved 2026-08-11: do not require PyMedPhys-versus-Numba numerical or mask-agreement thresholds for release. Continue to record and review disagreements without case-specific tuning.
- Resolved 2026-08-11: runtime is recorded; peak-memory characterization is deferred and no peak-memory performance claim is permitted in the current release scope.
- Decide when the internal legacy boolean engine switch and legacy-report compatibility path may be removed.

### Verification and CI

- Resolved 2026-08-11: the release candidate is based on the reviewed and merged PR #26 revision; local verification is repeated on the release-documentation revision before tagging.
- Resolved 2026-08-11: confirm the complete supported Python/operating-system CI matrix on the release revision before publishing the tag and GitHub Release.
- Resolved 2026-08-11: report-schema example validation and retained report-path coverage passed in the release test suite.
- Continue to review observed cross-engine disagreements without case-specific parameter tuning; no cross-engine acceptance threshold is defined.

### Offline delivery

- Perform a physically network-isolated installation check if that claim is desired.
- Perform the first-install test on a Windows x64 PC without Python when a suitable machine becomes available. This is an explicitly accepted pending item and does not block a source release, but it blocks any clean-machine-verified offline-installation claim.
- Do not describe the current candidate ZIP as clean-machine verified.

### Repository and publication hygiene

- Commit only the intended source and public-documentation changes.
- Keep `config/gui_config.ini` local and Git-ignored. Distributions and fresh checkouts fall back to the tracked, path-free `config/gui_config.example.ini`; packaging must exclude locally saved DICOM paths.
- Preserve the user's unrelated `AGENTS.md` change without staging it as part of the release work.
- Confirm that `test_data_local/`, `dist/`, DICOM, NPZ, reports, logs, databases, and local absolute paths are absent from the publication diff.
- Resolved 2026-08-11: the project owner selected and approved v0.9.3, its tag, and a source-only GitHub Release.

## Current disposition

The v0.9.3 source release is approved. Publication remains conditional on the final local checks and the supported CI matrix passing on the release revision. The release must contain no DICOM, NPZ, local reports, databases, absolute paths, or locally saved GUI configuration. The clean Windows/Python-absent installation test remains pending, so v0.9.3 makes no clean-machine-verified offline-installation claim and attaches no offline binary bundle.
