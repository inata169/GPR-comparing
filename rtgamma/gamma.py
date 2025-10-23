import numpy as np
from typing import Tuple, Literal, Optional
import numba


GammaType = Literal['global', 'local']
NormType = Literal['global_max', 'max_ref', 'none']


def _norm_factor(dose_ref: np.ndarray, dose_eval: np.ndarray, norm: NormType) -> float:
    if norm in ('global_max', 'max_ref'):
        return float(np.nanmax(dose_ref)) if np.isfinite(dose_ref).any() else 1.0
    return 1.0


@numba.jit(nopython=True, parallel=True)
def _numba_gamma_3d(
    axes_ref_mm: Tuple[np.ndarray, np.ndarray, np.ndarray],
    dose_ref: np.ndarray,
    axes_eval_mm: Tuple[np.ndarray, np.ndarray, np.ndarray],
    dose_eval: np.ndarray,
    dd_percent: float,
    dta_mm: float,
    cutoff_percent: float,
    norm_factor: float,
    local_mode: int,
    tiny: float,
) -> np.ndarray:
    gamma = np.full_like(dose_ref, np.nan)
    dta_mm_sq = dta_mm ** 2
    dd_percent_sq = dd_percent ** 2
    shape_ref = dose_ref.shape

    z_ref_ax, y_ref_ax, x_ref_ax = axes_ref_mm
    z_eval_ax, y_eval_ax, x_eval_ax = axes_eval_mm

    for k_ref in numba.prange(shape_ref[0]):
        for j_ref in range(shape_ref[1]):
            for i_ref in range(shape_ref[2]):
                dose_ref_val = dose_ref[k_ref, j_ref, i_ref]
                
                # Cutoff check is applied relative to global reference norm_factor
                if (dose_ref_val / norm_factor * 100.0) < cutoff_percent:
                    continue

                min_gamma_sq = np.inf
                
                z_ref = z_ref_ax[k_ref]
                y_ref = y_ref_ax[j_ref]
                x_ref = x_ref_ax[i_ref]

                z_min_idx = np.searchsorted(z_eval_ax, z_ref - dta_mm)
                z_max_idx = np.searchsorted(z_eval_ax, z_ref + dta_mm, side='right')
                y_min_idx = np.searchsorted(y_eval_ax, y_ref - dta_mm)
                y_max_idx = np.searchsorted(y_eval_ax, y_ref + dta_mm, side='right')
                x_min_idx = np.searchsorted(x_eval_ax, x_ref - dta_mm)
                x_max_idx = np.searchsorted(x_eval_ax, x_ref + dta_mm, side='right')

                for k_eval in range(z_min_idx, z_max_idx):
                    dist_z_sq = (z_eval_ax[k_eval] - z_ref) ** 2
                    if dist_z_sq > dta_mm_sq:
                        continue
                    for j_eval in range(y_min_idx, y_max_idx):
                        dist_y_sq = (y_eval_ax[j_eval] - y_ref) ** 2
                        dist_zy_sq = dist_z_sq + dist_y_sq
                        if dist_zy_sq > dta_mm_sq:
                            continue
                        for i_eval in range(x_min_idx, x_max_idx):
                            dist_x_sq = (x_eval_ax[i_eval] - x_ref) ** 2
                            dist_sq = dist_zy_sq + dist_x_sq
                            
                            if dist_sq <= dta_mm_sq:
                                dose_eval_val = dose_eval[k_eval, j_eval, i_eval]
                                # Global vs Local dose difference normalisation
                                if local_mode == 1:
                                    denom = dose_ref_val
                                    if denom < tiny and denom > -tiny:
                                        # avoid division by zero; skip contribution
                                        continue
                                    dd_sq = ((dose_eval_val - dose_ref_val) / denom * 100.0) ** 2
                                else:
                                    dd_sq = ((dose_eval_val - dose_ref_val) / norm_factor * 100.0) ** 2
                                
                                gamma_sq = dd_sq / dd_percent_sq + dist_sq / dta_mm_sq
                                if gamma_sq < min_gamma_sq:
                                    min_gamma_sq = gamma_sq
                
                if np.isfinite(min_gamma_sq):
                    gamma[k_ref, j_ref, i_ref] = np.sqrt(min_gamma_sq)

    return gamma


def compute_gamma(
    axes_ref_mm: Tuple[np.ndarray, ...],
    dose_ref: np.ndarray,
    axes_eval_mm: Tuple[np.ndarray, ...],
    dose_eval: np.ndarray,
    dd_percent: float,
    dta_mm: float,
    cutoff_percent: float,
    gamma_type: GammaType = 'global',
    norm: NormType = 'global_max',
    use_pymedphys: bool = False, # Default to False now
) -> Tuple[np.ndarray, float, dict]:
    
    nf = _norm_factor(dose_ref, dose_eval, norm)

    if use_pymedphys:
        import pymedphys
        ref_pct = (dose_ref / nf) * 100.0
        eval_pct = (dose_eval / nf) * 100.0
        g = pymedphys.gamma(axes_ref_mm, ref_pct, axes_eval_mm, eval_pct,
                                dose_percent_threshold=dd_percent,
                                distance_mm_threshold=dta_mm,
                                lower_percent_dose_cutoff=cutoff_percent)
    else:
        if dose_ref.ndim != 3:
            raise ValueError("Numba gamma implementation currently only supports 3D doses.")
        
        local_mode = 1 if gamma_type == 'local' else 0
        g = _numba_gamma_3d(
            axes_ref_mm,
            dose_ref,
            axes_eval_mm,
            dose_eval,
            dd_percent,
            dta_mm,
            cutoff_percent,
            nf,
            local_mode,
            1e-12,
        )

    valid = ~np.isnan(g)
    if valid.any():
        pass_rate = float(np.sum(g[valid] <= 1.0) / np.sum(valid) * 100.0)
    else:
        pass_rate = 0.0

    stats = {
        'gamma_mean': float(np.nanmean(g)) if np.isfinite(g).any() else float('nan'),
        'gamma_median': float(np.nanmedian(g)) if np.isfinite(g).any() else float('nan'),
        'gamma_max': float(np.nanmax(g)) if np.isfinite(g).any() else float('nan'),
        'valid_points': int(np.sum(valid)),
    }
    return g, pass_rate, stats


