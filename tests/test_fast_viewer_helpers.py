from types import SimpleNamespace

import numpy as np

from scripts.gamma_viewer_fast import (
    FastPlaneViewer,
    _auto_dose_display_range,
    _compute_gamma_if_needed,
    _dose_diff_value,
    _gamma_coverage_text,
    _gamma_value_text,
    _overall_gpr_text,
    _parse_args,
    _pass_fail_text,
    _resample_eval,
    _validated_dose_display_range,
    cursor_from_display_point,
    display_point_for_cursor,
)


def test_parser_accepts_explicit_engine_and_interpolation_fraction():
    args = _parse_args(
        [
            '--ct',
            'ct',
            '--ref',
            'ref.dcm',
            '--engine',
            'numba',
            '--interp-fraction',
            '4',
        ]
    )

    assert args.engine == 'numba'
    assert args.interp_fraction == 4
    assert args.opt_shift == 'off'
    assert args.shift_range == 'x:-3:3:1,y:-3:3:1,z:-3:3:1'
    assert args.refine == 'coarse2fine'
    assert args.fine_range_mm == 10.0
    assert args.fine_step_mm == 1.0
    assert args.early_stop_epsilon == 0.05
    assert args.early_stop_patience == 100
    assert args.prescan_2d == 'on'


def test_eval_pair_is_validated_before_fast_viewer_resampling(monkeypatch):
    reference = {'role': 'reference'}
    evaluation = {'role': 'evaluation'}
    calls = []

    monkeypatch.setattr(
        'scripts.gamma_viewer_fast.load_rtdose',
        lambda _: evaluation,
    )

    def fake_validate(ref_meta, eval_meta):
        calls.append((ref_meta, eval_meta))
        raise ValueError('incompatible RTDOSE pair')

    monkeypatch.setattr(
        'scripts.gamma_viewer_fast.validate_rtdose_pair_geometry',
        fake_validate,
    )
    monkeypatch.setattr(
        'scripts.gamma_viewer_fast.resample_eval_onto_ref',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError('resampling must not run')
        ),
    )

    with np.testing.assert_raises_regex(ValueError, 'incompatible RTDOSE pair'):
        _resample_eval('evaluation.dcm', reference)

    assert calls == [(reference, evaluation)]


def test_on_demand_gamma_routes_selected_engine(monkeypatch):
    captured = {}
    dose = np.ones((2, 2, 2), dtype=float)
    axes = np.arange(2, dtype=float)

    def fake_compute_gamma(**kwargs):
        captured.update(kwargs)
        return np.zeros_like(dose), 100.0, {}

    monkeypatch.setattr('scripts.gamma_viewer_fast.compute_gamma', fake_compute_gamma)
    args = SimpleNamespace(
        gamma_npz=None,
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        gamma_type='local',
        norm='none',
        engine='numba',
        interp_fraction=4,
        opt_shift='off',
    )
    dose_meta = {
        'dose': dose,
        'z_coords_mm': axes,
        'y_coords_mm': axes,
        'x_coords_mm': axes,
    }

    gamma = _compute_gamma_if_needed(args, dose_meta, dose.copy())

    np.testing.assert_array_equal(gamma, np.zeros_like(dose))
    assert captured['engine'] == 'numba'
    assert captured['gamma_type'] == 'local'
    assert captured['norm'] == 'none'
    assert captured['interp_fraction'] == 4


def test_stale_gui_gamma_cache_recomputes_with_selected_engine(monkeypatch):
    captured = {}
    dose = np.ones((2, 2, 2), dtype=float)
    axes = np.arange(2, dtype=float)

    monkeypatch.setattr(
        'scripts.gamma_viewer_fast.load_validated_gamma_cache',
        lambda *args, **kwargs: None,
    )

    def fake_compute_gamma(**kwargs):
        captured.update(kwargs)
        return np.full_like(dose, 0.25), 100.0, {}

    monkeypatch.setattr('scripts.gamma_viewer_fast.compute_gamma', fake_compute_gamma)
    args = SimpleNamespace(
        gamma_npz='stale-gamma3d.npz',
        gamma_report='run3d.json',
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        gamma_type='global',
        norm='global_max',
        engine='numba',
        interp_fraction=4,
        opt_shift='off',
    )
    dose_meta = {
        'source_path': 'reference.dcm',
        'source_sha256': '1' * 64,
        'dose': dose,
        'z_coords_mm': axes,
        'y_coords_mm': axes,
        'x_coords_mm': axes,
    }
    eval_meta = {'source_path': 'evaluation.dcm', 'source_sha256': '2' * 64}

    gamma = _compute_gamma_if_needed(args, dose_meta, dose.copy(), eval_meta)

    np.testing.assert_array_equal(gamma, np.full_like(dose, 0.25))
    assert captured['engine'] == 'numba'


