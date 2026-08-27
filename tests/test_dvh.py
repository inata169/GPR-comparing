import numpy as np

from rtgamma.dvh import (
    calculate_dvh,
    calculate_dvh_stats,
    calculate_paired_dvh_stats,
)
from rtgamma.main import _slice_volume_for_plane


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


def test_dvh_ignores_non_finite_dose_values():
    dose = np.array([1.0, 2.0, np.nan, np.inf]).reshape((1, 2, 2))
    mask = np.ones_like(dose, dtype=bool)

    bins, vol = calculate_dvh(dose, mask, n_bins=10)
    stats = calculate_dvh_stats(dose, mask)

    assert bins.size > 0
    assert np.isclose(vol[0], 100.0)
    assert stats['mean'] == 1.5
    assert stats['min'] == 1.0
    assert stats['max'] == 2.0


def test_dvh_returns_empty_result_when_roi_dose_is_all_non_finite():
    dose = np.array([np.nan, np.inf]).reshape((1, 1, 2))
    mask = np.ones_like(dose, dtype=bool)

    bins, vol = calculate_dvh(dose, mask)
    stats = calculate_dvh_stats(dose, mask)

    assert bins.size == 0
    assert vol.size == 0
    assert np.isnan(stats['mean'])
    assert np.isnan(stats['d95'])
    assert stats['dvh_bins'] == []
    assert stats['dvh_vol'] == []


def test_paired_dvh_uses_same_finite_voxels_for_both_doses():
    reference_dose = np.array([1.0, 100.0]).reshape((1, 1, 2))
    evaluation_dose = np.array([2.0, np.nan]).reshape((1, 1, 2))
    mask = np.ones_like(reference_dose, dtype=bool)

    reference_stats, evaluation_stats = calculate_paired_dvh_stats(
        reference_dose,
        evaluation_dose,
        mask,
    )

    assert reference_stats['mean'] == 1.0
    assert reference_stats['max'] == 1.0
    assert evaluation_stats['mean'] == 2.0
    assert evaluation_stats['max'] == 2.0


def test_paired_dvh_returns_empty_results_without_common_finite_voxels():
    reference_dose = np.array([1.0]).reshape((1, 1, 1))
    evaluation_dose = np.array([np.nan]).reshape((1, 1, 1))
    mask = np.ones_like(reference_dose, dtype=bool)

    reference_stats, evaluation_stats = calculate_paired_dvh_stats(
        reference_dose,
        evaluation_dose,
        mask,
    )

    assert np.isnan(reference_stats['mean'])
    assert np.isnan(evaluation_stats['mean'])
    assert reference_stats['dvh_bins'] == []
    assert evaluation_stats['dvh_bins'] == []


def test_slice_volume_for_plane_preserves_singleton_axis():
    volume = np.arange(24).reshape((2, 3, 4))

    axial = _slice_volume_for_plane(volume, 'axial', 1)
    sagittal = _slice_volume_for_plane(volume, 'sagittal', 2)
    coronal = _slice_volume_for_plane(volume, 'coronal', 1)

    assert axial.shape == (1, 3, 4)
    assert sagittal.shape == (2, 3, 1)
    assert coronal.shape == (2, 1, 4)
    assert np.array_equal(axial[0], volume[1])
    assert np.array_equal(sagittal[:, :, 0], volume[:, :, 2])
    assert np.array_equal(coronal[:, 0, :], volume[:, 1, :])
