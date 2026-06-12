import numpy as np

from scripts.gamma_viewer_fast import (
    FastPlaneViewer,
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
    assert _gamma_value_text(0.0, True, 12.0, 10.0) == "0.000"
    assert _gamma_value_text(None, True, 9.9, 10.0) == "Excluded"
    assert _gamma_value_text(None, True, 10.0, 10.0) == "N/A"
    assert _gamma_value_text(None, True, 12.0, 10.0) == "N/A"
    assert _gamma_value_text(None, True, None, 10.0) == "N/A"
    assert _gamma_value_text(None, False, 9.9, 10.0) == "N/A"


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


def test_axial_and_coronal_orientation_labels_place_r_on_left_l_on_right():
    viewer = FastPlaneViewer.__new__(FastPlaneViewer)
    viewer.x_coords_mm = np.array([0.0, 2.0, 4.0])
    viewer.y_coords_mm = np.array([10.0, 12.0, 14.0])
    viewer.z_coords_mm = np.array([20.0, 23.0, 26.0])

    axial = viewer._orientation_labels("axial")
    coronal = viewer._orientation_labels("coronal")

    assert [label[0] for label in axial[:2]] == ["R", "L"]
    assert [label[0] for label in coronal[:2]] == ["R", "L"]
    assert axial[0][1][0] < axial[1][1][0]
    assert coronal[0][1][0] < coronal[1][1][0]


def test_ref_dose_overlay_keeps_low_finite_dose_visible():
    viewer = FastPlaneViewer.__new__(FastPlaneViewer)
    viewer.overlay_visible = True
    viewer.overlay_mode = "Ref Dose"
    viewer.overlay_alpha = 128
    viewer.cur_z = 0
    viewer.ref_dose = np.array([[[0.05, 0.2], [0.0, np.nan]]], dtype=float)
    viewer.eval_dose = np.array([[[10.0, 10.0], [10.0, 10.0]]], dtype=float)
    viewer.gamma = None
    viewer._dose_vmax = 10.0

    rgba = viewer._overlay_rgba("axial")

    assert rgba is not None
    assert rgba[0, 0, 3] == 128
    assert rgba[0, 1, 3] == 128
    assert rgba[1, 0, 3] == 128
    assert rgba[1, 1, 3] == 0
