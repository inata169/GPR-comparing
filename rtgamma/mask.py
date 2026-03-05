"""ROI mask generation from RTSTRUCT contours onto RTDOSE grid."""

import logging
from typing import Dict, List, Optional

import numpy as np
from matplotlib.path import Path as MplPath

logger = logging.getLogger(__name__)


def _world_xy_to_grid_rc(points_xy: np.ndarray, meta_dose: Dict) -> np.ndarray:
    """Convert LPS (x, y) world points to dose grid fractional indices (j, i)."""
    ipp = meta_dose['ipp']
    v_col = meta_dose['v_col'] # Direction of i-index
    v_row = meta_dose['v_row'] # Direction of j-index
    s_col = meta_dose['s_col'] # Spacing for i-index
    s_row = meta_dose['s_row'] # Spacing for j-index

    # Displacement from IPP in world (x, y)
    dx = points_xy[:, 0] - ipp[0]
    dy = points_xy[:, 1] - ipp[1]

    # Project onto i and j directions (2D, ignoring z component for planar contours)
    # i_idx is displacement along v_col divided by s_col
    i_idx = (dx * v_col[0] + dy * v_col[1]) / s_col
    # j_idx is displacement along v_row divided by s_row
    j_idx = (dx * v_row[0] + dy * v_row[1]) / s_row

    return np.column_stack([j_idx, i_idx])


def contour_to_mask_3d(contours: List[Dict], meta_dose: Dict) -> np.ndarray:
    """Generate a 3D boolean mask on the RTDOSE grid from ROI contours.

    Parameters
    ----------
    contours : list of {'z': float, 'points': ndarray(N,2)}
        Contour slices for a single ROI. points are (x, y) LPS world coords.
    meta_dose : dict from load_rtdose

    Returns
    -------
    mask : ndarray bool, shape (z, y, x) matching dose grid
    """
    dose_shape = meta_dose['dose'].shape  # (z, y, x)
    nz, ny, nx = dose_shape
    mask = np.zeros(dose_shape, dtype=bool)

    if not contours:
        return mask

    # Compute world z for each dose slice
    ipp = meta_dose['ipp']
    v_slice = meta_dose['v_slice']
    z_offsets = meta_dose['z_offsets']
    # World z coordinate for each slice: ipp[2] + z_offset * v_slice[2]
    slice_world_z = np.array([ipp[2] + z_offsets[k] * v_slice[2] for k in range(nz)])

    # Determine slice spacing tolerance for matching
    if nz > 1:
        z_tol = abs(float(slice_world_z[1] - slice_world_z[0])) * 0.5
    else:
        z_tol = 1.0  # 1 mm fallback

    # Build pixel grid for inside-polygon testing
    row_indices = np.arange(ny, dtype=float)
    col_indices = np.arange(nx, dtype=float)
    rr, cc = np.meshgrid(row_indices, col_indices, indexing='ij')  # (ny, nx)
    grid_rc = np.column_stack([rr.ravel(), cc.ravel()])  # (ny*nx, 2)

    # Process each contour
    for contour in contours:
        z_world = contour['z']

        z_world = contour['z']
        # Find matching dose slice index
        diffs = np.abs(slice_world_z - z_world)
        best_k = int(np.argmin(diffs))
        if diffs[best_k] > z_tol:
            continue  # No matching slice

        # Convert contour points to grid coordinates
        pts_rc = _world_xy_to_grid_rc(contour['points'], meta_dose)

        # Build polygon path and test grid points
        poly = MplPath(pts_rc)
        inside = poly.contains_points(grid_rc)
        inside_2d = inside.reshape(ny, nx)

        # OR with existing mask (multiple contours on same slice = union)
        mask[best_k] |= inside_2d

    n_voxels = int(np.sum(mask))
    logger.info(f"ROI mask: {n_voxels} voxels across {np.sum(np.any(mask, axis=(1,2)))} slices")
    return mask


def build_roi_masks(rtstruct_meta: Dict, meta_dose: Dict,
                    roi_names: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
    """Build 3D boolean masks for selected ROIs.

    Parameters
    ----------
    rtstruct_meta : dict from load_rtstruct
    meta_dose : dict from load_rtdose
    roi_names : list of ROI name strings, or None for all ROIs

    Returns
    -------
    masks : dict mapping ROI name -> 3D bool ndarray (z, y, x)
    """
    masks = {}
    for roi in rtstruct_meta['roi_list']:
        name = roi['name']
        if roi_names is not None and name not in roi_names:
            continue
        if not roi['contours']:
            logger.warning(f"ROI '{name}' has no contours, skipping.")
            continue
        logger.info(f"Building mask for ROI '{name}' ({len(roi['contours'])} contour slices)")
        masks[name] = contour_to_mask_3d(roi['contours'], meta_dose)
    return masks
