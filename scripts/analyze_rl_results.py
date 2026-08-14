"""
Week 3, Entregable 7: paired bootstrap of each TD3 training seed against
AFAP and Round Robin, plus a SEPARATE cross-training-seed dispersion
analysis. Uses stats_utils.paired_bootstrap_ci (already written and tested
in Week 2) -- no new bootstrap implementation.

Two genuinely different uncertainty sources are reported, deliberately kept
apart rather than pooled (pooling them would understate the real
uncertainty -- see thesis_docs/chapters/03_rl_baseline.md):
  1. Scenario dispersion: for ONE training seed, how much does its measured
     performance vary across the 50 (SEEDS x EVAL_DAYS) evaluation cells?
     -> paired_bootstrap_ci, matched cell-by-cell against AFAP/Round Robin.
  2. Training-seed dispersion: holding the evaluation grid's AVERAGE fixed,
     how much does that average itself vary across the 3 independent
     training runs (TRAIN_SEEDS)? -> min/max/std across the 3 per-seed means.

Usage:
    PYTHONPATH=. python scripts/analyze_rl_results.py
Writes: results/rl_vs_baseline_bootstrap.csv, results/rl_train_seed_dispersion.csv
"""
import csv

import numpy as np

from ev2gym_thesis.registry_analysis import load_registry, main_grid_rows
from ev2gym_thesis.stats_utils import paired_bootstrap_ci, mean_ci

REFERENCE_CONFIG = "station_v0_bogota"
TD3_ALGOS = ["TD3_vanilla_ts100", "TD3_vanilla_ts101", "TD3_vanilla_ts102"]
BASELINE_ALGOS = ["ChargeAsFastAsPossible", "RoundRobin"]
METRICS = [
    "total_ev_served", "total_profits", "average_user_satisfaction",
    "energy_user_satisfaction", "min_energy_user_satisfaction",
    "total_transformer_overload", "tracking_error", "energy_tracking_error",
    "battery_degradation",
]
N_BOOTSTRAP = 5000


def cell_key(r):
    return (r["seed"], r["eval_day"])


def paired_vs_baseline(grid, td3_algo, baseline_algo, metric):
    baseline_by_cell = {cell_key(r): r for r in grid if r["algorithm"] == baseline_algo}
    td3_by_cell = {cell_key(r): r for r in grid if r["algorithm"] == td3_algo}
    common_cells = sorted(set(baseline_by_cell) & set(td3_by_cell))
    baseline_vals = np.array([baseline_by_cell[c][metric] for c in common_cells])
    td3_vals = np.array([td3_by_cell[c][metric] for c in common_cells])
    if np.any(baseline_vals == 0):
        result = paired_bootstrap_ci(baseline_vals, td3_vals, n_bootstrap=N_BOOTSTRAP, seed=0, statistic="diff")
        unit = "abs_diff"
    else:
        result = paired_bootstrap_ci(baseline_vals, td3_vals, n_bootstrap=N_BOOTSTRAP, seed=0, statistic="pct")
        unit = "pct_diff"
    result["unit"] = unit
    result["n_cells"] = len(common_cells)
    return result


if __name__ == "__main__":
    rows = load_registry()
    grid = main_grid_rows(rows, REFERENCE_CONFIG)

    bootstrap_report = []
    print("=== Paired bootstrap: each TD3 training seed vs. AFAP / Round Robin ===")
    for td3_algo in TD3_ALGOS:
        for baseline_algo in BASELINE_ALGOS:
            for metric in METRICS:
                r = paired_vs_baseline(grid, td3_algo, baseline_algo, metric)
                print(f"{td3_algo:20} vs {baseline_algo:24} {metric:28} "
                      f"{r['point_estimate']:>10.3f} [{r['ci_low']:>10.3f}, {r['ci_high']:>10.3f}] "
                      f"({r['unit']}, n={r['n_cells']})")
                bootstrap_report.append({
                    "td3_algorithm": td3_algo, "baseline_algorithm": baseline_algo,
                    "metric": metric, "point_estimate": r["point_estimate"],
                    "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                    "unit": r["unit"], "n_cells": r["n_cells"],
                })

    with open("results/rl_vs_baseline_bootstrap.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(bootstrap_report[0].keys()))
        writer.writeheader()
        writer.writerows(bootstrap_report)
    print("\nWrote results/rl_vs_baseline_bootstrap.csv")

    print("\n=== Cross-training-seed dispersion (separate from scenario dispersion above) ===")
    # doc:begin cross_seed_dispersion
    dispersion_report = []
    for metric in METRICS:
        per_seed_means = []
        for algo in TD3_ALGOS:
            vals = np.array([r[metric] for r in grid if r["algorithm"] == algo and r[metric] is not None])
            per_seed_means.append(float(np.mean(vals)))
        per_seed_means = np.array(per_seed_means)
        spread = per_seed_means.max() - per_seed_means.min()
        rel_spread_pct = (spread / abs(per_seed_means.mean()) * 100) if per_seed_means.mean() != 0 else float("nan")
        dispersion_report.append({
            "metric": metric,
            "mean_ts100": per_seed_means[0], "mean_ts101": per_seed_means[1], "mean_ts102": per_seed_means[2],
            "spread_max_minus_min": spread, "std_across_seeds": per_seed_means.std(),
            "relative_spread_pct": rel_spread_pct,
        })
    # doc:end cross_seed_dispersion
    for row in dispersion_report:
        print(f"{row['metric']:28} spread={row['spread_max_minus_min']:.3f}  "
              f"std={row['std_across_seeds']:.3f}  rel_spread={row['relative_spread_pct']:.1f}%")

    with open("results/rl_train_seed_dispersion.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(dispersion_report[0].keys()))
        writer.writeheader()
        writer.writerows(dispersion_report)
    print("\nWrote results/rl_train_seed_dispersion.csv")
