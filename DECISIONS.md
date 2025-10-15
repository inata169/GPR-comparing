# Architectural Decisions (ADR Summary)

## ADR-006: Geometry Sanity in Reports (FoR/Orientation/Shift)
- Decision: Emit `FrameOfReferenceUID` fields, `orientation_min_dot`, `best_shift_mag_mm`, and `absolute_geometry_only` to reports; warn on FoR mismatch and large shifts (threshold configurable).
- Rationale: Rapidly distinguishes header/geometry issues from dose-model differences; aids triage and reproducibility.

## ADR-007: Auto-Fallback Wide Search
- Decision: Provide an auto-fallback runner that executes absolute-geometry first, then widens the search (±150/±50/±50 mm) if pass rate is below a threshold or warnings exist.
- Rationale: Real-world datasets may include large initial offsets (e.g., differing SSD/SCD/isocenter settings). Automated recovery improves usability without masking geometry problems.
\n+## ADR-001: Slice Order and GFOV Alignment
- Decision: Reorder dose frames by ascending GFOV and use the same order for z-coordinates.
- Rationale: Prevents z–data mismatches; robust to non-monotonic GFOV.
- Alternatives: Trust on-disk order; sort coordinates only (risk: misaligned data).
- Verification: Self-compare 100% pass; consistent indices across scans.
\n+## ADR-002: Gamma Engine Implementation
- Decision: Use a Numba 3D gamma kernel; keep pymedphys off by default.
- Rationale: Predictable performance; fewer external dependencies.
- Alternatives: Always call pymedphys; slower and adds variance.
\n+## ADR-003: Shift Optimization Strategy
- Decision: Coarse-to-fine grid search over (dx,dy,dz) with fine refinement around the best coarse hit.
- Rationale: Balanced accuracy and runtime; easy to reproduce and log.
- Alternatives: Nelder–Mead/other optimizers (planned optional).
\n+## ADR-004: Origin Offset Correction
- Decision: Project IPP delta onto reference row/col/slice directions and apply as axis offsets for search.
- Rationale: Handles arbitrary orientations; avoids axis-mixing errors.
\n+## ADR-005: Resampling in LPS
- Decision: Convert (dx,dy,dz) in ref axes to an LPS vector and sample eval dose via `world_to_index` + `map_coordinates`.
- Rationale: Ensures geometric correctness across frames/orientations.
