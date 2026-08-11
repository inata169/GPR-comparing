# Design: PyMedPhys standard engine

## 1. Engine boundary

The source implementation uses an explicit engine identifier and a shared immutable gamma-settings object while retaining the boolean `use_pymedphys` parameter only for internal backwards compatibility. Removal of that boolean remains pending. Public identifiers are:

- `pymedphys` — standard and omitted-value default engine;
- `numba` — explicitly selected experimental/legacy engine.

The engine interface should accept reference/evaluation arrays, rectilinear axes in millimetres, DD, DTA, cutoff, gamma type, normalization, interpolation fraction, and any explicitly supported performance limits. It should return the gamma array plus engine-neutral statistics. Geometry preparation and report generation should remain outside the engine adapter.

## 2. PyMedPhys option mapping

The adapter should pass unscaled dose arrays and map settings explicitly:

| GPR-comparing setting | PyMedPhys argument |
|---|---|
| `dd_percent` | `dose_percent_threshold` |
| `dta_mm` | `distance_mm_threshold` |
| `cutoff_percent` | `lower_percent_dose_cutoff` |
| `interp_fraction` | `interp_fraction` |
| global/local | `local_gamma=False/True` |
| global normalization | `global_normalisation=<resolved value>` |

Do not depend on PyMedPhys defaults for any result-affecting option. The adapter must validate finite, monotonic axes and supported dimensionality before calling PyMedPhys. Performance options such as `max_gamma`, `skip_once_passed`, `random_subset`, and `ram_available` must be either fixed and reported or unavailable; stochastic subsets must not be enabled by default.

The current `global_max` and `max_ref` names both resolve to the maximum finite reference dose. Preserve that behavior unless a separately approved change distinguishes them. Phase one rejects `norm=none` for PyMedPhys until an explicit normalization of one dose unit and its cutoff behavior are approved and validated across both engines.

## 3. Geometry contract

Both engines require a common, documented geometry contract. Before engine dispatch:

1. Load dose arrays as `(k, j, i)` and sort frames and GFOV together.
2. Validate Dose Units, finite spacing, monotonic GFOV, non-degenerate IOP direction cosines, and dimensional consistency.
3. Resolve the reference coordinate frame.
4. For origins and spacing differences on parallel rectilinear grids, provide correct axes in the same reference-axis coordinate system.
5. For different orientation matrices, either resample the evaluation distribution to a reference-aligned rectilinear grid using full LPS transforms or fail closed with an unsupported-geometry error.

The present final 3D Numba path only projects the IPP delta and warns on orientation mismatch. It must not be used as evidence that arbitrary orientation differences are supported.

## 4. Shift optimization

Shift optimization must receive the selected engine and the same settings used by the final calculation. Every candidate must use identical normalization, cutoff, interpolation, and geometry semantics. The report must distinguish the requested shift search from the final selected shift and record:

- enabled/disabled;
- coarse axis ranges and step;
- refinement mode, fine range, and fine step;
- prescan mode;
- early-stop epsilon and patience;
- selected axis components and LPS vector;
- number of candidates evaluated.

For external-system comparison, shift optimization is off unless the prospective protocol explicitly defines it before data are evaluated.

## 5. CLI, GUI, batch, and configuration

Phase-one CLI:

```text
--engine {numba,pymedphys}
```

The omitted CLI and batch value is `pymedphys`; omitted CLI use emits a migration notice. The GUI displays an Engine control with PyMedPhys selected and a visible "legacy / experimental" qualifier on Numba. `config/gui_config.ini` persists `Gamma/engine`; an older INI without the key selects PyMedPhys and displays a migration warning. Batch CSV accepts an `engine` column, and unknown values fail validation. Legacy Numba reproduction requires an explicit `numba` value.

The Fast Viewer consumes saved arrays and does not calculate gamma; it should display engine metadata from a report/sidecar when available and label older arrays as engine unknown.

## 6. Failure policy

- Requested/default PyMedPhys unavailable: fail with installation and supported-version guidance.
- Requested Numba unavailable: fail explicitly.
- Unsupported settings or geometry: fail before calculation and list the incompatible fields.
- Engine exception: report the requested engine and preserve the original exception context; do not rerun with another engine.
- Legacy report without engine: display `unknown (legacy report)`.

## 7. Provenance envelope

Add a stable nested object (or an equivalently versioned flat schema) containing at least:

- report schema version;
- GPR-comparing version and Git commit when available;
- engine name and installed engine version;
- Python version and implementation;
- OS name, release, architecture;
- execution start/end time in UTC and elapsed time;
- reference/evaluation logical label, basename, optional approved SHA-256, and role;
- mode, plane, and plane index;
- gamma type, DD, DTA, cutoff, normalization value and resolved numeric factor;
- interpolation fraction and resampling interpolation mode;
- shift settings and result;
- ROI selection;
- reference/evaluation shape, IPP, IOP, Pixel Spacing, sorted GFOV summary, Dose Units, and Frame of Reference comparison;
- warnings and unsupported-condition flags.

Do not record PatientName, PatientID, birth date, accession number, institution identifiers, free-text DICOM fields, or arbitrary absolute paths. Schema version 2 records input basenames and SHA-256 digests under this explicit privacy policy.

