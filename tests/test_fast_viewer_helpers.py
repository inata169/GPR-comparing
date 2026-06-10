import numpy as np

from scripts.gamma_viewer_fast import (
    _dose_diff_value,
    _gamma_coverage_text,
    _gamma_value_text,
    _overall_gpr_text,
    _pass_fail_text,
    cursor_from_display_point,
    display_point_for_cursor,
)


def test_pass_fail_treats_zero_gamma_as_pass():
    assert _pass_fail_text(0.0) == "Pass"


def test_pass_fail_reports_nonfinite_or_missing_as_na():
    assert _pass_fail_text(None) == "N/A"


def test_pass_fail_threshold():
    assert _pass_fail_text(1.0) == "Pass"
    assert _pass_fail_text(1.0001) == "Fail"


def test_dose_diff_is_eval_minus_ref():
    assert _dose_diff_value(12.5, 10.0) == 2.5
    assert _dose_diff_value(None, 10.0) is None
    assert _dose_diff_value(12.5, None) is None


def test_gamma_value_text_distinguishes_excluded_from_missing():
    assert _gamma_value_text(0.0, True) == "0.000"
    assert _gamma_value_text(None, True) == "Excluded"
    assert _gamma_value_text(None, False) == "N/A"


def test_gamma_coverage_text_reports_valid_voxels():
    gamma = np.array([0.0, np.nan, 1.2, np.inf])
    assert _gamma_coverage_text(gamma) == "Gamma evaluated: 2/4 (50.000%)"
    assert _gamma_coverage_text(None) == "Gamma evaluated: N/A"


def test_overall_gpr_text_uses_evaluated_voxels_only():
    gamma = np.array([0.0, 0.9, 1.2, np.nan])
    assert _overall_gpr_text(gamma) == "Overall GPR: 66.67% (2/3)"
    assert _overall_gpr_text(None) == "Overall GPR: N/A"


def test_display_mapping_for_planes():
    x = np.array([0.0, 2.0, 4.0])
    y = np.array([10.0, 12.0, 14.0, 16.0])
    z = np.array([20.0, 23.0])
    cursor = (1, 2, 1)

    assert display_point_for_cursor("axial", cursor, x, y, z) == (2.0, 14.0)
    assert display_point_for_cursor("sagittal", cursor, x, y, z) == (14.0, 20.0)
    assert display_point_for_cursor("coronal", cursor, x, y, z) == (2.0, 20.0)


def test_inverse_mapping_clips_to_nearest_index():
    x = np.array([0.0, 2.0, 4.0])
    y = np.array([10.0, 12.0, 14.0, 16.0])
    z = np.array([20.0, 23.0])
    cursor = (1, 2, 1)

    assert cursor_from_display_point("axial", 100.0, -100.0, cursor, x, y, z) == (1, 0, 2)
    assert cursor_from_display_point("sagittal", 11.6, 21.7, cursor, x, y, z) == (0, 1, 1)
    assert cursor_from_display_point("coronal", -1.0, 99.0, cursor, x, y, z) == (0, 2, 0)
