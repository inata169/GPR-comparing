#!/usr/bin/env python
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


def run_cmd(cmd, env=None):
    cp = subprocess.run(cmd, text=True, capture_output=True, env=env)
    return cp.returncode, cp.stdout, cp.stderr


def main():
    ap = argparse.ArgumentParser(description="Run 2D coronal sweep (indices) and summarize GPR.")
    ap.add_argument('--ref', required=True)
    ap.add_argument('--eval', required=True)
    ap.add_argument('--indices', default='100,101,102', help='Comma-separated indices, e.g., 100,101,102')
    ap.add_argument('--profile', default='clinical_rel')
    ap.add_argument('--cutoff', type=float, default=10.0)
    ap.add_argument('--interp', default='linear')
    ap.add_argument('--opt-shift', default='off', choices=['on','off'])
    ap.add_argument('--threads', type=int, default=0)
    ap.add_argument('--outdir', default='phits-linac-validation/output/rtgamma/spec_check_coronal')
    ap.add_argument('--python', default=None, help='Python executable to use (default: current)')
    args = ap.parse_args()

    py = args.python or os.environ.get('PYTHON', None) or os.sys.executable
    out_base = Path(args.outdir)
    out_base.mkdir(parents=True, exist_ok=True)

    indices = [int(s.strip()) for s in args.indices.split(',') if s.strip()]
    rows = []

    env = os.environ.copy()
    # Ensure project is importable when running as module
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])

    for idx in indices:
        case_dir = out_base / f'coronal_{idx}'
        case_dir.mkdir(parents=True, exist_ok=True)
        base = case_dir / f'coronal_{idx}'

        cmd = [
            py, '-m', 'rtgamma.main',
            '--profile', args.profile,
            '--ref', args.ref,
            '--eval', args.eval,
            '--mode', '2d', '--plane', 'coronal', '--plane-index', str(idx),
            '--opt-shift', args.opt_shift,
            '--interp', args.interp,
            '--cutoff', str(args.cutoff),
            '--threads', str(args.threads),
            '--save-gamma-map', str(base.with_name(f'coronal_{idx}_gamma.png')),
            '--save-dose-diff', str(base.with_name(f'coronal_{idx}_diff.png')),
            '--report', str(base),
            '--log-level', 'INFO',
        ]
        code, out, err = run_cmd(cmd, env=env)
        report_json = base.with_suffix('.json')
        gpr = None
        if report_json.exists():
            try:
                with open(report_json, 'r', encoding='utf-8') as f:
                    rep = json.load(f)
                gpr = rep.get('pass_rate_percent', None)
            except Exception:
                gpr = None
        rows.append({
            'index': idx,
            'return_code': code,
            'report': str(report_json),
            'pass_rate_percent': gpr,
        })

    # Write summary markdown
    md = [
        f"# Coronal Sweep Summary ({args.profile}, opt-shift={args.opt_shift}, cutoff={args.cutoff}, interp={args.interp})",
        "",
        f"Ref: `{args.ref}`",
        f"Eval: `{args.eval}`",
        "",
        "| Index | Pass Rate (%) | JSON | Gamma | Diff |",
        "|---:|---:|---|---|---|",
    ]
    for r in rows:
        idx = r['index']
        base = out_base / f'coronal_{idx}' / f'coronal_{idx}'
        j = Path(r['report']).name if r['report'] else '-'
        g = base.with_name(f'coronal_{idx}_gamma.png').name
        d = base.with_name(f'coronal_{idx}_diff.png').name
        pr = r['pass_rate_percent'] if r['pass_rate_percent'] is not None else 'NaN'
        md.append(f"| {idx} | {pr} | {j} | {g} | {d} |")

    summary_path = out_base / 'summary.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print(f"Wrote {summary_path}")


if __name__ == '__main__':
    main()

