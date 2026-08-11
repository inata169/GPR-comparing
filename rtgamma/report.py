import csv
import json
import math
from typing import Dict


def sanitize_for_json(value):
    """Return strict-JSON-compatible values, replacing non-finite floats."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(item) for item in value]
    return value


def save_summary_csv(path: str, summary: Dict) -> None:
    fields = list(summary.keys())
    row = {}
    for key, value in sanitize_for_json(summary).items():
        row[key] = (
            json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            if isinstance(value, (dict, list))
            else value
        )
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)


def save_summary_json(path: str, summary: Dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(
            sanitize_for_json(summary),
            f,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )


def save_summary_markdown(path: str, summary: Dict) -> None:
    lines = ['| Key | Value |', '|---|---|']
    per_struct = summary.get('per_structure', None)
    hist = summary.get('histogram', None)

    for k, v in summary.items():
        if k in ('per_structure', 'histogram', 'provenance'):
            continue
        lines.append(f'| {k} | {v} |')

    provenance = summary.get('provenance')
    if provenance:
        application = provenance.get('application', {})
        execution = provenance.get('execution', {})
        runtime = provenance.get('runtime', {})
        engine = provenance.get('engine', {})
        inputs = provenance.get('inputs', {})
        lines.extend(
            [
                '',
                '## Reproducibility provenance',
                '',
                '| Key | Value |',
                '|---|---|',
                f'| schema_version | {provenance.get("schema_version")} |',
                f'| application_version | {application.get("version")} |',
                f'| git_commit | {application.get("git_commit")} |',
                f'| git_dirty | {application.get("git_dirty")} |',
                f'| engine | {engine.get("name")} {engine.get("version")} |',
                f'| python | {runtime.get("python_implementation")} {runtime.get("python_version")} |',
                f'| operating_system | {runtime.get("os")} {runtime.get("os_release")} ({runtime.get("architecture")}) |',
                f'| started_utc | {execution.get("started_utc")} |',
                f'| ended_utc | {execution.get("ended_utc")} |',
                f'| elapsed_seconds | {execution.get("elapsed_seconds")} |',
                f'| reference_sha256 | {inputs.get("reference", {}).get("sha256")} |',
                f'| evaluation_sha256 | {inputs.get("evaluation", {}).get("sha256")} |',
            ]
        )

    if hist:
        lines.append('')
        lines.append('## Gamma Histogram')
        lines.append('')
        lines.append('| Range | Voxel Count | Cumulative Pass (%) |')
        lines.append('|---|---|---|')
        edges = hist['bin_edges']
        counts = hist['counts']
        c_pass = hist['cumulative_pass']
        for i in range(len(edges) - 1):
            if i == len(edges) - 2:
                rng = f'[{edges[i]:.2f}, {edges[i + 1]:.2f}]'
            else:
                rng = f'[{edges[i]:.2f}, {edges[i + 1]:.2f})'
            lines.append(f'| {rng} | {counts[i]} | {c_pass[i + 1]:.2f} |')
        lines.append(f'| > {edges[-1]:.2f} | {counts[-1]} | - |')
        lines.append('')

    if per_struct:
        lines.append('## Per-Structure Gamma Analysis')
        lines.append('')
        lines.append('| ROI | Voxels | Evaluated | GPR (%) | Mean | Median | Max |')
        lines.append('|---|---|---|---|---|---|---|')
        for s in per_struct:
            lines.append(
                f'| {s["roi_name"]} | {s["voxel_count"]} | {s["evaluated_count"]} '
                f'| {s["pass_rate_percent"]:.2f} | {s["gamma_mean"]:.4f} '
                f'| {s["gamma_median"]:.4f} | {s["gamma_max"]:.4f} |'
            )

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
