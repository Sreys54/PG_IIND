"""
Closure brief, Part E2: voltage on the one shipped feeder that is inside the
+/-5% band with the station idle (results/closure_feeder_probe_summary.csv:
node_123, 0 of 20 idle cells out of band, minimum 0.9738 p.u.).

Rule (brief E2): rerun voltage for AFAP and Round Robin at 1.0 / 1.3 / 1.6x
station demand; 50 seeds, or 20 if time is short. A timed run took 5.2 s, so
the full 50 seeds x both EVAL_DAYS were run (2 workers, to keep the laptop
responsive). No feeder parameter is tuned: load_multiplier 1.0, pv_scale 80,
the node_123 bus/branch files as shipped; the 8 stations sit on bus 115, the
electrically farthest bus (same rule as Week 7's bus 27).

Weekend day excluded (labelled scope reduction). EV2Gym's background-load
generator (ev2gym/models/data_augment.py::sample_data, lines 75-87) redraws
a whole 123-bus profile inside `while True` until no value is NaN or inf.
For the weekend EVAL_DAY (2022-03-05, copula days 5-6) a single environment
build ran for more than 240 s without finishing (stack sampled inside
multicopula.sample). The weekday (2022-01-17) builds in about 6 s. Fixing
this would mean editing or overriding EV2Gym's load model (a hard stop, and
a change to the feeder data), so only the weekday day is run: 50 seeds x 1
day; n_clusters = 50.

Per (level, seed, day): AFAP and Round Robin runs with simulate_grid=True;
the idle-station (zero-action) run is made at EVERY level. It cannot be
shared across levels: EV2Gym draws the EV population from the global NumPy
stream before grid.reset samples the background load, so a different spawn
multiplier changes the background-load draw of the same (seed, day). The
first analysis shared one idle run across levels and gave drops that
straddled zero at 1.3x; it was corrected to per-level idle runs, matching
Week 7's per-setting baseline. Written to shard CSVs and
merged into results/closure_ieee123_voltage_by_run.csv; nothing is written
to the registry (station metrics are recorded alongside to show they equal
the non-grid rows).

Usage:
  PYTHONPATH=. python scripts/closure_ieee123_voltage.py --prepare
  PYTHONPATH=. python scripts/closure_ieee123_voltage.py --worker 0 --n-workers 2
  PYTHONPATH=. python scripts/closure_ieee123_voltage.py --merge
"""
import argparse
import csv
import glob
import os
import time

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

from scripts import run_week7_grid as w7

BASE = "experiments/phase3_infra_replicability/configs/closure/feeder_probe_node123.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs/closure"
SHARD_DIR = "experiments/phase3_infra_replicability/results/closure_shards"
LEVELS = {1.0: 30, 1.3: 39, 1.6: 48}
STATION_BUS = 115
N_SEEDS = 50
RUN_DAYS = [EVAL_DAYS[0]]  # weekday only; see the module docstring
ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "idle"]
OUT = "results/closure_ieee123_voltage_by_run.csv"
FIELDS = ["level", "algorithm", "seed", "eval_day", "total_energy_charged", "total_transformer_overload",
          "average_user_satisfaction", "n_steps", "n_bus_steps_outside", "n_steps_any_bus_outside", "min_voltage_pu",
          "max_voltage_pu", "worst_bus", "excursion_pu_steps", "station_bus_min_voltage_pu", "station_bus_steps_outside"]


def config_path(level):
    return f"{CONFIG_DIR}/grid123_sp{LEVELS[level]}.yaml"


def prepare():
    src = open(BASE, encoding="utf-8").read()
    old = next(l for l in src.splitlines() if l.startswith("spawn_multiplier:"))
    for level, sp in LEVELS.items():
        with open(config_path(level), "w", encoding="utf-8") as f:
            f.write(src.replace(old, f"spawn_multiplier: {sp} # closure E2: {level}x on node_123"))
        print("wrote", config_path(level))


def specs():
    out = []
    for seed in SEEDS[:N_SEEDS]:
        for day in RUN_DAYS:
            for level in LEVELS:
                out.append((level, "idle", seed, day))
                for arm in ["ChargeAsFastAsPossible", "RoundRobin"]:
                    out.append((level, arm, seed, day))
    return out


def run_one(level, arm, seed, day, commit):
    path = config_path(level)
    name = os.path.basename(path)[:-5]
    if arm == "idle":
        env = make_env(path, day, seed, day_config_dir=f"{CONFIG_DIR}/_tmp_grid123_idle_pid{os.getpid()}")
        reset_for_evaluation(env, seed)
        done = False
        while not done:
            _, _, te, tr, _ = env.step(np.zeros(env.action_space.shape))
            done = te or tr
        v = env.node_voltage
        stats = {"total_energy_charged": 0.0, "total_transformer_overload": 0.0, "average_user_satisfaction": np.nan}
    else:
        row, v = w7.run_cell(arm, name, path, seed, day, commit)
        stats = {k: row[k] for k in ["total_energy_charged", "total_transformer_overload", "average_user_satisfaction"]}
    return {"level": level, "algorithm": arm, "seed": seed, "eval_day": "%04d-%02d-%02d" % day, **stats,
            **band_check(v, station_bus=STATION_BUS)}


def worker(idx, n):
    w7.enable_process_hooks()
    commit = get_git_commit()
    os.makedirs(SHARD_DIR, exist_ok=True)
    shard = f"{SHARD_DIR}/ieee123_w{idx}.csv"
    done = set()
    if os.path.exists(shard):
        d = pd.read_csv(shard)
        done = set(zip(d.level, d.algorithm, d.seed, d.eval_day))
    mine = [s for i, s in enumerate(specs()) if i % n == idx]
    t0 = time.time()
    for k, (level, arm, seed, day) in enumerate(mine):
        if (level, arm, seed, "%04d-%02d-%02d" % day) in done:
            continue
        rec = run_one(level, arm, seed, day, commit)
        new = not os.path.exists(shard)
        with open(shard, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow({c: rec.get(c) for c in FIELDS})
        print(f"w{idx} {k + 1}/{len(mine)} {level} {arm} s{seed} {rec['eval_day']} "
              f"out {rec['n_bus_steps_outside']} minV {rec['min_voltage_pu']:.4f} ({time.time() - t0:.0f}s)", flush=True)


def merge():
    d = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{SHARD_DIR}/ieee123_w*.csv"))], ignore_index=True)
    d = d.drop_duplicates(["level", "algorithm", "seed", "eval_day"])
    keep = d.eval_day.isin(["%04d-%02d-%02d" % x for x in RUN_DAYS])
    if (~keep).any():  # weekend runs finished by the first launch before it stalled
        print(f"dropping {int((~keep).sum())} runs outside RUN_DAYS (weekend), kept only in the shards")
    d = d[keep]
    d.to_csv(OUT, index=False)
    print(f"merged {len(d)} runs -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--worker", type=int)
    ap.add_argument("--n-workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--time-one", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare()
    elif a.merge:
        merge()
    elif a.time_one:
        w7.enable_process_hooks()
        t = time.time()
        print(run_one(1.0, "RoundRobin", 49, EVAL_DAYS[0], get_git_commit()), f"{time.time() - t:.1f}s")
    else:
        worker(a.worker, a.n_workers)
