# Windows offline installation

This guide describes the repository's existing USB-transfer bundle for a Windows computer without internet access. It is an installation mechanism for research and education use, not a clinical deployment or commissioning procedure.

The bundle definition now pins PyMedPhys 0.41.0 and its required dependencies and explicitly smoke-tests both the PyMedPhys standard path and the Numba legacy path. A newly built ZIP is still a candidate bundle until it passes the clean-machine acceptance run described below; older ZIP artifacts must not be described as PyMedPhys-capable.

## Supported bundle target

- 64-bit Windows 10 or 11
- CPython 3.12.10 x64 supplied by the bundle
- a dedicated virtual environment at `app/.venv`
- installation and smoke testing without network access
- a writable local installation directory; do not execute directly from USB media

The source CI matrix also covers Python 3.10 and 3.11, but this offline bundle is specific to Python 3.12 x64.

## Dependency sources

- `REQUIREMENTS.txt`: source CLI/report runtime (Numba plus PyMedPhys 0.41.0)
- `requirements-fast-viewer.txt`: PySide6 Essentials and PyQtGraph
- `offline/requirements-offline.txt`: offline installation entry point
- `offline/constraints-py312-win64.txt`: pinned direct and transitive Windows x64/Python 3.12 packages

PyMedPhys 0.41.0, `setuptools`, `tomlkit`, and `typing_extensions` are pinned in the offline constraints. The builder must resolve their Windows x64/Python 3.12 wheels, collect their license material, and verify the installed PyMedPhys version without network access.

## Build on an online Windows computer

Use a clean worktree, Windows x64, Python 3.12 x64, Git, PowerShell 5.1 or later, and access to python.org and PyPI.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\offline\build_offline_bundle.ps1
```

To select the builder Python explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\offline\build_offline_bundle.ps1 `
  -PythonExe C:\Python312\python.exe
```

The builder downloads the official CPython installer, verifies its SHA-256 and Authenticode signer, resolves binary wheels, creates a temporary verification environment, performs an offline-only installation and import check, collects third-party license materials, hashes immutable bundle files, and creates a ZIP under `dist/offline/`.

Review at least:

- `BUNDLE_INFO.txt` for the commit, build time, Python version, and source;
- `SHA256SUMS.txt` for file integrity;
- `THIRD_PARTY_MANIFEST.json` and `THIRD_PARTY_LICENSES/` for package provenance and licensing;
- `NOTICE.txt` for distribution boundaries.

Do not add DICOM, local GUI settings, SQLite databases, generated results, credentials, licensed PHITS/RT-PHITS tools, or restricted vendor material to the bundle.

## Transfer and install offline

1. Copy the ZIP to approved USB storage.
2. On the offline computer, copy it to a short writable local path such as `C:\GPR-comparing-offline`.
3. Fully extract the ZIP.
4. Run `VERIFY_BUNDLE.ps1` or the packaged verification entry point before installation.
5. Double-click `INSTALL_OFFLINE.bat`.
6. Require the final success message; treat any hash, signature, Python preflight, wheel, or smoke-test failure as a failed installation.

The installer sets pip to offline-only operation, creates the bundled runtime and dedicated virtual environment, installs from the wheelhouse, checks runtime imports, and runs the synthetic smoke test. It does not use global site-packages. Its current preflight intentionally stops if an external Python 3.12 x64 installation is detected, to avoid modifying an existing environment.

## Launch and manual checks

Double-click `LAUNCH_GPR_COMPARING.bat`. Confirm manually that:

1. the main GUI opens;
2. Header Compare, 2D Gamma, 3D Gamma, and 3D Viewer actions are visible;
3. the Fast Viewer opens on the target display/graphics environment;
4. application-control and antivirus policies do not block Python or Qt;
5. the GUI is using the bundle's `app/.venv`, not another Python.

The automated test cannot fully validate display drivers, remote desktop behavior, or local application-control policy.

## Run the smoke test again

Double-click `RUN_SMOKE_TEST.bat`. It generates synthetic, non-patient CT, RTDOSE, and RTSTRUCT and checks:

- Python 3.12 x64 and current runtime imports;
- Fast Viewer imports;
- synthetic DICOM generation and loading;
- RTDOSE header comparison;
- 2D gamma with JSON, Markdown, PDF, and PNG outputs;
- 3D gamma;
- at least 99.99% pass rate for identical synthetic dose inputs.

Results are written below `smoke_output/YYYYMMDD_HHMMSS/`, including `SMOKE_TEST_RESULT.json`. The reports must identify PyMedPhys 0.41.0 for the explicit standard-engine 2D/3D runs and Numba for the explicit legacy run. This verifies installation health and engine routing only; it does not validate clinical accuracy or a facility workflow.

## Integrity and reproducibility record

For each distributed bundle, retain outside the public data path:

- source commit and worktree-clean status;
- bundle ZIP SHA-256;
- CPython installer source, signature result, and SHA-256;
- exact constraints and wheel SHA-256 values;
- third-party manifest and licenses;
- build-machine OS and Python;
- destination-machine OS and hardware architecture;
- install and smoke-test logs;
- the smoke-test result JSON and timestamp;
- manual GUI check result and reviewer.

Do not copy patient identifiers, patient DICOM, institutional credentials, or restricted file paths into this record.

## Current verification boundary

The repository contains automated builder, integrity, licensing, preflight, path, and smoke-test tests. A complete installation on a clean Windows computer without an existing Python 3.12 installation is explicitly **Pending — no suitable test PC is currently available**. This external acceptance item does not block source development, but the procedure must not be called clean-machine validated until a recorded human acceptance run exists.

## PyMedPhys standardization gate

Before publishing any future bundle as the standard-engine distribution:

1. pin an approved PyMedPhys version and all transitive dependencies;
2. collect and verify its wheel and license data;
3. install it with `--no-index` in the temporary and destination environments;
4. run explicit PyMedPhys 2D/3D identical-dose smoke tests;
5. run an explicitly selected Numba legacy smoke test;
6. assert engine names and versions in generated reports;
7. perform the clean-machine acceptance run again;
8. record failures without silently falling back to Numba.

The Japanese guide that records the existing bundle in more detail remains at [OFFLINE_INSTALL_JA.md](OFFLINE_INSTALL_JA.md).