def test_missing_optimized_cache_fails_closed(monkeypatch):
    dose = np.ones((2, 2, 2), dtype=float)
    axes = np.arange(2, dtype=float)
    monkeypatch.setattr(
        'scripts.gamma_viewer_fast.load_validated_gamma_cache',
        lambda *args, **kwargs: None,
    )
    args = SimpleNamespace(
        gamma_npz='stale-gamma3d.npz',
        gamma_report='run3d.json',
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        gamma_type='global',
        norm='global_max',
        engine='pymedphys',
        interp_fraction=4,
        opt_shift='on',
    )
    dose_meta = {
        'source_path': 'reference.dcm',
        'source_sha256': '1' * 64,
        'dose': dose,
        'z_coords_mm': axes,
        'y_coords_mm': axes,
        'x_coords_mm': axes,
    }

    with np.testing.assert_raises_regex(
        ValueError,
        'No compatible shift-optimized Gamma cache',
    ):
        _compute_gamma_if_needed(
            args,
            dose_meta,
            dose.copy(),
            {'source_path': 'evaluation.dcm', 'source_sha256': '2' * 64},
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
    viewer._dose_display_auto_range = {"ref": (0.0, 1.0), "eval": (0.0, 10.0)}
    viewer._dose_display_manual_range = {"ref": None, "eval": None}
    viewer._dose_display_auto_enabled = {"ref": True, "eval": True}
    viewer._overlay_rgba_cache = {}

    rgba = viewer._overlay_rgba("axial")

    assert rgba is not None
    assert rgba[0, 0, 3] == 128
    assert rgba[0, 1, 3] == 128
    assert rgba[1, 0, 3] == 128
    assert rgba[1, 1, 3] == 0


def test_cached_dose_overlay_respects_overlay_visibility():
    viewer = FastPlaneViewer.__new__(FastPlaneViewer)
    viewer.overlay_visible = True
    viewer.overlay_mode = "Ref Dose"
    viewer.overlay_alpha = 128
    viewer.cur_z = 0
    viewer.ref_dose = np.array([[[0.05, 0.2], [0.0, np.nan]]], dtype=float)
    viewer.eval_dose = None
    viewer.gamma = None
    viewer._dose_display_auto_range = {"ref": (0.0, 1.0), "eval": (0.0, 1.0)}
    viewer._dose_display_manual_range = {"ref": None, "eval": None}
    viewer._dose_display_auto_enabled = {"ref": True, "eval": True}
    viewer._overlay_rgba_cache = {}

    assert viewer._overlay_rgba("axial") is not None
    assert viewer._overlay_rgba_cache

    viewer.overlay_visible = False

    assert viewer._overlay_rgba("axial") is None


def test_auto_dose_display_range_ignores_single_extreme_outlier():
    volume = np.ones((20, 20, 20), dtype=float)
    volume *= 0.8
    volume[0, 0, 0] = 1000.0

    lo, hi = _auto_dose_display_range(volume)

    assert lo == 0.0
    assert hi < 10.0
    assert hi != float(np.nanmax(volume))


def test_ref_and_eval_auto_dose_ranges_are_independent():
    ref = np.full((20, 20, 20), 1.0, dtype=float)
    eval_dose = np.full((20, 20, 20), 0.5, dtype=float)
    eval_dose[0, 0, 0] = 1000.0

    ref_range = _auto_dose_display_range(ref)
    eval_range = _auto_dose_display_range(eval_dose)

    assert ref_range == (0.0, 1.0)
    assert eval_range[1] < 10.0
    assert ref_range != eval_range


def test_manual_dose_display_range_validation_accepts_valid_range():
    previous = (0.0, 1.0)

    new_range, ok, reason = _validated_dose_display_range(0.4, 1.0, previous)

    assert ok
    assert new_range == (0.4, 1.0)
    assert reason == ""


def test_manual_dose_display_range_validation_rejects_invalid_and_preserves_previous():
    previous = (0.0, 1.0)

    for min_value, max_value in [(1.0, 1.0), (2.0, 1.0), (np.nan, 1.0), (0.0, np.inf)]:
        new_range, ok, reason = _validated_dose_display_range(min_value, max_value, previous)
        assert not ok
        assert new_range == previous
        assert reason


def test_auto_dose_display_range_fallbacks_are_safe():
    cases = [
        np.zeros((2, 2, 2), dtype=float),
        np.full((2, 2, 2), np.nan, dtype=float),
        np.full((2, 2, 2), np.inf, dtype=float),
        np.full((2, 2, 2), -1.0, dtype=float),
        None,
    ]

    for volume in cases:
        assert _auto_dose_display_range(volume) == (0.0, 1.0)
