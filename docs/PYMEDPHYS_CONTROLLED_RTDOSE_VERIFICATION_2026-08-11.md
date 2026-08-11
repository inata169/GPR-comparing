# PyMedPhys controlled RTDOSE verification record — 2026-08-11

## Status and scope

This record documents a local source-GUI and Fast 3D Viewer workflow check using a non-patient, anonymized Monaco phantom RTDOSE and two deterministic derived evaluation doses. It is reproducibility and software-workflow evidence only. It is not clinical validation, patient-QA evidence, a commissioning result, a PyMedPhys-versus-Numba acceptance threshold, or vendor approval.

The source and derived DICOM files, numerical arrays, logs, and absolute local paths are intentionally excluded from version control. Only privacy-conscious identifiers, SHA-256 digests, effective settings, and summary results are recorded here.

## Environment

| Item | Value |
|---|---|
| Date | 2026-08-11 |
| Application revision | `6584d22ed63ccb68d2fe0accc133623c707b61e6` |
| Application version string | `v0.9.2-17-g6584d22` |
| Worktree state recorded by reports | dirty |
| Python | CPython 3.12.10 |
| Operating system | Windows 11 AMD64 |
| Gamma engine | PyMedPhys 0.41.0 |
| Reference field | 5 x 5 cm Monaco phantom |
| Reference grid | 151 x 153 x 153; 2.0 x 2.0 mm in-plane spacing |

Because both reports record a dirty worktree, these runs are retained as local workflow verification and must not be represented as release-gate results from a pristine source revision.

## Controlled inputs

| Role | Controlled operation | SHA-256 |
|---|---|---|
| Reference | Unmodified anonymized phantom RTDOSE | `efd5c7034db84393f960e32aa3f7cf6cfc9fb4fc4bf70f99a1cd5a985889b2b5` |
| Evaluation A | Multiply physical dose by 1.02 without changing geometry | `d0dcebb125be09f9f9ff1cdf963596f6eff23b7663c219a8a2263faf7d16bcc8` |
| Evaluation B | Shift the dose distribution +1.0 mm along the positive DICOM column direction, using linear interpolation and zero outside fill | `b2da1353803a8096795903a201d4a74208b46f22d6208dd867198795c196129b` |

The shifted input corresponds to 0.5 pixel at the 2.0 mm in-plane spacing. The operation shifts the dose distribution within the controlled evaluation object; it does not claim to model a particular delivery error or establish a clinical ground truth.

## Effective analysis settings

Both runs used 3D global gamma, 3% dose difference, 2 mm DTA, a 10% reference-dose cutoff, `global_max` normalization, linear evaluation-dose resampling, and interpolation fraction 3. The uniform +2% GUI run had shift optimization enabled; it evaluated 101 candidates and selected exactly 0 mm. The +1 mm spatial-shift run had shift optimization disabled and evaluated no shift candidates.

## Results

| Result | Uniform +2% | Positive-column +1 mm |
|---|---:|---:|
| Evaluated voxels | 121,904 | 121,904 |
| Passing voxels (`gamma <= 1`) | 121,904 | 121,773 |
| Failing voxels | 0 | 131 |
| GPR | 100.0000% | 99.8925% |
| Mean gamma | 0.258557 | 0.142844 |
| Median gamma | 0.224816 | 0.024414 |
| Gamma p95 | 0.539355 | 0.696922 |
| Gamma p99 | 0.634423 | 0.833425 |
| Maximum gamma | 0.666669 | 1.022724 |
| Selected shift | 0 mm | 0 mm (optimization disabled) |
| Report warnings | none | none |
| Runtime | 141.812 s | 3.762 s |

For the uniform +2% case, the observed maximum gamma of approximately 0.6667 is consistent with the zero-distance global dose term `2% / 3%`. The realistic spatial-shift case produced a small number of failing voxels near the threshold; this is an observed characterization result, not a generally applicable expected GPR.

## GUI and Fast 3D Viewer observations

The Windows source GUI successfully completed both 3D PyMedPhys runs and wrote Markdown, JSON, CSV, PDF, SQLite, dose-difference NPZ, gamma NPZ, and run-log outputs. The Fast 3D Viewer then loaded each saved `gamma3d.npz` with the phantom CT, reference dose, and evaluation dose. The operator confirmed that both viewers opened successfully and that the controlled positional displacement was visible for the +1 mm case.

These visual observations confirm the exercised GUI-to-CLI-to-report-to-viewer workflow. They do not independently validate coordinate orientation for every supported DICOM geometry, RTSTRUCT/ROI rendering, clinical interpretation, or treatment suitability.

## Data governance and limitations

- No source or derived DICOM, Gamma array, dose-difference array, database, PDF, or run log from these cases is distributed by the repository.
- The local case files and outputs remain under the Git-ignored `test_data_local/` tree.
- The reports recorded matching Frame of Reference UIDs, an orientation minimum dot product of 1.0, and no geometry warnings.
- This check does not compare against Sun Nuclear 3DVH and no such comparison is required for PyMedPhys standardization.
- A clean Windows machine without Python remains unavailable, so clean-machine offline installation acceptance is still pending.
- Release approval and the project's validation-scope approval remain separate human decisions.

## Project-owner disposition

On 2026-08-11, the project owner approved this verification scope and its stated limitations for the purpose of proceeding with release preparation. The approval does not convert these results into clinical validation and does not authorize a version change, tag, publication, or GitHub Release. Open release gates are tracked in the [release-readiness checkpoint](RELEASE_READINESS_2026-08-11.md).
