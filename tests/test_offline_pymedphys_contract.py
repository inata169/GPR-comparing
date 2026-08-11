from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_offline_constraints_pin_pymedphys_and_required_dependencies():
    constraints = (
        ROOT / 'offline' / 'constraints-py312-win64.txt'
    ).read_text(encoding='utf-8')
    active = {
        line.strip().lower()
        for line in constraints.splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }

    assert 'pymedphys==0.41.0' in active
    assert any(line.startswith('setuptools==') for line in active)
    assert any(line.startswith('tomlkit==') for line in active)
    assert any(line.startswith('typing_extensions==') for line in active)


def test_release_license_collection_includes_pymedphys():
    package_script = (ROOT / 'scripts' / 'package_release.ps1').read_text(
        encoding='utf-8-sig'
    )

    assert "'pymedphys'," in package_script
    assert 'numba, PyMedPhys if bundled' in package_script


def test_offline_builder_verifies_standard_engine_version():
    builder = (
        ROOT / 'offline' / 'build_offline_bundle.ps1'
    ).read_text(encoding='utf-8-sig')

    assert "version('pymedphys') == '0.41.0'" in builder
    assert 'import pydicom,numpy,scipy,numba,matplotlib,reportlab,pyqtgraph,pymedphys' in builder


def test_offline_smoke_exercises_both_engines_explicitly():
    smoke = (ROOT / 'offline' / 'smoke_test.py').read_text(encoding='utf-8')

    assert smoke.count('"--engine",') >= 3
    assert smoke.count('"pymedphys",') >= 2
    assert '"numba",' in smoke
    assert 'require_gamma_report' in smoke
    assert 'version("pymedphys") != "0.41.0"' in smoke
