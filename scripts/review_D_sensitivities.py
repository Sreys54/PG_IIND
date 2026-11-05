"""
Week 8 advisor review, Block D: DC sensitivities (advisor 3.11), in order,
each for AFAP, RR-TA and PS at 1.0x and 1.6x on the 8-port / 100 kW station
with the station-level arrival generator; paired against the C1 base runs
(same seeds, same stream).

  D1 load-dependent departure: a driver whose sampled dwell has ended stays
     while the battery is below the desired level, at most 90 min after
     arrival (station_arrivals.ArrivalSpec.load_dependent_departure_cap_min);
  D2 5-minute step (timescale 5, 288 steps; the dwell is rounded to 5 min,
     EV2Gym's median filter window scales itself, 5 x 15 / timescale);
  D3 22 kWh per session: every driver's requested energy scaled so that the
     stream's mean is 22.0 kWh (the DC reference), arrivals/day unchanged, so
     offered kWh/day rises; plus the RR-TA capacity threshold under D3.

Usage:
  PYTHONPATH=. python scripts/review_D_sensitivities.py --part d1 --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_D_sensitivities.py --merge
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.demand import station_arrivals as sa
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import get_git_commit
from scripts import review_dc
from scripts.review_C_run import CASE_FIELDS

OUT = "experiments/phase4_review/D"
ARMS = ["AFAP", "RR-TA", "PS"]
LEVELS = (1.0, 1.6)
TARGET_SESSION_KWH = 22.0


def energy_scale_for_22kwh():
    """Scale s such that the mean requested energy of the 1.0x streams (100
    cases) is 22.0 kWh after the battery cap (bisection; logged)."""
    from ev2gym_thesis.rl.env_factory import make_env
    envs = [make_env(rc.BASE_CONFIG, d, 0, day_config_dir=review_dc.DAY_CONFIG_DIR + "_d3")
            for d in rc.CALIBRATION_DAYS]
    a = rc.calibrated_arrivals_per_day(1.0)
    lo, hi = 1.0, 2.0
    for _ in range(25):
        mid = (lo + hi) / 2
        n, e = rc.offered_mean(a, envs, spec_kwargs={"energy_scale": mid})
        lo, hi = (mid, hi) if e / n < TARGET_SESSION_KWH else (lo, mid)
    return (lo + hi) / 2


def config(part, level):
    if part == "d1":
        return rc.write_config(level, load_dependent_departure_cap_min=90.0, tag="d1cap90")
    if part == "d2":
        return rc.write_config(level, timescale=5, tag="d2ts5")
    if part == "d3":
        s = float(open(f"{OUT}/d3_energy_scale.txt").read())
        return rc.write_config(level, energy_scale=s, tag="d3e22")
    raise ValueError(part)


def worker(part, idx, n):
    review_dc.process_hooks()
    commit = get_git_commit()
    os.makedirs(OUT, exist_ok=True)
    if part == "d3" and not os.path.exists(f"{OUT}/d3_energy_scale.txt"):
        open(f"{OUT}/d3_energy_scale.txt", "w").write(repr(energy_scale_for_22kwh()))
    specs = [(lv, arm, s, d) for lv in LEVELS for arm in ARMS for s in SEEDS for d in EVAL_DAYS]
    path = f"{OUT}/{part}_cases_w{idx}.csv"
    done = set(pd.read_csv(path).run_id) if os.path.exists(path) else set()
    cfgs = {lv: config(part, lv) for lv in LEVELS}
    for i, (lv, arm, s, d) in enumerate(specs):
        if i % n != idx:
            continue
        cfg = cfgs[lv]
        rid = f"{os.path.splitext(os.path.basename(cfg))[0]}__{arm}__seed{s}__%04d-%02d-%02d" % d
        if rid in done:
            continue
        row, ex = review_dc.run_case(arm, cfg, s, d, "station", commit, notes=f"week8_{part}")
        review_dc.append_csv(f"{OUT}/{part}_registry_w{idx}.csv", row, review_dc.REVIEW_COLUMNS)
        review_dc.append_csv(path, {**ex, "part": part, "level": lv}, CASE_FIELDS + ["part", "level"])
        if i % 60 == idx:
            print(part, i, len(specs), row["run_id"], round(row["runtime_s"], 2), flush=True)


def merge():
    for kind in ("cases", "registry"):
        files = sorted(glob.glob(f"{OUT}/d*_{kind}_w*.csv"))
        if not files:
            continue
        df = pd.concat([pd.read_csv(p) for p in files]).drop_duplicates("run_id")
        if kind == "cases":
            df.to_csv(f"{OUT}/D_cases.csv", index=False)
        else:
            path = review_dc.REVIEW_REGISTRY
            if os.path.exists(path):
                df = df[~df.run_id.isin(set(pd.read_csv(path, low_memory=False).run_id))]
            df[review_dc.REVIEW_COLUMNS].to_csv(path, mode="a", header=not os.path.exists(path), index=False)
        print(kind, len(df))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["d1", "d2", "d3"])
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    merge() if a.merge else worker(a.part, a.worker, a.workers)
