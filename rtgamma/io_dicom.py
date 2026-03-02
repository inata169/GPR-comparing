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

    # Sort frames by Z-offset to ensure monotonicity
    order = np.argsort(gfov)
    dose = dose[order, :, :]
    gfov = gfov[order]

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
