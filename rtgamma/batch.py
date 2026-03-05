"""Batch processing module for rtgamma.

Reads a CSV file where each row defines one ref/eval pair and optional
analysis parameters, runs gamma analysis for every row, and produces
an aggregated summary (CSV + Markdown).
"""

import csv
import json
import logging
import os
import sys
import traceback
from typing import Dict, List

from .main import main as run_gamma

# ---- CSV column spec ----
# Required: ref, eval
# Optional (override per row):
#   patient_id, rtstruct, roi, dta_mm, dd_percent, cutoff_percent,
#   gamma_type, norm, opt_shift, interp_fraction, mode, report_dir
# Blank cells fall back to CLI defaults.

_DEFAULTS = {
    'dta_mm': '2.0',
    'dd_percent': '3.0',
    'cutoff_percent': '10.0',
    'gamma_type': 'global',
    'norm': 'global_max',
    'opt_shift': 'on',
    'interp_fraction': '10',
    'mode': '3d',
}


def _build_argv(row: Dict[str, str], output_dir: str) -> List[str]:
    """Convert a CSV row dict into an argv list for ``run_gamma``."""
    argv: List[str] = []

    argv += ['--ref', row['ref']]
    argv += ['--eval', row['eval']]

    # Optional overrides (use row value or default)
    dta = row.get('dta_mm', '').strip() or _DEFAULTS['dta_mm']
    dd = row.get('dd_percent', '').strip() or _DEFAULTS['dd_percent']
    cutoff = row.get('cutoff_percent', '').strip() or _DEFAULTS['cutoff_percent']
    gamma_type = row.get('gamma_type', '').strip() or _DEFAULTS['gamma_type']
    norm = row.get('norm', '').strip() or _DEFAULTS['norm']
    opt_shift = row.get('opt_shift', '').strip() or _DEFAULTS['opt_shift']
    interp_fraction = row.get('interp_fraction', '').strip() or _DEFAULTS['interp_fraction']
    mode = row.get('mode', '').strip() or _DEFAULTS['mode']

    argv += ['--dta', dta]
    argv += ['--dd', dd]
    argv += ['--cutoff', cutoff]
    argv += ['--gamma-type', gamma_type]
    argv += ['--norm', norm]
    argv += ['--opt-shift', opt_shift]
    argv += ['--interp-fraction', interp_fraction]
    argv += ['--mode', mode]

    pdf = row.get('pdf', '').strip().lower()
    if pdf == 'true' or pdf == '1' or pdf == 'yes':
        argv += ['--pdf']

    # RTSTRUCT / ROI
    rtstruct = row.get('rtstruct', '').strip()
    if rtstruct:
        argv += ['--rtstruct', rtstruct]
    roi = row.get('roi', '').strip()
    if roi:
        for r in roi.split(';'):
            r = r.strip()
            if r:
                argv += ['--roi', r]

    # Per-row report output
    patient_id = row.get('patient_id', '').strip()
    if not patient_id:
        # Derive from ref filename
        patient_id = os.path.splitext(os.path.basename(row['ref']))[0]
    report_base = os.path.join(output_dir, patient_id)
    os.makedirs(os.path.dirname(report_base) or output_dir, exist_ok=True)
    argv += ['--report', report_base]

    return argv, patient_id


