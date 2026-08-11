# Tasks: PyMedPhys standard engine

The implemented source target is CPython 3.12 and PyMedPhys 0.41.0. Checked tasks do not by themselves approve clinical use, the offline bundle, or a release.

## A. Decisions and protocol freeze

- [ ] Approve supported Python and PyMedPhys versions and the lock/update policy.
- [x] Approve staged versus direct default-engine migration.
- [ ] Approve `norm=none` mapping or rejection.
- [x] Use fail-closed rejection for differing orientations; do not claim arbitrary-orientation resampling support.
- [ ] Approve cross-engine numerical and mask-agreement criteria.
- [x] Define application-version and report-schema-version sources. Source runs use installed metadata, an explicit environment value, or Git describe; report schema version is 2.

## B. Engine architecture

- [x] Add engine identifiers, an adapter dispatch interface, and a shared immutable gamma-settings model.
- [x] Implement the phase-one PyMedPhys mapping, including local gamma and interpolation fraction.
- [x] Adapt the Numba implementation without changing its legacy numerical path.
- [x] Route shift optimization through the selected engine.
- [x] Add fail-closed engine import checks and package-version reporting. Compatibility-range checks remain pending.
- [ ] Remove the internal boolean engine switch after migration.

## C. Public interfaces and compatibility

- [x] Add `--engine {numba,pymedphys}` and help text.
- [x] Add GUI engine selection and persistence.
- [x] Add batch CSV engine selection.
- [ ] Add migration warnings for legacy configuration/report files without engine identity.
- [x] Update source/EXE GUI launchers and the executable builder. Offline bundle verification remains separate.
- [x] Document how to reproduce a legacy Numba result explicitly.

## D. Provenance and reports

- [x] Implement the versioned provenance envelope and PHI redaction policy.
- [x] Record application, commit, engine, Python, OS, UTC time, and duration.
- [x] Record complete effective gamma, interpolation, shift, ROI, and grid settings; parsed non-effective controls are labelled as not applied.
- [x] Update JSON schema and example, Markdown, PDF, CSV, SQLite, and batch summaries.
- [ ] Mark old reports as engine unknown rather than inferring an engine.
- [ ] Add report-schema validation tests, including ROI/DVH reports and strict JSON handling.

## E. Synthetic tests

- [x] Add exact PyMedPhys identical-distribution tests in 2D and 3D; retain Numba 3D regression coverage.
- [x] Add analytical uniform dose-difference tests.
- [x] Add global/local analytical tests.
- [x] Add cutoff-boundary tests.
- [x] Add spacing and origin characterization tests.
- [x] Add orientation support/rejection tests.
- [x] Add invalid/non-monotonic geometry rejection tests.
- [x] Add reference/evaluation reversal characterization.

## F. PyMedPhys-versus-Numba study

- [x] Create local deterministic test manifests with input/output SHA-256 digests and fixed settings. The inputs and numerical artifacts remain non-distributed.
- [x] Record evaluated-mask counts and overlap.
- [x] Record GPR and voxelwise gamma differences.
- [x] Record pass/fail confusion and disagreement coordinates.
- [ ] Record runtime and peak memory.
- [ ] Review every threshold failure without case-specific tuning.
- [ ] Publish the complete non-patient reproducibility package or document why it cannot be public.

## G. External proprietary-system comparisons

- [x] Exclude a 3DVH comparison from the PyMedPhys-standardization acceptance requirements.
- [x] Keep historical case-tuned material archival and prohibit it from determining standard settings.

## H. Offline Windows delivery

- [x] Pin PyMedPhys 0.41.0 and its required dependencies in the Windows constraints.
- [ ] Build the Windows wheelhouse and confirm every pinned wheel is available.
- [ ] Extend license and SHA-256 manifests.
- [x] Add explicit PyMedPhys and Numba smoke paths.
- [x] Assert report engine/version fields in the offline smoke test.
- [ ] Build and verify with network-disabled installation.
- [ ] Pending (test environment unavailable): complete the clean Windows x64/Python-absent installation test when a suitable PC becomes available. This does not block source development.
- [ ] Record the exact bundle digest, environment, output, and limitations.

## I. Release gate

- [ ] Full CI and local test suite pass on every supported Python/OS combination.
- [x] CLI help, source/EXE GUI launchers, batch, config, schema, and public documentation agree. Rebuilt distribution artifacts remain pending.
- [x] No silent engine fallback exists.
- [x] No unsupported clinical, 3DVH-equivalence, precision-guarantee, or vendor claim remains in the canonical public documentation.
- [ ] Validation scope and known limitations receive human approval.
- [ ] Only after all gates: separately consider version, tag, and release actions.
