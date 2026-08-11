# GPR-comparing

[![CI](https://github.com/inata169/GPR-comparing/actions/workflows/ci.yml/badge.svg)](https://github.com/inata169/GPR-comparing/actions/workflows/ci.yml)

GPR-comparing is a research and education tool for comparing two DICOM RT Dose distributions with two-dimensional or three-dimensional gamma analysis. The Python package is currently named `rtgamma`.

> **Safety notice — not for clinical use.** This software must not be used for patient-specific QA, clinical commissioning, diagnosis, treatment decisions, treatment planning, or any other clinical decision. It is not a certified medical device and does not replace a commercial QA system, treatment planning system, phantom, or measurement device. It has no vendor approval, certification, or endorsement. Every user must perform an independent, purpose-specific verification before relying on any result. Do not place patient DICOM or protected health information in this repository or a public report.

The canonical public documentation is English. The former Japanese README is preserved in [README.ja.md](README.ja.md).

## 1. Overview

The command-line pipeline loads a reference RTDOSE and an evaluation RTDOSE, interprets their DICOM geometry, calculates gamma on reference-grid points, and can write summary reports, images, arrays, and a SQLite record. A Windows PowerShell/WinForms GUI exposes the main analysis options and launches the Fast 3D Viewer.

PyMedPhys 0.41.0 is the standard gamma engine and the omitted-value default in the CLI, batch runner, and GUI. The repository's Numba implementation remains available only through explicit selection for legacy reproduction and engine research. See the [PyMedPhys standardization change](docs/openspec/changes/pymedphys-standard-engine/proposal.md).

## 2. Intended use and limitations

GPR-comparing is intended for reproducible software research, education, method development, and non-patient phantom studies. A gamma pass rate is conditional on the input order, grids, coordinate handling, normalization, dose and distance criteria, cutoff, interpolation, and optional shift search. It is not a universal clinical acceptance result.

The labels `TG218_IMRT`, `TG218_Stereotactic`, and other preset names in [config/presets.json](config/presets.json) are compatibility labels for parameter sets. They do not establish clinical suitability, commissioning, certification, or compliance with any protocol.

The PDF report presents the observed numeric GPR without assigning a clinical PASS/FAIL decision. Interpret it only under a prospectively defined research protocol.

## 3. Features

Implemented features include:

- 2D axial, sagittal, and coronal gamma outputs, and full 3D gamma analysis;
- global and local dose-difference terms;
- reference-dose cutoff and selectable normalization;
- Numba voxel and trilinear sub-voxel search;
- explicit CLI, batch, and GUI selection of the PyMedPhys or Numba gamma engine;
- optional coarse-to-fine shift optimization;
- RTDOSE loading with IPP, IOP, Pixel Spacing, GFOV, and Dose Grid Scaling;
- RTSTRUCT contour masks, per-ROI gamma statistics, and per-ROI DVH statistics;
- CSV, JSON, Markdown, PDF, PNG, NPZ, SQLite, and search-log outputs;
- RTDOSE header comparison;
- a Windows GUI and a PySide6/PyQtGraph Fast 3D Viewer;
- an offline Windows bundle builder and a synthetic, non-patient installation smoke test.

The PyMedPhys default, GUI selection, versioned runtime provenance, controlled local PyMedPhys-versus-Numba characterization, geometry safety gates, and analytical regression tests are implemented. The current standardization scope fixes PyMedPhys at 0.41.0; changing that version requires a separately reviewed validation cycle. Cross-engine numerical equality is not a release criterion because Numba remains a legacy/experimental comparator. Release approval remains open, and a 3DVH comparison is not required for PyMedPhys standardization.

## 4. Supported environment

The CI workflow tests the CLI package on Windows and Ubuntu with Python 3.10, 3.11, and 3.12. The current Windows offline bundle is specifically constrained to 64-bit CPython 3.12.10 on 64-bit Windows 10/11. The WinForms GUI is Windows-specific. The Fast Viewer additionally requires PySide6 Essentials and PyQtGraph.

Python 3.9 has been mentioned in older project material but is not part of the current CI matrix. The PyMedPhys standardization target is CPython 3.12; other CI versions do not define the standardization acceptance environment.

## 5. Installation

For source use, create an isolated environment and install the tracked requirements:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r REQUIREMENTS.txt
```

For the Fast Viewer:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-fast-viewer.txt
```

For tests and document validation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

These commands install the standard PyMedPhys 0.41.0 engine and the explicit legacy/research Numba engine. Use CPython 3.12 for the standardization work.

For an offline Windows computer, follow [Windows offline installation](docs/OFFLINE_INSTALL.md). The current bundle pins PyMedPhys 0.41.0 and explicitly smoke-tests PyMedPhys and Numba. Any future engine-version update requires new dependency resolution, integrity and licensing manifests, software tests, controlled verification, and a rebuilt bundle before it enters the supported baseline.

## 6. CLI quick start

The positional meaning of the inputs is important: `--ref` is the reference distribution whose points are evaluated; `--eval` is the distribution interpolated and searched around each reference point.

```powershell
python -m rtgamma.main `
  --ref C:\data\reference_rtdose.dcm `
  --eval C:\data\evaluation_rtdose.dcm `
  --mode 3d `
  --dd 3 --dta 3 --cutoff 10 `
  --gamma-type global --norm global_max `
  --engine pymedphys `
  --opt-shift off --interp-fraction 10 `
  --report output\research_example\run3d
```

The `3% / 3 mm`, global gamma, 10% cutoff settings above are a reproducible research example for comparing a PHITS-derived RT Dose produced by [dicomxphits](https://github.com/inata169/dicomxphits) against a selected comparison RT Dose. They are not a universal clinical threshold, a vendor recommendation, a certification criterion, or proof of GPR-comparing's validity. Define criteria prospectively from the study aim, data, validation plan, and institutional procedure.

Run `python -m rtgamma.main --help` for the authoritative option list. Notable current defaults are the PyMedPhys engine, 3D mode, 3% DD, 2 mm DTA, 10% cutoff, global gamma, `global_max` normalization, shift optimization on, linear resampling, and interpolation fraction 10. An omitted engine emits a migration notice. Use `--engine numba` to reproduce a legacy Numba result. An unavailable requested/default PyMedPhys engine fails without falling back.

## 7. GUI usage

On Windows, start source mode with `run_gui_python.bat` or run `scripts/run_gui.ps1`. The GUI accepts reference and evaluation RTDOSE files, an output directory, optional RTSTRUCT/ROI values, DD, DTA, cutoff, normalization, a preset, gamma engine, 2D plane/index, thread count, shift optimization, local gamma, sub-voxel interpolation, PDF/NPZ/SQLite/log options, and the requested action.

The actions are Header Compare, 3D Gamma, 2D Gamma, and 3D Viewer. The GUI builds arguments for the same `rtgamma.main` CLI and always passes the selected engine. `PyMedPhys (standard)` is selected initially; `Numba (legacy / experimental)` is available for explicit reproduction work. The value is persisted locally as `Gamma/engine` in the Git-ignored `config/gui_config.ini`. When that file is absent, the GUI reads the tracked `config/gui_config.example.ini`, whose workstation paths are blank. Do not distribute locally saved DICOM paths. An older GUI configuration without the engine key migrates to PyMedPhys and shows a warning. The 3D Viewer launch path uses the Fast Viewer. It can load CT, RTDOSE, RTSTRUCT, and a precomputed `gamma3d.npz` containing the `gamma` array.

The tracked EXE launcher and PyInstaller builder include the same engine contract, but an already-built executable or offline ZIP is not modified in place. Rebuild and reverify those artifacts before expecting the PyMedPhys runtime to be bundled.

GUI labels and tooltips identify engine roles only; they are not clinical authorization.

## 8. 2D and 3D gamma analysis

In 3D mode, gamma is calculated for the full reference volume. The final Numba path searches the original evaluation array using one-dimensional coordinate axes adjusted for the projected IPP origin difference.

In 2D mode with shift optimization off, only the selected reference slice is built in world coordinates. The evaluation dose is sampled onto that thin reference slice, and gamma is calculated on the resulting singleton-axis 3D array. The global normalization value is taken from the full reference volume. With shift optimization on, the current implementation runs the full-volume search first and then reports/saves the requested slice; it is not the same computational path as the no-shift 2D fast path.

`--plane-index auto` selects the middle slice along the requested array axis. An explicit index is an array index, not a patient-coordinate value.

## 9. Global and local gamma

`--gamma-type global` uses a single dose normalization denominator. With `global_max` or `max_ref`, the current code uses the maximum finite reference dose; those two names are therefore equivalent in the current implementation.

`--gamma-type local` uses the dose at each reference voxel as the dose-difference denominator. It is normally stricter in lower-dose regions. Reference values effectively equal to zero are not evaluated in the local Numba path.

The PyMedPhys adapter explicitly forwards `local_gamma`, `interp_fraction`, and the resolved global normalization. Local results are not assumed numerically equivalent to Numba. The approved release policy does not require a numerical or mask-agreement threshold between engines; observed differences must still be recorded and reviewed without case-specific tuning.

A local migration characterization used two anonymized Monaco phantom RTDOSE distributions (3 x 3 cm and 5 x 5 cm fields) and controlled evaluation variants derived from each source: a uniform +2% dose scale and a +1 mm shift in the positive DICOM column direction. The fixed 2D protocol used axial slices 74, 75, and 76, 3% / 2 mm, a 10% reference cutoff, `global_max`, interpolation fraction 10, linear resampling, and shift optimization off. Across 24 engine comparisons, the finite evaluated masks agreed in every run. Global gamma had no pass/fail disagreements across 41,970 common points. Local gamma had 165 disagreements across 41,970 common points (0.393%), all in the +1 mm shift variants; the uniform +2% variants had none. Disagreements occurred in both directions, so they are recorded as engine-definition and interpolation differences rather than attributed solely to the Numba early exit.

These local results support the PyMedPhys standard while keeping Numba available for explicit legacy reproduction. They do not establish clinical validity, approve a numerical tolerance, or authorize a release. The source and derived DICOM files and numerical result arrays are local-only and are not distributed by this repository.

## 10. Dose-difference criterion

`--dd` is the dose-difference criterion in percent. For global gamma, the Numba dose term is `(evaluation - reference) / normalization * 100`. For local gamma it is `(evaluation - reference) / reference_voxel * 100`.

For the Numba engine, `--norm none` sets the normalization factor to `1.0` dose unit; it does not convert `--dd` into a clearly specified absolute-dose criterion. The approved PyMedPhys scope rejects `norm=none` fail-closed; no absolute-dose mapping is inferred. A future mapping would require a separate specification and validation cycle. Before calculation, the program rejects missing or invalid `DoseUnits` and reference/evaluation unit mismatches.

## 11. Distance-to-agreement criterion

`--dta` is the spatial criterion in millimetres. The Numba engine evaluates candidate points within the DTA sphere and combines squared spatial and dose terms. With interpolation fraction 1 it searches evaluation voxels. With a larger fraction it samples the evaluation grid trilinearly at sub-voxel offsets.

## 12. Dose cutoff

`--cutoff` is applied to the reference dose before gamma evaluation. For `global_max` and `max_ref`, the threshold is the stated percentage of the maximum finite reference dose. Excluded points are represented by `NaN` and are omitted from the pass-rate denominator.

The CLI also exposes `--cutoff-mask`, `--low-dose-exclusion`, and `--tolerance`, but the current main calculation does not use those parsed values. Do not rely on them until implementation and tests exist.

## 13. Sub-voxel interpolation

`--interp-fraction N` controls the current Numba sub-voxel search. For `N > 1`, the nominal sampling step is `DTA / N` millimetres and the evaluation dose is trilinearly sampled. `N = 1` selects voxel-centre search. Runtime and memory use increase with the search density.

The current Numba kernels stop searching a reference point when the first sampled candidate with `gamma <= 1` is found. This preserves the sampled pass/fail decision but does not guarantee the minimum gamma value for a passing point. Consequently, Numba gamma maps, means, and percentiles must not be treated as numerically equivalent to PyMedPhys even when GPR and evaluated masks agree. This is documented legacy behavior; the standardization work does not silently change it.

This parameter is distinct from `--interp`, which selects nearest, linear, or cubic B-spline interpolation when evaluation or CT values are resampled onto another grid. In the current 3D final gamma path, `--interp` does not select the Numba gamma interpolation method.

Do not tune `interp_fraction` case by case to reproduce another system's GPR. A comparison protocol must fix it before external-system evaluation. The existing `config/3dvh_reference.json` and sensitivity script are historical exploratory assets and are not an accepted validation protocol.

## 14. RTSTRUCT/ROI analysis

Supply `--rtstruct` and repeat `--roi` to select structures; omit `--roi` to process all contours found. Masks are generated on the reference RTDOSE grid. Reports include voxel count, evaluated count, ROI GPR, gamma statistics, and reference/evaluation DVH statistics.

Current limitations include exact, case-sensitive ROI-name matching; contour-to-slice matching by world `z`; in-plane polygon conversion using the world `x/y` components; union of multiple contours on a slice without explicit hole semantics; and incomplete evidence for oblique RTSTRUCT geometries. Independently inspect masks before interpreting ROI results. DVH functionality is exploratory and is not evidence of equivalence to a treatment planning system or commercial DVH implementation.

## 15. Output files and reports

With `--report output/run`, the program writes `run.csv`, `run.json`, `run.md`, and, by default, `run.pdf`. Use `--no-pdf` to suppress PDF generation. Shift optimization also writes `run_search_log.json`. Header mode writes exactly the path supplied to `--report` and requires that option.

For 2D mode, `--save-gamma-map` and `--save-dose-diff` write images. For 3D mode they write compressed NPZ files with keys `gamma` and `dose_diff_pct`, respectively. `--db [PATH]` writes a SQLite summary. Output directories are created when needed.

Reports contain input basenames, mode and plane, DD/DTA/cutoff, gamma type, normalization, interpolation fraction, pass rate, shift, selected Frame of Reference values, an orientation similarity value, warnings, gamma statistics, histogram data, optional ROI/DVH data, and the requested gamma-map path. Schema-versioned provenance is included in JSON and SQLite and rendered in CSV, Markdown, and PDF. CSV stores structured values as strict JSON text; JSON is the canonical machine-readable form and emits `null`, never non-standard `NaN`, for non-finite values.

## 16. Reproducibility information

Report schema version 2 records the application version source and Git commit when available, dirty-worktree state, engine and version, Python and operating system, UTC start/end and duration, reference/evaluation basenames and SHA-256 digests, complete effective gamma and shift settings, selected axis/LPS shift and candidate count, ROI selection, and reference/evaluation grid summaries. Parsed legacy controls that are not applied by the current calculation (`threads`, `gpu`, `seed`, `cutoff-mask`, `low-dose-exclusion`, `spacing`, and `tolerance`) are explicitly marked as not applied rather than presented as effective settings.

The provenance privacy policy records basenames and SHA-256 file identity but excludes absolute paths, PatientName, PatientID, birth date, accession numbers, institution fields, and other DICOM demographics.

## 17. Validation and known limitations

The repository includes synthetic unit and integration tests for the PyMedPhys default, explicit legacy Numba selection, Global/Local identity cases, adapter argument mapping, shift-search setting propagation, strict report-schema validation, and report/SQLite provenance. This is software verification, not clinical validation or an approved numerical acceptance package.

Local characterization with controlled derivatives of anonymized 3 x 3 cm and 5 x 5 cm Monaco phantom RTDOSE distributions confirmed that equal GPR can coexist with material voxelwise gamma differences. These local inputs and results are not distributed by the repository and are not acceptance or clinical-validation evidence.

A separate [controlled 5 x 5 cm RTDOSE verification record](docs/PYMEDPHYS_CONTROLLED_RTDOSE_VERIFICATION_2026-08-11.md) documents two full-volume PyMedPhys 0.41.0 source-GUI runs and Fast 3D Viewer checks: a uniform +2% dose variant and a +1 mm positive-column spatial-shift variant. It records only input hashes, effective settings, summary results, and explicit limitations; the DICOM inputs and numerical outputs remain local and Git-ignored.

The project owner approved the documented validation scope, numerical policy, and known limitations for release preparation on 2026-08-11. This is not clinical-use or release approval. Remaining compatibility-cleanup, clean-candidate, CI, offline-acceptance, and publication gates are listed in the [release-readiness checkpoint](docs/RELEASE_READINESS_2026-08-11.md).

The RTDOSE loader validates IPP, IOP, Pixel Spacing, GFOV, dimensions, Dose Grid Scaling, Dose Units, and finite dose values before calculation. It accepts strictly ascending or descending GFOV and sorts frames and offsets together into ascending order. Axial absolute-z GFOV is converted to offsets from IPP. Different origins and voxel spacing are supported, but differing reference/evaluation orientations, Dose Units, or present Frame of Reference UIDs fail closed. A missing Frame of Reference UID remains a recorded warning for compatibility with older research data. The interpolating Numba kernel assumes uniform evaluation-axis spacing based on the first interval; PyMedPhys is the standard engine.

Historical 3DVH summaries and PDFs remain archival material only. They are not required for PyMedPhys standardization, are not part of the acceptance plan, and do not support claims of equivalence, clinical validation, or vendor approval.

The Windows offline bundle has automated integrity and licensing checks plus explicit PyMedPhys 0.41.0 and Numba smoke paths. A Python 3.12 x64 wheelhouse/ZIP was rebuilt and passed a local `--no-index` bundle smoke test; its digest and limitations are recorded in the [2026-08-11 progress record](docs/PROGRESS_2026-08-11.md). A physically network-isolated installation and the clean Windows/Python-absent acceptance run remain explicitly pending because no suitable test PC is currently available; this is not a blocker for source development.

## 18. Testing

Install development dependencies, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check rtgamma tests scripts
.\.venv\Scripts\python.exe scripts\validate_report.py path\to\run.json
```

Tests requiring local DICOM fixtures skip when those files are absent. The offline bundle's `RUN_SMOKE_TEST.bat` generates non-patient synthetic CT, RTDOSE, and RTSTRUCT, checks imports and DICOM I/O, and runs header, 2D, and 3D paths. That is an installation smoke test, not clinical validation.

## 19. Companion projects

- [dicomxphits](https://github.com/inata169/dicomxphits) is an independently developed and versioned education/research workflow that can produce a coordinate-corrected PHITS-derived RT Dose and optionally hand it to this repository for external comparison. It is not bundled with GPR-comparing.
- [rt-dicom-toolkit](https://github.com/inata169/rt-dicom-toolkit) is an independently developed and versioned RT DICOM anonymization and verification toolkit. It is not bundled with GPR-comparing and does not form part of the gamma engine.

`dicom4dicomxphits` is not listed as a public data source or available companion project here.

## 20. License and disclaimer

GPR-comparing application code and documentation are provided under the [MIT License](LICENSE). Bundled Python, Qt/PySide6, and Python packages retain their own licenses; see `offline/NOTICE.txt` and the generated third-party manifest in an offline bundle.

The software is provided "AS IS" without warranty of accuracy, completeness, fitness for a particular purpose, or non-infringement. The authors and copyright holders are not liable for harm or loss arising from use, misuse, or inability to use it. These license terms do not convert the software into a medical device or authorize clinical use.
