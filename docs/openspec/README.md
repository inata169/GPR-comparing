# OpenSpec index

This directory contains project specifications, report schemas, change proposals, and historical design records. Public current-state statements must agree with the implementation and the canonical English [README](../../README.md).

## Active change

- [PyMedPhys as the standard gamma engine](changes/pymedphys-standard-engine/proposal.md)
  - [Design](changes/pymedphys-standard-engine/design.md)
  - [Tasks](changes/pymedphys-standard-engine/tasks.md)

The Python 3.12 source implementation now uses PyMedPhys as the CLI, batch, and GUI default; preserves Numba through explicit legacy/research selection; and writes strict-JSON schema-versioned provenance across report formats and SQLite. Controlled local characterization is recorded without approving clinical or cross-engine acceptance thresholds. Offline PyMedPhys packaging remains open; a 3DVH comparison is not required for this standardization.

## Current report contract

- [JSON Schema](report.schema.json)
- [Example report](examples/rtgamma_report_example.json)
- Validator: `python scripts/validate_report.py <report.json>`

Schema version 2 emits strict JSON and replaces non-finite floating-point values with `null`. The validator retains `--sanitize-nan` only for legacy reports.

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
