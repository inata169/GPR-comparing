import numpy as np
from scipy import ndimage
from typing import Literal, Tuple


InterpMode = Literal['linear', 'bspline', 'nearest']


def _order_from_interp(interp: InterpMode) -> int:
    if interp == 'nearest':
        return 0
    if interp == 'linear':
        return 1
    if interp == 'bspline':
        return 3
    return 1


def resample_eval_onto_ref(
    eval_dose: np.ndarray,
    world_to_eval_ijk,
    ref_world_coords: Tuple[np.ndarray, np.ndarray, np.ndarray],
    interp: InterpMode = 'linear',
    cval: float = np.nan,
    shift_mm: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> np.ndarray:
    # ref_world_coords: (Xw, Yw, Zw) world LPS coordinate arrays of shape (X,Y,Z) matching ref grid
    Xw, Yw, Zw = ref_world_coords
    # Apply inverse shift to sample eval as if shifted by +shift_mm
    dx, dy, dz = shift_mm
    Xs = Xw - dx
    Ys = Yw - dy
    Zs = Zw - dz
    # Stack world coordinates as (x,y,z)
    pts = np.stack([Xs.ravel(), Ys.ravel(), Zs.ravel()], axis=-1)
    ijk = world_to_eval_ijk(pts).reshape(Zs.shape + (3,))
    order = _order_from_interp(interp)
    sampled = ndimage.map_coordinates(eval_dose, [ijk[..., 0], ijk[..., 1], ijk[..., 2]],
                                      order=order, mode='constant', cval=cval)
    return sampled.reshape(Zs.shape)


def resample_ct_onto_dose(ct_meta: dict, dose_meta: dict, interp: InterpMode = 'linear') -> np.ndarray:
    """Resample CT (HU) volume onto the DOSE grid using world coordinates.

    Parameters
    ----------
    ct_meta : dict from load_ct
    dose_meta : dict from load_rtdose
    interp : interpolation mode

    Returns
    -------
    ct_on_dose : ndarray float32, shape matching dose grid (z, y, x), HU values
    """
    # Build fractional CT voxel indices for each DOSE grid world position
    dose = dose_meta['dose']
    nz_d, ny_d, nx_d = dose.shape

    # DOSE grid world coordinates
    ipp_d = dose_meta['ipp']
    v_col_d = dose_meta['v_col']
    v_row_d = dose_meta['v_row']
    v_slice_d = dose_meta['v_slice']
    i_mm = dose_meta['x_coords_mm']
    j_mm = dose_meta['y_coords_mm']
    k_mm = dose_meta['z_coords_mm']

    # Build flat world coordinate array for dose voxel centers
    J, I, K = np.meshgrid(j_mm, i_mm, k_mm, indexing='ij')
    Pw = (ipp_d[None, None, None, :]
          + J[..., None] * v_row_d[None, None, None, :]
          + I[..., None] * v_col_d[None, None, None, :]
          + K[..., None] * v_slice_d[None, None, None, :])
    Pw = np.moveaxis(Pw, 2, 0)  # (k, j, i, 3)

    # CT grid parameters
    ipp_ct = ct_meta['ipp']
    v_col_ct = ct_meta['v_col']
    v_row_ct = ct_meta['v_row']
    z_pos_ct = ct_meta['z_positions']
    s_col_ct = ct_meta['s_col']
    s_row_ct = ct_meta['s_row']

    # Project dose world points into CT voxel indices
    d = Pw.reshape(-1, 3) - ipp_ct
    i_ct = (d @ v_col_ct) / s_col_ct
    j_ct = (d @ v_row_ct) / s_row_ct
    # Z: interpolate using CT z_positions
    z_world = Pw[..., 2].ravel()  # world Z of each dose point
    k_ct = np.interp(z_world, z_pos_ct, np.arange(len(z_pos_ct), dtype=float),
                     left=-1, right=-1)

    coords = np.stack([k_ct, j_ct, i_ct], axis=0)
    order = _order_from_interp(interp)
    ct_on_dose = ndimage.map_coordinates(ct_meta['ct_hu'], coords,
                                         order=order, mode='constant', cval=-1000.0)
    return ct_on_dose.reshape(dose.shape).astype(np.float32)
