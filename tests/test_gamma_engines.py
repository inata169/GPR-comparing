import builtins
import logging
import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest

from rtgamma.gamma import (
    _start_gamma_heartbeat,
    compute_gamma,
    resolve_gamma_engine,
)
from rtgamma.optimize import grid_search_best_shift


def _case():
    axes = tuple(np.arange(3, dtype=float) * 2.0 for _ in range(3))
    dose = np.array(
        [
            [[0.0, 0.5, 1.0], [0.5, 1.0, 1.5], [1.0, 1.5, 2.0]],
            [[0.5, 1.0, 1.5], [1.0, 2.0, 2.5], [1.5, 2.5, 3.0]],
            [[1.0, 1.5, 2.0], [1.5, 2.5, 3.0], [2.0, 3.0, 4.0]],
        ],
        dtype=float,
    )
    return axes, dose


def test_default_engine_is_pymedphys():
    axes, dose = _case()
    common = dict(
        axes_ref_mm=axes,
        dose_ref=dose,
        axes_eval_mm=axes,
        dose_eval=dose.copy(),
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        interp_fraction=1,
    )

    default_gamma, default_rate, default_stats = compute_gamma(**common)
    named_gamma, named_rate, named_stats = compute_gamma(**common, engine='pymedphys')

    np.testing.assert_allclose(default_gamma, named_gamma, equal_nan=True)
    assert default_rate == named_rate
    assert default_stats['gamma_engine'] == 'pymedphys'
    assert named_stats['gamma_engine'] == 'pymedphys'


def test_gamma_heartbeat_reports_liveness(caplog):
    caplog.set_level(logging.INFO)
    stop, thread = _start_gamma_heartbeat(
        'PyMedPhys', active_points=123, interval_seconds=0.01
    )
    try:
        time.sleep(0.04)
    finally:
        stop.set()
        thread.join(timeout=1.0)

    assert 'PyMedPhys gamma is still calculating' in caplog.text
    assert '123 reference points above cutoff' in caplog.text


@pytest.mark.parametrize('gamma_type', ['global', 'local'])
def test_real_pymedphys_identity_case(gamma_type):
    axes, dose = _case()
    gamma, pass_rate, stats = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose,
        axes_eval_mm=axes,
        dose_eval=dose.copy(),
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=10.0,
        gamma_type=gamma_type,
        interp_fraction=1,
        engine='pymedphys',
    )

    assert pass_rate == 100.0
    assert np.nanmax(gamma) == pytest.approx(0.0)
    assert stats['gamma_engine'] == 'pymedphys'
    assert stats['gamma_engine_version'] == '0.41.0'


def test_real_pymedphys_identity_case_2d():
    axes = (
        np.arange(4, dtype=float) * 2.0,
        np.arange(5, dtype=float) * 2.5,
    )
    dose = np.arange(20, dtype=float).reshape(4, 5) + 1.0

    gamma, pass_rate, _ = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose,
        axes_eval_mm=axes,
        dose_eval=dose.copy(),
        dd_percent=3.0,
        dta_mm=2.0,
        cutoff_percent=0.0,
        interp_fraction=2,
        engine='pymedphys',
    )

    assert pass_rate == 100.0
    np.testing.assert_allclose(gamma, 0.0)


def test_real_pymedphys_global_and_local_analytical_dose_terms():
    axes = tuple(np.arange(2, dtype=float) * 2.0 for _ in range(3))
    dose_ref = np.array(
        [[[1.0, 2.0], [3.0, 4.0]], [[1.0, 2.0], [3.0, 4.0]]],
        dtype=float,
    )
    dose_eval = dose_ref + 0.1
    common = dict(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_eval,
        dd_percent=10.0,
        dta_mm=0.5,
        cutoff_percent=0.0,
        interp_fraction=1,
        engine='pymedphys',
    )

    gamma_global, _, _ = compute_gamma(**common, gamma_type='global')
    gamma_local, _, _ = compute_gamma(**common, gamma_type='local')

    np.testing.assert_allclose(gamma_global, 0.25)
    expected_local = np.abs(dose_eval - dose_ref) / (dose_ref * 0.10)
    np.testing.assert_allclose(gamma_local, expected_local)


