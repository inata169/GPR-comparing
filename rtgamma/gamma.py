from typing import Literal, Optional, Tuple

import numba
import numpy as np

GammaType = Literal['global', 'local']
NormType = Literal['global_max', 'max_ref', 'none']


def _norm_factor(dose_ref: np.ndarray, dose_eval: np.ndarray, norm: NormType) -> float:
    if norm in ('global_max', 'max_ref'):
        return float(np.nanmax(dose_ref)) if np.isfinite(dose_ref).any() else 1.0
    return 1.0


@numba.jit(nopython=True)
def _trilinear(dose_eval, nz, ny, nx,
               kf, jf, if_):
    """Trilinear interpolation of dose_eval at fractional indices (kf, jf, if_).
    Returns (value, valid) where valid=False if out of bounds."""
    if kf < 0.0 or jf < 0.0 or if_ < 0.0:
        return 0.0, False
    if kf > nz - 1.0 or jf > ny - 1.0 or if_ > nx - 1.0:
        return 0.0, False

    k0 = int(kf)
    j0 = int(jf)
    i0 = int(if_)
    k1 = min(k0 + 1, nz - 1)
    j1 = min(j0 + 1, ny - 1)
    i1 = min(i0 + 1, nx - 1)

    dk = kf - k0
    dj = jf - j0
    di = if_ - i0

    c000 = dose_eval[k0, j0, i0]
    c100 = dose_eval[k1, j0, i0]
    c010 = dose_eval[k0, j1, i0]
    c110 = dose_eval[k1, j1, i0]
    c001 = dose_eval[k0, j0, i1]
    c101 = dose_eval[k1, j0, i1]
    c011 = dose_eval[k0, j1, i1]
    c111 = dose_eval[k1, j1, i1]

    val = (c000 * (1 - dk) * (1 - dj) * (1 - di) +
           c100 * dk * (1 - dj) * (1 - di) +
           c010 * (1 - dk) * dj * (1 - di) +
           c110 * dk * dj * (1 - di) +
           c001 * (1 - dk) * (1 - dj) * di +
           c101 * dk * (1 - dj) * di +
           c011 * (1 - dk) * dj * di +
           c111 * dk * dj * di)
    return val, True


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


