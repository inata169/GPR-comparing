# Change proposal: PyMedPhys as the standard gamma engine

Status: Completed for the v0.9.3 source release — source CLI/GUI, controlled full-volume GUI verification, provenance and cache safety, local verification, and the supported CI matrix are complete; clean-machine offline acceptance remains pending
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

The Python 3.12 source implementation activates PyMedPhys 0.41.0 in requirements; makes it the CLI, batch, and GUI default; preserves explicit Numba legacy selection; and routes shift optimization through the selected engine with the same interpolation fraction as the final calculation. The source and EXE GUI launchers expose and persist the engine. Schema version 2 records privacy-conscious runtime, input, settings, geometry, and engine provenance in strict JSON and renders it through CSV, Markdown, PDF, SQLite, and batch outputs. A fixed local 24-run, multi-slice global/local characterization records masks, GPR, voxelwise differences, confusion, coordinates, and runtime for controlled variants derived from anonymized phantom RTDOSE. A separate full-volume 5 x 5 cm source-GUI check exercised uniform +2% and positive-column +1 mm evaluation variants through 3D PyMedPhys calculation, saved reports/NPZ, and the Fast 3D Viewer. The DICOM and numerical artifacts remain non-distributed. The rebuilt Python 3.12 offline bundle passed local `--no-index` smoke testing of PyMedPhys, explicit Numba, reports, DICOM I/O, and Fast Viewer imports. Cross-engine numerical equality is not a release criterion; peak-memory characterization is explicitly deferred. The v0.9.3 source release is approved; clean-machine/network-isolated installation claims remain open and no offline binary bundle is attached. A 3DVH comparison is not an acceptance requirement.

On 2026-08-11, the project owner approved the implemented validation scope and known limitations, then explicitly approved the v0.9.3 source version, tag, and GitHub Release. This fixes CPython 3.12 and PyMedPhys 0.41.0 as the present source baseline and accepts that 3DVH comparison and clean-machine testing are not prerequisites for this source release. The policy freeze keeps the exact PyMedPhys 0.41.0 pin until a separately reviewed validation cycle, approves fail-closed rejection of `norm=none` for PyMedPhys, declines to use PyMedPhys-versus-Numba numerical equality as a release criterion, defers peak-memory characterization, and retains clean-machine installation testing as pending. It does not approve clinical use or a clean-machine/offline-installation claim. The disposition is recorded in the [release-readiness checkpoint](../../../RELEASE_READINESS_2026-08-11.md).

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
- Publishing binary/offline artifacts without the separately required clean-machine acceptance evidence.

## Compatibility policy

The source default is PyMedPhys. Existing commands that omit an engine now change numerical implementation and emit a migration notice. Legacy reproduction remains possible with an explicit Numba selection. GUI launchers always pass the selected engine and migrate a missing `Gamma/engine` setting to PyMedPhys with a visible warning.

The v0.9.3 source transition release is approved. Publishing an offline bundle and removing the migration warning still require separate project-owner approval. A report without an engine field remains a legacy report and must not be inferred to be PyMedPhys.

## Safety and reproducibility

No fallback may substitute Numba when PyMedPhys was requested or is the default. The failure must name the unavailable engine and provide installation guidance. Reports must avoid DICOM demographics and local secrets. File digests may be recorded only under a documented privacy policy; basenames alone do not uniquely identify inputs.

## Existing 3DVH material

The tracked summary, PDFs, configuration, and scripts are historical exploratory records. They are not required for PyMedPhys standardization and are outside this change's acceptance plan. Historical scripts selected a different interpolation fraction per case by minimizing the GPR difference to 3DVH; those results must not determine standard settings or be presented as current validation evidence.

## Human decisions

Recorded on 2026-08-11:

- keep CPython 3.12 and an exact PyMedPhys 0.41.0 pin for the current baseline; use a separately reviewed validation cycle for an engine-version update;
- reject `norm=none` fail-closed for PyMedPhys while retaining the documented Numba legacy behavior;
- keep fail-closed rejection for differing DICOM orientations and present Frame of Reference UID mismatches;
- do not use PyMedPhys-versus-Numba numerical or mask-agreement thresholds as a release criterion;
- defer peak-memory characterization and clean-machine installation testing with their claims explicitly excluded.
- approve v0.9.3 as a source-only release, including its tag and GitHub Release, without binary assets.

Still requiring a separate decision:

- approve the schedule for removing the temporary omitted-engine migration notice, internal boolean compatibility switch, and legacy-report compatibility behavior.

## References

- [Design](design.md)
- [Implementation tasks](tasks.md)
- [PyMedPhys gamma API](https://docs.pymedphys.com/en/stable/users/ref/lib/gamma.html)
- [PyMedPhys package](https://pypi.org/project/pymedphys/)
