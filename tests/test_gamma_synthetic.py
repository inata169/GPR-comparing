import numpy as np

from rtgamma.gamma import compute_gamma


def make_axes(shape, spacing=(1.0, 1.0, 1.0)):
    sz, sy, sx = shape
    dz, dy, dx = spacing
    z = np.arange(sz, dtype=float) * dz
    y = np.arange(sy, dtype=float) * dy
    x = np.arange(sx, dtype=float) * dx
    return (z, y, x)


def test_self_compare_uniform_global():
    shape = (6, 7, 8)
    axes = make_axes(shape)
    dose = np.ones(shape, dtype=np.float32) * 2.0
    g, pr, st = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose,
        axes_eval_mm=axes,
        dose_eval=dose.copy(),
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        gamma_type='global',
        norm='global_max',
        use_pymedphys=False,
    )
    assert np.isfinite(g).any()
    assert abs(pr - 100.0) < 1e-6
    assert st['gamma_max'] == 0.0


def test_local_is_stricter_on_scaled_eval_synth():
    # Synthetic smooth gradient volume
    sz, sy, sx = 9, 9, 9
    z = np.linspace(0.5, 1.0, sz, dtype=np.float32)
    y = np.linspace(0.5, 1.0, sy, dtype=np.float32)
    x = np.linspace(0.5, 1.0, sx, dtype=np.float32)
    Z, Y, X = np.meshgrid(z, y, x, indexing='ij')
    dose_ref = (0.1 + 0.9 * (Z * Y * X)).astype(np.float32)
    dose_eval = (dose_ref * 1.05).astype(np.float32)
    axes = make_axes((sz, sy, sx))

    # Global
    _, pr_g, _ = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_eval,
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=0.0,
        gamma_type='global',
        norm='global_max',
        use_pymedphys=False,
    )
    # Local
    _, pr_l, _ = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_eval,
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=0.0,
        gamma_type='local',
        norm='global_max',
        use_pymedphys=False,
    )

    assert pr_l <= pr_g
    assert pr_l < 100.0

