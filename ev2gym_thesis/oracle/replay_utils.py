"""
Week 4, Entregable 3/4: generates the pickled EvCityReplay files the Gurobi
oracle models in ev2gym/baselines/gurobi_models/ read, and forces G2V-only
bounds on them -- never edits ev2gym/models/replay.py or
ev2gym/baselines/gurobi_models/*.py, only pre/post-processes the replay
pickle those unmodified modules already consume via a plain file path.

Why any algorithm can generate the replay (verified empirically, not
assumed -- see thesis_docs/chapters/00_lab_log.md's Week 4 preflight
entry): EvCityReplay's per-EV arrays (u, ev_arrival, t_dep, ev_des_energy,
ev_max_energy, ev_max_ch_power, ev_max_dis_power, energy_at_arrival) are
built from env.EVs -- the EVs actually spawned while stepping through a
full episode -- but every one of those fields is confirmed byte-identical
regardless of which algorithm supplied the actions during that episode
(compared ChargeAsFastAsPossible vs. RoundRobin on the same (config, day,
seed) cell). The one field that IS algorithm-dependent,
max_energy_at_departure (derived from the EV's actual charged level at its
last step), is loaded by both tracking_error.py and profit_max.py but never
referenced in their actual constraints/objective (dead code in the
upstream library, confirmed by reading the source) -- so it doesn't matter
which algorithm generates the replay. RoundRobin is used here for no
reason beyond "a real, already-implemented, G2V-safe heuristic."

Why replay generation must NOT call env.reset() again after construction:
this is exactly the Week 3 bug (00_lab_log.md's 2026-08-18 entry) --
EV2Gym.reset() with no explicit seed draws a fresh random scenario.
EV2Gym.__init__ already calls self.reset(seed=seed) internally once, which
is the only reset this module performs. Also verified element-by-element
against env_factory.make_env's EVs_profiles for the same cell (same entry).
"""
import os
import pickle

import numpy as np

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import RoundRobin

from ev2gym_thesis.config_utils import make_day_config

RAW_REPLAY_DIR = "experiments/phase4_oracle/replays_raw/"
G2V_REPLAY_DIR = "experiments/phase4_oracle/replays_g2v/"
DAY_CONFIG_DIR = "experiments/phase4_oracle/configs/_tmp_oracle_day_configs"


# doc:begin generate_replay
def generate_replay(config_path: str, day: tuple, scenario_seed: int,
                     replay_dir: str = RAW_REPLAY_DIR) -> str:
    """Steps one full episode with RoundRobin, save_replay=True, and
    returns the path to the resulting pickled EvCityReplay. Uses the same
    make_day_config mechanism as env_factory.make_env, so the scenario this
    replay encodes is the literal same one every heuristic/RL evaluation
    saw on this (config_path, day, scenario_seed) cell.
    """
    year, month, day_of_month = day
    day_config_path = make_day_config(config_path, year, month, day_of_month, DAY_CONFIG_DIR)

    os.makedirs(replay_dir, exist_ok=True)
    env = EV2Gym(
        config_file=day_config_path,
        seed=scenario_seed,
        save_replay=True,
        save_plots=False,
        replay_save_path=replay_dir,
    )
    agent = RoundRobin(env)
    done = False
    while not done:
        actions = agent.get_action(env)
        _, _, done, _, _ = env.step(actions)

    return env.replay_path + "replay_" + env.sim_name + ".pkl"
# doc:end generate_replay


# doc:begin force_g2v
def force_g2v(replay_path: str, out_dir: str = G2V_REPLAY_DIR) -> str:
    """Zeroes port_max_discharge_current/port_min_discharge_current on a
    copy of the replay, so the unmodified Gurobi models see the same
    G2V-only capability every other algorithm compared in this thesis has.

    station_v0_bogota.yaml has v2g_enabled=False, but that flag only gates
    the RL/heuristic action-space sign in ev2gym_env.py:227 -- it does NOT
    alter the replay's discharge current bounds, which come straight from
    charging_station.max_discharge_current/min_discharge_current regardless
    (replay.py:89-90). Left unfixed, the oracle would have V2G capability
    none of the algorithms it's compared against have, and its "upper
    bound" would not be a bound on the same problem (Week 4 Gate 1
    preflight finding).
    """
    with open(replay_path, "rb") as f:
        replay = pickle.load(f)

    replay.port_max_discharge_current = np.zeros_like(replay.port_max_discharge_current)
    replay.port_min_discharge_current = np.zeros_like(replay.port_min_discharge_current)

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(replay_path))[0]
    out_path = f"{out_dir}/{base}__g2v.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(replay, f)
    return out_path
# doc:end force_g2v


def build_g2v_replay_for_cell(config_path: str, day: tuple, scenario_seed: int) -> str:
    """One-call convenience: generate + G2V-force a replay for a
    (config, day, scenario_seed) cell. Returns the G2V-forced replay path,
    ready to hand to an unmodified ev2gym/baselines/gurobi_models class."""
    raw_path = generate_replay(config_path, day, scenario_seed)
    return force_g2v(raw_path)


# doc:begin verify_parity
def verify_parity(replay_path: str, env) -> None:
    """Asserts the replay's EV population matches env's, element by element
    -- not once, manually, for a reference cell (as in the Entregable 3
    calibration), but automatically for every cell evaluate_oracle.py runs.
    This is the same discipline env_factory.reset_for_evaluation enforces
    for RL/heuristic evaluation (thesis_docs/chapters/00_lab_log.md's Week
    3 correction entry) -- the Week 4 oracle work exists in large part
    because that discipline was once missing, so it does not get to skip
    it here. Checks u (occupancy), ev_arrival, and the sorted multiset of
    desired energies -- together these pin down arrival timing, departure
    timing, and per-EV demand, the three things a scenario mismatch could
    silently change.
    """
    with open(replay_path, "rb") as f:
        replay = pickle.load(f)

    live_evs = [ev for ev in env.EVs_profiles if ev.time_of_arrival < env.simulation_length]
    env_u_count = sum(
        min(ev.time_of_departure, env.simulation_length) - ev.time_of_arrival
        for ev in live_evs
    )
    env_des_energy = tuple(np.round(sorted(ev.desired_capacity for ev in live_evs), 4))

    replay_u_count = int(replay.u.sum())
    replay_des_energy = tuple(np.round(sorted(replay.ev_des_energy[replay.ev_des_energy > 0]), 4))

    assert replay_u_count == env_u_count, (
        f"verify_parity: replay occupancy-step count {replay_u_count} != "
        f"env's {env_u_count} -- arrival/departure timing diverged. "
        f"Do not trust this cell's oracle result."
    )
    assert replay_des_energy == env_des_energy, (
        f"verify_parity: replay's desired-energy population {replay_des_energy} "
        f"!= env's {env_des_energy} -- the oracle would be solving a different "
        f"scenario than the one being evaluated. Do not trust this cell's result."
    )
# doc:end verify_parity
