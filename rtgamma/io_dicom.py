import numpy as np
from typing import Dict, Tuple, List, Optional

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

    # Workaround for files with missing TransferSyntaxUID
    if not hasattr(ds.file_meta, 'TransferSyntaxUID'):
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

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
    # v_col is the direction of the first row (incrementing column index i)
    # v_row is the direction of the first column (incrementing row index j)
    v_col, v_row, v_slice = _dircos_to_matrix(iop)

    # PixelSpacing is (row, column) spacing
    # ps[0] is distance between adjacent rows (spacing along v_row)
    # ps[1] is distance between adjacent columns (spacing along v_col)
    ps = np.array(ds.PixelSpacing, dtype=float)
    s_row = float(ps[0])
    s_col = float(ps[1])

    # GridFrameOffsetVector gives per-slice offsets (mm) along the normal from IPP
    gfov = np.array(ds.GridFrameOffsetVector, dtype=float)
    if len(gfov) != nframes:
        # Some RTDOSEs use equally spaced frames; derive from SliceThickness when needed
        st = float(getattr(ds, 'SliceThickness', 0.0) or 0.0)
        if st > 0.0 and nframes > 1:
            gfov = np.linspace(0.0, st * (nframes - 1), nframes)
        else:
            gfov = np.arange(nframes, dtype=float)  # fallback

    # Sort frames by Z-offset to ensure monotonicity
    order = np.argsort(gfov)
    dose = dose[order, :, :]
    gfov = gfov[order]

    # Coordinate vectors along each image axis in mm (distances from IPP along dirs)
    # i (columns): 0..cols-1 along v_col spaced by s_col
    # j (rows):    0..rows-1 along v_row spaced by s_row
    i_mm = np.arange(cols, dtype=float) * s_col
    j_mm = np.arange(rows, dtype=float) * s_row
    k_mm = gfov.copy()

    meta = {
        'dose': dose.astype(np.float32),  # (z,y,x) -> (k,j,i)
        'ipp': ipp,
        'v_col': v_col, # i-axis (horizontal in 2D)
        'v_row': v_row, # j-axis (vertical in 2D)
        'v_slice': v_slice, # k-axis
        's_col': s_col, # spacing for i-index
        's_row': s_row, # spacing for j-index
        'z_offsets': k_mm,  # mm from IPP along v_slice
        'x_coords_mm': i_mm, # used by legacy code as 'x' coords
        'y_coords_mm': j_mm, # used by legacy code as 'y' coords
        'z_coords_mm': k_mm, # used by legacy code as 'z' coords
        'units': getattr(ds, 'DoseUnits', 'UNKNOWN'),
        'dataset': ds,
        'shape': dose.shape,
    }
    return meta


def load_rtplan(path: str) -> Dict:
    if pydicom is None:
        raise RuntimeError("pydicom is required to read RTPLAN DICOM. Install pydicom.")
    ds = pydicom.dcmread(path, force=True)

    if getattr(ds, 'Modality', None) != 'RTPLAN':
        raise ValueError("DICOM is not RTPLAN (Modality != RTPLAN)")

    beam_seq = list(getattr(ds, 'BeamSequence', []) or [])
    isocenters: List[np.ndarray] = []
    sad_vals: List[float] = []
    ssd_vals: List[float] = []

    for beam in beam_seq:
        # SAD may be on Beam or Control Points
        sad = None
        if hasattr(beam, 'SourceToAxisDistance'):
            try:
                sad = float(beam.SourceToAxisDistance)
            except Exception:
                sad = None
        # Control points for isocenter and possibly SSD/SAD
        cps = list(getattr(beam, 'ControlPointSequence', []) or [])
        for cp in cps:
            if hasattr(cp, 'IsocenterPosition'):
                try:
                    iso = np.array(cp.IsocenterPosition, dtype=float)
                    isocenters.append(iso)
                except Exception:
                    pass
            if hasattr(cp, 'SourceToSurfaceDistance'):
                try:
                    ssd = float(cp.SourceToSurfaceDistance)
                    if np.isfinite(ssd):
                        ssd_vals.append(ssd)
                except Exception:
                    pass
            if sad is None and hasattr(cp, 'SourceToAxisDistance'):
                try:
                    sad = float(cp.SourceToAxisDistance)
                except Exception:
                    sad = None
        if sad is not None and np.isfinite(sad):
            sad_vals.append(float(sad))

    iso_mean: Optional[np.ndarray] = None
    if isocenters:
        iso_mean = np.mean(np.stack(isocenters, axis=0), axis=0)

    meta = {
        'dataset': ds,
        'beam_count': len(beam_seq),
        'isocenters_lps_mm': isocenters,
        'isocenter_mean_lps_mm': iso_mean if iso_mean is not None else None,
        'sad_mm_vals': sad_vals,
        'sad_mm_mean': float(np.mean(sad_vals)) if len(sad_vals) > 0 else None,
        'ssd_mm_vals': ssd_vals,
        'ssd_mm_mean': float(np.mean(ssd_vals)) if len(ssd_vals) > 0 else None,
    }
    return meta


