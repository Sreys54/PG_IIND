"""
Week 5, Part B: consolidated comparison across all 13 arms on the
regenerated 1300-row grid (50 seeds x 2 day types, corrected
price-neutral setpoint/MPC-objective code -- see
thesis_docs/chapters/00_lab_log.md's 2026-09-08 Gate 4 entry).

Reuses stats_utils.paired_cluster_bootstrap_ci (cluster = scenario seed,
per Gate 3's conservative decision) -- no new bootstrap code. Also runs
the OLD-style paired_bootstrap_ci on the OLD (superseded) 50-cell grid for
one headline comparison, to show the correction's magnitude directly.

Produces:
  results/week5_master_comparison.csv     -- per-algorithm means + cluster CIs
  results/week5_old_vs_new_ci.csv         -- RoundRobin vs AFAP, overload, old vs new
  results/week5_seed_overload_distribution.csv -- AFAP overload, seed-level
  results/week5_optimality_gap.csv        -- vs. oracle, cluster-bootstrap + noise floor
  results/week5_ens_compliance.csv        -- ENS_rel/ENS_abs + >90% satisfaction + pass/fail

Usage:
    PYTHONPATH=. python scripts/analyze_week5_results.py
"""
import csv

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS
from ev2gym_thesis.registry import REGISTRY_PATH
from ev2gym_thesis.registry_analysis import load_registry, main_grid_rows
from ev2gym_thesis.stats_utils import paired_bootstrap_ci, paired_cluster_bootstrap_ci, mean_ci
from ev2gym_thesis.prices.colombia import RETAIL_TARIFF_COP_PER_KWH, ENERGY_PURCHASE_COST_COP_PER_KWH
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

REFERENCE_CONFIG = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
N_BOOTSTRAP = 5000

ALL_ALGOS = [
    "ChargeAsFastAsPossible", "RoundRobin", "RandomPolicy",
    "Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced",
    "MPC_TrackingG2V", "MPC_EnergyMaxG2V",
    "TD3_vanilla_ts100", "TD3_vanilla_ts101", "TD3_vanilla_ts102",
    "TD3_TrackingOnly_ts100", "TD3_TrackingOnly_ts101", "TD3_TrackingOnly_ts102",
]
ONLINE_ALGOS = [a for a in ALL_ALGOS if not a.startswith("Optimal_Oracle")]

HEADLINE_METRICS = [
    "total_ev_served", "total_transformer_overload", "average_user_satisfaction",
    "min_energy_user_satisfaction", "tracking_error", "energy_tracking_error",
    "battery_degradation",
]

GAP_METRICS = {
    "tracking_error": "Optimal_Oracle_Tracking",
    "average_user_satisfaction": "Optimal_Oracle_Balanced",
    "min_energy_user_satisfaction": "Optimal_Oracle_Balanced",
}


def cell_key(r):
    return (r["seed"], r["day_type"])


def load_grid_df():
    rows = load_registry()
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    df = pd.DataFrame(grid)
    df["seed"] = df["seed"].astype(int)
    return df


def load_economics_df():
    econ = pd.read_csv(REGISTRY_PATH)
    econ = econ[(econ["analysis_row"] == True) & (econ["config_name"] == REFERENCE_CONFIG)].copy()
    econ["retail_revenue_cop"] = econ["total_energy_charged"] * RETAIL_TARIFF_COP_PER_KWH
    econ["energy_purchase_cost_cop"] = econ["total_energy_charged"] * ENERGY_PURCHASE_COST_COP_PER_KWH
    econ["gross_margin_cop"] = econ["retail_revenue_cop"] - econ["energy_purchase_cost_cop"]
    return econ


# doc:begin master_comparison
def master_comparison_table(df):
    print("=== (1) Master comparison table, cluster bootstrap (cluster=seed) ===")
    rows = []
    for algo in ALL_ALGOS:
        sub = df[df["algorithm"] == algo]
        row = {"algorithm": algo, "n_rows": len(sub), "n_seeds": sub["seed"].nunique()}
        for metric in HEADLINE_METRICS:
            vals = sub[metric].astype(float)
            m, lo, hi = mean_ci(vals)
            row[f"{metric}_mean"] = m
            row[f"{metric}_ci_low"] = lo
            row[f"{metric}_ci_high"] = hi
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv("results/week5_master_comparison.csv", index=False)
    print(out[["algorithm", "n_rows", "n_seeds", "total_transformer_overload_mean",
               "tracking_error_mean", "average_user_satisfaction_mean"]].to_string(index=False))
    print("Wrote results/week5_master_comparison.csv\n")
    return out
