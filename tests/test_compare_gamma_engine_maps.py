import numpy as np
import pytest

from scripts.compare_gamma_engine_maps import compare_gamma_maps


def test_compare_gamma_maps_reports_masks_differences_and_confusion():
    gamma_numba = np.array([[[0.5, 1.2, np.nan, 0.9]]])
    gamma_pymedphys = np.array([[[0.4, 0.8, 1.1, np.nan]]])
    axes = (np.array([5.0]), np.array([10.0]), np.arange(4, dtype=float) * 2.0)

    summary, arrays = compare_gamma_maps(
        gamma_numba,
        gamma_pymedphys,
        axes,
        coordinate_limit=10,
    )

    assert summary["mask"] == {
        "numba_finite": 3,
        "pymedphys_finite": 3,
        "common_finite": 2,
        "finite_union": 4,
        "numba_only": 1,
        "pymedphys_only": 1,
    }
    assert summary["gpr_on_common_mask"]["numba"] == 50.0
    assert summary["gpr_on_common_mask"]["pymedphys"] == 100.0
    assert summary["gamma_difference_numba_minus_pymedphys"]["mean"] == pytest.approx(0.25)
    assert summary["pass_fail_confusion_on_common_mask"] == {
        "both_pass": 1,
        "numba_pass_pymedphys_fail": 0,
        "numba_fail_pymedphys_pass": 1,
        "both_fail": 0,
        "total_disagreements": 1,
    }
    assert summary["first_disagreement_coordinates"] == [
        {
            "index_kji": [0, 0, 1],
            "axis_coordinates_mm": [5.0, 10.0, 2.0],
            "gamma_numba": 1.2,
            "gamma_pymedphys": 0.8,
        }
    ]
    assert summary["largest_gamma_difference_coordinates"][0] == {
        "index_kji": [0, 0, 1],
        "axis_coordinates_mm": [5.0, 10.0, 2.0],
        "gamma_numba": 1.2,
        "gamma_pymedphys": 0.8,
        "difference_numba_minus_pymedphys": pytest.approx(0.4),
        "absolute_difference": pytest.approx(0.4),
    }
    assert arrays["disagreement_indices_kji"].tolist() == [[0, 0, 1]]


def test_compare_gamma_maps_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="shapes differ"):
        compare_gamma_maps(
            np.zeros((1, 2, 2)),
            np.zeros((2, 2, 2)),
            (np.array([0.0]), np.arange(2), np.arange(2)),
        )