def test_pymedphys_cutoff_includes_boundary_and_excludes_below():
    axes = (
        np.arange(2, dtype=float) * 2.0,
        np.arange(2, dtype=float) * 2.0,
    )
    dose_ref = np.array([[0.999, 1.0], [1.001, 10.0]], dtype=float)

    gamma, pass_rate, stats = compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose_ref,
        axes_eval_mm=axes,
        dose_eval=dose_ref.copy(),
        dd_percent=3.0,
        dta_mm=1.0,
        cutoff_percent=10.0,
        interp_fraction=1,
        engine='pymedphys',
    )

    assert np.isnan(gamma[0, 0])
    assert np.isfinite(gamma[0, 1:]).all()
    assert np.isfinite(gamma[1]).all()
    assert stats['valid_points'] == 3
    assert pass_rate == 100.0


def test_pymedphys_supports_different_rectilinear_spacing():
    axes_ref = (
        np.array([0.0, 2.0, 4.0]),
        np.array([0.0, 2.0, 4.0]),
        np.array([0.0, 2.0, 4.0]),
    )
    axes_eval = tuple(np.arange(5, dtype=float) for _ in range(3))
    z_ref, y_ref, x_ref = np.meshgrid(*axes_ref, indexing='ij')
    z_eval, y_eval, x_eval = np.meshgrid(*axes_eval, indexing='ij')
    dose_ref = 1.0 + x_ref + 2.0 * y_ref + 3.0 * z_ref
    dose_eval = 1.0 + x_eval + 2.0 * y_eval + 3.0 * z_eval

    gamma, pass_rate, _ = compute_gamma(
        axes_ref_mm=axes_ref,
        dose_ref=dose_ref,
        axes_eval_mm=axes_eval,
        dose_eval=dose_eval,
        dd_percent=3.0,
        dta_mm=1.0,
        cutoff_percent=0.0,
        interp_fraction=2,
        engine='pymedphys',
    )

    assert pass_rate == 100.0
    np.testing.assert_allclose(gamma, 0.0, atol=1e-12)


def test_reference_evaluation_reversal_uses_reference_normalisation():
    axes = tuple(np.arange(2, dtype=float) * 2.0 for _ in range(3))
    dose_ref = np.arange(1.0, 9.0).reshape(2, 2, 2)
    dose_eval = dose_ref + 0.1
    common = dict(
        axes_ref_mm=axes,
        axes_eval_mm=axes,
        dd_percent=10.0,
        dta_mm=0.01,
        cutoff_percent=0.0,
        interp_fraction=1,
        engine='pymedphys',
    )

    forward, _, forward_stats = compute_gamma(
        **common,
        dose_ref=dose_ref,
        dose_eval=dose_eval,
    )
    reverse, _, reverse_stats = compute_gamma(
        **common,
        dose_ref=dose_eval,
        dose_eval=dose_ref,
    )

    assert forward_stats['resolved_normalisation'] == pytest.approx(8.0)
    assert reverse_stats['resolved_normalisation'] == pytest.approx(8.1)
    np.testing.assert_allclose(forward, 0.125)
    np.testing.assert_allclose(reverse, 0.1 / 0.81)
    assert not np.array_equal(forward, reverse)


