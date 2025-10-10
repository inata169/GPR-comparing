import numpy as np
from typing import Tuple, List, Dict
from .gamma import compute_gamma
from .resample import resample_eval_onto_ref


def parse_shift_range(spec: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    # spec: "x:-3:3:1,y:-3:3:1,z:-3:3:1"
    ranges = {'x': (-3.0, 3.0, 1.0), 'y': (-3.0, 3.0, 1.0), 'z': (-3.0, 3.0, 1.0)}
    for part in spec.split(','):
        if not part:
            continue
        axis, nums = part.split(':', 1)
        axis = axis.strip()
        s, e, st = [float(x) for x in nums.split(':')]
        ranges[axis] = (s, e, st)
    xs = np.arange(ranges['x'][0], ranges['x'][1] + 1e-6, ranges['x'][2])
    ys = np.arange(ranges['y'][0], ranges['y'][1] + 1e-6, ranges['y'][2])
    zs = np.arange(ranges['z'][0], ranges['z'][1] + 1e-6, ranges['z'][2])
    return xs, ys, zs


def grid_search_best_shift(
    ref_axes_mm_1d: Tuple[np.ndarray, np.ndarray, np.ndarray],
    dose_ref: np.ndarray,
    eval_axes_mm_1d: Tuple[np.ndarray, np.ndarray, np.ndarray],
    dose_eval: np.ndarray,
    dd: float,
    dta: float,
    cutoff: float,
    norm: str,
    shift_spec: str,
) -> Tuple[Tuple[float, float, float], float, Dict]:
    xs, ys, zs = parse_shift_range(shift_spec)
    best = (0.0, 0.0, 0.0)
    best_pass = -1.0
    log: List[Dict] = []

    # Unpack original axes
    z_eval, y_eval, x_eval = eval_axes_mm_1d

    for dz in zs:
        for dy in ys:
            for dx in xs:
                # Apply shift directly to eval coordinates
                shifted_axes_eval = (z_eval + dz, y_eval + dy, x_eval + dx)

                g, pass_rate, _ = compute_gamma(
                    axes_ref_mm=ref_axes_mm_1d,
                    dose_ref=dose_ref,
                    axes_eval_mm=shifted_axes_eval,
                    dose_eval=dose_eval,
                    dd_percent=dd,
                    dta_mm=dta,
                    cutoff_percent=cutoff,
                    gamma_type='global',
                    norm=norm,
                    use_pymedphys=True,
                )
                log.append({'dx': dx, 'dy': dy, 'dz': dz, 'pass_rate': pass_rate})
                if pass_rate > best_pass:
                    best_pass = pass_rate
                    best = (dx, dy, dz)
    return best, best_pass, {'search_log': log}
