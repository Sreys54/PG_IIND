"""
Week 7, Step 1b: grid bring-up equivalence check.

Runs AFAP and Round Robin on seeds 0-9 x both EVAL_DAYS under the non-grid
reference config and its grid-enabled variant, through the REAL heuristic
row builder (scripts/backfill_registry.run_single), and writes a paired
per-cell table. Nothing is appended to the registry.

TOLERANCE, FIXED BEFORE LOOKING AT ANY RESULT (2026-10-05): for every
compared metric, max |grid - non-grid| over the 40 paired cells must be
<= 1e-6 (absolute). Rationale: with ev2gym_thesis/grid/placement.py the
station is the same 8 ports on one 100 kW transformer, the EV population and
power setpoints are generated before the grid's own reset draws any random
numbers, and the feeder does not feed back into the station's power. The
station-level metrics should therefore be identical up to floating-point
noise; any larger difference is a divergence to be explained.

Usage: PYTHONPATH=. python scripts/week7_grid_equivalence.py
"""
import pandas as pd

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.grid import placement
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.rl import price_data_cache
from scripts.backfill_registry import run_single

NONGRID = ("station_v0_bogota", "experiments/phase1_baseline/configs/station_v0_bogota.yaml")
GRID = ("station_v0_bogota_grid", "experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml")
SEEDS_1B = list(range(10))
TOLERANCE_ABS = 1e-6
METRICS = ["total_ev_served", "total_energy_charged", "total_transformer_overload",
           "average_user_satisfaction", "tracking_error"]
OUT = "results/week7_grid_equivalence.csv"


def main():
    price_data_cache.enable()
    placement.enable()
    commit = get_git_commit()
    rows = []
    for algo_cls, name in [(ChargeAsFastAsPossible, "ChargeAsFastAsPossible"), (RoundRobin, "RoundRobin")]:
        for seed in SEEDS_1B:
            for day in EVAL_DAYS:
                pair = {}
                for tag, (cfg_name, cfg_path) in [("nongrid", NONGRID), ("grid", GRID)]:
                    r = run_single(cfg_name, cfg_path, 8, 100, algo_cls, name, "heuristic", seed, day, commit)
                    pair[tag] = r
                row = {"algorithm": name, "seed": seed, "eval_day": pair["grid"]["eval_day"]}
                for m in METRICS:
                    a, b = float(pair["nongrid"][m]), float(pair["grid"][m])
                    row[f"{m}_nongrid"], row[f"{m}_grid"], row[f"{m}_absdiff"] = a, b, abs(b - a)
                row["voltage_violation_grid"] = float(pair["grid"]["voltage_violation"])
                row["voltage_violation_counter_grid"] = float(pair["grid"]["voltage_violation_counter"])
                rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    summary = pd.DataFrame([{"metric": m, "mean_nongrid": df[f"{m}_nongrid"].mean(),
                             "mean_grid": df[f"{m}_grid"].mean(),
                             "max_abs_diff": df[f"{m}_absdiff"].max(),
                             "within_tolerance": bool(df[f"{m}_absdiff"].max() <= TOLERANCE_ABS),
                             "n_cells": len(df), "tolerance_abs": TOLERANCE_ABS} for m in METRICS])
    summary.to_csv(OUT.replace(".csv", "_summary.csv"), index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
