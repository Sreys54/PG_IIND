"""
Week 7, Objective 4: zero-charging voltage baseline for every Step 2 cell.

For each growth setting x scenario seed x EVAL_DAY, steps the grid env with
every action = 0 (the feeder's background load and PV only, the station
idle) and records band_check. Lets chapter 06 attribute voltage-band
excursions to the station (arm minus zero-charging, same cell) rather than
to the feeder. Diagnostic only: not an arm, never written to the registry.

Usage: PYTHONPATH=. python scripts/week7_zero_charging_baseline.py --seeds 50
"""
import argparse

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from scripts import run_week7_grid as w7

OUT = "results/week7_voltage_zero_charging_baseline.csv"


def main(n_seeds):
    w7.enable_process_hooks()
    rows = []
    for st in w7.SETTINGS:
        name, path = w7.setting_config(st)
        for seed in SEEDS[:n_seeds]:
            for day in EVAL_DAYS:
                env = make_env(path, day, seed, day_config_dir=f"{w7.CONFIG_DIR}/_tmp_zero_day_configs")
                reset_for_evaluation(env, seed)
                done = False
                while not done:
                    _, _, te, tr, _ = env.step(np.zeros(env.action_space.shape))
                    done = te or tr
                rows.append({"setting": st, "config_name": name, "seed": seed, "eval_day": "%04d-%02d-%02d" % day,
                             **band_check(env.node_voltage, station_bus=w7.STATION_BUS)})
        print(f"{st}: done", flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    main(ap.parse_args().seeds)
