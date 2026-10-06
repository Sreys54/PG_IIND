"""
Week 7, Step 1d: when does the voltage metric trip?

Probe rows (analysis_row=False, superseded=False, notes "probe=voltage_trip")
for AFAP and Round Robin on seeds 0-9 x both EVAL_DAYS, at spawn_multiplier
30 (Week 5 value) and load_multiplier in PROBE_LOAD_MULTIPLIERS, written to
shard files and merged into the registry once. A zero-charging diagnostic
(every action 0, i.e. the feeder's background load and PV only, no EV power)
runs on the same cells and is written to a separate CSV only -- it is not an
algorithm arm and never enters the registry.

Usage: PYTHONPATH=. python scripts/week7_voltage_probe.py
"""
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.registry import REGISTRY_COLUMNS, append_runs, get_git_commit
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

from scripts import run_week7_grid as w7
from scripts.evaluate_mpc import analysis_row_existing_keys

PROBE_LOAD_MULTIPLIERS = [0.5, 0.7, 0.8, 0.9, 1.0]
PROBE_SEEDS = list(range(10))
PROBE_ARMS = ["ChargeAsFastAsPossible", "RoundRobin"]
OUT_VOLT = "results/week7_voltage_probe.csv"
OUT_ZERO = "results/week7_voltage_probe_zero_charging.csv"


def main():
    w7.enable_process_hooks()
    commit = get_git_commit()
    existing = {k for k in analysis_row_existing_keys()}
    regrows, volt, zero = [], [], []
    for lm in PROBE_LOAD_MULTIPLIERS:
        probe = {"spawn_multiplier": w7.BASE_SPAWN_MULTIPLIER, "load_multiplier": lm}
        name = w7.config_name_for(None, probe)
        path = w7.write_config(name, probe["spawn_multiplier"], lm)
        for seed in PROBE_SEEDS:
            for day in EVAL_DAYS:
                for arm in PROBE_ARMS:
                    row, v = w7.run_cell(arm, name, path, seed, day, commit)
                    row["analysis_row"] = False
                    row["superseded"] = False
                    row["notes"] = (row["notes"] or "") + (f",probe=voltage_trip,station_bus={w7.STATION_BUS},"
                                                           f"spawn_multiplier=30,load_multiplier={lm}")
                    regrows.append({c: row.get(c) for c in REGISTRY_COLUMNS})
                    volt.append({**w7.voltage_record(row, v, f"probe_lm{lm}"), "load_multiplier": lm})
                env = make_env(path, day, seed, day_config_dir=f"{w7.CONFIG_DIR}/_tmp_probe_day_configs")
                reset_for_evaluation(env, seed)
                done = False
                while not done:
                    _, _, te, tr, _ = env.step(np.zeros(env.action_space.shape))
                    done = te or tr
                zero.append({"load_multiplier": lm, "seed": seed, "eval_day": "%04d-%02d-%02d" % day,
                             **band_check(env.node_voltage, station_bus=w7.STATION_BUS)})
        print(f"load_multiplier={lm}: done", flush=True)
    todo = [r for r in regrows if (r["config_name"], r["algorithm"], str(r["seed"]), r["eval_day"]) not in existing]
    res = append_runs(todo, force=True)
    pd.DataFrame(volt).to_csv(OUT_VOLT, index=False)
    pd.DataFrame(zero).to_csv(OUT_ZERO, index=False)
    print(f"probe rows appended: {res['appended']} (analysis_row=False)")


if __name__ == "__main__":
    main()
