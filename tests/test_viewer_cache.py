import json

import numpy as np

from rtgamma.provenance import sha256_file
from rtgamma.viewer_cache import load_validated_gamma_cache


def _settings(engine="pymedphys"):
    return {
        "gamma_engine": engine,
        "dd_percent": 3.0,
        "dta_mm": 2.0,
        "cutoff_percent": 10.0,
        "gamma_type": "global",
        "norm": "global_max",
        "interp_fraction": 10,
    }


def _write_cache(tmp_path, report_settings):
    ref = tmp_path / "reference.dcm"
    evaluation = tmp_path / "evaluation.dcm"
    ref.write_bytes(b"reference")
    evaluation.write_bytes(b"evaluation")
    npz = tmp_path / "gamma3d.npz"
    np.savez_compressed(npz, gamma=np.full((1, 2, 2), 0.5))
    report = tmp_path / "run3d.json"
    report.write_text(
        json.dumps(
            {
                **report_settings,
                "provenance": {
                    "inputs": {
                        "reference": {"sha256": sha256_file(ref)},
                        "evaluation": {"sha256": sha256_file(evaluation)},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return ref, evaluation, npz, report


def test_validated_gamma_cache_loads_matching_report(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings())

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings(),
        ref_source_path=str(ref),
        eval_source_path=str(evaluation),
    )

    np.testing.assert_array_equal(gamma, np.full((1, 2, 2), 0.5))


def test_validated_gamma_cache_rejects_engine_change(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings("pymedphys"))

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings("numba"),
        ref_source_path=str(ref),
        eval_source_path=str(evaluation),
    )

    assert gamma is None


def test_validated_gamma_cache_rejects_input_change(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings())
    evaluation.write_bytes(b"changed evaluation")

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings(),
        ref_source_path=str(ref),
        eval_source_path=str(evaluation),
    )

    assert gamma is None
