"""
Week 7, Objective 4: place the whole station on ONE bus of EV2Gym's
34-node feeder.

Why this exists. With simulate_grid=True, EV2Gym's
ev2gym/utilities/loaders.py::load_grid overrides number_of_transformers with
(node_num - 1) = 33 -- one transformer per feeder bus -- and distributes the
charging stations round-robin over them (`cs_transformers =
arange(n_tr) * (cs // n_tr) + arange(cs % n_tr)`). With 8 stations and 33
transformers, every station would land on a DIFFERENT bus with its OWN
100 kW transformer: 800 kW of transformer capacity instead of the single
100 kW station transformer every Week 1-5 result is built on. No config key
controls this placement.

What this does. It wraps the `load_grid` name that ev2gym/models/ev2gym_env.py
imported, from the outside (same pattern as ev2gym_thesis/rl/price_data_cache.py),
and after the library's own load_grid runs, reassigns every charging station
to the single transformer of the bus named in the config's
`network_info.thesis_station_bus`. That key is consumed only here; the library
reads only vm_pu/s_base/load_multiplier/pv_scale/bus_info_file/branch_info_file
from network_info (verified by grep), so the extra key is inert to EV2Gym.
load_transformers runs after load_grid (ev2gym_env.py __init__ and reset), so
the station transformer is built with the reassigned cs_ids and the config's
transformer.max_power (100 kW). Nothing in ev2gym/ is edited.

Bus <-> transformer mapping (from ev2gym_env.py step): node_ev_power row
tr.id + 1 is node (tr.id + 2) in Nodes_34.csv's 1-based NODES numbering
(row 0 / node 1 is the slack bus). So transformer id = bus - 2.
"""
import numpy as np
import pandas as pd

import ev2gym.models.ev2gym_env as _env_module

_ORIGINAL_LOAD_GRID = _env_module.load_grid
STATION_BUS_KEY = "thesis_station_bus"


def transformer_id_for_bus(bus: int) -> int:
    if bus < 2:
        raise ValueError("Bus 1 is the slack/substation bus; it has no EV2Gym transformer.")
    return bus - 2


def _placed_load_grid(env):
    grid = _ORIGINAL_LOAD_GRID(env)
    if env.simulate_grid and env.load_from_replay_path is None:
        bus = env.config.get("network_info", {}).get(STATION_BUS_KEY)
        if bus is None:
            raise KeyError(
                f"simulate_grid=True but network_info.{STATION_BUS_KEY} is not set: EV2Gym would "
                f"silently spread the stations over {env.number_of_transformers} transformers. "
                f"Refusing to build a grid env without an explicit station bus.")
        tr = transformer_id_for_bus(int(bus))
        if not 0 <= tr < env.number_of_transformers:
            raise ValueError(f"Station bus {bus} is outside the {env.number_of_transformers + 1}-node feeder.")
        env.cs_transformers = [tr] * env.cs
    return grid


def enable():
    _env_module.load_grid = _placed_load_grid


def is_enabled():
    return _env_module.load_grid is _placed_load_grid


# doc:begin electrical_distance
def electrical_distance(lines_csv="ev2gym/data/network_data/node_34/Lines_34.csv",
                        nodes_csv="ev2gym/data/network_data/node_34/Nodes_34.csv") -> pd.DataFrame:
    """Series resistance/reactance of the radial path from the substation to
    every bus. Used to pick the station bus: the bus with the largest path
    resistance is the most voltage-sensitive (conservative choice)."""
    lines = pd.read_csv(lines_csv)
    nodes = pd.read_csv(nodes_csv)
    parent = {r.TO: (r.FROM, r.R, r.X) for r in lines.itertuples()}
    rows = []
    for n in nodes.NODES:
        r_sum = x_sum = 0.0
        hops = 0
        cur = n
        while cur in parent:
            f, r, x = parent[cur]
            r_sum, x_sum, hops, cur = r_sum + r, x_sum + x, hops + 1, f
        rows.append({"bus": int(n), "path_R": r_sum, "path_X": x_sum, "hops": hops})
    return pd.DataFrame(rows).sort_values("path_R", ascending=False).reset_index(drop=True)
# doc:end electrical_distance
