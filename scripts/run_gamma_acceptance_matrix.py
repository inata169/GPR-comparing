#!/usr/bin/env python
"""Run a fixed multi-slice global/local gamma-engine comparison matrix.

The generated artifacts are intended for local research characterization. Input
paths are accepted only on the command line and are not written to the report;
the per-run reports retain only basenames and SHA-256 digests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compare_gamma_engine_maps import run_comparison  # noqa: E402


def summarize_runs(runs: list[dict]) -> dict:
    """Summarize mask and pass/fail observations without approving thresholds."""
    total_common = 0
    total_disagreements = 0
    exact_mask_runs = 0
    by_gamma_type: dict[str, dict[str, int]] = {}

    for run in runs:
        comparison = run["report"]["comparison"]
        mask = comparison["mask"]
        confusion = comparison["pass_fail_confusion_on_common_mask"]
        common = int(mask["common_finite"])
        disagreements = int(confusion["total_disagreements"])
        total_common += common
        total_disagreements += disagreements
        if mask["numba_only"] == 0 and mask["pymedphys_only"] == 0:
            exact_mask_runs += 1

        gamma_type = run["gamma_type"]
        bucket = by_gamma_type.setdefault(
            gamma_type,
            {"runs": 0, "common_points": 0, "pass_fail_disagreements": 0},
        )
        bucket["runs"] += 1
        bucket["common_points"] += common
        bucket["pass_fail_disagreements"] += disagreements

    for bucket in by_gamma_type.values():
        common = bucket["common_points"]
        bucket["pass_fail_disagreement_percent"] = (
            bucket["pass_fail_disagreements"] / common * 100.0
            if common
            else None
        )

    return {
        "run_count": len(runs),
        "exact_finite_mask_run_count": exact_mask_runs,
        "all_runs_have_exact_finite_masks": exact_mask_runs == len(runs),
        "common_points": total_common,
        "pass_fail_disagreements": total_disagreements,
        "pass_fail_disagreement_percent": (
            total_disagreements / total_common * 100.0
            if total_common
            else None
        ),
        "by_gamma_type": by_gamma_type,
    }


def _run_matrix(args: argparse.Namespace) -> dict:
    output_root = Path(args.out).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    runs = []

    for case_label, ref_value, eval_value in args.pair:
        ref_path = Path(ref_value).resolve()
        eval_path = Path(eval_value).resolve()
        pair_label = f"{case_label}_{eval_path.stem}"
        for gamma_type in args.gamma_types:
            for plane_index in args.plane_indices:
                relative_output = Path(pair_label) / gamma_type / f"axial_{plane_index}"
                comparison_args = SimpleNamespace(
                    ref=str(ref_path),
                    eval=str(eval_path),
                    out=str(output_root / relative_output),
                    plane="axial",
                    plane_index=str(plane_index),
                    dd=args.dd,
                    dta=args.dta,
                    cutoff=args.cutoff,
                    gamma_type=gamma_type,
                    norm=args.norm,
                    interp_fraction=args.interp_fraction,
                    resample_interp=args.resample_interp,
                    coordinate_limit=args.coordinate_limit,
                )
                report = run_comparison(comparison_args)
                runs.append(
                    {
                        "case_label": case_label,
                        "evaluation_label": eval_path.stem,
                        "gamma_type": gamma_type,
                        "plane": "axial",
                        "plane_index": plane_index,
                        "result_directory": relative_output.as_posix(),
                        "report": report,
                    }
                )

    summary = {
        "schema_version": 1,
        "status": "characterization_complete_threshold_approval_pending",
        "purpose": "PyMedPhys standard-engine migration acceptance characterization",
        "protocol": {
            "plane": "axial",
            "plane_indices": args.plane_indices,
            "gamma_types": args.gamma_types,
            "dd_percent": args.dd,
            "dta_mm": args.dta,
            "cutoff_percent": args.cutoff,
            "norm": args.norm,
            "interp_fraction": args.interp_fraction,
            "resample_interp": args.resample_interp,
            "opt_shift": "off",
        },
        "aggregate": summarize_runs(runs),
        "interpretation": (
            "This report records observations only. Numerical acceptance thresholds "
            "and the final default-engine switch require explicit approval."
        ),
        "runs": runs,
    }
    (output_root / "acceptance_matrix_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        nargs=3,
        action="append",
        required=True,
        metavar=("LABEL", "REFERENCE", "EVALUATION"),
        help="Repeat for each reference/evaluation pair.",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--plane-indices", nargs="+", type=int, default=[74, 75, 76])
    parser.add_argument(
        "--gamma-types",
        nargs="+",
        choices=["global", "local"],
        default=["global", "local"],
    )
    parser.add_argument("--dd", type=float, default=3.0)
    parser.add_argument("--dta", type=float, default=2.0)
    parser.add_argument("--cutoff", type=float, default=10.0)
    parser.add_argument("--norm", choices=["global_max", "max_ref"], default="global_max")
    parser.add_argument("--interp-fraction", type=int, default=10)
    parser.add_argument(
        "--resample-interp",
        choices=["linear", "bspline", "nearest"],
        default="linear",
    )
    parser.add_argument("--coordinate-limit", type=int, default=100)
    args = parser.parse_args()

    summary = _run_matrix(args)
    print(json.dumps(summary["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
