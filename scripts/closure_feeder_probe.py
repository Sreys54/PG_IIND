"""
Closure brief, Part E2: is any feeder shipped with EV2Gym inside the
+/-5% band (0.95-1.05 p.u.) with the station idle, at nominal load?

For each network in ev2gym/data/network_data (node_25, node_34, node_69,
node_123) the Week 7 grid config is copied with only the bus/branch files and
the station bus changed (station bus = the electrically farthest bus,
ev2gym_thesis/grid/placement.electrical_distance, the same rule as Week 7).
Load multiplier 1.0 and pv_scale 80 are unchanged: no parameter is tuned to
bring a feeder into band. The station is idle (every action 0), so only the
feeder's own background load and PV are simulated. Screening only: seeds 0-9
x both EVAL_DAYS; nothing is written to the registry.

Qualifying criterion (stated before the run): no bus outside the band in
any step of any of the 20 cells. One out-of-band cell therefore decides that
a feeder does not qualify, so the screen stops a feeder at its first
out-of-band cell (rows are written cell by cell; a first, unbounded run
showed node_34 out of band in 15 of 20 cells, minimum 0.9311 p.u., but was
cut off by a shell timeout during node_123 before writing its CSV).

node_25 and node_69 ship bus files with only NODES and Tb columns (no PD/QD
nominal loads), so EV2Gym's Laurent power flow cannot build them
(grid_tensor.py line 83 reads column 2). They are recorded as "not runnable
as shipped"; no load data is invented for them.

Usage: PYTHONPATH=. python scripts/closure_feeder_probe.py
"""
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.grid.placement import electrical_distance
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

from scripts import run_week7_grid as w7

BASE_GRID_CONFIG = "experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs/closure"
FEEDERS = {25: ("node_25/Nodes_25.csv", "node_25/Lines_25.csv"),
           34: ("node_34/Nodes_34.csv", "node_34/Lines_34.csv"),
           69: ("node_69/Nodes_69.csv", "node_69/Lines_69.csv"),
           123: ("node_123/Nodes_123.csv", "node_123/Lines_123.csv")}
SEEDS = list(range(10))
OUT = "results/closure_feeder_probe.csv"


def feeder_config(n):
    nodes, lines = (f"./ev2gym/data/network_data/{p}" for p in FEEDERS[n])
    bus = int(electrical_distance(lines.lstrip("./"), nodes.lstrip("./")).bus.iloc[0])
    src = open(BASE_GRID_CONFIG, encoding="utf-8").read().splitlines()
    out = []
    for line in src:
        s = line.strip()
        if s.startswith("bus_info_file:"):
            line = f"  bus_info_file: '{nodes}' # closure E2 feeder probe"
        elif s.startswith("branch_info_file:"):
            line = f"  branch_info_file: '{lines}' # closure E2 feeder probe"
        elif s.startswith("thesis_station_bus:"):
            line = f"  thesis_station_bus: {bus} # closure E2: electrically farthest bus of node_{n}"
        out.append(line)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    path = f"{CONFIG_DIR}/feeder_probe_node{n}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return path, bus


def main():
    w7.enable_process_hooks()
    rows, not_runnable = [], []
    for n in FEEDERS:
        cols = pd.read_csv(f"ev2gym/data/network_data/{FEEDERS[n][0]}", nrows=1).columns.tolist()
        if "PD" not in cols:
            not_runnable.append({"feeder": f"node_{n}", "bus_file_columns": ";".join(cols),
                                 "reason": "no PD/QD nominal-load columns; Laurent power flow cannot be built"})
            print(f"node_{n}: not runnable as shipped (columns {cols})", flush=True)
            continue
        path, bus = feeder_config(n)
        for seed in SEEDS:
            for day in EVAL_DAYS:
                env = make_env(path, day, seed, day_config_dir=f"{CONFIG_DIR}/_tmp_feeder_probe_pid{os.getpid()}")
                reset_for_evaluation(env, seed)
                done = False
                while not done:
                    _, _, te, tr, _ = env.step(np.zeros(env.action_space.shape))
                    done = te or tr
                rows.append({"feeder": f"node_{n}", "n_buses": int(env.grid.node_num), "station_bus": bus,
                             "seed": seed, "eval_day": "%04d-%02d-%02d" % day,
                             **band_check(env.node_voltage, station_bus=bus)})
                pd.DataFrame(rows).to_csv(OUT, index=False)
                print(f"node_{n} seed {seed} {rows[-1]['eval_day']}: outside {rows[-1]['n_bus_steps_outside']}, "
                      f"min V {rows[-1]['min_voltage_pu']:.4f}", flush=True)
                if rows[-1]["n_bus_steps_outside"] > 0:
                    break
            if rows[-1]["n_bus_steps_outside"] > 0:
                break
        g = pd.DataFrame([r for r in rows if r["feeder"] == f"node_{n}"])
        print(f"node_{n}: cells with any bus out of band {int((g.n_bus_steps_outside > 0).sum())}/{len(g)}, "
              f"min V {g.min_voltage_pu.min():.4f}, max V {g.max_voltage_pu.max():.4f}, station bus {bus}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    s = out.groupby("feeder").agg(n_buses=("n_buses", "first"), station_bus=("station_bus", "first"),
                                  cells_screened=("seed", "size"),
                                  cells_out_of_band=("n_bus_steps_outside", lambda x: int((x > 0).sum())),
                                  min_v=("min_voltage_pu", "min"), max_v=("max_voltage_pu", "max"))
    s["qualifies_in_band_idle"] = s.cells_out_of_band == 0
    s["runnable_as_shipped"] = True
    nr = pd.DataFrame(not_runnable).set_index("feeder").assign(runnable_as_shipped=False, qualifies_in_band_idle=False)
    s = pd.concat([s, nr[["runnable_as_shipped", "qualifies_in_band_idle", "reason"]]])
    s.to_csv("results/closure_feeder_probe_summary.csv")
    print(s.to_string())


if __name__ == "__main__":
    main()
