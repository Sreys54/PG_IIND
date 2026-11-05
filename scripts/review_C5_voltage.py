"""
Week 8 advisor review, C5: voltage on node_123 with the station-level
arrival generator.

Protocol (as the Final capacity brief's scripts/dwell_ieee123_voltage.py,
except the arrivals): node_123 as shipped (load_multiplier 1.0, pv_scale
80), the 8 ports on bus 115 (network_info.thesis_station_bus, placed by
ev2gym_thesis/grid/placement.py), simulate_grid = True, weekday only
(EV2Gym's background-load generator stalls on the weekend day for 123
buses), seeds 0-49, levels 1.0x and 1.6x, arms AFAP, PS, RR-TA and an idle
station (same stream, zero actions) as the matched baseline.

Reported per run: feeder minimum and maximum voltage, station-bus minimum
voltage, steps outside 0.95-1.05 p.u. (EV2Gym's fixed band, get_statistics)
and outside 0.90-1.10 p.u. (CREG 024 de 2005, steady state), feeder-wide and
at the station bus. Output: results/review_C5_voltage_by_run.csv
(post-processing data; grid rows never enter a non-grid statistic).

Usage:
  PYTHONPATH=. python scripts/review_C5_voltage.py --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_C5_voltage.py --merge
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.demand import station_arrivals as sa
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.rl import safety
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from scripts import review_dc

GRID_BASE = "experiments/phase3_infra_replicability/configs/dwell/grid123_dc42_sp30.yaml"
OUT_DIR = "experiments/phase4_review/C5"
OUT = "results/review_C5_voltage_by_run.csv"
STATION_BUS = 115
LEVELS = (1.0, 1.6)
ARMS = ["idle", "AFAP", "PS", "RR-TA"]
BANDS = {"ev2gym_095_105": (0.95, 1.05), "creg024_090_110": (0.90, 1.10)}


def grid_config(level, extra_connected_steps=0):
    """node_123 copy of the grid config + the calibrated station-arrivals sidecar."""
    os.makedirs(rc.CONFIG_DIR, exist_ok=True)
    name = f"grid123_bus115_poisson_{level:.2f}x" + (f"_conn+{extra_connected_steps}" if extra_connected_steps else "")
    path = f"{rc.CONFIG_DIR}/{name}.yaml"
    text = open(GRID_BASE, encoding="utf-8").read()
    text = re.sub(r"(?m)^spawn_multiplier: *[\d.]+.*$", "spawn_multiplier: 30 # NOT READ: station_arrivals sidecar", text)
    rc.write_if_changed(path, "# Week 8 review C5: node_123, station on bus 115, station-level "
                              "arrivals (sidecar)\n" + text)
    a = rc.calibrated_arrivals_per_day(level)
    sa.write_sidecar(path, sa.ArrivalSpec({"weekday": a, "weekend": a}, extra_connected_steps=extra_connected_steps,
                                          level=level, level_label=f"{level:.1f}x"))
    return path


def run_one(cfg, arm, seed, day):
    sa.enable(sa.spec_for_config(cfg))
    try:
        env = make_env(cfg, day, seed, day_config_dir=review_dc.DAY_CONFIG_DIR + "_grid")
        reset_for_evaluation(env, seed)
        act = None if arm == "idle" else review_dc.ARMS[arm][0](env, seed, day)
        layer = "none" if arm == "idle" else review_dc.ARMS[arm][1]
        for _ in range(env.simulation_length):
            a = np.zeros(env.number_of_ports) if act is None else act(env)
            if layer == "proportional":
                a, _ = safety.project_actions(env, a)
            _, _, _, _, stats = env.step(a)
        v = np.asarray(env.node_voltage, float)
        st_tr = env.transformers[env.charging_stations[0].connected_transformer]
        e = float(stats["total_energy_charged"])
        station_over = float(np.sum(np.maximum(0, env.current_power_usage - 100.0)) * env.timescale / 60)
    finally:
        sa.disable()
    rec = {"algorithm": arm, "seed": seed, "eval_day": "%04d-%02d-%02d" % day, "total_energy_charged": e,
           "station_overload_kwh": station_over, "station_transformer_id": st_tr.id}
    for band, (lo, hi) in BANDS.items():
        b = band_check(v, station_bus=STATION_BUS, low=lo, high=hi)
        rec.update({f"{band}_{k}": val for k, val in b.items()})
    return rec


def specs(extra):
    cfgs = {lv: grid_config(lv, extra) for lv in LEVELS}
    return [(lv, cfgs[lv], arm, s, EVAL_DAYS[0]) for lv in LEVELS for s in SEEDS for arm in ARMS]


def worker(idx, n, extra):
    review_dc.process_hooks()
    os.makedirs(OUT_DIR, exist_ok=True)
    path = f"{OUT_DIR}/voltage_w{idx}.csv"
    done = set()
    if os.path.exists(path):
        d = pd.read_csv(path)
        done = set(zip(d.level, d.algorithm, d.seed))
    for i, (lv, cfg, arm, s, d) in enumerate(specs(extra)):
        if i % n != idx or (lv, arm, s) in done:
            continue
        rec = {"level": lv, "config_name": os.path.basename(cfg)[:-5], **run_one(cfg, arm, s, d)}
        review_dc.append_csv(path, rec)
        if i % 40 == idx:
            print(i, lv, arm, s, round(rec["ev2gym_095_105_min_voltage_pu"], 4), flush=True)


def merge():
    df = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT_DIR}/voltage_w*.csv"))])
    df = df.drop_duplicates(["level", "algorithm", "seed"])
    df.to_csv(OUT, index=False)
    print(len(df), "runs ->", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--extra-connected-steps", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args()
    if not a.summarize:
        merge() if a.merge else worker(a.worker, a.workers, a.extra_connected_steps)


# doc:begin C5_summary
def summarize():
    """Per level x arm: feeder minimum and station-bus minimum voltage (mean
    over the 50 weekday cases, p.u.), paired differences vs the idle station
    and vs AFAP with 95% CIs (bootstrap over the 50 seeds, 10,000 resamples;
    one case per seed, so the seed is the resampling unit), and the number of
    cases with any bus-step outside 0.95-1.05 p.u. and 0.90-1.10 p.u.,
    feeder-wide and at the station bus. Physical vs statistical significance:
    the differences are reported in p.u. next to the band widths (0.05 and
    0.10 p.u.)."""
    from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
    df = pd.read_csv(OUT)
    rows = []
    for lv, g in df.groupby("level"):
        idx = lambda a: g[g.algorithm == a].set_index("seed").sort_index()
        idle, afap = idx("idle"), idx("AFAP")
        for arm in ARMS:
            x = idx(arm)
            one = np.ones(len(x))
            cl = x.index.values
            o = {"level": lv, "algorithm": arm, "n_cases": len(x), "n_clusters": len(cl)}
            for col, name in [("ev2gym_095_105_min_voltage_pu", "feeder_min_pu"),
                              ("ev2gym_095_105_station_bus_min_voltage_pu", "station_bus_min_pu")]:
                o[name] = float(x[col].mean())
                for ref, rname in [(idle, "idle"), (afap, "AFAP")]:
                    if arm in ("idle",) or (rname == "AFAP" and arm == "AFAP"):
                        continue
                    r = rci(ref.loc[cl, col].values, one, cl, x[col].values, one)
                    o.update({f"{name}_diff_vs_{rname}": r["point_estimate"], f"{name}_diff_vs_{rname}_ci_low": r["ci_low"],
                              f"{name}_diff_vs_{rname}_ci_high": r["ci_high"]})
            for band in BANDS:
                o[f"cases_any_bus_outside_{band}"] = int((x[f"{band}_n_bus_steps_outside"] > 0).sum())
                o[f"cases_station_bus_outside_{band}"] = int((x[f"{band}_station_bus_steps_outside"] > 0).sum())
            o["energy_kwh_per_day"] = float(x.total_energy_charged.mean())
            rows.append(o)
    out = pd.DataFrame(rows)
    out.to_csv("results/review_C5_voltage_summary.csv", index=False)
    print(out.round(5).to_string())
# doc:end C5_summary


if __name__ == "__main__" and "--summarize" in sys.argv:
    summarize()
