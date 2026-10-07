"""
Closure brief, Part B: arrivals that EV2Gym never spawns, and the demand-not-
served metric built on them.

Mechanism (read from source, ev2gym/utilities/utils.py::EV_spawner, lines
477-557 at commit 6f42b02):
  - Arrivals are drawn PER PORT. At the start the spawner draws one uniform
    number per (port, step): `arrival_probabilities = np.random.rand(ports,
    steps)` (line 490, the function's first random call).
  - For each step t and port, an arrival happens iff the port has been free
    at t, t-1 and t-2 (lines 531-535) AND
    `arrival_probabilities[port, t] * 100 < tau * multiplier * (timescale/60) * spawn_multiplier`
    (line 537). If the port is occupied, the draw is never evaluated: the EV
    that would have arrived is NOT queued, NOT rejected and NOT counted
    anywhere. It never exists.
  - spawn_single_EV also returns None (the EV is dropped) when
    `empty_ports_at_end_of_simulation` is set (EV2Gym default True,
    ev2gym_env.py line 52) and the stay would end within 4 steps of the
    horizon (utils.py lines 255-258) -- a horizon artefact, reported
    separately and not counted as a capacity rejection.
  - ev_charger.EV_Charger.spawn_ev asserts the port is free (line 271);
    every EV that exists is connected. total_ev_served,
    average_user_satisfaction, energy_user_satisfaction and ENS_rel (which
    compares an arm with AFAP on the SAME censored population) therefore
    all ignore censored arrivals.

What this module does (outside the library): wraps the `EV_spawner` name that
ev2gym/utilities/loaders.py imported. The wrapper snapshots the global numpy
state, lets the original spawner run, replays the snapshot to recover the
exact `arrival_probabilities` matrix, restores the post-spawner state (the
simulation is unchanged), and re-walks the spawner's loop to count every
draw that fell on a blocked port. Two bounds, because EV2Gym gives each port
its own arrival stream while a real arriving driver would take any free
port:
  - rejected_upper: every successful draw on a blocked port (EV2Gym's own
    lost arrivals);
  - rejected_lower: per step, max(0, blocked successful draws - eligible
    free ports that received no arrival) -- only arrivals no free port
    could absorb, i.e. the station was effectively full.
The energy a lost arrival would have requested is taken as EV2Gym's own mean
requested energy for its arrival time (env.df_req_energy, the mean of the
normal draw in spawn_single_EV, line 207), capped at the battery capacity
(labelled assumption: the expectation, not a sample).

Demand not served for an arm on a cell:
  DNS = (E_rejected + R_served - E_delivered) / (E_rejected + R_served)
where R_served is the energy requested by the EVs that were spawned and
E_delivered the arm's total_energy_charged (no V2G in this project).
Censoring is policy-independent (arrivals are generated at reset, before any
action), so it is computed once per (config, day, seed).
"""
import datetime

import numpy as np

import ev2gym.utilities.loaders as _loaders

_ORIGINAL_EV_SPAWNER = _loaders.EV_spawner
LAST = {}
# The spawner the replay wraps: the library's by default, or whatever was
# installed before enable() (final capacity brief: the DC session-duration
# transform, ev2gym_thesis/demand/dc_sessions.py, which must be enabled
# first). Added 2026-10-06; behaviour without the transform is unchanged.
_INNER = {"spawner": _ORIGINAL_EV_SPAWNER}