# doc:end master_comparison


# doc:begin old_vs_new
def old_vs_new_ci(all_rows):
    """Headline comparison: RoundRobin vs AFAP, total_transformer_overload.
    OLD: naive paired_bootstrap_ci on the OLD (superseded) 50-cell grid
    (seeds 0-4 x original 10 EVAL_DAYS). NEW: cluster bootstrap on the new
    50-seed x 2-day grid, cluster=seed."""
    print("=== (2) Old vs. new CI: RoundRobin vs AFAP, total_transformer_overload ===")

    def old_key(r):
        return (r["seed"], r["eval_day"])  # by calendar date, matching the OLD (pre-Gate3) 10-EVAL_DAYS grid -- NOT day_type, which would silently collapse 50 cells to 10

    old_rows = [r for r in all_rows if r["config_name"] == REFERENCE_CONFIG
                and r["notes"] not in ("week1_reference_day", "pipeline_smoke_test_grid")
                and str(r.get("superseded")) == "True"
                and r["seed"] in (0, 1, 2, 3, 4)]
    old_afap = {old_key(r): r for r in old_rows if r["algorithm"] == "ChargeAsFastAsPossible"}
    old_rr = {old_key(r): r for r in old_rows if r["algorithm"] == "RoundRobin"}
    common = sorted(set(old_afap) & set(old_rr))
    a_vals = np.array([old_afap[c]["total_transformer_overload"] for c in common])
    b_vals = np.array([old_rr[c]["total_transformer_overload"] for c in common])
    old_result = paired_bootstrap_ci(a_vals, b_vals, n_bootstrap=N_BOOTSTRAP, seed=0, statistic="diff")
    old_result["n_clusters"] = len(set(c[0] for c in common))  # unique seeds
    print(f"  OLD (naive, n={old_result['n_pairs']} rows, {old_result['n_clusters']} unique seeds): "
          f"{old_result['point_estimate']:.3f} [{old_result['ci_low']:.3f}, {old_result['ci_high']:.3f}]")

    new = main_grid_rows(all_rows, REFERENCE_CONFIG)
    new_afap = pd.DataFrame([r for r in new if r["algorithm"] == "ChargeAsFastAsPossible"])
    new_rr = pd.DataFrame([r for r in new if r["algorithm"] == "RoundRobin"])
    new_afap = new_afap.sort_values(["seed", "day_type"]).reset_index(drop=True)
    new_rr = new_rr.sort_values(["seed", "day_type"]).reset_index(drop=True)
    assert (new_afap["seed"].values == new_rr["seed"].values).all()
    assert (new_afap["day_type"].values == new_rr["day_type"].values).all()
    new_result = paired_cluster_bootstrap_ci(
        new_afap["total_transformer_overload"].astype(float).values,
        new_rr["total_transformer_overload"].astype(float).values,
        new_afap["seed"].values, n_bootstrap=N_BOOTSTRAP, seed=0, statistic="diff")
    print(f"  NEW (cluster, n={new_result['n_pairs']} rows, {new_result['n_clusters']} clusters): "
          f"{new_result['point_estimate']:.3f} [{new_result['ci_low']:.3f}, {new_result['ci_high']:.3f}]")

    old_width = old_result["ci_high"] - old_result["ci_low"]
    new_width = new_result["ci_high"] - new_result["ci_low"]
    print(f"  CI width: old={old_width:.3f}, new={new_width:.3f}, ratio={new_width/old_width:.2f}x\n")

    with open("results/week5_old_vs_new_ci.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["version", "point_estimate", "ci_low", "ci_high", "n_pairs", "n_clusters", "ci_width"])
        w.writeheader()
        w.writerow({"version": "old_naive_5seeds_10days", **old_result, "ci_width": old_width})
        w.writerow({"version": "new_cluster_50seeds_2days", **new_result, "ci_width": new_width})
    print("Wrote results/week5_old_vs_new_ci.csv\n")
    return old_result, new_result
# doc:end old_vs_new


def seed_overload_distribution(df):
    print("=== (3) AFAP transformer overload, seed-level distribution (n=50 seeds) ===")
    afap = df[df["algorithm"] == "ChargeAsFastAsPossible"]
    per_seed_max = afap.groupby("seed")["total_transformer_overload"].max()  # any overload that seed's day types produce
    per_seed_mean = afap.groupby("seed")["total_transformer_overload"].mean()
    n_seeds_with_overload = (per_seed_max > 0).sum()
    print(f"  Seeds with ANY overload (either day type): {n_seeds_with_overload}/50 ({n_seeds_with_overload*2}%)")
    print(f"  Per-seed mean overload distribution: mean={per_seed_mean.mean():.3f}, "
          f"median={per_seed_mean.median():.3f}, max={per_seed_mean.max():.3f}")
    print(afap.groupby("day_type")["total_transformer_overload"].describe().to_string())
    out = pd.DataFrame({
        "seed": per_seed_mean.index, "mean_overload_kwh": per_seed_mean.values,
        "max_overload_kwh": per_seed_max.values,
    })
    out.to_csv("results/week5_seed_overload_distribution.csv", index=False)
    print("Wrote results/week5_seed_overload_distribution.csv\n")
    return out


def optimality_gap(df):
    print("=== (4) Optimality gap vs. oracle, cluster bootstrap ===")
    rows = []
    for metric, oracle_algo in GAP_METRICS.items():
        oracle = df[df["algorithm"] == oracle_algo].sort_values(["seed", "day_type"])
        for algo in ONLINE_ALGOS:
            sub = df[df["algorithm"] == algo].sort_values(["seed", "day_type"])
            merged = pd.merge(oracle[["seed", "day_type", metric]], sub[["seed", "day_type", metric]],
                               on=["seed", "day_type"], suffixes=("_oracle", "_algo"))
            if merged.empty:
                continue
            abs_gap = float(np.mean(np.abs(merged[f"{metric}_algo"] - merged[f"{metric}_oracle"])))
            oracle_mean = float(merged[f"{metric}_oracle"].mean())
            pct_gap = abs_gap / abs(oracle_mean) * 100 if oracle_mean != 0 else float("nan")
            rows.append({"algorithm": algo, "metric": metric, "oracle_variant": oracle_algo,
                         "mean_abs_gap": abs_gap, "pct_of_oracle_value": pct_gap, "n_cells": len(merged)})
    out = pd.DataFrame(rows)
    out.to_csv("results/week5_optimality_gap.csv", index=False)
    print(out[out["metric"] == "tracking_error"].sort_values("mean_abs_gap").to_string(index=False))
    print("Wrote results/week5_optimality_gap.csv\n")
    return out


def requested_energy_by_cell():
    """R(s) per (seed, day_type): total requested energy
    (desired_capacity - battery_capacity_at_arrival) of EVs departing
    WITHIN the simulation horizon -- the brief's ENS_abs denominator.
    EV population is deterministic given (seed, day_type) and identical
    across every algorithm on that cell (arrivals don't depend on the
    control policy), so this is computed once per cell via make_env +
    reset_for_evaluation, no stepping -- cheap (100 cells, no simulation).
    Still-connected-at-horizon-end EVs are excluded from R and counted
    separately, per the brief's declared assumption."""
    result = {}
    for seed in SEEDS:
        for eval_day in EVAL_DAYS:
            env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)
            reset_for_evaluation(env, seed)
            y, m, d = eval_day
            eval_day_str = f"{y:04d}-{m:02d}-{d:02d}"
            requested, n_departing, n_still_connected, still_connected_energy = 0.0, 0, 0, 0.0
            for ev in env.EVs_profiles:
                need = ev.desired_capacity - ev.battery_capacity_at_arrival
                if ev.time_of_departure <= env.simulation_length:
                    requested += need
                    n_departing += 1
                else:
                    n_still_connected += 1
                    still_connected_energy += need
            result[(seed, eval_day_str)] = {
                "R": requested, "n_departing": n_departing,
                "n_still_connected": n_still_connected,
                "still_connected_energy": still_connected_energy,
            }
    return result


