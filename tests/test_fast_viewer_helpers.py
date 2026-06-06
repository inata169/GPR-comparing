import numpy as np

from scripts.gamma_viewer_fast import (
    _dose_diff_value,
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


def test_display_mapping_for_planes():
    x = np.array([0.0, 2.0, 4.0])
    y = np.array([10.0, 12.0, 14.0, 16.0])
    z = np.array([20.0, 23.0])
    cursor = (1, 2, 1)

    assert display_point_for_cursor("axial", cursor, x, y, z) == (2.0, 14.0)
    assert display_point_for_cursor("sagittal", cursor, x, y, z) == (14.0, 23.0)
    assert display_point_for_cursor("coronal", cursor, x, y, z) == (2.0, 23.0)


def test_inverse_mapping_clips_to_nearest_index():
    x = np.array([0.0, 2.0, 4.0])
    y = np.array([10.0, 12.0, 14.0, 16.0])
    z = np.array([20.0, 23.0])
    cursor = (1, 2, 1)

    assert cursor_from_display_point("axial", 100.0, -100.0, cursor, x, y, z) == (1, 0, 2)
    assert cursor_from_display_point("sagittal", 11.6, 21.7, cursor, x, y, z) == (1, 1, 1)
    assert cursor_from_display_point("coronal", -1.0, 99.0, cursor, x, y, z) == (1, 2, 0)
