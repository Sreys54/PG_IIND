"""
Week 8 advisor review, C4: capacity and infrastructure under the
station-level arrival generator (demand is a station property, so port
variants keep the offered energy fixed).

Parts (the smallest grid proposed at Gate 0):
  threshold  RR-TA and PS at 8 and 10 ports, 100 kW: the largest
             arrivals/day with DNS <= 15% (ratio of totals, CI upper bound)
             AND mean energy satisfaction f including rejected drivers
             >= 0.90 (CI lower bound), by bisection on arrivals/day
             (7 steps between 0.5x and 1.6x of the 1.0x calibration),
             100 cases per step;
  ports16    1.6x, 100 kW: RR-TA and PS at 12, 14, 16 ports (8 and 10 come
             from C1/threshold), EV2Gym RR at 8-16 ports (RR does not read
             the rating, so the transformer it needs is read from its peak);
  afap300    AFAP at 8 ports with the 300 kVA unit (268.3 kW at pf 0.894)
             at 1.0x/1.3x/1.6x: identical actions to the 100 kW runs, only
             the overload accounting changes.
Every case goes to experiments/phase4_review/C4/ (cases + registry shards);
--merge appends registry rows to results/review_registry.csv.

Usage:
  PYTHONPATH=. python scripts/review_C4_capacity.py --part threshold --arm RR-TA --ports 8
  PYTHONPATH=. python scripts/review_C4_capacity.py --part grid --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_C4_capacity.py --merge
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from scripts import review_dc
from scripts.review_C_run import CASE_FIELDS

OUT = "experiments/phase4_review/C4"
DNS_MAX, F_MIN = 0.15, 0.90
KW_300KVA = 268.3


def evaluate_level(arm, ports, kw, arrivals, commit, tag, extra=0, energy_scale=1.0):
    cfg = rc.write_config(None, ports=ports, kw=kw, arrivals_per_day=arrivals, extra_connected_steps=extra,
                          tag=tag, energy_scale=energy_scale)
    cases = []
    for s in SEEDS:
        for d in EVAL_DAYS:
            row, ex = review_dc.run_case(arm, cfg, s, d, "station", commit, notes=f"week8_C4,{tag}")
            review_dc.append_csv(f"{OUT}/registry_{tag}.csv", row, review_dc.REVIEW_COLUMNS)
            review_dc.append_csv(f"{OUT}/cases_{tag}.csv", {**ex, "arrivals_per_day": arrivals, "ports": ports,
                                                            "transformer_kw": kw}, CASE_FIELDS +
                                 ["arrivals_per_day", "ports", "transformer_kw"])
            cases.append(ex)
    return judge(pd.DataFrame(cases))


def judge(g):
    cl = g.seed.values
    dns = rci(g.energy_offered_kwh - g.energy_delivered_kwh, g.energy_offered_kwh, cl)
    f = rci(g.sum_f, g.n_served + g.n_rejected, cl)
    return {"dns": dns["point_estimate"], "dns_ci_high": dns["ci_high"], "mean_f_all": f["point_estimate"],
            "mean_f_all_ci_low": f["ci_low"], "offered_kwh": float(g.energy_offered_kwh.mean()),
            "offered_arrivals": float(g.arrivals_offered.mean()),
            "meets": bool(dns["ci_high"] <= DNS_MAX and f["ci_low"] >= F_MIN), "n_clusters": dns["n_clusters"]}


# doc:begin bisection
def threshold(arm, ports, kw=100.0, steps=7, extra=0, energy_scale=1.0, label=""):
    """Largest arrivals/day meeting both targets, by bisection (the stream is
    nested across arrivals/day, so service degrades monotonically up to
    sampling noise; every evaluated level is logged, not only the bracket)."""
    review_dc.process_hooks()
    commit = get_git_commit()
    a1 = rc.calibrated_arrivals_per_day(1.0)
    lo, hi = 0.5 * a1, 1.6 * a1 * 1.0
    log = []
    tag = lambda a: f"thr{label}_{arm}_p{ports}_tr{kw:g}_a{a:.3f}".replace("+", "p")
    ev = lambda a: evaluate_level(arm, ports, kw, a, commit, tag(a), extra, energy_scale)
    r_lo = ev(lo)
    log.append({"arrivals_per_day": lo, **r_lo})
    if not r_lo["meets"]:
        return log, None
    r_hi = ev(hi)
    log.append({"arrivals_per_day": hi, **r_hi})
    if r_hi["meets"]:
        return log, hi
    for _ in range(steps):
        mid = (lo + hi) / 2
        r = ev(mid)
        log.append({"arrivals_per_day": mid, **r})
        lo, hi = (mid, hi) if r["meets"] else (lo, mid)
    return log, lo
# doc:end bisection


def grid_specs():
    out = []
    a16 = rc.calibrated_arrivals_per_day(1.6)
    for arm in ("RR-TA", "PS"):
        out += [(arm, p, 100.0, a16, "1.6x") for p in (12, 14, 16)]
    out += [("RR", p, 100.0, a16, "1.6x") for p in (10, 12, 14, 16)]
    out += [("AFAP", 8, KW_300KVA, rc.calibrated_arrivals_per_day(lv), f"{lv}x") for lv in rc.LEVELS]
    # added 2026-11-03 after the first C4 result (ports never bind at 1.6x): the transformer RR-TA
    # and PS need at 1.6x with 8 ports, on the ET-013 sizes 150 / 225 / 300 kVA
    out += [(arm, 8, kw, a16, "1.6x") for arm in ("RR-TA", "PS") for kw in (134.2, 201.2, 268.3)]
    return out


def grid_worker(idx, n, extra=0):
    review_dc.process_hooks()
    commit = get_git_commit()
    for i, (arm, p, kw, a, lv) in enumerate(grid_specs()):
        if i % n != idx:
            continue
        tag = f"grid_{arm}_p{p}_tr{kw:g}_{lv}"
        if os.path.exists(f"{OUT}/cases_{tag}.csv") and len(pd.read_csv(f"{OUT}/cases_{tag}.csv")) >= 100:
            continue
        r = evaluate_level(arm, p, kw, a, commit, tag, extra)
        print(tag, r, flush=True)


def merge():
    cases = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/cases_*.csv"))]).drop_duplicates("run_id")
    cases.to_csv(f"{OUT}/C4_cases.csv", index=False)
    reg = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/registry_*.csv"))]).drop_duplicates("run_id")
    path = review_dc.REVIEW_REGISTRY
    if os.path.exists(path):
        reg = reg[~reg.run_id.isin(set(pd.read_csv(path, low_memory=False).run_id))]
    reg[review_dc.REVIEW_COLUMNS].to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    print(len(cases), "C4 cases; appended", len(reg), "registry rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["threshold", "grid"], default=None)
    ap.add_argument("--arm", default="RR-TA")
    ap.add_argument("--ports", type=int, default=8)
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--extra-connected-steps", type=int, default=0)
    ap.add_argument("--energy-scale-file", default=None, help="Block D3: file holding the energy scale")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.merge:
        merge()
    elif a.part == "threshold":
        es = float(open(a.energy_scale_file).read()) if a.energy_scale_file else 1.0
        label = "_d3e22" if a.energy_scale_file else ""
        log, best = threshold(a.arm, a.ports, extra=a.extra_connected_steps, energy_scale=es, label=label)
        out = f"{OUT}/threshold{label}_{a.arm}_p{a.ports}.json"
        json.dump({"arm": a.arm, "ports": a.ports, "transformer_kw": 100.0, "threshold_arrivals_per_day": best,
                   "energy_scale": es,
                   "criteria": f"DNS CI high <= {DNS_MAX} and mean f incl. rejected CI low >= {F_MIN}",
                   "log": log}, open(out, "w"), indent=2)
        print(out, best)
    else:
        grid_worker(a.worker, a.workers, a.extra_connected_steps)