def test_pymedphys_adapter_forwards_public_parameters(monkeypatch):
    axes, dose = _case()
    captured = {}

    def fake_gamma(*args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        return np.zeros_like(args[1], dtype=float)

    monkeypatch.setitem(sys.modules, 'pymedphys', SimpleNamespace(gamma=fake_gamma))
    compute_gamma(
        axes_ref_mm=axes,
        dose_ref=dose,
        axes_eval_mm=axes,
        dose_eval=dose.copy(),
        dd_percent=2.0,
        dta_mm=1.5,
        cutoff_percent=7.0,
        gamma_type='local',
        norm='global_max',
        interp_fraction=6,
        engine='pymedphys',
    )

    assert captured['args'][1] is dose
    assert captured['kwargs'] == {
        'dose_percent_threshold': 2.0,
        'distance_mm_threshold': 1.5,
        'lower_percent_dose_cutoff': 7.0,
        'interp_fraction': 6,
        'local_gamma': True,
        'global_normalisation': 4.0,
        'max_gamma': np.inf,
        'skip_once_passed': False,
        'random_subset': None,
        'interp_algo': 'pymedphys',
    }


def test_requested_pymedphys_does_not_fall_back(monkeypatch):
    axes, dose = _case()
    real_import = builtins.__import__

    def import_without_pymedphys(name, *args, **kwargs):
        if name == 'pymedphys':
            raise ImportError('simulated missing dependency')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', import_without_pymedphys)
    with pytest.raises(RuntimeError, match='requested but pymedphys is not installed'):
        compute_gamma(
            axes_ref_mm=axes,
            dose_ref=dose,
            axes_eval_mm=axes,
            dose_eval=dose,
            dd_percent=3.0,
            dta_mm=2.0,
            cutoff_percent=10.0,
            engine='pymedphys',
        )


def test_pymedphys_rejects_unapproved_installed_version(monkeypatch):
    axes, dose = _case()
    monkeypatch.setitem(
        sys.modules,
        'pymedphys',
        SimpleNamespace(gamma=lambda *args, **kwargs: np.zeros_like(dose)),
    )
    monkeypatch.setattr(
        'rtgamma.gamma.metadata.version',
        lambda package: '0.40.0' if package == 'pymedphys' else 'unknown',
    )

    with pytest.raises(
        RuntimeError,
        match='requires exactly PyMedPhys 0.41.0, but 0.40.0 is installed',
    ):
        compute_gamma(
            axes_ref_mm=axes,
            dose_ref=dose,
            axes_eval_mm=axes,
            dose_eval=dose,
            dd_percent=3.0,
            dta_mm=2.0,
            cutoff_percent=10.0,
            engine='pymedphys',
        )


def test_engine_resolution_rejects_conflicting_legacy_flag():
    assert resolve_gamma_engine() == 'pymedphys'
    assert resolve_gamma_engine(use_pymedphys=True) == 'pymedphys'
    with pytest.raises(ValueError, match='Conflicting'):
        resolve_gamma_engine(engine='pymedphys', use_pymedphys=False)


def test_pymedphys_rejects_unapproved_norm_none_mapping():
    axes, dose = _case()
    with pytest.raises(ValueError, match='does not support norm=none'):
        compute_gamma(
            axes_ref_mm=axes,
            dose_ref=dose,
            axes_eval_mm=axes,
            dose_eval=dose,
            dd_percent=3.0,
            dta_mm=2.0,
            cutoff_percent=10.0,
            norm='none',
            engine='pymedphys',
        )


def test_pymedphys_rejects_non_monotonic_axes_before_dispatch():
    axes, dose = _case()
    invalid_axes = (np.array([0.0, 2.0, 1.0]), axes[1], axes[2])
    with pytest.raises(ValueError, match='not strictly monotonic'):
        compute_gamma(
            axes_ref_mm=invalid_axes,
            dose_ref=dose,
            axes_eval_mm=axes,
            dose_eval=dose,
            dd_percent=3.0,
            dta_mm=2.0,
            cutoff_percent=10.0,
            engine='pymedphys',
        )


def test_shift_optimization_routes_selected_engine(monkeypatch):
    axes, dose = _case()
    selected_engines = []
    interpolation_fractions = []

    def fake_compute_gamma(*args, **kwargs):
        selected_engines.append(kwargs['engine'])
        interpolation_fractions.append(kwargs['interp_fraction'])
        return np.zeros_like(dose), 100.0, {'valid_points': dose.size}

    monkeypatch.setattr('rtgamma.optimize.compute_gamma', fake_compute_gamma)
    grid_search_best_shift(
        ref_axes_mm_1d=axes,
        dose_ref=dose,
        eval_axes_mm_1d=axes,
        dose_eval=dose,
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        norm='global_max',
        shift_spec='x:0:0:1,y:0:0:1,z:0:0:1',
        refine=False,
        prescan_2d=False,
        engine='pymedphys',
        interp_fraction=7,
    )

    assert selected_engines == ['pymedphys']
    assert interpolation_fractions == [7]


def test_shift_optimization_logs_prescan_evaluations(monkeypatch):
    axes, dose = _case()

    def fake_compute_gamma(*args, **kwargs):
        return np.zeros_like(dose), 50.0, {'valid_points': dose.size}

    monkeypatch.setattr('rtgamma.optimize.compute_gamma', fake_compute_gamma)
    _, _, extras = grid_search_best_shift(
        ref_axes_mm_1d=axes,
        dose_ref=dose,
        eval_axes_mm_1d=axes,
        dose_eval=dose,
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        norm='global_max',
        shift_spec='x:-1:1:1,y:-1:1:1,z:0:0:1',
        refine=False,
        prescan_2d=True,
        engine='pymedphys',
        interp_fraction=1,
    )

    search_log = extras['search_log']
    assert [entry['type'] for entry in search_log].count('prescan_2d') == 9
    assert [entry['type'] for entry in search_log].count('coarse') == 9
    assert len(search_log) == 18
