import numpy as np

from rtgamma.gamma import compute_gamma


def make_axes(shape):
    sz, sy, sx = shape
    z = np.arange(sz, dtype=float)
    y = np.arange(sy, dtype=float)
    x = np.arange(sx, dtype=float)
    return (z, y, x)


def test_gamma_equal_arrays_global_and_local_pass_100():
    shape = (5, 5, 5)
    axes = make_axes(shape)
    dose_ref = np.ones(shape, dtype=np.float32)
    dose_eval = np.ones(shape, dtype=np.float32)

    # Global
    g_g, pr_g, st_g = compute_gamma(
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
    g_l, pr_l, st_l = compute_gamma(
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

    assert np.isfinite(g_g).any()
    assert np.isfinite(g_l).any()
    assert abs(pr_g - 100.0) < 1e-6
    assert abs(pr_l - 100.0) < 1e-6
    assert st_g['gamma_max'] == 0.0
    assert st_l['gamma_max'] == 0.0


def test_local_is_stricter_than_global_on_scaled_eval():
    # Reference: gradient field (0.1..1.0), Eval: +5% everywhere
    sz, sy, sx = 9, 9, 9
    z = np.linspace(0.5, 1.0, sz, dtype=np.float32)
    y = np.linspace(0.5, 1.0, sy, dtype=np.float32)
    x = np.linspace(0.5, 1.0, sx, dtype=np.float32)
    Z, Y, X = np.meshgrid(z, y, x, indexing='ij')
    dose_ref = (0.1 + 0.9 * (Z * Y * X)).astype(np.float32)
    dose_eval = (dose_ref * 1.05).astype(np.float32)
    axes = (np.arange(sz, dtype=float), np.arange(sy, dtype=float), np.arange(sx, dtype=float))

    # Global
    g_g, pr_g, _ = compute_gamma(
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
    g_l, pr_l, _ = compute_gamma(
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

    # Expect local to be stricter → lower or equal pass rate
    assert pr_l <= pr_g
    # With +5% everywhere and threshold 3%, local should fail many points
    assert pr_l < 100.0
