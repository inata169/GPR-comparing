# Change proposal: PyMedPhys as the standard gamma engine

Status: In progress — validation scope approved for release preparation; source CLI/GUI, controlled full-volume GUI verification, and a locally smoke-tested offline bundle are complete; clean-candidate, policy, CI, and release gates remain pending
Priority: Primary development track
Public interfaces affected: CLI, batch CSV, GUI, configuration, reports, tests, executable builder, and offline bundle builder; clean-machine artifact acceptance remains pending

## Why

GPR-comparing needs one clearly identified, independently maintained standard gamma implementation and complete provenance for every result. PyMedPhys is the selected standard engine. The in-repository Numba implementation remains valuable for performance research, controlled comparison, and legacy reproduction, and is identified as experimental/legacy.

Before phase one, the repository was not in that state:

- `REQUIREMENTS.txt` comments out PyMedPhys;
- `rtgamma.main` and `rtgamma.optimize` pass `use_pymedphys=False` at every production call;
- the CLI, GUI, batch CSV, and INI configuration have no engine selector;
- the dormant wrapper does not forward local gamma or interpolation fraction to PyMedPhys;
- reports do not record the engine, engine version, application version, commit, Python, OS, or complete calculation settings;
- the offline bundle and smoke test include only the Numba production path;
- no PyMedPhys-versus-Numba acceptance criteria have been approved.

A local audit using PyMedPhys 0.41.0 confirmed the wrapper gap: requesting `gamma_type=local` produced the same result as global, and changing the wrapper's `interp_fraction` from 1 to 10 did not change the PyMedPhys call. This is evidence about the current adapter, not an acceptance result for either engine.

## Phase-one implementation status

The Python 3.12 source implementation activates PyMedPhys 0.41.0 in requirements; makes it the CLI, batch, and GUI default; preserves explicit Numba legacy selection; and routes shift optimization through the selected engine with the same interpolation fraction as the final calculation. The source and EXE GUI launchers expose and persist the engine. Schema version 2 records privacy-conscious runtime, input, settings, geometry, and engine provenance in strict JSON and renders it through CSV, Markdown, PDF, SQLite, and batch outputs. A fixed local 24-run, multi-slice global/local characterization records masks, GPR, voxelwise differences, confusion, coordinates, and runtime for controlled variants derived from anonymized phantom RTDOSE. A separate full-volume 5 x 5 cm source-GUI check exercised uniform +2% and positive-column +1 mm evaluation variants through 3D PyMedPhys calculation, saved reports/NPZ, and the Fast 3D Viewer. The DICOM and numerical artifacts remain non-distributed. The rebuilt Python 3.12 offline bundle passed local `--no-index` smoke testing of PyMedPhys, explicit Numba, reports, DICOM I/O, and Fast Viewer imports. Approved numerical criteria, clean-machine/network-isolated installation, peak-memory characterization, and release approval remain open. A 3DVH comparison is not an acceptance requirement.

On 2026-08-11, the project owner approved the implemented validation scope and known limitations for release preparation. This approval fixes CPython 3.12 and PyMedPhys 0.41.0 as the present source baseline and accepts that 3DVH comparison and clean-machine testing are not prerequisites for continued source development. It does not approve clinical use, numerical cross-engine thresholds, a dependency update policy, a version change, tag, or GitHub Release. Remaining gates are enumerated in the [release-readiness checkpoint](../../../RELEASE_READINESS_2026-08-11.md).

## Proposed outcome

After implementation and acceptance:

1. PyMedPhys is the default when an engine is omitted.
2. The Numba engine is selected only by an explicit `numba` value and is labelled experimental/legacy in public documentation and reports.
3. An unavailable or incompatible requested engine causes a clear error. There is no silent fallback.
4. Every result records a machine-readable provenance envelope and renders the same information in human-readable reports.
5. Engine comparison uses fixed, prospective inputs and settings; it never tunes a case to reproduce another implementation or commercial system.
6. Standardization is supported by exact synthetic tests, differential tests, performance characterization, and an offline installation test.

## Scope

- Introduce a typed engine abstraction and one settings object used by CLI, GUI, batch mode, shift optimization, and report generation.
- Implement a complete PyMedPhys adapter for 2D and 3D, global and local gamma, normalization, cutoff, interpolation fraction, and supported geometry.
- Preserve the current Numba calculation as an explicitly selected experimental engine.
- Add engine selection to CLI, GUI, `gui_config.ini`, batch CSV, and packaged launch paths.
- Add deterministic engine errors and migration guidance.
- Add provenance fields and update the JSON schema, CSV/Markdown/PDF rendering, SQLite storage, and examples.
- Add synthetic known-solution tests and PyMedPhys-versus-Numba comparison tests.
- Extend the Windows offline wheelhouse, licensing manifest, integrity checks, and smoke test to PyMedPhys.

## Non-goals

- Declaring PyMedPhys a gold standard, clinical truth, medical device, or vendor-approved reference.
- Claiming clinical validity or suitability for patient QA or commissioning.
- Choosing numerical cross-engine acceptance thresholds without investigator approval.
- Reproducing 3DVH by case-specific parameter adjustment.
- Publishing patient DICOM, restricted vendor data, or data with unclear redistribution rights.
- Changing a version, tag, or release as part of this documentation change.

## Compatibility policy

The source default is PyMedPhys. Existing commands that omit an engine now change numerical implementation and emit a migration notice. Legacy reproduction remains possible with an explicit Numba selection. GUI launchers always pass the selected engine and migrate a missing `Gamma/engine` setting to PyMedPhys with a visible warning.

The transition release, offline bundle, and removal schedule for the migration warning still require project-owner approval. A report without an engine field remains a legacy report and must not be inferred to be PyMedPhys.

## Safety and reproducibility

No fallback may substitute Numba when PyMedPhys was requested or is the default. The failure must name the unavailable engine and provide installation guidance. Reports must avoid DICOM demographics and local secrets. File digests may be recorded only under a documented privacy policy; basenames alone do not uniquely identify inputs.

## Existing 3DVH material

The tracked summary, PDFs, configuration, and scripts are historical exploratory records. They are not required for PyMedPhys standardization and are outside this change's acceptance plan. Historical scripts selected a different interpolation fraction per case by minimizing the GPR difference to 3DVH; those results must not determine standard settings or be presented as current validation evidence.

## Human decisions required

- Approve the PyMedPhys version range and dependency-lock policy.
- Approve the transition release and the schedule for removing the temporary omitted-engine migration notice.
- Approve the meaning or rejection policy for `norm=none` under both engines.
- Review the implemented fail-closed policy for differing DICOM orientations and present Frame of Reference UID mismatches.
- Approve cross-engine numerical tolerances and required pass/fail-mask agreement.

## References

- [Design](design.md)
- [Implementation tasks](tasks.md)
- [PyMedPhys gamma API](https://docs.pymedphys.com/en/stable/users/ref/lib/gamma.html)
- [PyMedPhys package](https://pypi.org/project/pymedphys/)
