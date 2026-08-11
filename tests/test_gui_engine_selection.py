import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_gui_launchers_expose_persist_and_forward_engine():
    for relative_path in ('scripts/run_gui.ps1', 'scripts/run_gui_exe.ps1'):
        script = (ROOT / relative_path).read_text(encoding='utf-8-sig')
        assert 'PyMedPhys (standard)' in script
        assert 'Numba (legacy / experimental)' in script
        assert "'--engine', $engineVal" in script
        assert 'engine           = $engineVal' in script
        assert "$savedCfg.ContainsKey('engine')" in script
        assert 'using pymedphys. Save Settings to persist it.' in script


def test_gui_default_and_saved_config_select_pymedphys():
    defaults = json.loads(
        (ROOT / 'config' / 'gui_defaults.json').read_text(encoding='utf-8-sig')
    )
    saved_config = (ROOT / 'config' / 'gui_config.ini').read_text(encoding='utf-8-sig')

    assert defaults['engine'] == 'pymedphys'
    assert 'engine = pymedphys' in saved_config


def test_tracked_gui_seed_has_no_workstation_paths():
    saved_config = (ROOT / 'config' / 'gui_config.ini').read_text(
        encoding='utf-8-sig'
    )

    assert re.search(r'(?im)^ref_dose\s*=\s*$', saved_config)
    assert re.search(r'(?im)^eval_dose\s*=\s*$', saved_config)
    assert re.search(r'(?im)^output_dir\s*=\s*$', saved_config)
    assert re.search(r'(?im)^ct_dir\s*=\s*$', saved_config)
    assert not re.search(r'(?i)[a-z]:\\', saved_config)


def test_cli_executable_build_collects_pymedphys():
    build_script = (ROOT / 'scripts' / 'build_exe.ps1').read_text(encoding='utf-8-sig')
    assert "'--collect-all', 'pymedphys'" in build_script
