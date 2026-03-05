import csv
import json
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
    hist = summary.get('histogram', None)
    
    for k, v in summary.items():
        if k in ('per_structure', 'histogram'):
            continue
        lines.append(f"| {k} | {v} |")

    if hist:
        lines.append("")
        lines.append("## Gamma Histogram")
        lines.append("")
        lines.append("| Range | Voxel Count | Cumulative Pass (%) |")
        lines.append("|---|---|---|")
        edges = hist['bin_edges']
        counts = hist['counts']
        c_pass = hist['cumulative_pass']
        for i in range(len(edges) - 1):
            if i == len(edges) - 2:
                 rng = f"[{edges[i]:.2f}, {edges[i+1]:.2f}]"
            else:
                 rng = f"[{edges[i]:.2f}, {edges[i+1]:.2f})"
            lines.append(f"| {rng} | {counts[i]} | {c_pass[i+1]:.2f} |")
        lines.append(f"| > {edges[-1]:.2f} | {counts[-1]} | - |")
        lines.append("")

    if per_struct:
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

