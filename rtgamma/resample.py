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
