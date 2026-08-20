from types import SimpleNamespace

import numpy as np
import pytest

from rtgamma.io_dicom import RTDoseGeometryError
from rtgamma.provenance import sha256_file
from scripts.compare_gamma_engine_maps import (
    _input_identity,
    _write_strict_json,
    compare_gamma_maps,
    run_comparison,
)


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


def test_run_comparison_rejects_dose_unit_mismatch(monkeypatch, tmp_path):
    loaded = iter([
        {'units': 'GY'},
        {'units': 'RELATIVE'},
    ])
    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.load_rtdose',
        lambda _path: next(loaded),
    )
    args = SimpleNamespace(
        ref='reference.dcm',
        eval='evaluation.dcm',
        out=str(tmp_path / 'comparison'),
    )

    with pytest.raises(RTDoseGeometryError, match='DoseUnits mismatch'):
        run_comparison(args)


def test_run_comparison_passes_original_projected_evaluation_extent(
    monkeypatch,
    tmp_path,
):
    dose = np.ones((1, 2, 3), dtype=float)
    axes = (
        np.array([0.0]),
        np.array([0.0, 1.0]),
        np.array([0.0, 1.0, 2.0]),
    )
    reference = {
        'dose': dose,
        'ipp': np.array([0.0, 0.0, 0.0]),
        'v_slice': np.array([0.0, 0.0, 1.0]),
        'v_row': np.array([0.0, 1.0, 0.0]),
        'v_col': np.array([1.0, 0.0, 0.0]),
        'z_coords_mm': axes[0],
        'y_coords_mm': axes[1],
        'x_coords_mm': axes[2],
        'source_path': 'reference.dcm',
        'source_sha256': '1' * 64,
    }
    evaluation = {
        **reference,
        'ipp': np.array([1.0, -2.0, 3.0]),
        'source_path': 'evaluation.dcm',
        'source_sha256': '2' * 64,
    }
    loaded = iter([reference, evaluation])
    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.load_rtdose',
        lambda _path: next(loaded),
    )
    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.validate_rtdose_pair_geometry',
        lambda *_args, **_kwargs: 1.0,
    )
    world = tuple(np.zeros(dose.shape, dtype=float) for _ in range(3))
    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.build_plane_world_coords',
        lambda *_args, **_kwargs: (world, axes),
    )
    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.resample_eval_onto_ref',
        lambda *_args, **_kwargs: dose.copy(),
    )
    captured_domains = []

    def fake_compute_gamma(**kwargs):
        captured_domains.append(kwargs['evaluation_domain_axes_mm'])
        stats = {
            'gamma_engine_version': 'test',
            'valid_points': dose.size,
            'gamma_mean': 0.0,
            'gamma_median': 0.0,
            'gamma_p95': 0.0,
            'gamma_p99': 0.0,
            'gamma_max': 0.0,
        }
        return np.zeros_like(dose), 100.0, stats

    monkeypatch.setattr(
        'scripts.compare_gamma_engine_maps.compute_gamma',
        fake_compute_gamma,
    )
    args = SimpleNamespace(
        ref='reference.dcm',
        eval='evaluation.dcm',
        out=str(tmp_path / 'comparison'),
        plane='axial',
        plane_index='0',
        resample_interp='linear',
        norm='global_max',
        dd=3.0,
        dta=2.0,
        cutoff=10.0,
        gamma_type='global',
        interp_fraction=1,
        coordinate_limit=10,
    )

    run_comparison(args)

    assert len(captured_domains) == 2
    expected_domain = (axes[0] + 3.0, axes[1] - 2.0, axes[2] + 1.0)
    for domain in captured_domains:
        for actual, expected in zip(domain, expected_domain):
            np.testing.assert_array_equal(actual, expected)


def test_input_identity_hashes_resolved_rtdose_not_directory(tmp_path):
    input_dir = tmp_path / "dose-directory"
    input_dir.mkdir()
    resolved = input_dir / "selected-rtdose.dcm"
    resolved.write_bytes(b"resolved dose bytes")

    loaded_digest = sha256_file(resolved)
    metadata = {
        "source_path": str(resolved),
        "source_sha256": loaded_digest,
    }
    resolved.write_bytes(b"replacement after load")

    identity = _input_identity(input_dir, metadata)

    assert identity["basename"] == resolved.name
    assert identity["sha256"] == loaded_digest
    assert identity["sha256"] != sha256_file(resolved)


def test_write_strict_json_replaces_nonfinite_values(tmp_path):
    output = tmp_path / "comparison.json"

    _write_strict_json(output, {"mean": float("nan"), "maximum": float("inf")})

    assert output.read_text(encoding="utf-8") == (
        '{\n  "mean": null,\n  "maximum": null\n}'
    )
