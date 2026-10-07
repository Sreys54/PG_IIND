"""
Closure brief, Part B: rejected (never-spawned) arrivals and demand not served
for the existing Step 2 rows -- computed in post-processing, never written
to the registry (new workbook, not a new column).

Censoring depends only on (spawn_multiplier, day, scenario seed): arrivals
are generated at reset, before any action, and the feeder (Axis 2) does not
touch the EV population. So it is computed once per (demand level, seed,
day) on the NON-grid config with the same spawn_multiplier (identical EV
population to the grid config, verified in Week 7: 0.0 difference), and
joined to every arm's energy delivered.

Usage: PYTHONPATH=. python scripts/closure_demand_censoring.py --levels 1.0,1.3,1.6
       (any level list; used again by Part C for its own levels)
       PYTHONPATH=. python scripts/closure_demand_censoring.py --levels 0.75,1.0 --ports 10,12
       (Part C2 port variants: censoring depends on the number of ports, not
       on the transformer limit, so the _tx100 variant configs written by
       run_closure_capacity.py --prepare are used; results go to a separate
       file, keyed by ports, and the 8-port table is never rewritten)
"""
import argparse
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.demand.censoring import scenario_demand
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.rl import price_data_cache

BASE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs/closure"
BASE_SPAWN = 30
OUT = "results/closure_censoring_by_cell.csv"
OUT_PORTS = "results/closure_censoring_port_variants_by_cell.csv"


def config_for_level(level: float) -> str:
    """Non-grid reference config with spawn_multiplier = round(30 x level);
    only that one line differs (text replacement keeps every comment)."""
    sp = int(round(BASE_SPAWN * level))
    if sp == BASE_SPAWN:
        return BASE_CONFIG
    os.makedirs(CONFIG_DIR, exist_ok=True)
    src = open(BASE_CONFIG, encoding="utf-8").read()
    old = next(l for l in src.splitlines() if l.startswith("spawn_multiplier:"))
    path = f"{CONFIG_DIR}/station_v0_bogota_sp{sp}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        f.write(src.replace(old, f"spawn_multiplier: {sp} # closure brief demand level {level}x (base 30)"))
    return path


def port_variant_config(level: float, ports: int, cd: bool = False) -> str:
    """C2 port-variant config (100 kW limit), written once by
    run_closure_capacity.py --prepare; never rewritten here. cd=True is the
    constant-station-demand variant (spawn_multiplier scaled by 8/ports)."""
    path = (f"{CONFIG_DIR}/station_v0_bogota_sp{int(round(BASE_SPAWN * level))}_p{ports}_tx100"
            + ("_cd" if cd else "") + ".yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing -- run scripts/run_closure_capacity.py --prepare first")
    return path


def censoring_table(levels, n_seeds=50, ports=8, cd=False):
    out_path = OUT if ports == 8 else OUT_PORTS
    done = pd.read_csv(out_path) if os.path.exists(out_path) else pd.DataFrame(columns=["level", "seed", "eval_day"])
    if ports != 8 and len(done):
        if "constant_demand" not in done.columns:
            done["constant_demand"] = False
        done["constant_demand"] = done.constant_demand.astype(str) == "True"
        done_p = done[(done.ports.astype(int) == ports) & (done.constant_demand == cd)]
    else:
        done_p = done
    have = set(zip(done_p.level.astype(float).round(4), done_p.seed.astype(int), done_p.eval_day)) if len(done_p) else set()
    rows = []
    for lvl in levels:
        path = config_for_level(lvl) if ports == 8 else port_variant_config(lvl, ports, cd)
        for seed in SEEDS[:n_seeds]:
            for day in EVAL_DAYS:
                ds = "%04d-%02d-%02d" % day
                if (round(lvl, 4), seed, ds) in have:
                    continue
                r = scenario_demand(path, day, seed, f"{CONFIG_DIR}/_tmp_censor_day_configs_pid{os.getpid()}")
                row = {"level": lvl, "spawn_multiplier": int(round(BASE_SPAWN * lvl)), "seed": seed,
                       "eval_day": ds, **r}
                if ports != 8:
                    row = {"ports": ports, "constant_demand": cd, **row}
                rows.append(row)
        print(f"level {lvl}, {ports} ports{' (constant demand)' if cd else ''}: censoring done", flush=True)
    out = pd.concat([done, pd.DataFrame(rows)], ignore_index=True) if rows else done
    out.to_csv(out_path, index=False)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="1.0,1.3,1.6")
    ap.add_argument("--ports", default="8", help="comma list; 8 = the reference table, others = C2 variants")
    ap.add_argument("--constant-demand", action="store_true", help="the C2 _cd variants (spawn scaled by 8/ports)")
    a = ap.parse_args()
    price_data_cache.enable()
    for p in [int(x) for x in a.ports.split(",")]:
        t = censoring_table([float(x) for x in a.levels.split(",")], ports=p, cd=a.constant_demand)
    keys = ["level"] if "ports" not in t.columns else ["constant_demand", "ports", "level"]
    print(t.groupby(keys)[["n_spawned", "rejected_lower", "rejected_upper", "dropped_late_horizon",
                              "energy_rejected_lower_kwh", "requested_served_kwh"]].mean().round(2).to_string())
