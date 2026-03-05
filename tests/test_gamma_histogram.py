import numpy as np
import math

from rtgamma.gamma import compute_gamma

def make_axes(shape, spacing=(1.0, 1.0, 1.0)):
    sz, sy, sx = shape
    dz, dy, dx = spacing
    z = np.arange(sz, dtype=float) * dz
    y = np.arange(sy, dtype=float) * dy
    x = np.arange(sx, dtype=float) * dx
    return (z, y, x)

def test_gamma_histogram_output():
    shape = (5, 5, 5)
    axes = make_axes(shape)
    
    # Baseline dose
    dose_ref = np.ones(shape, dtype=np.float32) * 100.0
    dose_eval = np.ones(shape, dtype=np.float32) * 100.0
    
    # Introduce some variations to get different gamma values
    # For e.g. a 3% DD limit, local or global:
    # +1.0 -> 1% diff -> gamma = 1.0 / 3.0 = 0.33
    # +3.0 -> 3% diff -> gamma = 1.0
    # +6.0 -> 6% diff -> gamma = 2.0
    
    dose_eval[1, 1, 1] += 3.0  # Gamma should be ~1.0
    dose_eval[2, 2, 2] += 6.0  # Gamma should be ~2.0
    dose_eval[3, 3, 3] -= 4.5  # Gamma should be ~1.5

    # Force cutoff
    dose_ref[0, 0, 0] = 5.0 # Below 10% cutoff -> invalid point

    gamma_map, pass_rate, stats = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_eval,
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        gamma_type='global',
        norm='global_max',
        use_pymedphys=False
    )

    # basic asserts
    assert 'histogram' in stats
    assert 'gamma_p95' in stats
    assert 'gamma_p99' in stats

    hist = stats['histogram']
    assert 'bin_edges' in hist
    assert 'counts' in hist
    assert 'cumulative_pass' in hist

    edges = hist['bin_edges']
    counts = hist['counts']
    cumulative = hist['cumulative_pass']

    # check lengths
    assert len(counts) == len(edges)
    assert len(cumulative) == len(edges)
    
    # Total counts should match valid_points
    # We set 1 voxel below cutoff (out of 125)
    total_valid = sum(counts)
    assert total_valid == stats['valid_points']
    assert total_valid == 124

    # Percentiles should be valid non-negative floats
    assert not math.isnan(stats['gamma_p95'])
    assert not math.isnan(stats['gamma_p99'])
    assert stats['gamma_p95'] >= 0.0

def test_gamma_histogram_empty_valid():
    shape = (3, 3, 3)
    axes = make_axes(shape)
    dose_ref = np.zeros(shape, dtype=np.float32) # All points will be below cutoff
    dose_eval = np.zeros(shape, dtype=np.float32)

    gamma_map, pass_rate, stats = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_eval,
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        gamma_type='global',
        norm='global_max',
        use_pymedphys=False
    )

    # valid_points should be 0
    assert stats['valid_points'] == 0

    # Ensure it handles no valid points gracefully
    hist = stats['histogram']
    assert sum(hist['counts']) == 0
    assert math.isnan(stats['gamma_p95'])
    assert math.isnan(stats['gamma_p99'])
