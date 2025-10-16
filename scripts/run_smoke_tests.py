#!/usr/bin/env python
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'phits-linac-validation' / 'output' / 'rtgamma'
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT)
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def check_ok(cp: subprocess.CompletedProcess, label: str) -> None:
    if cp.returncode != 0:
        print(f'[FAIL] {label}: rc={cp.returncode}')
        print(cp.stdout)
        print(cp.stderr)
        sys.exit(1)
    else:
        print(f'[ OK ] {label}')


def test_compare_headers() -> None:
    a = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    b = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'
    out_md = OUT / 'smoke_Test05_compare.md'
    cmd = [sys.executable, str(ROOT / 'scripts' / 'compare_rtdose_headers.py'),
           '--a', str(a), '--b', str(b), '--out', str(out_md)]
    cp = run(cmd)
    check_ok(cp, 'compare_rtdose_headers (Test05)')
    txt = out_md.read_text(encoding='utf-8')
    assert '# RTDOSE Header Comparison' in txt
    assert 'FrameOfReferenceUID' in txt


def test_main_2d_axial() -> None:
    a = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    b = ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'
    base = OUT / 'smoke_Test05_axial'
    json_path = OUT / 'smoke_Test05_axial.json'
    cmd = [sys.executable, '-m', 'rtgamma.main',
           '--ref', str(a), '--eval', str(b),
           '--mode', '2d', '--plane', 'axial', '--plane-index', 'auto',
           '--opt-shift', 'off', '--norm', 'global_max', '--dd', '3', '--dta', '2', '--cutoff', '10',
           '--save-gamma-map', str(OUT / 'smoke_Test05_axial_gamma.png'),
           '--save-dose-diff', str(OUT / 'smoke_Test05_axial_diff.png'),
           '--report', str(base)]
    cp = run(cmd)
    check_ok(cp, 'rtgamma.main 2d axial (Test05)')
    data = json.loads(json_path.read_text(encoding='utf-8'))
    pr = float(data.get('pass_rate_percent', -1))
    assert 0.0 <= pr <= 100.0


def test_io_dicom_monotonic() -> None:
    from rtgamma.io_dicom import load_rtdose
    m = load_rtdose(str(ROOT / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'))
    z = m['z_coords_mm']
    assert (z[1:] - z[:-1] >= -1e-6).all(), 'z_offsets must be non-decreasing'


def main():
    print('[ RUN ] smoke tests')
    test_compare_headers()
    test_main_2d_axial()
    test_io_dicom_monotonic()
    print('[ DONE ] all smoke tests passed')


if __name__ == '__main__':
    main()