def load_rtstruct(path: str) -> Dict:
    """Load DICOM RTSTRUCT and extract ROI contour data.

    Returns dict with keys:
        roi_list: list of dicts with 'number', 'name', 'contours'
                  where contours is a list of {'z': float, 'points': ndarray(N,2)}
                  points are (x, y) in LPS world coordinates.
        for_uid: FrameOfReferenceUID string
        dataset: raw pydicom Dataset
    """
    if pydicom is None:
        raise RuntimeError("pydicom is required to read RTSTRUCT DICOM.")
    ds = pydicom.dcmread(path, force=True)

    if not hasattr(ds.file_meta, 'TransferSyntaxUID'):
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    if getattr(ds, 'Modality', None) != 'RTSTRUCT':
        raise ValueError("DICOM is not RTSTRUCT (Modality != RTSTRUCT)")

    # Build ROI number -> name mapping
    roi_name_map = {}
    for roi_seq in getattr(ds, 'StructureSetROISequence', []):
        roi_num = int(roi_seq.ROINumber)
        roi_name_map[roi_num] = str(roi_seq.ROIName)

    # Extract contours per ROI
    roi_list = []
    for roi_contour in getattr(ds, 'ROIContourSequence', []):
        ref_num = int(roi_contour.ReferencedROINumber)
        name = roi_name_map.get(ref_num, f'ROI_{ref_num}')
        contours = []
        for contour_seq in getattr(roi_contour, 'ContourSequence', []):
            geo_type = getattr(contour_seq, 'ContourGeometricType', 'CLOSED_PLANAR')
            if geo_type != 'CLOSED_PLANAR':
                continue
            data = np.array(contour_seq.ContourData, dtype=float)
            n_pts = len(data) // 3
            if n_pts < 3:
                continue
            pts = data.reshape(n_pts, 3)  # (x, y, z) in LPS
            z_val = float(pts[0, 2])  # All points on same slice share z
            contours.append({
                'z': z_val,
                'points': pts[:, :2].copy(),  # (N, 2) = (x, y)
            })
        roi_list.append({
            'number': ref_num,
            'name': name,
            'contours': contours,
        })

    for_uid = str(getattr(ds, 'FrameOfReferenceUID', ''))
    # Also check ReferencedFrameOfReferenceSequence
    if not for_uid:
        ref_for_seq = getattr(ds, 'ReferencedFrameOfReferenceSequence', [])
        if ref_for_seq:
            for_uid = str(getattr(ref_for_seq[0], 'FrameOfReferenceUID', ''))

    return {
        'roi_list': roi_list,
        'for_uid': for_uid,
        'dataset': ds,
    }


def voxel_to_world(ipp: np.ndarray,
                   v_col: np.ndarray,
                   v_row: np.ndarray,
                   v_slice: np.ndarray,
                   s_col: float,
                   s_row: float,
                   z_offsets: np.ndarray,
                   ijk: np.ndarray) -> np.ndarray:
    """Convert grid indices (k, j, i) to world LPS coordinates."""
    k = ijk[..., 0]
    j = ijk[..., 1]
    i = ijk[..., 2]
    # Position = IPP + j * s_row * v_row + i * s_col * v_col + k_offset * v_slice
    p = (ipp
         + np.outer(j, v_row) * s_row
         + np.outer(i, v_col) * s_col)
    # Add slice normal contribution (non-affine if z_offsets is irregular)
    z_mm = np.interp(k, np.arange(z_offsets.size, dtype=float), z_offsets)
    p = p + np.outer(z_mm, v_slice)
    return p


def world_to_index(ipp: np.ndarray,
                   v_col: np.ndarray,
                   v_row: np.ndarray,
                   v_slice: np.ndarray,
                   s_col: float,
                   s_row: float,
                   z_offsets: np.ndarray,
                   xyz: np.ndarray) -> np.ndarray:
    """Convert world LPS coordinates (x, y, z) to fractional grid indices (k, j, i)."""
    d = xyz - ipp
    i = (d @ v_col) / s_col
    j = (d @ v_row) / s_row
    dist_s = (d @ v_slice)
    # Map distance along slice normal to fractional slice index k
    k = np.interp(dist_s, z_offsets, np.arange(z_offsets.size, dtype=float), left=-1, right=-1)
    ijk = np.stack([k, j, i], axis=-1)
    return ijk
