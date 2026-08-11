#!/usr/bin/env python
"""Compare Numba and PyMedPhys gamma maps for one RTDOSE pair.

This follows the current no-shift 2D CLI path and writes only local numerical
artifacts. It does not copy DICOM data or emit DICOM demographics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rtgamma.gamma import compute_gamma  # noqa: E402
from rtgamma.io_dicom import load_rtdose, world_to_index  # noqa: E402
from rtgamma.main import build_plane_world_coords  # noqa: E402
from rtgamma.resample import resample_eval_onto_ref  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _selected_slice(dose: np.ndarray, plane: str, index: int) -> np.ndarray:
    if plane == "axial":
        return dose[index:index + 1, :, :]
    if plane == "sagittal":
        return dose[:, :, index:index + 1]
    return dose[:, index:index + 1, :]


def _resolve_index(shape: tuple[int, ...], plane: str, value: str) -> int:
    axis_size = {
        "axial": shape[0],
        "sagittal": shape[2],
        "coronal": shape[1],
    }[plane]
    index = axis_size // 2 if value.lower() == "auto" else int(value)
    if index < 0 or index >= axis_size:
        raise ValueError(f"plane index {index} is outside 0..{axis_size - 1}")
    return index


def _numeric_stats(values: np.ndarray) -> dict:
    if values.size == 0:
        return {
            "mean": None,
            "median": None,
            "p95": None,
            "p99": None,
            "max_abs": None,
        }
    absolute = np.abs(values)
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p95": float(np.percentile(absolute, 95)),
        "p99": float(np.percentile(absolute, 99)),
        "max_abs": float(np.max(absolute)),
    }


def compare_gamma_maps(
    gamma_numba: np.ndarray,
    gamma_pymedphys: np.ndarray,
    axes_mm: tuple[np.ndarray, ...],
    coordinate_limit: int = 100,
) -> tuple[dict, dict]:
    if gamma_numba.shape != gamma_pymedphys.shape:
        raise ValueError("Gamma map shapes differ")

    finite_numba = np.isfinite(gamma_numba)
    finite_pymedphys = np.isfinite(gamma_pymedphys)
    common = finite_numba & finite_pymedphys
    finite_union = finite_numba | finite_pymedphys
    difference = np.full(gamma_numba.shape, np.nan, dtype=np.float64)
    difference[common] = gamma_numba[common] - gamma_pymedphys[common]

    pass_numba = common & (gamma_numba <= 1.0)
    pass_pymedphys = common & (gamma_pymedphys <= 1.0)
    disagreements = common & (pass_numba != pass_pymedphys)
    disagreement_indices = np.argwhere(disagreements)

    coordinates = []
    for index in disagreement_indices[:coordinate_limit]:
        index_tuple = tuple(int(value) for value in index)
        coordinates.append(
            {
                "index_kji": list(index_tuple),
                "axis_coordinates_mm": [
                    float(axes_mm[dimension][index_tuple[dimension]])
                    for dimension in range(len(index_tuple))
                ],
                "gamma_numba": float(gamma_numba[index_tuple]),
                "gamma_pymedphys": float(gamma_pymedphys[index_tuple]),
            }
        )

    common_indices = np.argwhere(common)
    if len(common_indices):
        common_differences = difference[common]
        largest_order = np.argsort(np.abs(common_differences))[::-1]
    else:
        common_differences = np.array([], dtype=float)
        largest_order = np.array([], dtype=int)
    largest_difference_coordinates = []
    for position in largest_order[:coordinate_limit]:
        index_tuple = tuple(int(value) for value in common_indices[position])
        signed_difference = float(common_differences[position])
        largest_difference_coordinates.append(
            {
                "index_kji": list(index_tuple),
                "axis_coordinates_mm": [
                    float(axes_mm[dimension][index_tuple[dimension]])
                    for dimension in range(len(index_tuple))
                ],
                "gamma_numba": float(gamma_numba[index_tuple]),
                "gamma_pymedphys": float(gamma_pymedphys[index_tuple]),
                "difference_numba_minus_pymedphys": signed_difference,
                "absolute_difference": abs(signed_difference),
            }
        )

    common_count = int(np.sum(common))
    summary = {
        "shape": list(gamma_numba.shape),
        "mask": {
            "numba_finite": int(np.sum(finite_numba)),
            "pymedphys_finite": int(np.sum(finite_pymedphys)),
            "common_finite": common_count,
            "finite_union": int(np.sum(finite_union)),
            "numba_only": int(np.sum(finite_numba & ~finite_pymedphys)),
            "pymedphys_only": int(np.sum(finite_pymedphys & ~finite_numba)),
        },
        "gpr_on_common_mask": {
            "numba": (
                float(np.sum(pass_numba) / common_count * 100.0)
                if common_count else None
            ),
            "pymedphys": (
                float(np.sum(pass_pymedphys) / common_count * 100.0)
                if common_count else None
            ),
        },
        "gamma_difference_numba_minus_pymedphys": _numeric_stats(difference[common]),
        "pass_fail_confusion_on_common_mask": {
            "both_pass": int(np.sum(pass_numba & pass_pymedphys)),
            "numba_pass_pymedphys_fail": int(np.sum(pass_numba & ~pass_pymedphys)),
            "numba_fail_pymedphys_pass": int(np.sum(~pass_numba & pass_pymedphys & common)),
            "both_fail": int(np.sum(~pass_numba & ~pass_pymedphys & common)),
            "total_disagreements": int(len(disagreement_indices)),
        },
        "first_disagreement_coordinates": coordinates,
        "coordinate_list_truncated": bool(len(disagreement_indices) > coordinate_limit),
        "largest_gamma_difference_coordinates": largest_difference_coordinates,
        "largest_difference_list_truncated": bool(common_count > coordinate_limit),
    }
    arrays = {
        "gamma_numba": gamma_numba,
        "gamma_pymedphys": gamma_pymedphys,
        "gamma_difference_numba_minus_pymedphys": difference,
        "common_finite_mask": common,
        "pass_fail_disagreement_mask": disagreements,
        "disagreement_indices_kji": disagreement_indices,
    }
    return summary, arrays


def run_comparison(args: argparse.Namespace) -> dict:
    ref_path = Path(args.ref).resolve()
    eval_path = Path(args.eval).resolve()
    output_dir = Path(args.out).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    meta_ref = load_rtdose(str(ref_path))
    meta_eval = load_rtdose(str(eval_path))
    dose_ref = meta_ref["dose"]
    dose_eval = meta_eval["dose"]
    plane_index = _resolve_index(dose_ref.shape, args.plane, args.plane_index)
    (world_x, world_y, world_z), axes_mm = build_plane_world_coords(
        meta_ref,
        args.plane,
        plane_index,
    )

    def world_to_eval_ijk(points):
        return world_to_index(
            meta_eval["ipp"],
            meta_eval["v_col"],
            meta_eval["v_row"],
            meta_eval["v_slice"],
            meta_eval["s_col"],
            meta_eval["s_row"],
            meta_eval["z_offsets"],
            points,
        )

    eval_on_ref_slice = resample_eval_onto_ref(
        dose_eval,
        world_to_eval_ijk,
        (world_x, world_y, world_z),
        interp=args.resample_interp,
        shift_mm=(0.0, 0.0, 0.0),
    )
    ref_slice = _selected_slice(dose_ref, args.plane, plane_index)
    normalisation_override = (
        float(np.nanmax(dose_ref))
        if args.norm in ("global_max", "max_ref")
        else None
    )

    engine_results = {}
    gamma_maps = {}
    for engine in ("numba", "pymedphys"):
        started = time.perf_counter()
        gamma_map, pass_rate, stats = compute_gamma(
            axes_ref_mm=axes_mm,
            dose_ref=ref_slice,
            axes_eval_mm=axes_mm,
            dose_eval=eval_on_ref_slice,
            dd_percent=args.dd,
            dta_mm=args.dta,
            cutoff_percent=args.cutoff,
            gamma_type=args.gamma_type,
            norm=args.norm,
            norm_factor_override=normalisation_override,
            interp_fraction=args.interp_fraction,
            engine=engine,
        )
        elapsed = time.perf_counter() - started
        gamma_maps[engine] = gamma_map
        engine_results[engine] = {
            "version": stats["gamma_engine_version"],
            "pass_rate_percent": pass_rate,
            "valid_points": stats["valid_points"],
            "gamma_mean": stats["gamma_mean"],
            "gamma_median": stats["gamma_median"],
            "gamma_p95": stats["gamma_p95"],
            "gamma_p99": stats["gamma_p99"],
            "gamma_max": stats["gamma_max"],
            "elapsed_seconds_cold_process": elapsed,
        }

    comparison, arrays = compare_gamma_maps(
        gamma_maps["numba"],
        gamma_maps["pymedphys"],
        axes_mm,
        coordinate_limit=args.coordinate_limit,
    )
    if args.gamma_type == "global":
        dose_denominator = normalisation_override * args.dd / 100.0
        zero_distance_gamma = np.abs(eval_on_ref_slice - ref_slice) / dose_denominator
    else:
        dose_denominator = np.abs(ref_slice) * args.dd / 100.0
        zero_distance_gamma = np.full(ref_slice.shape, np.nan, dtype=np.float64)
        nonzero = dose_denominator > 1e-12
        zero_distance_gamma[nonzero] = (
            np.abs(eval_on_ref_slice[nonzero] - ref_slice[nonzero])
            / dose_denominator[nonzero]
        )
    diagnostic_mask = (
        np.isfinite(zero_distance_gamma)
        & np.isfinite(gamma_maps["numba"])
        & np.isfinite(gamma_maps["pymedphys"])
    )
    numba_matches_zero = diagnostic_mask & np.isclose(
        gamma_maps["numba"],
        zero_distance_gamma,
        rtol=1e-5,
        atol=1e-6,
    )
    pymedphys_lower = diagnostic_mask & (
        gamma_maps["pymedphys"] < gamma_maps["numba"] - 1e-6
    )
    diagnostic_count = int(np.sum(diagnostic_mask))
    comparison["zero_distance_diagnostic"] = {
        "points": diagnostic_count,
        "numba_matches_zero_distance_gamma": int(np.sum(numba_matches_zero)),
        "numba_matches_zero_distance_percent": (
            float(np.sum(numba_matches_zero) / diagnostic_count * 100.0)
            if diagnostic_count else None
        ),
        "pymedphys_lower_than_numba": int(np.sum(pymedphys_lower)),
        "pymedphys_lower_than_numba_percent": (
            float(np.sum(pymedphys_lower) / diagnostic_count * 100.0)
            if diagnostic_count else None
        ),
        "numba_zero_match_and_pymedphys_lower": int(
            np.sum(numba_matches_zero & pymedphys_lower)
        ),
        "interpretation_limit": (
            "This characterizes the observed maps; it does not by itself prove "
            "the implementation cause."
        ),
    }
    arrays["dose_ref_slice"] = ref_slice
    arrays["dose_eval_on_ref_slice"] = eval_on_ref_slice
    arrays["zero_distance_gamma"] = zero_distance_gamma
    for dimension, axis in enumerate(axes_mm):
        arrays[f"axis_{dimension}_mm"] = axis

    report = {
        "status": "preliminary_characterization_not_acceptance",
        "inputs": {
            "reference": {"basename": ref_path.name, "sha256": _sha256(ref_path)},
            "evaluation": {"basename": eval_path.name, "sha256": _sha256(eval_path)},
        },
        "settings": {
            "mode": "2d",
            "plane": args.plane,
            "plane_index": plane_index,
            "dd_percent": args.dd,
            "dta_mm": args.dta,
            "cutoff_percent": args.cutoff,
            "gamma_type": args.gamma_type,
            "norm": args.norm,
            "resolved_normalisation": normalisation_override,
            "interp_fraction": args.interp_fraction,
            "resample_interp": args.resample_interp,
            "opt_shift": "off",
        },
        "engines": engine_results,
        "comparison": comparison,
        "timing_note": "Cold-process timings include engine import and any JIT compilation.",
        "array_file": "gamma_map_comparison.npz",
    }
    np.savez_compressed(output_dir / "gamma_map_comparison.npz", **arrays)
    (output_dir / "gamma_map_comparison.json").write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--eval", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--plane", choices=["axial", "sagittal", "coronal"], default="axial")
    parser.add_argument("--plane-index", default="auto")
    parser.add_argument("--dd", type=float, default=3.0)
    parser.add_argument("--dta", type=float, default=2.0)
    parser.add_argument("--cutoff", type=float, default=10.0)
    parser.add_argument("--gamma-type", choices=["global", "local"], default="global")
    parser.add_argument("--norm", choices=["global_max", "max_ref"], default="global_max")
    parser.add_argument("--interp-fraction", type=int, default=10)
    parser.add_argument(
        "--resample-interp",
        choices=["linear", "bspline", "nearest"],
        default="linear",
    )
    parser.add_argument("--coordinate-limit", type=int, default=100)
    args = parser.parse_args()
    report = run_comparison(args)
    comparison = report["comparison"]
    print(
        json.dumps(
            {
                "numba_gpr": comparison["gpr_on_common_mask"]["numba"],
                "pymedphys_gpr": comparison["gpr_on_common_mask"]["pymedphys"],
                "mask": comparison["mask"],
                "gamma_difference": comparison["gamma_difference_numba_minus_pymedphys"],
                "pass_fail": comparison["pass_fail_confusion_on_common_mask"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
