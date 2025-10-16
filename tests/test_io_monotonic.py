from pathlib import Path
from rtgamma.io_dicom import load_rtdose


def test_gfov_monotonic():
    root = Path(__file__).resolve().parents[1]
    m = load_rtdose(str(root / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'))
    z = m['z_coords_mm']
    assert (z[1:] - z[:-1] >= -1e-6).all()

