import numpy as np
import pytest
from rtgamma.dvh import calculate_dvh, calculate_dvh_stats

def test_calculate_dvh_uniform():
    # Uniform dose ROI
    dose = np.ones((5, 5, 5)) * 2.0
    mask = np.zeros((5, 5, 5), dtype=bool)
    mask[1:4, 1:4, 1:4] = True # 3x3x3 = 27 voxels
    
    bins, vol = calculate_dvh(dose, mask, n_bins=10)
    
    assert bins.size > 0
    assert np.isclose(vol[0], 100.0) # At 0 dose, 100% volume
    assert np.isclose(vol[-1], 100.0) # Even at max dose (since it is uniform 2.0 and bins go up to 2.1)
    # Actually our binning goes high-to-low
    
def test_dvh_stats():
    dose = np.zeros((10, 10, 10))
    dose[5, 5, 5] = 10.0 # One peak
    mask = np.zeros((10, 10, 10), dtype=bool)
    mask[5, 5, 5] = True
    
    stats = calculate_dvh_stats(dose, mask)
    assert stats['mean'] == 10.0
    assert stats['max'] == 10.0
    assert stats['d95'] == 10.0
    assert stats['d50'] == 10.0
    assert stats['d2'] == 10.0

def test_dvh_gradient():
    dose = np.linspace(0, 100, 1000).reshape((10, 10, 10))
    mask = np.ones((10, 10, 10), dtype=bool)
    
    stats = calculate_dvh_stats(dose, mask)
    assert np.isclose(stats['mean'], 50.0, atol=1.0)
    assert np.isclose(stats['d50'], 50.0, atol=1.0)
    assert np.isclose(stats['d95'], 5.0, atol=1.0) # 95% volume has >= 5Gy
    assert np.isclose(stats['d2'], 98.0, atol=1.0) # 2% volume has >= 98Gy
