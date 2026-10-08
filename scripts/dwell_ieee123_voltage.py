"""
Last run, Part 3: voltage on node_123 under 42-minute DC sessions.

Same protocol as the closure run's Part E (scripts/closure_ieee123_voltage.py):
  - node_123, as shipped (load_multiplier 1.0, pv_scale 80); the station is
    on bus 115;
  - weekday only (EV2Gym's background-load generator stalls on the weekend
    day for 123 buses; reason in that script's docstring);
  - 50 seeds;
  - levels 1.0x / 1.3x / 1.6x;
  - an idle-station run at every level (matched baseline).
Arms: AFAP and the transformer-aware Round Robin
(ev2gym_thesis.heuristics.RoundRobinTransformerCapped).

Configs: the closure's grid123_sp{30,39,48}.yaml, copied to the dwell config
directory with a .dwell.json sidecar (mean 42 min, CV 0.5). Only the config
name and the sidecar differ. The DC transform is enabled for every run,
including idle, so the idle run has the same EV population and the same
background-load draw.

Output: results/dwell_ieee123_voltage_by_run.csv (post-processing data,
never the registry).

Usage:
  PYTHONPATH=. python scripts/dwell_ieee123_voltage.py --prepare
  PYTHONPATH=. python scripts/dwell_ieee123_voltage.py --worker 0 --n-workers 2
  PYTHONPATH=. python scripts/dwell_ieee123_voltage.py --merge
"""
import argparse
import csv
import glob
import json
import os
import shutil
import time

import numpy as np
import pandas as pd

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.demand import dc_sessions
from ev2gym_thesis.eval_protocol import SEEDS
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.heuristics import RoundRobinTransformerCapped
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

from scripts import closure_ieee123_voltage as c
from scripts import run_week7_grid as w7
from scripts.backfill_registry import run_single as heuristic_run_single

CONFIG_DIR = "experiments/phase3_infra_replicability/configs/dwell"
SHARD_DIR = "experiments/phase3_infra_replicability/results/dwell_shards"
OUT = "results/dwell_ieee123_voltage_by_run.csv"
RR_TA = "RoundRobin_TransformerCapped"
ARMS = {"ChargeAsFastAsPossible": ChargeAsFastAsPossible, RR_TA: RoundRobinTransformerCapped}


def config_path(level):
    return f"{CONFIG_DIR}/grid123_dc42_sp{c.LEVELS[level]}.yaml"


def prepare():
    for level in c.LEVELS:
        if not os.path.exists(c.config_path(level)):
            c.prepare()
        shutil.copyfile(c.config_path(level), config_path(level))
        with open(dc_sessions.sidecar_path(config_path(level)), "w", encoding="utf-8") as f:
            json.dump({"session_model": "lognormal connection duration, ev2gym_thesis/demand/dc_sessions.py",
                       "mean_min": 42.0, "cv": 0.5, "rounding": "nearest timestep, floor 1 step",
                       "label": "external reference, not Colombian (U.S. DOE 2023 / Hardman 2026)"}, f, indent=2)
        print("wrote", config_path(level))


def specs():
    out = []
    for seed in SEEDS[:c.N_SEEDS]:
        for day in c.RUN_DAYS:
            for level in c.LEVELS:
                out += [(level, arm, seed, day) for arm in ["idle", *ARMS]]
    return out


# doc:begin dwell_voltage_run
def run_one(level, arm, seed, day, commit):
    path = config_path(level)
    name = os.path.basename(path)[:-5]
    dc_sessions.enable(dc_sessions.model_for_config(path))
    try:
        if arm == "idle":
            env = make_env(path, day, seed, day_config_dir=f"{CONFIG_DIR}/_tmp_grid123_idle_pid{os.getpid()}")
            reset_for_evaluation(env, seed)
            done = False
            while not done:
                _, _, te, tr, _ = env.step(np.zeros(env.action_space.shape))
                done = te or tr
            v = env.node_voltage
            stats = {"total_energy_charged": 0.0, "total_transformer_overload": 0.0,
                     "average_user_satisfaction": np.nan}
        else:
            w7.LAST_VOLTAGE.clear()
            row = heuristic_run_single(name, path, 8, 100, ARMS[arm], arm, "heuristic", seed, day, commit)
            v = w7.LAST_VOLTAGE.get("v")
            if v is None:
                raise RuntimeError(f"{name} {arm} s{seed}: no voltage captured")
            stats = {k: row[k] for k in ["total_energy_charged", "total_transformer_overload",
                                         "average_user_satisfaction"]}
    finally:
        dc_sessions.disable()
    return {"level": level, "algorithm": arm, "seed": seed, "eval_day": "%04d-%02d-%02d" % day, **stats,
            **band_check(v, station_bus=c.STATION_BUS)}
# doc:end dwell_voltage_run


def worker(idx, n):
    w7.enable_process_hooks()
    commit = get_git_commit()
    os.makedirs(SHARD_DIR, exist_ok=True)
    shard = f"{SHARD_DIR}/ieee123_dc_w{idx}.csv"
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
            w = csv.DictWriter(f, fieldnames=c.FIELDS)
            if new:
                w.writeheader()
            w.writerow({k2: rec.get(k2) for k2 in c.FIELDS})
        print(f"w{idx} {k + 1}/{len(mine)} {level} {arm} s{seed} minV {rec['min_voltage_pu']:.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)


def merge():
    d = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{SHARD_DIR}/ieee123_dc_w*.csv"))], ignore_index=True)
    d = d.drop_duplicates(["level", "algorithm", "seed", "eval_day"])
    d.to_csv(OUT, index=False)
    print(f"merged {len(d)} runs -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--worker", type=int)
    ap.add_argument("--n-workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.prepare:
        prepare()
    elif a.merge:
        merge()
    else:
        worker(a.worker, a.n_workers)
