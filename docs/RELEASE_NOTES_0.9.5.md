# GPR-comparing v0.9.5 release notes

Date: 2026-08-20

## Purpose

Version 0.9.5 packages the post-v0.9.4 safety and geometry corrections merged through PR #29 and PR #30. It supersedes the unreleased PR #29 acceptance-candidate ZIP. The published `v0.9.4` tag remains unchanged and must not be moved.

## User-visible changes

- Frame of Reference UID mismatches remain rejected by default. An operator may explicitly permit a mismatch in the CLI, GUI, batch runner, and Viewers only after independently verifying that both RTDOSE objects use the same patient coordinate system and differ only because of UID replacement or anonymization. This option does not register or transform either dose grid.
- Gamma evaluation now uses the common patient-coordinate spatial domain. Cutoff-qualified reference points outside the evaluation RTDOSE extent are unavailable and excluded from the pass-rate denominator; they are not counted as failures.
- Reports distinguish cutoff-qualified, common-spatial, spatially excluded, and evaluated point counts. For GUI launches and direct Viewer launches supplied with the matching report, report schema version 3 and Gamma cache contract version 2 reject older cache semantics.
- Viewer and comparison paths preserve the original evaluation-grid extent for Gamma, Pass/Fail, dose difference, and dose ratio behavior.
- Offline installation can safely create the application venv from an existing CPython 3.12 executable whose path contains Japanese or other non-ASCII characters. It does not modify that Python installation, its global packages, PATH, or registry entries.

## Acceptance evidence

Source execution was checked on the target TPS PC using a corrected evaluation RTDOSE. The final acceptance run kept the Frame of Reference mismatch permission disabled because the two UIDs actually matched.

- RTDOSE header geometry and UID comparison was completed.
- Reference PyMedPhys and practical Numba 3D calculations completed under fixed, separately recorded conditions. Cross-engine Gamma maps and statistics were not treated as numerically identical.
- JSON, Markdown, PDF, chart, SQLite, `gamma3d.npz`, and `diff3d.npz` outputs were generated and validated.
- Ref Dose, Eval Dose, Dose Diff, Dose Ratio, Gamma, and Pass/Fail Viewer displays were inspected without an observed display anomaly.
- With no compatible Gamma cache, dose-only Viewer fallback remained usable and clearly marked Gamma/Pass-Fail as unavailable.
- Invalid CT input caused a nonzero Viewer exit, a GUI error dialog, and a saved traceback log while the parent GUI remained usable.

The earlier 0.02% result from an invalid evaluation dose produced during a separate dicomxphits defect investigation is excluded from this acceptance and is not evidence about GPR-comparing.

## Companion input-producer traceability

The relevant dicomxphits correction baseline is commit `3b389717c9142e4ba47ef46e051c69b81a5b3732` (`Fix gantry direction and PLAN fraction dose semantics`). It was merged through dicomxphits PR #37 at `e534be951629519cec1dfa920c3711fa74a177b8` and is included in dicomxphits `v1.0.2` and later releases.

The accepted RTDOSE did not embed its dicomxphits Git revision in the GPR-comparing evidence. These identifiers therefore establish the correction baseline, but do not prove the exact dicomxphits commit that generated that particular file.

## Distribution status and limitations

The source-workflow evidence supports functional acceptance of the source paths described above. It is not clinical QA, patient-dose approval, commissioning, cross-engine equivalence, or approval of any packaged executable.

Direct Viewer launch with `--gamma-npz` but without `--gamma-report` cannot prove which cache contract created the NPZ. Supply the matching report or regenerate the Gamma cache with v0.9.5 before interpreting Gamma or Pass/Fail.

Post-tag build and publication update, 2026-08-20:

1. the annotated `v0.9.5` tag was created at the exact approved release commit `74881d77ee8d654cbe2c368e457136cbf6827da2`;
2. the EXE and Python 3.12 offline archives were built from a clean detached worktree at that tag after explicit approval;
3. ZIP CRC, SHA-256, embedded identity, license material, offline-only dependency installation, Viewer startup, and synthetic non-patient Numba/PyMedPhys execution were verified;
4. the project owner explicitly approved publishing the GitHub Release and both archives on 2026-08-20 before installation and acceptance of those exact final archives on the TPS PC.

Item 4 is a deliberate v0.9.5 exception to the standard target-PC-before-distribution gate. The GitHub Release states that exact-final-binary TPS acceptance remains pending. This exception does not mark the binary package as accepted, does not waive the pending installation and fixed-condition smoke checks, and is not a precedent for future releases.

Do not rename or redistribute the PR #29 candidate ZIP as v0.9.5. Do not replace the published v0.9.5 assets or move the existing `v0.9.4` or `v0.9.5` tags as part of the pending acceptance record.
