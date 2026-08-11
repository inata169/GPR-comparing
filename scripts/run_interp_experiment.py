"""Historical case-specific interpolation sensitivity experiment.

This script was designed to find settings close to stored 3DVH GPR values.
That method is not permitted for the prospective fixed-condition validation
protocol and its output must not be presented as an optimal standard setting.
"""

import argparse
import json
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Try to import rtgamma or add path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rtgamma.main as rg_main


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_experiment(case_name, params, interp_fractions, output_base):
    print(f"\n[{case_name}] Starting interp_fraction experiment (1 to {max(interp_fractions)})...")
    target_gpr = params.get('3dvh_gpr')
    if target_gpr is None:
        print(f"[{case_name}] No 3DVH GPR target defined in config. Skipping.")
        return None

    case_out_dir = os.path.join(output_base, case_name)
    os.makedirs(case_out_dir, exist_ok=True)
    
    results = []

    for frac in interp_fractions:
        print(f"  -> Testing interp_fraction = {frac} ...")
        # Build argv
        argv = [
            '--ref', params['ref'],
            '--eval', params['eval'],
            '--dta', str(params['dta_mm']),
            '--dd', str(params['dd_percent']),
            '--cutoff', str(params['cutoff_percent']),
            '--gamma-type', params['gamma_type'],
            '--norm', params['norm'],
            '--engine', 'numba',  # This is a legacy Numba sensitivity study.
            '--opt-shift', 'off',
            '--interp-fraction', str(frac),
            # Do not save map, report, or pdf to save time and disk space
            # just get the GPR from the summary
            '--log-level', 'INFO' # Change to DEBUG if you want verbose
        ]
        if 'rtstruct' in params:
            argv.extend(['--rtstruct', params['rtstruct']])
            
        try:
            summary = rg_main.main(argv)
            gpr = summary.get('pass_rate_percent', float('nan'))
            delta = gpr - target_gpr
            results.append({
                'interp_fraction': frac,
                'rtgamma_gpr': gpr,
                'target_gpr': target_gpr,
                'delta_pp': delta,
                'abs_delta_pp': abs(delta)
            })
            print(f"     => GPR: {gpr:.2f} % (Delta: {delta:+.2f} pp)")
        except Exception as e:
            print(f"[{case_name}] Error running rtgamma for frac={frac}: {e}")
            results.append({
                'interp_fraction': frac,
                'rtgamma_gpr': float('nan'),
                'target_gpr': target_gpr,
                'delta_pp': float('nan'),
                'abs_delta_pp': float('nan')
            })

    # Summary
    df = pd.DataFrame(results)
    best_row = df.loc[df['abs_delta_pp'].idxmin()]
    
    print(f"\n[{case_name}] Best interp_fraction = {best_row['interp_fraction']} (Delta = {best_row['delta_pp']:+.2f} pp)")

    # Save to CSV
    csv_path = os.path.join(case_out_dir, "interp_experiment_results.csv")
    df.to_csv(csv_path, index=False)
    
    # Plotting
    plt.figure(figsize=(10, 6))
    
    # Plot Rtgamma GPR
    plt.plot(df['interp_fraction'], df['rtgamma_gpr'], marker='o', label='rtgamma GPR', color='steelblue')
    
    # Plot Target
    plt.axhline(y=target_gpr, color='red', linestyle='--', label=f'SunNuclear 3DVH Target ({target_gpr}%)')
    
    # Highlight Best
    plt.scatter(best_row['interp_fraction'], best_row['rtgamma_gpr'], color='darkorange', s=150, zorder=5,
                label=f"Best: frac={int(best_row['interp_fraction'])} (Δ={best_row['delta_pp']:+.2f}pp)")

    plt.title(f"GPR vs Sub-Voxel Interp Fraction ({params.get('label', case_name)})")
    plt.xlabel("interp_fraction")
    plt.ylabel("Gamma Pass Rate (%)")
    plt.xticks(interp_fractions)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    plot_path = os.path.join(case_out_dir, "interp_experiment_plot.png")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()

    print(f"[{case_name}] Saved results to {csv_path} and {plot_path}")
    return df

def main():
    parser = argparse.ArgumentParser(description="Run the historical case-specific interp_fraction sensitivity experiment")
    parser.add_argument('--config', default='config/3dvh_reference.json', help='Path to reference config')
    parser.add_argument('--output', default='output/interp_experiment', help='Output directory')
    parser.add_argument('--case', help='Specific case to run (e.g. Prostate). If omitted, runs all cases.')
    parser.add_argument('--max-frac', type=int, default=20, help='Maximum interp_fraction to test (default 20)')
    args = parser.parse_args()

    cfg = load_config(args.config)
    interp_fractions = list(range(1, args.max_frac + 1))
    
    os.makedirs(args.output, exist_ok=True)
    
    for case_name, params in cfg.items():
        if args.case and case_name != args.case:
            continue
        run_experiment(case_name, params, interp_fractions, args.output)

    print("\n[DONE] Experiment completed.")

if __name__ == '__main__':
    main()