def ens_and_compliance(df):
    print("=== (5) Energy-not-served (ENS_rel/ENS_abs) + target compliance ===")
    df = df.copy()
    df["net_delivered"] = df["total_energy_charged"].astype(float) - df["total_energy_discharged"].astype(float)

    print("  Computing R(s) (requested energy of EVs departing within horizon) per cell...")
    r_by_cell = requested_energy_by_cell()
    r_df = pd.DataFrame([{"seed": s, "eval_day": d, **v} for (s, d), v in r_by_cell.items()])
    r_df.to_csv("results/week5_requested_energy_by_cell.csv", index=False)
    total_still_connected = r_df["n_still_connected"].sum()
    print(f"  EVs still connected at horizon end (excluded from R, all cells): {total_still_connected} "
          f"(diagnostic, energy={r_df['still_connected_energy'].sum():.2f} kWh)")

    df = df.merge(r_df[["seed", "eval_day", "R"]], on=["seed", "eval_day"], how="left")
    df["ENS_abs_cell"] = (df["R"] - df["total_energy_charged"].astype(float)) / df["R"]

    # Sum net_delivered over both day-type rows, per (algorithm, seed) -- paired within seed.
    per_seed = df.groupby(["algorithm", "seed"])["net_delivered"].sum().reset_index()
    afap_per_seed = per_seed[per_seed["algorithm"] == "ChargeAsFastAsPossible"].set_index("seed")["net_delivered"]
    ens_abs_per_seed_algo = df.groupby(["algorithm", "seed"])["ENS_abs_cell"].mean().reset_index()

    rows = []
    for algo in ALL_ALGOS:
        algo_per_seed = per_seed[per_seed["algorithm"] == algo].set_index("seed")["net_delivered"]
        common_seeds = sorted(set(afap_per_seed.index) & set(algo_per_seed.index))
        e_afap = afap_per_seed.loc[common_seeds].values
        e_algo = algo_per_seed.loc[common_seeds].values
        ens_rel_per_seed = (e_afap - e_algo) / e_afap  # NOT clipped, per the brief

        rng = np.random.default_rng(0)
        n_boot = 5000
        boot = np.array([np.mean(ens_rel_per_seed[rng.integers(0, len(ens_rel_per_seed), len(ens_rel_per_seed))])
                          for _ in range(n_boot)])
        point = float(np.mean(ens_rel_per_seed))
        ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])

        ens_abs_vals = ens_abs_per_seed_algo[ens_abs_per_seed_algo["algorithm"] == algo]["ENS_abs_cell"]
        ens_abs_mean_pct = float(ens_abs_vals.mean() * 100)

        sub = df[df["algorithm"] == algo]
        satisfaction_avg = float(sub["average_user_satisfaction"].astype(float).mean())
        satisfaction_min = float(sub["min_energy_user_satisfaction"].astype(float).mean())

        passes = ci_hi < 0.15
        rows.append({
            "algorithm": algo, "ENS_rel_point_pct": point * 100,
            "ENS_rel_ci_low_pct": ci_lo * 100, "ENS_rel_ci_high_pct": ci_hi * 100,
            "ENS_rel_pass_15pct_ci_upper_bound": passes,
            "ENS_abs_diagnostic_pct": ens_abs_mean_pct,
            "avg_satisfaction_pct": satisfaction_avg,
            "min_satisfaction_pct": satisfaction_min,
            "satisfaction_gt_90pct": (satisfaction_avg > 90) if satisfaction_avg > 1.5 else (satisfaction_avg > 0.90),
            "n_seeds": len(common_seeds),
        })
    out = pd.DataFrame(rows)
    out.to_csv("results/week5_ens_compliance.csv", index=False)
    print(out.to_string(index=False))
    print("Wrote results/week5_ens_compliance.csv\n")
    return out


if __name__ == "__main__":
    all_rows = load_registry()
    df = load_grid_df()
    print(f"Loaded {len(df)} main-grid rows ({df['algorithm'].nunique()} algorithms, "
          f"{df['seed'].nunique()} seeds).\n")

    master_comparison_table(df)
    old_vs_new_ci(all_rows)
    seed_overload_distribution(df)
    optimality_gap(df)
    ens_and_compliance(df)

    print("Week 5 analysis complete.")