def run_batch(csv_path: str, output_dir: str, pdf: bool = False) -> Dict:
    """Run batch gamma analysis from a CSV definition file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file defining analysis pairs.
    output_dir : str
        Directory for per-patient reports and the aggregated summary.
    pdf : bool
        Whether to generate PDF reports for all rows.

    Returns
    -------
    dict with keys:
        results : list of dicts (one per row)
        errors  : list of dicts (rows that failed)
        summary_path : str (path to the summary CSV)
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    results: List[Dict] = []
    errors: List[Dict] = []

    logging.info(f"Batch: {total} pairs loaded from {csv_path}")

    for idx, row in enumerate(rows, 1):
        if pdf and 'pdf' not in row:
            row['pdf'] = 'true'

        ref_path = row.get('ref', '').strip()
        eval_path = row.get('eval', '').strip()
        if not ref_path or not eval_path:
            msg = f"[{idx}/{total}] Skipped: missing ref or eval path."
            logging.warning(msg)
            errors.append({'index': idx, 'patient_id': row.get('patient_id', ''), 'error': msg})
            continue

        try:
            argv, patient_id = _build_argv(row, output_dir)
            logging.info(f"[{idx}/{total}] Processing {patient_id} ...")
            summary = run_gamma(argv)
            summary['patient_id'] = patient_id
            summary['batch_index'] = idx
            summary['status'] = 'OK'
            results.append(summary)
            gpr = summary.get('pass_rate_percent', 'N/A')
            logging.info(f"[{idx}/{total}] {patient_id} done. GPR={gpr}")
        except SystemExit:
            # argparse may call sys.exit on error
            msg = f"Argument parsing failed for row {idx}"
            logging.error(f"[{idx}/{total}] ERROR: {msg}")
            errors.append({'index': idx, 'patient_id': row.get('patient_id', ''), 'error': msg})
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logging.error(f"[{idx}/{total}] ERROR: {msg}")
            logging.debug(traceback.format_exc())
            errors.append({'index': idx, 'patient_id': row.get('patient_id', ''), 'error': msg})

    # ---- Aggregated summary ----
    summary_csv_path = os.path.join(output_dir, 'batch_summary.csv')
    summary_md_path = os.path.join(output_dir, 'batch_summary.md')
    summary_json_path = os.path.join(output_dir, 'batch_summary.json')

    _write_summary_csv(summary_csv_path, results)
    _write_summary_md(summary_md_path, results, errors, total)
    _write_summary_json(summary_json_path, results, errors)

    logging.info(f"Batch complete: {len(results)} succeeded, {len(errors)} failed out of {total}.")
    logging.info(f"Summary written to {summary_csv_path}")

    return {
        'results': results,
        'errors': errors,
        'summary_path': summary_csv_path,
    }


def _write_summary_csv(path: str, results: List[Dict]):
    """Write aggregated summary as CSV (one row per patient)."""
    if not results:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("No results.\n")
        return

    # Flatten per_structure into separate rows
    rows = []
    for r in results:
        base = {
            'patient_id': r.get('patient_id', ''),
            'ref': r.get('ref', ''),
            'eval': r.get('eval', ''),
            'mode': r.get('mode', ''),
            'dd_percent': r.get('dd_percent', ''),
            'dta_mm': r.get('dta_mm', ''),
            'cutoff_percent': r.get('cutoff_percent', ''),
            'gamma_type': r.get('gamma_type', ''),
            'pass_rate_percent': r.get('pass_rate_percent', ''),
            'gamma_mean': r.get('gamma_mean', ''),
            'gamma_median': r.get('gamma_median', ''),
            'gamma_max': r.get('gamma_max', ''),
            'best_shift_mm': str(r.get('best_shift_mm', '')),
            'warnings': r.get('warnings', ''),
            'status': r.get('status', ''),
        }
        per_struct = r.get('per_structure', [])
        if per_struct:
            for s in per_struct:
                row = dict(base)
                row['roi_name'] = s.get('roi_name', '')
                row['roi_pass_rate'] = s.get('pass_rate_percent', '')
                row['roi_voxels'] = s.get('voxel_count', '')
                rows.append(row)
        else:
            base['roi_name'] = ''
            base['roi_pass_rate'] = ''
            base['roi_voxels'] = ''
            rows.append(base)

    fields = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_md(path: str, results: List[Dict], errors: List[Dict], total: int):
    """Write aggregated summary as Markdown."""
    lines = [
        "# Batch Gamma Analysis Summary",
        "",
        f"**Total pairs**: {total}  ",
        f"**Succeeded**: {len(results)}  ",
        f"**Failed**: {len(errors)}",
        "",
        "## Results",
        "",
        "| # | Patient | Ref | Eval | GPR (%) | Mean | Median | Max | Shift (mm) | Warnings |",
        "|---|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        gpr = r.get('pass_rate_percent', '')
        if isinstance(gpr, float):
            gpr = f"{gpr:.2f}"
        gmean = r.get('gamma_mean', '')
        if isinstance(gmean, float):
            gmean = f"{gmean:.4f}"
        gmed = r.get('gamma_median', '')
        if isinstance(gmed, float):
            gmed = f"{gmed:.4f}"
        gmax = r.get('gamma_max', '')
        if isinstance(gmax, float):
            gmax = f"{gmax:.4f}"
        lines.append(
            f"| {r.get('batch_index', '')} | {r.get('patient_id', '')} "
            f"| {r.get('ref', '')} | {r.get('eval', '')} "
            f"| {gpr} | {gmean} | {gmed} | {gmax} "
            f"| {r.get('best_shift_mm', '')} | {r.get('warnings', '')} |"
        )

    # Per-structure sub-table (if any results have per_structure)
    has_struct = any(r.get('per_structure') for r in results)
    if has_struct:
        lines.append("")
        lines.append("## Per-Structure Results")
        lines.append("")
        lines.append("| Patient | ROI | Voxels | Evaluated | GPR (%) | Mean | Median | Max |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for r in results:
            for s in r.get('per_structure', []):
                spr = s.get('pass_rate_percent', '')
                if isinstance(spr, float):
                    spr = f"{spr:.2f}"
                sm = s.get('gamma_mean', '')
                if isinstance(sm, float):
                    sm = f"{sm:.4f}"
                smd = s.get('gamma_median', '')
                if isinstance(smd, float):
                    smd = f"{smd:.4f}"
                smx = s.get('gamma_max', '')
                if isinstance(smx, float):
                    smx = f"{smx:.4f}"
                lines.append(
                    f"| {r.get('patient_id', '')} | {s.get('roi_name', '')} "
                    f"| {s.get('voxel_count', '')} | {s.get('evaluated_count', '')} "
                    f"| {spr} | {sm} | {smd} | {smx} |"
                )

    if errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        lines.append("| # | Patient | Error |")
        lines.append("|---|---|---|")
        for e in errors:
            lines.append(f"| {e.get('index', '')} | {e.get('patient_id', '')} | {e.get('error', '')} |")

    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")


def _write_summary_json(path: str, results: List[Dict], errors: List[Dict]):
    """Write aggregated summary as JSON."""
    # Convert tuples to lists for JSON serialization
    clean_results = []
    for r in results:
        cr = {}
        for k, v in r.items():
            if isinstance(v, tuple):
                cr[k] = list(v)
            else:
                cr[k] = v
        clean_results.append(cr)
    data = {
        'total': len(results) + len(errors),
        'succeeded': len(results),
        'failed': len(errors),
        'results': clean_results,
        'errors': errors,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ---- CLI entry point ----
def batch_main(argv=None):
    """CLI entry point for batch processing."""
    import argparse
    parser = argparse.ArgumentParser(
        description='rtgamma batch processing: run gamma analysis on multiple pairs defined in CSV'
    )
    parser.add_argument('--csv', required=True, help='Path to CSV file defining ref/eval pairs')
    parser.add_argument('--output-dir', required=True, help='Output directory for reports and summary')
    parser.add_argument('--pdf', action='store_true', help='Generate PDF reports for all rows')
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('rtgamma_batch.log', mode='w', encoding='utf-8'),
        ]
    )

    result = run_batch(args.csv, args.output_dir, getattr(args, 'pdf', False))
    print(f"\nBatch complete: {result['results'].__len__()} succeeded, {result['errors'].__len__()} failed.")
    print(f"Summary: {result['summary_path']}")


if __name__ == '__main__':
    batch_main()
