import json
import csv
from typing import Dict


def save_summary_csv(path: str, summary: Dict) -> None:
    fields = list(summary.keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow(summary)


def save_summary_json(path: str, summary: Dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def save_summary_markdown(path: str, summary: Dict) -> None:
    lines = ["| Key | Value |", "|---|---|"]
    per_struct = summary.get('per_structure', None)
    for k, v in summary.items():
        if k == 'per_structure':
            continue
        lines.append(f"| {k} | {v} |")
    if per_struct:
        lines.append("")
        lines.append("## Per-Structure Gamma Analysis")
        lines.append("")
        lines.append("| ROI | Voxels | Evaluated | GPR (%) | Mean | Median | Max |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in per_struct:
            lines.append(
                f"| {s['roi_name']} | {s['voxel_count']} | {s['evaluated_count']} "
                f"| {s['pass_rate_percent']:.2f} | {s['gamma_mean']:.4f} "
                f"| {s['gamma_median']:.4f} | {s['gamma_max']:.4f} |"
            )
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

