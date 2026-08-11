"""Validation helpers for Gamma maps auto-loaded by the GUI viewers."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from .provenance import sha256_file

_SETTING_KEYS = (
    "gamma_engine",
    "dd_percent",
    "dta_mm",
    "cutoff_percent",
    "gamma_type",
    "norm",
    "interp_fraction",
)


def _same_setting(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        try:
            return bool(np.isclose(float(actual), expected, rtol=0.0, atol=1e-12))
        except (TypeError, ValueError):
            return False
    return actual == expected


def load_validated_gamma_cache(
    npz_path: str,
    report_path: str,
    *,
    expected_settings: dict[str, Any],
    ref_source_path: str,
    eval_source_path: str,
    logger: logging.Logger | None = None,
) -> np.ndarray | None:
    """Load a GUI-discovered cache only when its report matches this run."""
    log = logger or logging.getLogger(__name__)
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
        for key in _SETTING_KEYS:
            if not _same_setting(report.get(key), expected_settings[key]):
                log.warning(
                    "Ignoring stale Gamma cache: %s differs (report=%r, selected=%r)",
                    key,
                    report.get(key),
                    expected_settings[key],
                )
                return None

        inputs = report["provenance"]["inputs"]
        expected_hashes = {
            "reference": sha256_file(ref_source_path),
            "evaluation": sha256_file(eval_source_path),
        }
        for name, expected_hash in expected_hashes.items():
            if inputs[name].get("sha256") != expected_hash:
                log.warning("Ignoring stale Gamma cache: %s RTDOSE differs", name)
                return None

        with np.load(npz_path) as npz:
            if "gamma" not in npz:
                log.warning("Gamma NPZ has no 'gamma' key: %s", npz_path)
                return None
            return np.asarray(npz["gamma"])
    except Exception as exc:
        log.warning("Ignoring unverified Gamma cache '%s': %s", npz_path, exc)
        return None
