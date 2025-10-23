import os
import sys
import subprocess
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT)
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def test_compare_headers_test05(tmp_path):
    a = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    b = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'
    if not (a.exists() and b.exists()):
        pytest.skip("Test data not present in CI environment")
    out_md = tmp_path / 'compare.md'
    cp = run([sys.executable, str(ROOT / 'scripts' / 'compare_rtdose_headers.py'),
              '--a', str(a), '--b', str(b), '--out', str(out_md)])
    assert cp.returncode == 0, cp.stderr
    t = out_md.read_text(encoding='utf-8')
    assert '# RTDOSE Header Comparison' in t
    assert 'FrameOfReferenceUID' in t
