from pathlib import Path
import pytest
from rtgamma.io_dicom import load_rtdose


def test_gfov_monotonic():
    root = Path(__file__).resolve().parents[1]
    p = root / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    if not p.exists():
        pytest.skip("Test data not present in CI environment")
    m = load_rtdose(str(p))
    z = m['z_coords_mm']
    assert (z[1:] - z[:-1] >= -1e-6).all()
