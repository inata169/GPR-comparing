import hashlib
import io
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pydicom

GEOMETRY_TOLERANCE = 1e-5
logger = logging.getLogger(__name__)


class RTDoseGeometryError(ValueError):
    """Raised when RTDOSE geometry is invalid or unsupported."""


def _read_dicom_snapshot(path: str):
    """Hash and parse exactly the same immutable byte snapshot."""
    with open(path, 'rb') as stream:
        source_bytes = stream.read()
    dataset = pydicom.dcmread(io.BytesIO(source_bytes), force=True)
    return dataset, hashlib.sha256(source_bytes).hexdigest()


def _geometry_error(message: str) -> RTDoseGeometryError:
    return RTDoseGeometryError(f"Invalid RTDOSE geometry: {message}")


def _required_numeric_vector(ds, name: str, length: int) -> np.ndarray:
    if not hasattr(ds, name):
        raise _geometry_error(f"missing required {name}")
    try:
        values = np.asarray(getattr(ds, name), dtype=float)
    except (TypeError, ValueError) as exc:
        raise _geometry_error(f"{name} is not numeric") from exc
    if values.ndim != 1 or values.size != length:
        raise _geometry_error(f"{name} must contain exactly {length} values")
    if not np.isfinite(values).all():
        raise _geometry_error(f"{name} contains non-finite values")
    return values


def _validate_iop(iop: np.ndarray) -> None:
    v_col = iop[:3]
    v_row = iop[3:6]
    col_norm = float(np.linalg.norm(v_col))
    row_norm = float(np.linalg.norm(v_row))
    if col_norm <= GEOMETRY_TOLERANCE or row_norm <= GEOMETRY_TOLERANCE:
        raise _geometry_error("ImageOrientationPatient contains a zero direction vector")
    if not np.isclose(col_norm, 1.0, atol=GEOMETRY_TOLERANCE, rtol=0.0):
        raise _geometry_error("ImageOrientationPatient first direction is not unit length")
    if not np.isclose(row_norm, 1.0, atol=GEOMETRY_TOLERANCE, rtol=0.0):
        raise _geometry_error("ImageOrientationPatient second direction is not unit length")
    if abs(float(np.dot(v_col, v_row))) > GEOMETRY_TOLERANCE:
        raise _geometry_error("ImageOrientationPatient directions are not orthogonal")
    if float(np.linalg.norm(np.cross(v_col, v_row))) <= GEOMETRY_TOLERANCE:
        raise _geometry_error("ImageOrientationPatient directions are degenerate")


def _normalise_gfov(ds, ipp: np.ndarray, iop: np.ndarray, nframes: int) -> np.ndarray:
    if not hasattr(ds, 'GridFrameOffsetVector'):
        raise _geometry_error("missing required GridFrameOffsetVector")
    try:
        gfov = np.asarray(ds.GridFrameOffsetVector, dtype=float)
    except (TypeError, ValueError) as exc:
        raise _geometry_error("GridFrameOffsetVector is not numeric") from exc
    if gfov.ndim != 1 or gfov.size != nframes:
        raise _geometry_error(
            "GridFrameOffsetVector length does not match NumberOfFrames"
        )
    if not np.isfinite(gfov).all():
        raise _geometry_error("GridFrameOffsetVector contains non-finite values")

    # DICOM permits axial grids to encode absolute patient-z coordinates.
    axial_iop = np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
    if (
        gfov.size
        and np.allclose(iop, axial_iop, atol=GEOMETRY_TOLERANCE, rtol=0.0)
        and np.isclose(gfov[0], ipp[2], atol=GEOMETRY_TOLERANCE, rtol=0.0)
    ):
        gfov = gfov - ipp[2]

    if gfov.size > 1:
        differences = np.diff(gfov)
        if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
            raise _geometry_error(
                "GridFrameOffsetVector must be strictly monotonic without duplicates"
            )
    return gfov


