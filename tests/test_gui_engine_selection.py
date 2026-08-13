import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_gui_launchers_expose_persist_and_forward_engine():
    for relative_path in ('scripts/run_gui.ps1', 'scripts/run_gui_exe.ps1'):
        script = (ROOT / relative_path).read_text(encoding='utf-8-sig')
        assert 'PyMedPhys (reference / slow 3D)' in script
        assert 'Numba (fast full-volume GPR)' in script
        assert "'--engine', $engineVal" in script
        assert 'engine           = $engineVal' in script
        assert "$savedCfg.ContainsKey('engine')" in script
        assert 'using numba for fast full-volume GPR' in script
        assert "$engineVal -eq 'pymedphys' -and $viewerNormVal -eq 'none'" in script
        assert "does not support Norm 'none'" in script
        assert "'--engine',$engineVal,'--interp-fraction',$interpVal" in script
        assert "$viewerCmd += @('--gamma-type','local')" in script
        assert "'--gamma-npz', $npzPath, '--gamma-report', $reportPath" in script
        assert "'--opt-shift',$optVal" in script
        assert "'--skip-gamma-compute'" in script
        assert '$psi.RedirectStandardOutput = $true' in script
        assert '$psi.RedirectStandardError = $true' in script
        assert 'Viewer exited with code $code.' in script
        assert 'Status: Viewer running' in script
        assert 'Slow 3D Gamma Warning' in script
        assert 'Threads (0=auto)' in script
        assert "New-DarkCheck 'Save Viewer Cache'" in script
        assert '$cbNPZ.Enabled = $false' in script
        assert "'--save-gamma-map',(Join-Path $out 'gamma3d.npz')" in script
        assert 'Viewer Gamma cache found' in script
        assert 'Viewer Gamma cache is missing' in script
        assert "New-DarkCheck 'Allow different FoR UID'" in script
        assert "@('--allow-frame-of-reference-mismatch')" in script
        assert '$viewerCmd += $forArg' in script
        assert 'Frame of Reference Override' in script
        assert 'allow_frame_of_reference_mismatch = $cbAllowFoR.Checked' in script
        assert "enable 'Allow different FoR UID' and retry" in script
        assert 'correct the indicated input or runtime issue' in script


def test_gui_default_and_saved_config_select_fast_numba():
    defaults = json.loads(
        (ROOT / 'config' / 'gui_defaults.json').read_text(encoding='utf-8-sig')
    )
    example_config = (ROOT / 'config' / 'gui_config.example.ini').read_text(
        encoding='utf-8-sig'
    )

    assert defaults['engine'] == 'numba'
    assert defaults['interp_fraction'] == 4
    assert defaults['threads'] == 0
    assert defaults['save_npz_3d'] is True
    assert defaults['allow_frame_of_reference_mismatch'] is False
    assert 'engine = numba' in example_config
    assert 'interp_fraction = 4' in example_config
    assert 'threads = 0' in example_config
    assert 'save_npz_3d = true' in example_config
    assert 'allow_frame_of_reference_mismatch = false' in example_config


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


def test_both_viewers_validate_rtdose_pairs_before_resampling():
    legacy = (ROOT / 'scripts' / 'gamma_viewer.py').read_text(encoding='utf-8-sig')
    fast = (ROOT / 'scripts' / 'gamma_viewer_fast.py').read_text(encoding='utf-8-sig')

    for script in (legacy, fast):
        assert 'validate_rtdose_pair_geometry(' in script
        assert 'allow_frame_of_reference_mismatch=' in script
