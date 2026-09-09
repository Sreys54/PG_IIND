"""
Week 5, Part B, section 14: MPC_TrackingG2V horizon sensitivity, on a
10-seed subset (seeds 0-9, both day types = 20 cells per horizon), per the
brief's explicit "small subset, not the full grid" instruction.

Candidate horizons: 5, 10 (the default/calibrated value), 20 -- brackets
the shipped classes' own default (10) with a shorter and longer option,
matching the kind of bracketing Week 4's PI-TD3 horizon check used.

Usage:
    PYTHONPATH=. python scripts/run_horizon_sensitivity.py
"""
import time

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from ev2gym_thesis.mpc.tracking_mpc import MPCTrackingG2V

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
SUBSET_SEEDS = list(range(10))
CANDIDATE_HORIZONS = [5, 10, 20]


def run_cell(seed, eval_day, horizon):
    env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)
    reset_for_evaluation(env, seed)
    agent = MPCTrackingG2V(env, control_horizon=horizon)
    t0 = time.perf_counter()
    done = truncated = False
    stats = None
    while not done and not truncated:
        actions = agent.get_action(env)
        _, _, done, truncated, stats = env.step(actions)
    runtime_s = time.perf_counter() - t0
    return stats, runtime_s


def main():
    rows = []
    for horizon in CANDIDATE_HORIZONS:
        print(f"--- horizon={horizon} ---")
        for seed in SUBSET_SEEDS:
            for eval_day in EVAL_DAYS:
                stats, runtime_s = run_cell(seed, eval_day, horizon)
                rows.append({
                    "horizon": horizon, "seed": seed,
                    "eval_day": f"{eval_day[0]:04d}-{eval_day[1]:02d}-{eval_day[2]:02d}",
                    "tracking_error": stats["tracking_error"],
                    "total_energy_charged": stats["total_energy_charged"],
                    "total_transformer_overload": stats["total_transformer_overload"],
                    "average_user_satisfaction": stats["average_user_satisfaction"],
                    "runtime_s": runtime_s,
                })
        print(f"  {len(SUBSET_SEEDS)*len(EVAL_DAYS)} cells done for horizon={horizon}")

    df = pd.DataFrame(rows)
    df.to_csv("results/week5_horizon_sensitivity.csv", index=False)

    print("\n=== Summary: mean tracking_error / energy_charged / runtime by horizon ===")
    summary = df.groupby("horizon").agg(
        tracking_error_mean=("tracking_error", "mean"),
        tracking_error_std=("tracking_error", "std"),
        energy_charged_mean=("total_energy_charged", "mean"),
        overload_mean=("total_transformer_overload", "mean"),
        runtime_mean_s=("runtime_s", "mean"),
    )
    print(summary.to_string())
    summary.to_csv("results/week5_horizon_sensitivity_summary.csv")
    print("\nWrote results/week5_horizon_sensitivity.csv and _summary.csv")


if __name__ == "__main__":
    main()
