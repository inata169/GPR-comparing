import numpy as np
from typing import Tuple, List, Dict
import logging
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
    refine: bool = True,
) -> Tuple[Tuple[float, float, float], float, Dict]:
    
    z_eval, y_eval, x_eval = eval_axes_mm_1d

    def _evaluate_shift(dx, dy, dz):
        logging.info(f"Testing shift: dx={dx}, dy={dy}, dz={dz}")
        shifted_axes_eval = (z_eval + dz, y_eval + dy, x_eval + dx)
        _, pass_rate, _ = compute_gamma(
            axes_ref_mm=ref_axes_mm_1d,
            dose_ref=dose_ref,
            axes_eval_mm=shifted_axes_eval,
            dose_eval=dose_eval,
            dd_percent=dd,
            dta_mm=dta,
            cutoff_percent=cutoff,
            gamma_type='global',
            norm=norm,
            use_pymedphys=False,
        )
        return pass_rate

    # Coarse search
    logging.info("Starting coarse shift search.")
    xs_coarse, ys_coarse, zs_coarse = parse_shift_range(shift_spec)
    # --- GEMINI AGENT MODIFICATION ---
    # The original logic only tested the boundaries and zero of the shift range.
    # This is a bug that prevents forcing a specific manual shift.
    # The logic is now changed to iterate over the entire specified range.
    coarse_shifts = []
    for z in zs_coarse:
        for y in ys_coarse:
            for x in xs_coarse:
                coarse_shifts.append((x, y, z))

    best_pass = -1.0
    best_shift = (0.0, 0.0, 0.0)
    log: List[Dict] = []

    for x, y, z in coarse_shifts:
        pass_rate = _evaluate_shift(x, y, z)
        log.append({'dx': x, 'dy': y, 'dz': z, 'pass_rate': pass_rate, 'type': 'coarse'})
        if pass_rate > best_pass:
            best_pass = pass_rate
            best_shift = (x, y, z)
    
    logging.info(f"Coarse search complete. Best shift: {best_shift} with pass rate {best_pass:.2f}%")

    # Fine search (refinement)
    if refine:
        logging.info("Starting fine shift search.")
        fine_range = 1.0
        fine_step = 0.5
        
        xs_fine = np.arange(best_shift[0] - fine_range, best_shift[0] + fine_range + 1e-6, fine_step)
        ys_fine = np.arange(best_shift[1] - fine_range, best_shift[1] + fine_range + 1e-6, fine_step)
        zs_fine = np.arange(best_shift[2] - fine_range, best_shift[2] + fine_range + 1e-6, fine_step)

        for z in zs_fine:
            for y in ys_fine:
                for x in xs_fine:
                    # Skip re-evaluating the coarse best point
                    if np.allclose([x, y, z], best_shift):
                        continue
                    pass_rate = _evaluate_shift(x, y, z)
                    log.append({'dx': x, 'dy': y, 'dz': z, 'pass_rate': pass_rate, 'type': 'fine'})
                    if pass_rate > best_pass:
                        best_pass = pass_rate
                        best_shift = (x, y, z)
        logging.info(f"Fine search complete. Best shift: {best_shift} with pass rate {best_pass:.2f}%")

    return best_shift, best_pass, {'search_log': log}