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
        assert "$engineVal -eq 'pymedphys' -and $viewerNormVal -eq 'none'" in script
        assert "does not support Norm 'none'" in script
        assert "'--engine',$engineVal,'--interp-fraction',$interpVal" in script
        assert "$viewerCmd += @('--gamma-type','local')" in script


def test_gui_default_and_saved_config_select_pymedphys():
    defaults = json.loads(
        (ROOT / 'config' / 'gui_defaults.json').read_text(encoding='utf-8-sig')
    )
    example_config = (ROOT / 'config' / 'gui_config.example.ini').read_text(
        encoding='utf-8-sig'
    )

    assert defaults['engine'] == 'pymedphys'
    assert 'engine = pymedphys' in example_config


def test_tracked_gui_example_has_no_workstation_paths():
    example_config = (ROOT / 'config' / 'gui_config.example.ini').read_text(
        encoding='utf-8-sig'
    )

    assert re.search(r'(?im)^ref_dose\s*=\s*$', example_config)
    assert re.search(r'(?im)^eval_dose\s*=\s*$', example_config)
    assert re.search(r'(?im)^output_dir\s*=\s*$', example_config)
    assert re.search(r'(?im)^ct_dir\s*=\s*$', example_config)
    assert not re.search(r'(?i)[a-z]:\\', example_config)


def test_gui_config_is_local_and_falls_back_to_tracked_example():
    gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8-sig')
    common = (ROOT / 'scripts' / 'gui_config_common.ps1').read_text(
        encoding='utf-8-sig'
    )

    assert 'config/gui_config.ini' in gitignore
    assert "'config/gui_config.example.ini'" in common


def test_executable_builds_collect_pymedphys_and_metadata():
    build_script = (ROOT / 'scripts' / 'build_exe.ps1').read_text(encoding='utf-8-sig')
    fast_spec = (ROOT / 'gamma_viewer_fast.spec').read_text(encoding='utf-8-sig')

    assert build_script.count("'--collect-all', 'pymedphys'") == 2
    assert build_script.count("'--copy-metadata', 'pymedphys'") == 2
    assert build_script.count("'--copy-metadata', 'numba'") == 2
    assert 'Write-ApplicationIdentity' in build_script
    assert 'application_identity.json' in build_script
    assert "collect_all('pymedphys')" in fast_spec
    assert "copy_metadata('pymedphys')" in fast_spec
    assert "copy_metadata('numba')" in fast_spec


def test_viewers_accept_and_route_explicit_engine():
    for relative_path in ('scripts/gamma_viewer.py', 'scripts/gamma_viewer_fast.py'):
        script = (ROOT / relative_path).read_text(encoding='utf-8-sig')
        assert 'pymedphys' in script
        assert 'numba' in script
        assert 'engine=args.engine' in script
        assert 'interp_fraction=args.interp_fraction' in script
