"""Validation helpers for Gamma maps auto-loaded by the GUI viewers."""
from __future__ import annotations

import hashlib
import io
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

_SETTING_PATHS = {
    "gamma_engine": ("gamma_engine",),
    "gamma_engine_version": ("gamma_engine_version",),
    "dd_percent": ("dd_percent",),
    "dta_mm": ("dta_mm",),
    "cutoff_percent": ("cutoff_percent",),
    "gamma_type": ("gamma_type",),
    "norm": ("norm",),
    "interp_fraction": ("interp_fraction",),
    "opt_shift": ("provenance", "analysis", "opt_shift_requested"),
}

_SHIFT_SEARCH_SETTING_PATHS = {
    "shift_range": ("provenance", "analysis", "gamma", "shift_range"),
    "refine": ("provenance", "analysis", "gamma", "refine"),
    "fine_range_mm": ("provenance", "analysis", "gamma", "fine_range_mm"),
    "fine_step_mm": ("provenance", "analysis", "gamma", "fine_step_mm"),
    "early_stop_epsilon": (
        "provenance",
        "analysis",
        "gamma",
        "early_stop_epsilon",
    ),
    "early_stop_patience": (
        "provenance",
        "analysis",
        "gamma",
        "early_stop_patience",
    ),
    "prescan_2d": ("provenance", "analysis", "gamma", "prescan_2d"),
}


def _same_setting(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        try:
            return bool(np.isclose(float(actual), expected, rtol=0.0, atol=1e-12))
        except (TypeError, ValueError):
            return False
    return actual == expected


def _nested_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def load_validated_gamma_cache(
    npz_path: str,
    report_path: str,
    *,
    expected_settings: dict[str, Any],
    ref_source_sha256: str,
    eval_source_sha256: str,
    logger: logging.Logger | None = None,
) -> np.ndarray | None:
    """Load a GUI-discovered cache only when its report matches this run."""
    log = logger or logging.getLogger(__name__)
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
        for key, path in _SETTING_PATHS.items():
            actual = _nested_value(report, path)
            if not _same_setting(actual, expected_settings[key]):
                log.warning(
                    "Ignoring stale Gamma cache: %s differs (report=%r, selected=%r)",
                    key,
                    actual,
                    expected_settings[key],
                )
                return None

        analysis = report["provenance"]["analysis"]
        opt_shift_requested = analysis["opt_shift_requested"]
        opt_shift_effective = analysis["gamma"]["opt_shift"]
        identity_shortcut = analysis["identity_comparison_shortcut"]
        valid_shift_state = (
            (not opt_shift_requested and not opt_shift_effective and not identity_shortcut)
            or (opt_shift_requested and opt_shift_effective and not identity_shortcut)
            or (opt_shift_requested and not opt_shift_effective and identity_shortcut)
        )
        if not valid_shift_state:
            log.warning("Ignoring stale Gamma cache: inconsistent shift provenance")
            return None
        if opt_shift_effective:
            for key, path in _SHIFT_SEARCH_SETTING_PATHS.items():
                actual = _nested_value(report, path)
                if not _same_setting(actual, expected_settings[key]):
                    log.warning(
                        "Ignoring stale Gamma cache: %s differs "
                        "(report=%r, selected=%r)",
                        key,
                        actual,
                        expected_settings[key],
                    )
                    return None

        inputs = report["provenance"]["inputs"]
        expected_hashes = {
            "reference": ref_source_sha256,
            "evaluation": eval_source_sha256,
        }
        for name, expected_hash in expected_hashes.items():
            if inputs[name].get("sha256") != expected_hash:
                log.warning("Ignoring stale Gamma cache: %s RTDOSE differs", name)
                return None
        if identity_shortcut and ref_source_sha256 != eval_source_sha256:
            log.warning(
                "Ignoring stale Gamma cache: identity shortcut inputs differ"
            )
            return None

        npz_bytes = Path(npz_path).read_bytes()
        actual_npz_sha256 = hashlib.sha256(npz_bytes).hexdigest()
        if report.get("save_gamma_map_sha256") != actual_npz_sha256:
            log.warning("Ignoring stale Gamma cache: NPZ digest differs from report")
            return None

        with np.load(io.BytesIO(npz_bytes)) as npz:
            if "gamma" not in npz:
                log.warning("Gamma NPZ has no 'gamma' key: %s", npz_path)
                return None
            return np.asarray(npz["gamma"])
    except Exception as exc:
        log.warning("Ignoring unverified Gamma cache '%s': %s", npz_path, exc)
        return None
