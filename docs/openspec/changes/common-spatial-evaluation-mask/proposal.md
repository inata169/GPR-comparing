# Change proposal: common spatial evaluation mask

Status: In implementation
Priority: Acceptance-test correctness
Public interfaces affected: Gamma maps, GPR denominator, JSON/CSV/Markdown/PDF reports, SQLite, Viewer cache contract, tests, and documentation

## Why

When the reference RTDOSE extends beyond the evaluation RTDOSE, a reference voxel can contain a valid dose while no evaluation value exists at the same patient-coordinate position. PyMedPhys previously represented such cutoff-qualified points as failures, while the Numba search could omit most of them or evaluate boundary-near points through its DTA neighborhood. This made the denominator depend on the selected engine even before algorithm and interpolation differences were considered.

The approved interpretation is that a point with no value in one distribution is not evaluated. A stored zero inside both grids is a value and must not be confused with absent spatial coverage.

## Outcome

1. Build one engine-neutral mask from reference coordinates and the evaluation grid extent on every axis.
2. Apply the mask to PyMedPhys and Numba results before pass rate, statistics, ROI summaries, cache output, and Viewer display.
3. Represent spatially excluded points as `NaN` so they remain transparent and outside the GPR denominator.
4. Keep reference-dose cutoff exclusion separate from spatial exclusion.
5. Record cutoff-qualified, common-spatial, spatially excluded, and evaluated point counts in every report format and SQLite.
6. Increment the Gamma cache contract so pre-change maps are rejected as stale.

## Scope

- Rectilinear 2D and 3D reference/evaluation axes already supported by the selected engine.
- Shifted evaluation axes used by final calculation and shift optimization.
- The 2D fast path, using the original evaluation RTDOSE extent rather than the resampled slice extent.
- Synthetic tests for partial overlap, boundaries, inside-grid zero dose, both engines, report schema, database migration, and cache invalidation.

## Non-goals

- Making PyMedPhys and Numba Gamma maps or statistics numerically equal.
- Changing DD, DTA, normalization, cutoff, interpolation, or shift-search definitions.
- Inferring dose outside the evaluation RTDOSE or padding it with zero.
- Treating a low GPR as an acceptance result or changing the research-only safety boundary.
- Building or distributing an EXE or offline ZIP.

## Compatibility and migration

Report schema version 3 adds mandatory evaluation-coverage counts. Gamma cache contract version 2 invalidates earlier cached arrays because the `NaN` mask and GPR denominator can change without any user setting changing. Existing SQLite databases are migrated by adding nullable integer columns before new rows are inserted.

## Acceptance

- For partial-overlap synthetic data, both engines produce `NaN` at every cutoff-qualified reference point outside the evaluation extent.
- Boundary points are included and an inside-grid zero value is evaluated for global Gamma.
- Both engines report the same cutoff-qualified/common-spatial/spatially-excluded counts for the same input geometry.
- JSON validates against schema version 3; CSV, Markdown, PDF, and SQLite contain the coverage counts.
- Existing engine, geometry, report, Viewer-cache, and CLI tests remain green.
- The approved fixed-condition TPS data are rerun into new output folders after code review; generated DICOM, logs, NPZ, PDF, SQLite, and other output artifacts are not committed.

## Human decision

Approved on 2026-08-20: a location where only one RTDOSE has a value is excluded from evaluation. Implementation may proceed through a new branch, specification and test update, PR, Codex review, CI, and fix loop.
