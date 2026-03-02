#!/usr/bin/env python
import argparse
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Validate all report JSONs under a directory")
    ap.add_argument('--root', default='phits-linac-validation/output/rtgamma', help='Root directory to search for *.json')
    ap.add_argument('--schema', default='docs/openspec/report.schema.json', help='Path to schema JSON')
    ap.add_argument('--sanitize-nan', action='store_true', help='Replace NaN with null before validation')
    args = ap.parse_args()

    root = Path(args.root)
    jsons = sorted(root.rglob('*.json')) if root.exists() else []
    if not jsons:
        print(f"No JSON files found under: {root}")
        return

    ok = True
    for j in jsons:
        cmd = ['python', 'scripts/validate_report.py']
        if args.sanitize_nan:
            cmd.append('--sanitize-nan')
        cmd.extend(['--schema', args.schema, str(j)])
        cp = subprocess.run(cmd, text=True)
        ok = ok and (cp.returncode == 0)

    if not ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