def validate_rtdose_pair_geometry(meta_ref: Dict, meta_eval: Dict) -> float:
    """Validate geometry assumptions shared by both gamma engines.

    Differing origins, in-plane spacing, and slice spacing are supported. The
    direction matrices must match because the direct 3D gamma path represents
    both distributions with one common rectilinear axis frame.
    """
    ref_units = str(meta_ref.get('units', '')).strip().upper()
    eval_units = str(meta_eval.get('units', '')).strip().upper()
    if ref_units != eval_units:
        raise RTDoseGeometryError(
            "Unsupported RTDOSE pair geometry: DoseUnits mismatch "
            f"(reference={ref_units}, evaluation={eval_units})"
        )

    ref_for_uid = str(
        getattr(meta_ref['dataset'], 'FrameOfReferenceUID', '')
    ).strip()
    eval_for_uid = str(
        getattr(meta_eval['dataset'], 'FrameOfReferenceUID', '')
    ).strip()
    if ref_for_uid and eval_for_uid and ref_for_uid != eval_for_uid:
        logger.warning(
            "FrameOfReferenceUID values differ; continuing with explicit DICOM "
            "patient coordinates after validating matching dose units and "
            "ImageOrientationPatient directions (reference=%s, evaluation=%s).",
            ref_for_uid,
            eval_for_uid,
        )

    signed_dots = np.array([
        np.dot(meta_ref['v_col'], meta_eval['v_col']),
        np.dot(meta_ref['v_row'], meta_eval['v_row']),
        np.dot(meta_ref['v_slice'], meta_eval['v_slice']),
    ], dtype=float)
    orientation_min_dot = float(np.min(signed_dots))
    ref_matrix = np.stack([
        meta_ref['v_col'], meta_ref['v_row'], meta_ref['v_slice']
    ])
    eval_matrix = np.stack([
        meta_eval['v_col'], meta_eval['v_row'], meta_eval['v_slice']
    ])
    if not np.allclose(
        ref_matrix,
        eval_matrix,
        atol=GEOMETRY_TOLERANCE,
        rtol=0.0,
    ):
        raise RTDoseGeometryError(
            "Unsupported RTDOSE pair geometry: reference and evaluation "
            "ImageOrientationPatient directions differ"
        )
    return orientation_min_dot


def _dircos_to_matrix(iop: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = np.array(iop[:3], dtype=float)
    c = np.array(iop[3:6], dtype=float)
    r /= np.linalg.norm(r)
    c /= np.linalg.norm(c)
    s = np.cross(r, c)
    s /= np.linalg.norm(s)
    return r, c, s


def load_rtdose(path: str) -> Dict:
    import os

    target_path = path
    if os.path.isdir(path):
        found = None
        for root, _, files in os.walk(path):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    ds_test = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
                    if getattr(ds_test, 'Modality', None) == 'RTDOSE':
                        found = fpath
                        break
                except Exception:
                    continue
            if found: break
        if found:
            target_path = found
        else:
            raise FileNotFoundError(f"No RTDOSE found in directory: {path}")

    ds, source_sha256 = _read_dicom_snapshot(target_path)

    # Workaround for files with missing TransferSyntaxUID
    if not hasattr(ds.file_meta, 'TransferSyntaxUID'):
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    if getattr(ds, 'Modality', None) != 'RTDOSE':
        raise ValueError("DICOM is not RTDOSE (Modality != RTDOSE)")

    try:
        rows = int(ds.Rows)
        cols = int(ds.Columns)
        nframes = int(ds.NumberOfFrames)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _geometry_error(
            "Rows, Columns, and NumberOfFrames must be present integers"
        ) from exc
    if rows <= 0 or cols <= 0 or nframes <= 0:
        raise _geometry_error("Rows, Columns, and NumberOfFrames must be positive")

    ipp = _required_numeric_vector(ds, 'ImagePositionPatient', 3)
    iop = _required_numeric_vector(ds, 'ImageOrientationPatient', 6)
    _validate_iop(iop)
    ps = _required_numeric_vector(ds, 'PixelSpacing', 2)
    if np.any(ps <= 0.0):
        raise _geometry_error("PixelSpacing values must be positive")
    gfov = _normalise_gfov(ds, ipp, iop, nframes)

    units = str(getattr(ds, 'DoseUnits', '')).strip().upper()
    if units not in {'GY', 'RELATIVE'}:
        raise _geometry_error("DoseUnits must be GY or RELATIVE")

    try:
        scaling = float(ds.DoseGridScaling)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _geometry_error("DoseGridScaling must be present and numeric") from exc
    if not np.isfinite(scaling) or scaling <= 0.0:
        raise _geometry_error("DoseGridScaling must be finite and positive")
    pixel_array = ds.pixel_array.astype(np.float64) * scaling
    # Shape normalize to (z, y, x)
    if pixel_array.ndim == 3:
        dose = pixel_array.reshape(nframes, rows, cols)
    elif pixel_array.ndim == 2:
        dose = pixel_array[None, :, :]
    else:
        raise ValueError("Unexpected RTDOSE pixel array dimensions")
    if dose.shape != (nframes, rows, cols):
        raise _geometry_error(
            "decoded pixel array dimensions do not match "
            "NumberOfFrames, Rows, and Columns"
        )
    if not np.isfinite(dose).all():
        raise _geometry_error("scaled dose array contains non-finite values")

    # v_col is the direction of the first row (incrementing column index i)
    # v_row is the direction of the first column (incrementing row index j)
    v_col, v_row, v_slice = _dircos_to_matrix(iop)

    # PixelSpacing is (row, column) spacing
    # ps[0] is distance between adjacent rows (spacing along v_row)
    # ps[1] is distance between adjacent columns (spacing along v_col)
    s_row = float(ps[0])
    s_col = float(ps[1])

    # GridFrameOffsetVector gives per-slice offsets (mm) along the normal from IPP
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
        'source_path': os.path.abspath(target_path),
        'source_sha256': source_sha256,
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
        'units': units,
        'dataset': ds,
        'shape': dose.shape,
    }
    return meta


