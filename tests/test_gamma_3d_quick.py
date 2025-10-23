import numpy as np
from pathlib import Path
import pytest

from rtgamma.io_dicom import load_rtdose
from rtgamma.resample import resample_eval_onto_ref


def test_gamma_quick_3d_crop():
    # Load Test05 and evaluate a small 3D crop to keep runtime short
    root = Path(__file__).resolve().parents[1]
    pa = root / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATCCC_Dose_RxQA_Bm1.dcm'
    pb = root / 'dicom' / 'Test05' / 'AGLPhantom_AGLCATpMCFF_Dose_RxQA_Bm1.dcm'
    if not (pa.exists() and pb.exists()):
        pytest.skip("Test data not present in CI environment")
    ref = load_rtdose(str(pa))
    eva = load_rtdose(str(pb))

    # Determine crop indices around the center
    zc = ref['dose'].shape[0] // 2
    yc = ref['dose'].shape[1] // 2
    xc = ref['dose'].shape[2] // 2
    z_slice = slice(zc-1, zc+2)   # 3 slices
    y_slice = slice(yc-32, yc+32) # 64 rows
    x_slice = slice(xc-32, xc+32) # 64 cols

    # Build world coords for the crop
    y_mm = ref['y_coords_mm'][y_slice]
    x_mm = ref['x_coords_mm'][x_slice]
    z_mm = ref['z_coords_mm'][z_slice]
    ipp = ref['ipp']
    r = ref['row_dir']
    c = ref['col_dir']
    s = ref['slice_dir']
    Y, X, Z = np.meshgrid(y_mm, x_mm, z_mm, indexing='ij')
    Pw = (ipp[None, None, None, :]
          + Y[..., None] * r[None, None, None, :]
          + X[..., None] * c[None, None, None, :]
          + Z[..., None] * s[None, None, None, :])
    Pw = np.moveaxis(Pw, 2, 0)  # (z,y,x,3)
    Xw, Yw, Zw = Pw[..., 0], Pw[..., 1], Pw[..., 2]

    # Resample eval onto the cropped ref world coords (no shift)
    from rtgamma.io_dicom import world_to_index
    def world_to_eval_ijk(xyz):
        return world_to_index(eva['ipp'], eva['row_dir'], eva['col_dir'], eva['slice_dir'],
                              eva['row_spacing'], eva['col_spacing'], eva['z_offsets'], xyz)

    eval_on_ref_crop = resample_eval_onto_ref(eva['dose'], world_to_eval_ijk, (Xw, Yw, Zw), interp='linear', shift_mm=(0, 0, 0))

    # Compute 3D gamma for the crop
    from rtgamma.gamma import compute_gamma
    axes_ref_mm = (z_mm, y_mm, x_mm)
    dose_ref_crop = ref['dose'][z_slice, y_slice, x_slice]
    _, pr, _ = compute_gamma(
        axes_ref_mm=axes_ref_mm,
        dose_ref=dose_ref_crop,
        axes_eval_mm=axes_ref_mm,
        dose_eval=eval_on_ref_crop,
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        gamma_type='global',
        norm='global_max',
        use_pymedphys=False,
    )
    assert 0.0 <= pr <= 100.0
