# Design: common spatial evaluation mask

## 1. Spatial-domain rule

For each reference coordinate on axis `d`, include the coordinate when:

```text
min(eval_axis_d) <= ref_coordinate_d <= max(eval_axis_d)
```

The full mask is the Cartesian intersection across all axes. Boundaries are inclusive with a small floating-point tolerance. Evaluation-domain axes must be finite, non-empty, one-dimensional, and strictly monotonic unless singleton.

This is a coverage rule, not a dose rule. Dose zero inside the domain remains available. Reference cutoff is calculated independently using the existing normalization and inclusive boundary behavior.

## 2. Engine application

The mask is calculated before engine dispatch from reference axes and the effective evaluation axes, including any selected shift.

- PyMedPhys receives only the rectangular reference-axis crop inside the evaluation extent. Its result is inserted into a full-size reference array initialized with `NaN`.
- Numba may use the full reference array for its existing search, but out-of-domain reference values are made non-finite before the kernel and the returned array is masked again defensively.
- Pass rate, histogram, percentiles, ROI summaries, saved NPZ, and Viewer overlays consume the final masked array.

Cropping the PyMedPhys reference input prevents its unlimited `max_gamma` search from spending time on locations that are explicitly outside the evaluation domain.

## 3. 2D fast path

The 2D fast path currently resamples evaluation dose onto reference slice coordinates. Those resampled axes cannot identify source-grid absence. `compute_gamma()` therefore accepts optional `evaluation_domain_axes_mm`; the fast path supplies the original evaluation RTDOSE axes projected into the reference coordinate frame. Other paths default the domain axes to the actual evaluation axes passed to the engine.

## 4. Coverage accounting

The engine-neutral statistics are:

- `cutoff_qualified_points`: finite reference points at or above cutoff;
- `common_spatial_points`: cutoff-qualified points inside every evaluation-axis extent;
- `spatially_excluded_points`: cutoff-qualified points outside at least one evaluation-axis extent;
- `evaluated_points`: non-`NaN` Gamma results after the common mask;
- `valid_points`: compatibility alias for `evaluated_points` used by shift optimization.

An infinite Gamma value is evaluated and fails. A `NaN` Gamma value is not in the denominator.

## 5. Reports and cache

The four coverage counts are mandatory top-level fields in report schema version 3. Generic CSV and Markdown writers include them automatically; PDF has a dedicated Evaluation Coverage table; SQLite adds four integer columns through its existing migration mechanism.

Gamma cache contract version 2 is required because applying the common mask changes saved arrays and pass rates without changing input hashes or user-selected Gamma settings.

## 6. Safety and privacy

No DICOM demographics, absolute paths, calculation outputs, or PHI are added to source control. The change does not relax orientation, Dose Units, Frame of Reference, or geometry validation. FrameOfReferenceUID override remains limited to separately verified anonymization-only UID differences in the same patient coordinate system.
