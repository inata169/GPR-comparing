import os
import sys
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT)
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def test_cli_2d_axial_central(tmp_path):
    a = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    b = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'
    base = tmp_path / 'axial'
    cp = run([sys.executable, '-m', 'rtgamma.main',
              '--ref', str(a), '--eval', str(b),
              '--mode', '2d', '--plane', 'axial', '--plane-index', 'auto',
              '--opt-shift', 'off', '--norm', 'global_max', '--dd', '3', '--dta', '2', '--cutoff', '10',
              '--report', str(base)])
    assert cp.returncode == 0, cp.stderr
    data = json.loads((tmp_path / 'axial.json').read_text(encoding='utf-8'))
    pr = float(data.get('pass_rate_percent', -1))
    assert 0.0 <= pr <= 100.0

