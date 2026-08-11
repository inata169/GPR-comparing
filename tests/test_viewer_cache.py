import json

import numpy as np

from rtgamma.gamma import gamma_engine_version
from rtgamma.provenance import sha256_file
from rtgamma.viewer_cache import load_validated_gamma_cache


def _settings(engine="pymedphys"):
    return {
        "gamma_engine": engine,
        "gamma_engine_version": gamma_engine_version(engine),
        "dd_percent": 3.0,
        "dta_mm": 2.0,
        "cutoff_percent": 10.0,
        "gamma_type": "global",
        "norm": "global_max",
        "interp_fraction": 10,
        "opt_shift": False,
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
                    "analysis": {
                        "gamma": {"opt_shift": report_settings["opt_shift"]}
                    },
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
        ref_source_sha256=sha256_file(ref),
        eval_source_sha256=sha256_file(evaluation),
    )

    np.testing.assert_array_equal(gamma, np.full((1, 2, 2), 0.5))


def test_validated_gamma_cache_rejects_engine_change(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings("pymedphys"))

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings("numba"),
        ref_source_sha256=sha256_file(ref),
        eval_source_sha256=sha256_file(evaluation),
    )

    assert gamma is None


def test_validated_gamma_cache_uses_loaded_digest_after_path_change(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings())
    ref_digest = sha256_file(ref)
    evaluation_digest = sha256_file(evaluation)
    evaluation.write_bytes(b"changed evaluation")

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings(),
        ref_source_sha256=ref_digest,
        eval_source_sha256=evaluation_digest,
    )

    np.testing.assert_array_equal(gamma, np.full((1, 2, 2), 0.5))


def test_validated_gamma_cache_rejects_loaded_digest_mismatch(tmp_path):
    ref, evaluation, npz, report = _write_cache(tmp_path, _settings())

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=_settings(),
        ref_source_sha256=sha256_file(ref),
        eval_source_sha256="0" * 64,
    )

    assert gamma is None


def test_validated_gamma_cache_rejects_shift_policy_change(tmp_path):
    settings = _settings()
    ref, evaluation, npz, report = _write_cache(tmp_path, settings)
    selected = {**settings, "opt_shift": True}

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=selected,
        ref_source_sha256=sha256_file(ref),
        eval_source_sha256=sha256_file(evaluation),
    )

    assert gamma is None


def test_validated_gamma_cache_rejects_engine_version_change(tmp_path):
    settings = _settings("numba")
    ref, evaluation, npz, report = _write_cache(tmp_path, settings)
    selected = {**settings, "gamma_engine_version": "future-numba"}

    gamma = load_validated_gamma_cache(
        str(npz),
        str(report),
        expected_settings=selected,
        ref_source_sha256=sha256_file(ref),
        eval_source_sha256=sha256_file(evaluation),
    )

    assert gamma is None