# doc:begin censoring_reconstruction
def _reconstruct(env, arrival_probabilities, evs):
    """Re-walk EV_spawner's loop (same order, same tests) and count draws on
    blocked ports. Asserts that the replay reproduces every spawned EV."""
    n_ports, T = env.number_of_ports, env.simulation_length
    occ = np.zeros((n_ports, T))
    spawn_mult = env.config["spawn_multiplier"]
    min_stay_steps = env.config["ev"]["min_time_of_stay"] // env.timescale
    battery = env.config["ev"]["battery_capacity"]
    by_key = {}
    for ev in evs:
        by_key[(ev.location, ev.id, ev.time_of_arrival)] = ev
    time = env.sim_date
    matched = dropped_late = blocked_upper = blocked_lower = 0
    e_rej_upper = e_rej_lower = 0.0
    per_step = []
    for t in range(2, T - min_stay_steps - 1):
        day, hour, minute = time.weekday(), time.hour, time.minute
        i = hour * 4 + minute // 15
        tau = (env.df_arrival_week if day < 5 else env.df_arrival_weekend)[env.scenario].iloc[i]
        thr = tau * 1 * (env.timescale / 60) * spawn_mult
        arr_time = f"{hour:02d}:{0 if minute < 30 else 30:02d}"
        req_mean = float(env.df_req_energy[env.df_req_energy["Arrival Time"] == arr_time][env.scenario].values[0])
        e_req = min(max(req_mean, 5.0), battery)
        blocked_draws = free_unused = 0
        counter = 0
        for cs in env.charging_stations:
            for port in range(cs.n_ports):
                free = occ[counter, t] == 0 and occ[counter, t - 1] == 0 and occ[counter, t - 2] == 0
                hit = arrival_probabilities[counter, t] * 100 < thr
                if free and hit:
                    ev = by_key.get((cs.id, port, t + 1))
                    if ev is None:
                        dropped_late += 1
                    else:
                        matched += 1
                        occ[counter, t + 1:ev.time_of_departure] = 1
                elif free and not hit:
                    free_unused += 1
                elif hit:  # port blocked: EV2Gym never evaluates this arrival
                    blocked_draws += 1
                counter += 1
        lower = max(0, blocked_draws - free_unused)
        blocked_upper += blocked_draws
        blocked_lower += lower
        e_rej_upper += blocked_draws * e_req
        e_rej_lower += lower * e_req
        per_step.append(blocked_draws)
        time = time + datetime.timedelta(minutes=env.timescale)
    assert matched == len(evs), f"replay matched {matched} of {len(evs)} spawned EVs -- reconstruction is wrong"
    r_served = float(sum(ev.desired_capacity - ev.battery_capacity_at_arrival for ev in evs))
    return {"n_spawned": len(evs), "dropped_late_horizon": dropped_late,
            "rejected_upper": blocked_upper, "rejected_lower": blocked_lower,
            "energy_rejected_upper_kwh": e_rej_upper, "energy_rejected_lower_kwh": e_rej_lower,
            "requested_served_kwh": r_served}
# doc:end censoring_reconstruction


def _capturing_spawner(env):
    snap = np.random.get_state()
    evs = _INNER["spawner"](env)
    post = np.random.get_state()
    np.random.set_state(snap)
    ap = np.random.rand(env.number_of_ports, env.simulation_length)
    np.random.set_state(post)
    LAST["result"] = _reconstruct(env, ap, evs)
    return evs


def enable():
    if _loaders.EV_spawner is not _capturing_spawner:
        _INNER["spawner"] = _loaders.EV_spawner
    _loaders.EV_spawner = _capturing_spawner


def disable():
    _loaders.EV_spawner = _INNER["spawner"]
    _INNER["spawner"] = _ORIGINAL_EV_SPAWNER


# doc:begin scenario_demand
def scenario_demand(config_path, day, seed, day_config_dir):
    """Censoring statistics for one (config, day, scenario seed) cell, from
    the population EV2Gym actually builds for that cell."""
    from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
    enable()
    try:
        env = make_env(config_path, day, seed, day_config_dir=day_config_dir)
        reset_for_evaluation(env, seed)
        return dict(LAST["result"])
    finally:
        disable()
# doc:end scenario_demand


def demand_not_served(energy_delivered_kwh, cell, bound="lower"):
    e_rej = cell[f"energy_rejected_{bound}_kwh"]
    total = e_rej + cell["requested_served_kwh"]
    return (e_rej + cell["requested_served_kwh"] - energy_delivered_kwh) / total
