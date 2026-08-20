# OpenSpec index

This directory contains project specifications, report schemas, change proposals, and historical design records. Public current-state statements must agree with the implementation and the canonical English [README](../../README.md).

## Active changes

- [Common spatial evaluation mask](changes/common-spatial-evaluation-mask/proposal.md)
  - [Design](changes/common-spatial-evaluation-mask/design.md)
  - [Tasks](changes/common-spatial-evaluation-mask/tasks.md)

- [PyMedPhys as the standard gamma engine](changes/pymedphys-standard-engine/proposal.md)
  - [Design](changes/pymedphys-standard-engine/design.md)
  - [Tasks](changes/pymedphys-standard-engine/tasks.md)
  - [Controlled RTDOSE verification record — 2026-08-11](../PYMEDPHYS_CONTROLLED_RTDOSE_VERIFICATION_2026-08-11.md)
  - [Release-readiness checkpoint — 2026-08-11](../RELEASE_READINESS_2026-08-11.md)
  - [v0.9.4 progress and handoff record — 2026-08-12](../PROGRESS_2026-08-12.md)
  - [v0.9.5 release notes — 2026-08-20](../RELEASE_NOTES_0.9.5.md)

The Python 3.12 source implementation uses PyMedPhys as the CLI and batch omitted-value default, while the GUI defaults to parallel Numba for practical full-volume runtime and keeps PyMedPhys explicitly selectable as the reference engine. It writes strict-JSON schema-versioned provenance across report formats and SQLite. Controlled local characterization and a full-volume source-GUI/Fast-Viewer workflow check are recorded without treating numerical equality with Numba as an acceptance threshold. Version 0.9.5 adds the explicit, operator-verified Frame of Reference UID override and the common-spatial evaluation mask. A v0.9.5 binary bundle must be built from the approved v0.9.5 tag and accepted separately. A 3DVH comparison is not required for this standardization.

## Current report contract

- [JSON Schema](report.schema.json)
- [Example report](examples/rtgamma_report_example.json)
- Validator: `python scripts/validate_report.py <report.json>`

Schema version 3 emits strict JSON, replaces non-finite floating-point values with `null`, and records cutoff-qualified, common-spatial, spatially excluded, and evaluated point counts. The validator retains `--sanitize-nan` only for legacy reports.

## Historical specifications

- `rtgamma_openspec.md`
- `rtgamma_spec_JA.md`
- `Global_Local_Illustrated_JA.md`
- `FAQ_JA.md`
- `GUI_RUN.md`

These files preserve earlier implementation and development context. They are not the canonical source for current validation or clinical claims. In particular, historical 3DVH results, case-specific interpolation tuning, “clinical” preset wording, and numerical acceptance language must not be treated as current evidence. Use the active change proposal and canonical README for the present project position.

## Specification requirements

A new change should define:

- purpose, scope, and non-goals;
- user-visible and machine-readable interfaces;
- reference/evaluation input order;
- DICOM geometry and unsupported-geometry behavior;
- algorithm/engine option mapping;
- report and provenance schema changes;
- exact tests, characterization tests, and human-approved acceptance criteria;
- privacy, licensing, offline delivery, and failure behavior;
- compatibility and migration policy;
- unresolved decisions assigned to a human reviewer.

Do not use a roadmap item as evidence that a feature is implemented. Do not create validation results, citations, data provenance, vendor positions, or acceptance thresholds that are not present and reviewable.

## Safety boundary

GPR-comparing is for research and education only. It is not for patient QA, clinical commissioning, diagnosis, treatment planning, treatment decisions, or clinical decision support. It is not a medical device or a replacement for commercial QA systems, and it has no vendor approval, certification, or endorsement. Public specifications and examples must use synthetic or properly governed non-patient data and must not include PHI.