@numba.jit(nopython=True, parallel=True)
def _numba_gamma_3d_interp(
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
    interp_fraction: int,
) -> np.ndarray:
    """Gamma kernel with sub-voxel interpolation.
    
    Searches DTA sphere at resolution dta_mm/interp_fraction using
    trilinear interpolation of eval dose. Uses early exit when gamma<=1.
    """
    gamma = np.full_like(dose_ref, np.nan)
    dta_mm_sq = dta_mm ** 2
    dd_percent_sq = dd_percent ** 2
    shape_ref = dose_ref.shape
    nz_e, ny_e, nx_e = dose_eval.shape

    z_ref_ax, y_ref_ax, x_ref_ax = axes_ref_mm
    z_eval_ax, y_eval_ax, x_eval_ax = axes_eval_mm

    # Eval grid spacing (assume uniform)
    if len(z_eval_ax) > 1:
        dz_eval = z_eval_ax[1] - z_eval_ax[0]
    else:
        dz_eval = 1.0
    if len(y_eval_ax) > 1:
        dy_eval = y_eval_ax[1] - y_eval_ax[0]
    else:
        dy_eval = 1.0
    if len(x_eval_ax) > 1:
        dx_eval = x_eval_ax[1] - x_eval_ax[0]
    else:
        dx_eval = 1.0

    z_eval_origin = z_eval_ax[0]
    y_eval_origin = y_eval_ax[0]
    x_eval_origin = x_eval_ax[0]

    step = dta_mm / interp_fraction

    # Pre-compute search offsets (half-axis)
    n_steps = interp_fraction  # number of steps from 0 to dta_mm

    for k_ref in numba.prange(shape_ref[0]):
        for j_ref in range(shape_ref[1]):
            for i_ref in range(shape_ref[2]):
                dose_ref_val = dose_ref[k_ref, j_ref, i_ref]

                if (dose_ref_val / norm_factor * 100.0) < cutoff_percent:
                    continue

                min_gamma_sq = np.inf
                found_pass = False

                z_ref = z_ref_ax[k_ref]
                y_ref = y_ref_ax[j_ref]
                x_ref = x_ref_ax[i_ref]

                # Search in expanding shells for early exit
                # Shell radius r goes from 0 to dta_mm in steps
                for shell in range(n_steps + 1):
                    if found_pass:
                        break
                    r = shell * step

                    # iterate over all grid points at distance ~r
                    iz_start = int(np.floor(-r / step)) if shell > 0 else 0
                    iz_end = int(np.ceil(r / step)) if shell > 0 else 0

                    for iz in range(iz_start, iz_end + 1):
                        if found_pass:
                            break
                        dz = iz * step
                        dz_sq = dz * dz
                        if dz_sq > dta_mm_sq:
                            continue
                        remain_yz = dta_mm_sq - dz_sq

                        iy_lim = int(np.floor(np.sqrt(max(remain_yz, 0.0)) / step))

                        for iy in range(-iy_lim, iy_lim + 1):
                            if found_pass:
                                break
                            dy = iy * step
                            dy_sq = dy * dy
                            dzy_sq = dz_sq + dy_sq
                            if dzy_sq > dta_mm_sq:
                                continue
                            remain_x = dta_mm_sq - dzy_sq

                            ix_lim = int(np.floor(np.sqrt(max(remain_x, 0.0)) / step))

                            for ix in range(-ix_lim, ix_lim + 1):
                                dx = ix * step
                                dist_sq = dzy_sq + dx * dx
                                if dist_sq > dta_mm_sq:
                                    continue

                                # Check if this point is on the current shell
                                # (on shell boundary or shell==0 for center)
                                max_abs = max(abs(iz), max(abs(iy), abs(ix)))
                                if shell == 0:
                                    if max_abs != 0:
                                        continue
                                else:
                                    if max_abs != shell:
                                        continue

                                # Fractional indices into eval grid
                                eval_z = z_ref + dz
                                eval_y = y_ref + dy
                                eval_x = x_ref + dx

                                kf = (eval_z - z_eval_origin) / dz_eval
                                jf = (eval_y - y_eval_origin) / dy_eval
                                if_ = (eval_x - x_eval_origin) / dx_eval

                                dose_eval_val, valid = _trilinear(
                                    dose_eval, nz_e, ny_e, nx_e,
                                    kf, jf, if_)
                                if not valid:
                                    continue

                                if local_mode == 1:
                                    denom = dose_ref_val
                                    if denom < tiny and denom > -tiny:
                                        continue
                                    dd_sq = ((dose_eval_val - dose_ref_val) / denom * 100.0) ** 2
                                else:
                                    dd_sq = ((dose_eval_val - dose_ref_val) / norm_factor * 100.0) ** 2

                                gamma_sq = dd_sq / dd_percent_sq + dist_sq / dta_mm_sq
                                if gamma_sq < min_gamma_sq:
                                    min_gamma_sq = gamma_sq
                                    if min_gamma_sq <= 1.0:
                                        found_pass = True

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
    norm_factor_override: Optional[float] = None,
    interp_fraction: int = 1,
) -> Tuple[np.ndarray, float, dict]:

    nf = float(norm_factor_override) if (norm_factor_override is not None) else _norm_factor(dose_ref, dose_eval, norm)

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

        if interp_fraction > 1:
            g = _numba_gamma_3d_interp(
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
                interp_fraction,
            )
        else:
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

    has_finite = np.isfinite(g).any()
    stats = {
        'gamma_mean': float(np.nanmean(g)) if has_finite else float('nan'),
        'gamma_median': float(np.nanmedian(g)) if has_finite else float('nan'),
        'gamma_max': float(np.nanmax(g)) if has_finite else float('nan'),
        'valid_points': int(np.sum(valid)),
    }

    # ---- Histogram statistics ----
    bin_edges = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
    if valid.any():
        g_valid = g[valid]
        n_valid = len(g_valid)
        counts = []
        cumulative_pass = []
        for i in range(len(bin_edges) - 1):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            if i == len(bin_edges) - 2:  # last bin includes upper edge
                c = int(np.sum((g_valid >= lo) & (g_valid <= hi)))
            else:
                c = int(np.sum((g_valid >= lo) & (g_valid < hi)))
            counts.append(c)
        # Voxels with gamma > last bin edge
        counts.append(int(np.sum(g_valid > bin_edges[-1])))
        for edge in bin_edges:
            cumulative_pass.append(float(np.sum(g_valid <= edge) / n_valid * 100.0))
        stats['histogram'] = {
            'bin_edges': bin_edges,
            'counts': counts,
            'cumulative_pass': cumulative_pass,
        }
        stats['gamma_p95'] = float(np.percentile(g_valid, 95))
        stats['gamma_p99'] = float(np.percentile(g_valid, 99))
    else:
        stats['histogram'] = {
            'bin_edges': bin_edges,
            'counts': [0] * (len(bin_edges)),
            'cumulative_pass': [0.0] * len(bin_edges),
        }
        stats['gamma_p95'] = float('nan')
        stats['gamma_p99'] = float('nan')

    return g, pass_rate, stats
