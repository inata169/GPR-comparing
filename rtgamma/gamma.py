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


@numba.jit(nopython=True)
def _get_interp_offsets(interp_fraction: int, dta_mm: float):
    step = dta_mm / interp_fraction
    n_steps = interp_fraction
    dta_mm_sq = dta_mm ** 2
    
    # Pre-allocate large enough (cube volume)
    max_pts = (2 * n_steps + 1) ** 3
    offsets = np.zeros((max_pts, 3))
    dists_sq = np.zeros(max_pts)
    count = 0
    
    for iz in range(-n_steps, n_steps + 1):
        dz = iz * step
        dz_sq = dz * dz
        for iy in range(-n_steps, n_steps + 1):
            dy = iy * step
            dy_sq = dy * dy
            for ix in range(-n_steps, n_steps + 1):
                dx = ix * step
                ds_sq = dz_sq + dy_sq + dx * dx
                if ds_sq <= dta_mm_sq + 1e-9:
                    offsets[count, 0] = dz
                    offsets[count, 1] = dy
                    offsets[count, 2] = dx
                    dists_sq[count] = ds_sq
                    count += 1
    
    # Sort by distance for early exit
    res = offsets[:count]
    rds = dists_sq[:count]
    idx = np.argsort(rds)
    return res[idx], rds[idx]


@numba.jit(nopython=True)
def _get_voxel_offsets(dz: float, dy: float, dx: float, dta_mm: float):
    """Precompute integer index offsets (dk, dj, di) within DTA sphere, sorted by distance."""
    dta_mm_sq = dta_mm ** 2
    nk = int(dta_mm / abs(dz)) + 1 if dz != 0 else 0
    nj = int(dta_mm / abs(dy)) + 1 if dy != 0 else 0
    ni = int(dta_mm / abs(dx)) + 1 if dx != 0 else 0
    
    # Pre-allocate
    max_pts = (2 * nk + 1) * (2 * nj + 1) * (2 * ni + 1)
    offsets = np.zeros((max_pts, 3), dtype=np.int32)
    dists_sq = np.zeros(max_pts, dtype=np.float64)
    count = 0
    
    for k in range(-nk, nk + 1):
        z = k * dz
        z2 = z * z
        for j in range(-nj, nj + 1):
            y = j * dy
            zy2 = z2 + y * y
            for i in range(-ni, ni + 1):
                x = i * dx
                ds_sq = zy2 + x * x
                if ds_sq <= dta_mm_sq + 1e-9:
                    offsets[count, 0] = k
                    offsets[count, 1] = j
                    offsets[count, 2] = i
                    dists_sq[count] = ds_sq
                    count += 1
    
    res_o = offsets[:count]
    res_d = dists_sq[:count]
    idx = np.argsort(res_d)
    return res_o[idx], res_d[idx]


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
    offsets_ijk: np.ndarray,
    dists_sq: np.ndarray,
) -> np.ndarray:
    gamma = np.full_like(dose_ref, np.nan)
    dta_mm_sq = dta_mm ** 2
    dd_percent_sq = dd_percent ** 2
    shape_ref = dose_ref.shape
    nz_e, ny_e, nx_e = dose_eval.shape

    z_ref_ax, y_ref_ax, x_ref_ax = axes_ref_mm
    z_eval_ax, y_eval_ax, x_eval_ax = axes_eval_mm

    # Pre-calculate nearest eval index for each reference pixel axis (for initial guess)
    z_near_indices = np.searchsorted(z_eval_ax, z_ref_ax)
    y_near_indices = np.searchsorted(y_eval_ax, y_ref_ax)
    x_near_indices = np.searchsorted(x_eval_ax, x_ref_ax)

    # Clamp nearest indices
    for i in range(len(z_near_indices)):
        z_near_indices[i] = min(max(0, z_near_indices[i]), nz_e - 1)
    for i in range(len(y_near_indices)):
        y_near_indices[i] = min(max(0, y_near_indices[i]), ny_e - 1)
    for i in range(len(x_near_indices)):
        x_near_indices[i] = min(max(0, x_near_indices[i]), nx_e - 1)

    n_offsets = len(dists_sq)

    for k_ref in numba.prange(shape_ref[0]):
        k_near = z_near_indices[k_ref]

        for j_ref in range(shape_ref[1]):
            j_near = y_near_indices[j_ref]

            for i_ref in range(shape_ref[2]):
                dose_ref_val = dose_ref[k_ref, j_ref, i_ref]

                if (dose_ref_val / norm_factor * 100.0) < cutoff_percent:
                    continue

                min_gamma_sq = np.inf
                found_pass = False
                i_near = x_near_indices[i_ref]

                # Search distance-sorted voxel offsets
                for o_idx in range(n_offsets):
                    dist_sq = dists_sq[o_idx]
                    
                    if dist_sq >= min_gamma_sq * dta_mm_sq:
                        break # Sorted, so all subsequent will be larger

                    dk = offsets_ijk[o_idx, 0]
                    dj = offsets_ijk[o_idx, 1]
                    di = offsets_ijk[o_idx, 2]
                    
                    ke = k_near + dk
                    je = j_near + dj
                    ie = i_near + di

                    # Boundary check
                    if ke < 0 or ke >= nz_e or je < 0 or je >= ny_e or ie < 0 or ie >= nx_e:
                        continue

                    dose_eval_val = dose_eval[ke, je, ie]
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
                            break

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
    offsets: np.ndarray,
    dists_sq: np.ndarray,
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

    n_offsets = len(dists_sq)

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

                for o_idx in range(n_offsets):
                    dz = offsets[o_idx, 0]
                    dy = offsets[o_idx, 1]
                    dx = offsets[o_idx, 2]
                    dist_sq = dists_sq[o_idx]

                    # Optimization: Skip if distance already >= min_gamma_sq
                    if dist_sq >= min_gamma_sq * dta_mm_sq:
                        continue

                    # Fractional indices into eval grid
                    kf = (z_ref + dz - z_eval_origin) / dz_eval
                    jf = (y_ref + dy - y_eval_origin) / dy_eval
                    if_ = (x_ref + dx - x_eval_origin) / dx_eval

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
                            break

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
            # Precompute offsets for interp outside the parallel loop
            offsets, dists_sq = _get_interp_offsets(interp_fraction, dta_mm)
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
                offsets,
                dists_sq
            )
        else:
            # Precompute voxel offsets for non-interp
            z_eval_ax, y_eval_ax, x_eval_ax = axes_eval_mm
            dz_e = z_eval_ax[1] - z_eval_ax[0] if len(z_eval_ax) > 1 else 1.0
            dy_e = y_eval_ax[1] - y_eval_ax[0] if len(y_eval_ax) > 1 else 1.0
            dx_e = x_eval_ax[1] - x_eval_ax[0] if len(x_eval_ax) > 1 else 1.0
            
            v_offsets, v_dists_sq = _get_voxel_offsets(dz_e, dy_e, dx_e, dta_mm)
            
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
                v_offsets,
                v_dists_sq
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
