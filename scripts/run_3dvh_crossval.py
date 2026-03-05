import argparse
import json
import os
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Try to import rtgamma or add path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rtgamma.main as rg_main


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_case(case_name, params, output_base):
    print(f"[{case_name}] Starting cross-validation...")
    case_out_dir = os.path.join(output_base, case_name)
    os.makedirs(case_out_dir, exist_ok=True)
    
    # Build argv
    argv = [
        '--ref', params['ref'],
        '--eval', params['eval'],
        '--dta', str(params['dta_mm']),
        '--dd', str(params['dd_percent']),
        '--cutoff', str(params['cutoff_percent']),
        '--gamma-type', params['gamma_type'],
        '--norm', params['norm'],
        '--opt-shift', 'off', # Don't optimize shift for 3DVH exact comp
        '--interp-fraction', str(params.get('interp_fraction', 10)),
        '--save-gamma-map', os.path.join(case_out_dir, "gamma3d.npz"),
        '--report', os.path.join(case_out_dir, "run3d"),
        '--pdf',
        '--log-level', 'INFO'
    ]
    if 'rtstruct' in params:
        argv.extend(['--rtstruct', params['rtstruct']])
        
    print(f"[{case_name}] Args: {' '.join(argv)}")
    
    # Run pipeline via API
    try:
        summary = rg_main.main(argv)
        return summary
    except Exception as e:
        print(f"[{case_name}] Error running rtgamma: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Run 3DVH Cross-Validation")
    parser.add_argument('--config', default='config/3dvh_reference.json', help='Path to reference config')
    parser.add_argument('--output', default='output/3dvh_crossval', help='Output directory')
    args = parser.parse_args()

    cfg = load_config(args.config)
    
    results = {}
    for case_name, params in cfg.items():
        summary = run_case(case_name, params, args.output)
        if summary is not None:
            results[case_name] = {
                'params': params,
                'summary': summary
            }

    # Generate Cross-Val Summary Report
    report_md_path = os.path.join(args.output, "crossval_summary.md")
    report_json_path = os.path.join(args.output, "crossval_summary.json")
    
    out_json = {}
    
    md_lines = [
        "# 3DVH Cross-Validation Summary",
        "",
        "**Δpp 許容範囲**:",
        "- 許容範囲1: Δpp ≤ 2.0 pp以内 (PASS)",
        "- 許容範囲2: Δpp ≤ 3.0 pp以内 (ACCEPTABLE)",
        "- それ以外: NG",
        "",
        "| Case | rtgamma GPR (%) | 3DVH GPR (%) | Δ (pp) | 判定 | Gamma Mean | Gamma Median | Gamma Max | 95th Percentile |",
        "|---|---|---|---|---|---|---|---|---|"
    ]
    
    # For overlaid histograms
    fig, axes = plt.subplots(len(results), 1, figsize=(8, 4 * len(results)), squeeze=False)
    
    for i, (case_name, data) in enumerate(results.items()):
        sm = data['summary']
        p = data['params']
        
        rg_gpr = sm.get('pass_rate_percent', float('nan'))
        v3_gpr = p.get('3dvh_gpr', None)
        delta = (rg_gpr - v3_gpr) if v3_gpr is not None else float('nan')
        
        abs_delta = abs(delta)
        if abs_delta <= 2.0:
            judge = "PASS (≤2pp)"
        elif abs_delta <= 3.0:
            judge = "ACCEPT (≤3pp)"
        else:
            judge = "NG (>3pp)"
        
        md_lines.append(
            f"| {p.get('label', case_name)} | {rg_gpr:.2f} | {v3_gpr if v3_gpr else 'N/A'} | {delta:.2f} | {judge} | "
            f"{sm.get('gamma_mean', float('nan')):.3f} | {sm.get('gamma_median', float('nan')):.3f} | {sm.get('gamma_max', float('nan')):.3f} | {sm.get('gamma_p95', float('nan')):.3f} |"
        )
        
        out_json[case_name] = {
            'rtgamma_gpr': rg_gpr,
            '3dvh_gpr': v3_gpr,
            'delta_pp': delta,
            'gamma_mean': sm.get('gamma_mean'),
            'gamma_median': sm.get('gamma_median'),
            'gamma_max': sm.get('gamma_max'),
            'gamma_p95': sm.get('gamma_p95'),
            'gamma_p99': sm.get('gamma_p99')
        }
        
        # Plot histogram
        hist = sm.get('histogram')
        if hist:
            ax = axes[i][0]
            edges = hist['bin_edges']
            counts = hist['counts']
            c_pass = hist['cumulative_pass']
            
            x_pos = list(range(len(edges)))
            labels = [f"{edges[j]:.2f}-{edges[j+1]:.2f}" for j in range(len(edges)-1)] + [f">{edges[-1]:.2f}"]
            
            ax.bar(x_pos, counts, color='steelblue', edgecolor='black', zorder=3)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.set_title(f"Gamma Histogram: {p.get('label', case_name)}")
            ax.set_xlabel('Gamma Value')
            ax.set_ylabel('Voxel Count', color='steelblue')
            ax.grid(True, linestyle='--', alpha=0.5, axis='y', zorder=0)
            
            try:
                idx_1 = edges.index(1.0)
                ax.axvline(x=idx_1 - 0.5, color='red', linestyle='--', linewidth=1.5, zorder=5, label='Pass/Fail (g=1.0)')
                ax.legend()
            except ValueError:
                pass
                
            ax2 = ax.twinx()
            ax2.plot(x_pos, c_pass, color='darkorange', marker='o', markersize=4, zorder=4)
            ax2.set_ylabel('Cumulative Pass (%)', color='darkorange')
            ax2.set_ylim([0, 105])

    with open(report_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
        
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(out_json, f, indent=2, ensure_ascii=False)
        
    plt.tight_layout()
    hist_out = os.path.join(args.output, "histogram_comparison.png")
    plt.savefig(hist_out, dpi=150)
    plt.close(fig)
    
    print(f"\n[DONE] Cross-Validation summary saved to: {report_md_path}")
    print(f"       Histogram plots saved to: {hist_out}")

if __name__ == '__main__':
    main()