JSON is the canonical machine-readable report. Markdown and PDF render the same provenance. CSV may flatten it with a documented key convention. Update SQLite migrations explicitly rather than silently dropping new fields.

## 8. Synthetic known-solution tests

Separate exact/analytical tests from characterization tests.

Exact candidates:

- identical finite distributions: finite evaluated gamma is zero and GPR is 100%;
- uniform nonzero dose offset on a uniform distribution: zero-distance gamma equals the absolute dose offset divided by the applicable DD criterion wherever the cutoff includes the point;
- cutoff boundary: values immediately below the resolved threshold are excluded and values at/above the implementation's documented comparison boundary are handled consistently;
- global versus local on explicitly chosen nonzero reference values: calculate the dose term analytically at zero spatial distance;
- reference/evaluation grid identity in 2D and 3D with singleton-axis coverage;
- invalid shapes, non-monotonic axes, degenerate IOP, and unsupported orientation are rejected with stable errors.

Characterization candidates that require carefully constructed numerical expectations:

- a spatial shift near the DTA boundary;
- different voxel spacing and grid origin;
- parallel versus oblique orientation;
- reference/evaluation reversal, including evaluated-mask and gamma asymmetry.

Do not call a test “known solution” unless its expected values and tolerance are derived before execution. Use generated, non-patient DICOM with fixed UIDs and no demographics when testing the DICOM layer.

## 9. Cross-engine comparison

Freeze one manifest per case before execution. It must bind input hashes, common coordinate arrays, normalization factor, cutoff mask, interpolation fraction, mode, shift setting, and engine versions. Compare more than GPR:

- evaluated-voxel counts and mask intersection/union;
- GPR difference in percentage points;
- voxelwise absolute gamma difference on the shared finite mask;
- median, high-percentile, and maximum finite gamma difference;
- pass/fail confusion counts and agreement rate;
- coordinates and clustered regions of disagreement;
- reference/evaluation reversal behavior;
- runtime, peak resident memory, and any engine resource settings.

Numerical tolerances and required agreement are human decisions. Report all failures; do not remove cases or alter parameters after seeing results.

The legacy Numba kernels exit the candidate loop at the first sampled `gamma <= 1`. That is sufficient for the sampled pass/fail classification but can leave a non-minimal gamma value at a passing reference point. The comparison must therefore separate pass-mask agreement from gamma-map agreement and must not define voxelwise equality as a prerequisite for legacy reproduction. Any proposal to remove this early exit is a separate numerical-behavior change requiring explicit approval and new regression baselines.

### Local controlled-input characterization

A local, non-distributed characterization used anonymized Monaco phantom RTDOSE sources for 3 x 3 cm and 5 x 5 cm fields. Each reference was paired with a deterministic +2% physical-dose variant and a +1 mm positive-column dose-shift variant. The frozen matrix covered axial indices 74, 75, and 76; global and local gamma; 3% / 2 mm; 10% cutoff; `global_max`; interpolation fraction 10; linear resampling; and shift optimization off.

All 24 runs had identical finite masks between engines. The 12 global runs had zero pass/fail disagreements over 41,970 common points. The 12 local runs had 165 pass/fail disagreements over 41,970 common points (0.393%); all occurred in the spatial-shift variants and included disagreements in both directions. The +2% variants had no pass/fail disagreements for either gamma type. Gamma-value distributions remained different even where pass/fail agreed, consistent with the documented Numba early-exit behavior.

This characterization does not use Numba agreement as the definition of PyMedPhys correctness. PyMedPhys is the selected standard, while Numba preserves legacy behavior. The local matrix establishes reproducibility and identifies migration-visible differences; human approval of thresholds and release readiness remain separate gates. Source DICOM, derived DICOM, result arrays, and absolute local paths are excluded from version control.

## 10. External proprietary-system comparisons

A 3DVH comparison is not required for this standardization. PyMedPhys 0.41.0 is the fixed standard engine, while software tests, controlled inputs, input hashes, settings, and runtime provenance establish reproducibility of this application's use of that engine. Historical proprietary-system comparisons remain archival and must not determine standard parameters or be presented as current validation evidence.

## 11. Windows offline design

Extend the existing Python 3.12 x64 bundle only after the supported PyMedPhys version is approved:

1. Add PyMedPhys to runtime requirements and resolve its transitive dependencies into the constraints file.
2. Download wheels on an online Windows x64/Python 3.12 builder with binary-only and hash recording.
3. Collect and verify PyMedPhys license/provenance in the third-party manifest.
4. Install into the temporary verification environment with `--no-index --find-links`.
5. Import PyMedPhys and record its version.
6. Run identical-dose 2D/3D PyMedPhys smoke tests and an explicit Numba smoke test.
7. Verify reports name the requested engine and version.
8. Copy only the signed Python installer, wheelhouse, tracked application files, manifests, and scripts to USB media.
9. Re-run hash verification and offline smoke tests on the destination.

The clean-machine installation acceptance is explicitly pending because no Windows x64 PC without Python 3.12 is currently available. This does not block source development. Do not label the procedure clean-machine verified until that run is eventually recorded.
