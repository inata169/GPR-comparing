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
    for k, v in summary.items():
        lines.append(f"| {k} | {v} |")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

