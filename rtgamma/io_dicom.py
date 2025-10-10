import numpy as np
from typing import Dict, Tuple

try:
    import pydicom
except Exception as e:
    pydicom = None


def _dircos_to_matrix(iop: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = np.array(iop[:3], dtype=float)
    c = np.array(iop[3:6], dtype=float)
    r /= np.linalg.norm(r)
    c /= np.linalg.norm(c)
    s = np.cross(r, c)
    s /= np.linalg.norm(s)
    return r, c, s


def load_rtdose(path: str) -> Dict:
    if pydicom is None:
        raise RuntimeError("pydicom is required to read RTDOSE DICOM. Install pydicom.")
    ds = pydicom.dcmread(path, force=True)
    if getattr(ds, 'Modality', None) != 'RTDOSE':
        raise ValueError("DICOM is not RTDOSE (Modality != RTDOSE)")

    rows = int(ds.Rows)
    cols = int(ds.Columns)
    nframes = int(getattr(ds, 'NumberOfFrames', 1))

    scaling = float(getattr(ds, 'DoseGridScaling', 1.0))
    pixel_array = ds.pixel_array.astype(np.float64) * scaling
    # Shape normalize to (z, y, x)
    if pixel_array.ndim == 3:
        dose = pixel_array.reshape(nframes, rows, cols)
    elif pixel_array.ndim == 2:
        dose = pixel_array[None, :, :]
    else:
        raise ValueError("Unexpected RTDOSE pixel array dimensions")

    ipp = np.array(ds.ImagePositionPatient, dtype=float)
    iop = np.array(ds.ImageOrientationPatient, dtype=float)
    r_dir, c_dir, s_dir = _dircos_to_matrix(iop)

    # PixelSpacing is (row, column) spacing
    ps = np.array(ds.PixelSpacing, dtype=float)
    row_spacing = float(ps[0])
    col_spacing = float(ps[1])

    # GridFrameOffsetVector gives per-slice offsets (mm) along the normal from IPP
    gfov = np.array(ds.GridFrameOffsetVector, dtype=float)
    if len(gfov) != nframes:
        # Some RTDOSEs use equally spaced frames; derive from SliceThickness when needed
        st = float(getattr(ds, 'SliceThickness', 0.0) or 0.0)
        if st > 0.0 and nframes > 1:
            gfov = np.linspace(0.0, st * (nframes - 1), nframes)
        else:
            gfov = np.arange(nframes, dtype=float)  # fallback

    # Coordinate vectors along each image axis in mm (distances along r/c/s directions)
    # X (columns): 0..cols-1 along c_dir spaced by col_spacing
    # Y (rows):    0..rows-1 along r_dir spaced by row_spacing
    x_mm = np.arange(cols, dtype=float) * col_spacing
    y_mm = np.arange(rows, dtype=float) * row_spacing
    z_mm = gfov.copy()

    meta = {
        'dose': dose.astype(np.float32),  # (z,y,x)
        'ipp': ipp,
        'row_dir': r_dir,
        'col_dir': c_dir,
        'slice_dir': s_dir,
        'row_spacing': row_spacing,
        'col_spacing': col_spacing,
        'z_offsets': z_mm,  # mm
        'x_coords_mm': x_mm,
        'y_coords_mm': y_mm,
        'z_coords_mm': z_mm,
        'units': getattr(ds, 'DoseUnits', 'UNKNOWN'),
        'dataset': ds,
        'shape': dose.shape,
    }
    return meta


def voxel_to_world(ipp: np.ndarray,
                   r_dir: np.ndarray,
                   c_dir: np.ndarray,
                   s_dir: np.ndarray,
                   row_spacing: float,
                   col_spacing: float,
                   z_offsets: np.ndarray,
                   ijk: np.ndarray) -> np.ndarray:
    # ijk: (..., 3) with order (z,y,x)
    k = ijk[..., 0]
    j = ijk[..., 1]
    i = ijk[..., 2]
    p = (ipp
         + np.outer(j, r_dir) * row_spacing
         + np.outer(i, c_dir) * col_spacing)
    # Add slice normal contribution with per-slice offsets (non-affine along k)
    # Broadcast k over s_dir
    z_mm = np.interp(k, np.arange(z_offsets.size, dtype=float), z_offsets)
    p = p + np.outer(z_mm, s_dir)
    return p


def world_to_index(ipp: np.ndarray,
                   r_dir: np.ndarray,
                   c_dir: np.ndarray,
                   s_dir: np.ndarray,
                   row_spacing: float,
                   col_spacing: float,
                   z_offsets: np.ndarray,
                   xyz: np.ndarray) -> np.ndarray:
    # xyz: (..., 3) world LPS coords
    d = xyz - ipp
    j = (d @ r_dir) / row_spacing
    i = (d @ c_dir) / col_spacing
    dist_s = (d @ s_dir)
    k = np.interp(dist_s, z_offsets, np.arange(z_offsets.size, dtype=float), left=-1, right=-1)
    ijk = np.stack([k, j, i], axis=-1)
    return ijk

