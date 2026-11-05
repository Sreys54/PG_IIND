"""
Week 8 advisor review, Gate 1: EV2Gym's per-port spawner vs the station-level
arrival generator, in the DC regime, for AFAP and RR-TA; and how the
capacity threshold and the port recommendation move without the dead time.

Variants (each isolates one change from the previous one):
  V0 spawner          EV2Gym spawner + DC durations (dc_sessions.py), the
                      Final-capacity-brief configuration (spawn 30 = 1.0x);
  V1 station_conn1_dead2  station-level Poisson arrivals, old connection
                      convention (connected n + 1 steps) and EV2Gym's dead
                      time (port reusable 2 steps after the departure step):
                      V1 - V0 = pooling the arrivals at station level;
  V2 station_conn1    as V1, no dead time: V2 - V1 = the dead time;
  V3 station          as V2, connected exactly the sampled n steps: V3 - V2 =
                      the connection-window convention.
Levels 1.0x/1.3x/1.6x (offered energy 627/815/1,003 kWh/day) x 8/10 ports for
V1-V3; V0 at 1.0x and 8 ports only (its other levels are in
results/dwell_registry.csv). 100 cases each (seeds 0-49 x 2 days).

Usage:
  PYTHONPATH=. python scripts/review_gate1.py --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_gate1.py --merge
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

OUT_DIR = "experiments/phase4_review/gate1"
SPAWNER_CFG = rc.BASE_CONFIG
VARIANTS = {"V1_station_conn1_dead2": dict(extra_connected_steps=1, dead_time_steps=2),
            "V2_station_conn1": dict(extra_connected_steps=1, dead_time_steps=0),
            "V3_station": dict(extra_connected_steps=0, dead_time_steps=0)}
ARMS = ["AFAP", "RR-TA"]


def specs():
    out = [("V0_spawner", SPAWNER_CFG, "spawner", 1.0, 8, arm, s, d) for arm in ARMS for s in SEEDS for d in EVAL_DAYS]
    for v, kw in VARIANTS.items():
        for level in rc.LEVELS:
            for ports in (8, 10):
                cfg = rc.write_config(level, ports=ports, **kw)
                out += [(v, cfg, "station", level, ports, arm, s, d) for arm in ARMS for s in SEEDS for d in EVAL_DAYS]
    return out


def worker(idx, n):
    review_dc.process_hooks()
    commit = get_git_commit()
    path = os.path.join(OUT_DIR, f"cases_w{idx}.csv")
    done = set()
    if os.path.exists(path):
        done = set(zip(pd.read_csv(path).variant, pd.read_csv(path).run_id))
    all_specs = specs()
    for i, (v, cfg, arrival, level, ports, arm, s, d) in enumerate(all_specs):
        if i % n != idx:
            continue
        row, ex = review_dc.run_case(arm, cfg, s, d, arrival, commit, notes="week8_gate1")
        if (v, row["run_id"]) in done:
            continue
        ex.update({"variant": v, "level": level, "ports": ports, "total_transformer_overload":
                   row["total_transformer_overload"], "average_user_satisfaction": row["average_user_satisfaction"],
                   "total_ev_served": row["total_ev_served"], "runtime_s": row["runtime_s"]})
        review_dc.append_csv(path, ex, FIELDS)
        if i % 100 == idx:
            print(i, len(all_specs), v, level, ports, arm, s, d, round(row["runtime_s"], 2), flush=True)


FIELDS = ["variant", "level", "ports", "algorithm", "seed", "eval_day", "day_type", "run_id", "config_name",
          "arrival_model", "safety_layer", "causal", "arrivals_offered", "arrivals_served", "arrivals_rejected",
          "arrivals_offered_lower", "arrivals_offered_upper", "arrivals_rejected_lower", "arrivals_rejected_upper",
          "dropped_horizon", "energy_offered_kwh", "energy_offered_lower_kwh", "energy_offered_upper_kwh",
          "energy_rejected_kwh", "energy_rejected_lower_kwh", "energy_rejected_upper_kwh",
          "energy_requested_served_kwh", "energy_delivered_kwh", "dns_exact", "dns_lower", "dns_upper",
          "n_served", "mean_f_served", "mean_f_all", "mean_f_all_lower", "mean_f_all_upper",
          "service_level_served", "service_level_all", "service_level_all_lower", "service_level_all_upper",
          "mean_s_ev2gym_served", "average_user_satisfaction", "max_identity_error_s", "total_ev_served",
          "connected_port_steps", "port_occupancy", "peak_station_kw", "overload_kwh", "total_transformer_overload",
          "overload_steps", "overload_day", "gross_margin_cop", "r_tracking", "r_overload", "r_user",
          "projection_active_steps", "runtime_s"]


def merge():
    df = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT_DIR, "cases_w*.csv")))])
    df = df.drop_duplicates(["variant", "run_id"])
    df.to_csv(os.path.join(OUT_DIR, "gate1_cases.csv"), index=False)
    print(len(df), "cases")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--count", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge()
    elif a.count:
        print(len(specs()))
    else:
        worker(a.worker, a.workers)