def load_ct(path: str) -> Dict:
    """Load a CT DICOM series from a directory.

    Arguments:
        path: Directory containing CT DICOM slice files.

    Returns dict with keys:
        ct_hu: 3D ndarray float32 (z, y, x) in Hounsfield Units
        ipp: ImagePositionPatient of the first slice (LPS, mm)
        v_col, v_row, v_slice: direction cosines (same convention as RTDOSE)
        s_col, s_row: pixel spacing (mm)
        z_positions: 1D array of world-Z for each slice (mm)
        shape: tuple (nz, ny, nx)
    """
    import os

    if not os.path.isdir(path):
        raise ValueError(f"load_ct requires a directory, got: {path}")

    # Collect CT slices
    slices = []
    for f in os.listdir(path):
        fpath = os.path.join(path, f)
        if not os.path.isfile(fpath):
            continue
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=False, force=True)
            if not hasattr(ds.file_meta, 'TransferSyntaxUID'):
                ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
            if getattr(ds, 'Modality', None) == 'CT':
                slices.append(ds)
        except Exception:
            continue

    if not slices:
        raise FileNotFoundError(f"No CT slices found in: {path}")

    # Sort by ImagePositionPatient Z (or InstanceNumber fallback)
    try:
        slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))
    except Exception:
        slices.sort(key=lambda s: int(getattr(s, 'InstanceNumber', 0)))

    # Extract geometry from first slice
    ds0 = slices[0]
    ipp = np.array(ds0.ImagePositionPatient, dtype=float)
    iop = np.array(ds0.ImageOrientationPatient, dtype=float)
    v_col, v_row, v_slice = _dircos_to_matrix(iop)

    ps = np.array(ds0.PixelSpacing, dtype=float)
    s_row = float(ps[0])
    s_col = float(ps[1])

    rows = int(ds0.Rows)
    cols = int(ds0.Columns)
    nz = len(slices)

    # Build 3D HU array
    ct_hu = np.zeros((nz, rows, cols), dtype=np.float32)
    z_positions = np.zeros(nz, dtype=float)

    for k, ds in enumerate(slices):
        slope = float(getattr(ds, 'RescaleSlope', 1.0))
        intercept = float(getattr(ds, 'RescaleIntercept', 0.0))
        ct_hu[k] = ds.pixel_array.astype(np.float32) * slope + intercept
        z_positions[k] = float(ds.ImagePositionPatient[2])

    return {
        'ct_hu': ct_hu,
        'ipp': ipp,
        'v_col': v_col,
        'v_row': v_row,
        'v_slice': v_slice,
        's_col': s_col,
        's_row': s_row,
        'z_positions': z_positions,
        'shape': ct_hu.shape,
    }


def load_rtplan(path: str) -> Dict:
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

    Arguments:
        path: Path to RTSTRUCT file, or a directory containing one.

    Returns dict with keys:
        roi_list: list of dicts with 'number', 'name', 'contours'
                  where contours is a list of {'z': float, 'points': ndarray(N,2)}
                  points are (x, y) in LPS world coordinates.
        for_uid: FrameOfReferenceUID string
        dataset: raw pydicom Dataset
    """
    import os

    target_path = path
    if os.path.isdir(path):
        # Search for RTSTRUCT in directory
        found = None
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            if os.path.isfile(fpath):
                try:
                    ds_test = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
                    if getattr(ds_test, 'Modality', None) == 'RTSTRUCT':
                        found = fpath
                        break
                except Exception:
                    continue
        if found:
            target_path = found
        else:
            raise FileNotFoundError(f"No RTSTRUCT found in directory: {path}")

    ds, source_sha256 = _read_dicom_snapshot(target_path)

    if not hasattr(ds.file_meta, 'TransferSyntaxUID'):
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    if getattr(ds, 'Modality', None) != 'RTSTRUCT':
        raise ValueError(f"DICOM is not RTSTRUCT (Modality={getattr(ds, 'Modality', 'UNKNOWN')}) at {target_path}")

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
        'source_path': os.path.abspath(target_path),
        'source_sha256': source_sha256,
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
