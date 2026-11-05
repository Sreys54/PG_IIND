"""
Week 8 advisor review, Block C runs (DC regime, station-level arrivals,
simulate_grid = False): C1 arms x levels 1.0x/1.3x/1.6x x 100 cases on the
8-port / 100 kW station, and the C4 infrastructure variants.

Each case appends its registry row (master schema + arrival_model +
safety_layer) and its per-case extras (exact DNS, A1 service metrics,
peaks, overload days, margin, post-hoc reward terms) to per-worker shards in
experiments/phase4_review/C/; --merge appends the new rows to
results/review_registry.csv (never rewriting existing rows) and writes
experiments/phase4_review/C/C_cases.csv.

Usage:
  PYTHONPATH=. python scripts/review_C_run.py --plan c1 --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_C_run.py --plan c1 --merge
  PYTHONPATH=. python scripts/review_C_run.py --plan td3 --td3 TD3_safe_ts100=<ckpt.zip> ... --state service_causal
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import get_git_commit
from scripts import review_dc

OUT = "experiments/phase4_review/C"
C1_ARMS = ["AFAP", "PS", "FIX12.5", "RR", "RR+S", "RR-TA", "Random+S", "MPC-soft", "MPC-soft-est", "Oracle-E"]


def plan_specs(plan, td3_arms=()):
    """(config path, arm, seed, day, notes) for a named plan."""
    out = []
    if plan == "c1":
        for lv in rc.LEVELS:
            cfg = rc.write_config(lv)
            out += [(cfg, arm, s, d, f"week8_C1,level={lv}") for arm in C1_ARMS for s in SEEDS for d in EVAL_DAYS]
    elif plan == "td3":
        for lv in rc.LEVELS:
            cfg = rc.write_config(lv)
            out += [(cfg, arm, s, d, f"week8_C3_test,level={lv}") for arm in td3_arms for s in SEEDS
                    for d in EVAL_DAYS]
    else:
        raise ValueError(plan)
    return out


def worker(plan, idx, n, td3=None, state=None):
    review_dc.process_hooks()
    if td3:
        from ev2gym_thesis.rl import config_safe as cfg
        for arm, path in td3.items():
            review_dc.register_td3_safe(arm, path, cfg.STATE_FNS[state])
    commit = get_git_commit()
    os.makedirs(OUT, exist_ok=True)
    rpath, epath = os.path.join(OUT, f"{plan}_registry_w{idx}.csv"), os.path.join(OUT, f"{plan}_cases_w{idx}.csv")
    done = set(pd.read_csv(epath).run_id) if os.path.exists(epath) else set()
    specs = plan_specs(plan, tuple(td3 or ()))
    for i, (cfg_path, arm, s, d, notes) in enumerate(specs):
        if i % n != idx:
            continue
        name = os.path.splitext(os.path.basename(cfg_path))[0]
        rid = f"{name}__{arm}__seed{s}__%04d-%02d-%02d" % d
        if rid in done:
            continue
        row, ex = review_dc.run_case(arm, cfg_path, s, d, "station", commit, notes=notes)
        review_dc.append_csv(rpath, row, review_dc.REVIEW_COLUMNS)
        review_dc.append_csv(epath, ex, CASE_FIELDS)
        if i % 100 == idx:
            print(i, len(specs), rid, round(row["runtime_s"], 2), flush=True)


CASE_FIELDS = ["run_id", "config_name", "algorithm", "seed", "eval_day", "day_type", "arrival_model",
               "safety_layer", "causal", "arrivals_offered", "arrivals_served", "arrivals_rejected",
               "dropped_horizon", "energy_offered_kwh", "energy_rejected_kwh", "energy_requested_served_kwh",
               "energy_delivered_kwh", "dns_exact", "n_served", "n_rejected", "mean_f_served", "mean_f_all",
               "service_level_served", "service_level_all", "sum_f", "n_f_ge_09", "mean_s_ev2gym_served",
               "max_identity_error_s", "connected_port_steps", "port_occupancy", "peak_station_kw", "overload_kwh",
               "overload_steps", "overload_day", "gross_margin_cop", "r_tracking", "r_overload", "r_user",
               "projection_active_steps"]


def merge(plan):
    reg = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT, f"{plan}_registry_w*.csv")))])
    cases = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT, f"{plan}_cases_w*.csv")))])
    reg = reg.drop_duplicates("run_id")
    cases = cases.drop_duplicates("run_id")
    cases.to_csv(os.path.join(OUT, f"{plan}_cases.csv"), index=False)
    path = review_dc.REVIEW_REGISTRY
    if os.path.exists(path):
        old = pd.read_csv(path, low_memory=False)
        reg = reg[~reg.run_id.isin(set(old.run_id))]
    new = not os.path.exists(path)
    reg[review_dc.REVIEW_COLUMNS].to_csv(path, mode="a", header=new, index=False)
    print(f"{plan}: {len(cases)} cases; appended {len(reg)} rows to {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--td3", nargs="*", default=None, help="arm=checkpoint.zip")
    ap.add_argument("--state", default="service_causal")
    a = ap.parse_args()
    td3 = dict(x.split("=", 1) for x in a.td3) if a.td3 else None
    merge(a.plan) if a.merge else worker(a.plan, a.worker, a.workers, td3, a.state)
