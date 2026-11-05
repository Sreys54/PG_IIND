"""
Week 8 advisor review (2026-11-01), Block B: a station-level arrival
generator for the DC fast-charging regime, replacing EV2Gym's per-port
EV_spawner from outside the library (the same injection point
dc_sessions.py uses).

Why. EV2Gym's EV_spawner (ev2gym/utilities/utils.py lines 477-557) draws one
arrival stream PER PORT and only evaluates a port's draw when that port was
free at t, t-1 and t-2 (lines 534-536). Two consequences for a DC station:
  - demand depends on the number of ports (more ports, more draws), so the
    offered energy is not a station property (advisor 3.8; Week 8 A3);
  - after every departure the port stays unusable for 2 further steps
    (measured: the minimum idle gap between consecutive sessions on a port
    is 2 steps = 30 min), negligible with 5-hour Dutch sessions, not with
    42-minute DC sessions.
A rejected driver is never generated, so demand not served had to be
reconstructed as a lower/upper bound (censoring.py).

What this module does.
  1. Arrival stream, fixed per scenario, drawn before the episode
     (`draw_stream`): a Poisson count per step with
        lambda_s = tau(slot(s)) * (timescale / 15) / sum(tau) * A_daytype,
     where tau is EV2Gym's own 15-minute arrival profile
     (distribution-of-arrival[-weekend].csv, 'public'), indexed by the clock
     time of step s, so with the 05:00 start the profile is read from 05:00
     onwards; A_daytype is arrivals per day for that day type (sidecar).
     Counts use inverse-CDF sampling from one uniform per step, keyed on
     (scenario seed, day type, step): streams at different demand levels
     are nested (common random numbers), so a higher level only adds
     drivers. The j-th driver of a step has attributes keyed on
     (seed, day type, step, j): its requested energy is drawn by the
     library's own spawn_single_EV (arrival-time table
     mean-demand-per-arrival.csv, Normal(e, 0.5 e), redrawn in [5, 10) below
     5 kWh, battery logic unchanged) and its dwell by dc_sessions.DwellModel
     (lognormal, mean 42 min, CV 0.5). Every arm sees the same stream.
  2. Port assignment online (`_assign`, run at the start of every env.step,
     before the library's charger step): every driver arriving in the step
     takes the first free port by index; a port is free as soon as its EV
     departs (no dead time; `dead_time_steps` > 0 reproduces EV2Gym's rule
     for the Gate 1 decomposition only); a driver who finds every port
     occupied is rejected and recorded with the energy requested. Under
     fixed departures the online assignment equals the plan made at reset
     (asserted every step), so it is identical across arms.
  3. Exact demand not served:
        DNS = (E_rejected + R_served - E_delivered) / (E_rejected + R_served)
     with E_rejected the sampled requested energy of the rejected drivers --
     observed, not a bound.

Connection-window convention (measured 2026-11-03, Week 8 Gate 1 finding).
In EV2Gym an EV with arrival a and departure d is connected, and charged,
during steps a..d inclusive: d - a + 1 steps (spawned at the end of step
a - 1, ev2gym_env.py lines 400-414; departs after charging in step d,
ev_charger.py lines 210-224, ev.is_departing; the library's own degradation
model counts d - a + 1, ev.py line 477). dc_sessions.py sets d = a + n for a
sampled duration of n steps, so its EVs were connected n + 1 steps -- one
step (15 min) longer than the labelled duration. Here d = a + n - 1 +
extra_connected_steps: extra_connected_steps = 0 (default) connects the EV
for exactly the sampled n steps; 1 reproduces the dc_sessions convention.

Horizon rule: as the library (utils.py lines 254-256, empty ports at the end
of the episode), a driver whose departure would fall at or after step T - 1
is not part of the offered demand (counted as dropped_horizon).

Parameters come from a sidecar `<config>.arrivals.json`, never a YAML key.
"""
import json
import math
import os
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import poisson

import ev2gym.utilities.loaders as _loaders
import ev2gym.utilities.utils as _utils
from ev2gym.models.ev2gym_env import EV2Gym

from ev2gym_thesis.demand.dc_sessions import DwellModel

_LIB_EV_SPAWNER = _loaders.EV_spawner
_LIB_SPAWN_SINGLE_EV = _utils.spawn_single_EV
_LIB_GENERATE_POWER_SETPOINTS = _loaders.generate_power_setpoints
from ev2gym.models.ev import EV as _EV
_LIB_IS_DEPARTING = _EV.is_departing
_ACTIVE = {}
STREAM_TAG = 20261101  # fixed salt of every keyed draw (date of the advisor review)
ARRIVAL_MODEL = "station_poisson"


@dataclass(frozen=True)
class ArrivalSpec:
    """Station-level demand. arrivals_per_day is keyed 'weekday'/'weekend'."""
    arrivals_per_day: dict
    dwell: DwellModel = field(default_factory=lambda: DwellModel(42.0, 0.5))
    dead_time_steps: int = 0
    extra_connected_steps: int = 0
    level: float = float("nan")
    level_label: str = ""
    # Block D sensitivities (both off by default):
    #  load_dependent_departure_cap_min > 0 (D1): a driver whose sampled dwell has ended
    #    stays while not full, at most this many minutes after arrival;
    #  energy_scale != 1 (D3): every driver's requested energy is multiplied by it
    #    (capped at battery - min_battery_capacity), e.g. 22 / 16.1 kWh.
    load_dependent_departure_cap_min: float = 0.0
    energy_scale: float = 1.0


def sidecar_path(config_path: str) -> str:
    return os.path.splitext(config_path)[0] + ".arrivals.json"


def spec_for_config(config_path: str):
    p = sidecar_path(config_path)
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    return ArrivalSpec(arrivals_per_day={"weekday": float(d["arrivals_per_day"]["weekday"]),
                                         "weekend": float(d["arrivals_per_day"]["weekend"])},
                       dwell=DwellModel(float(d["dwell_mean_min"]), float(d["dwell_cv"])),
                       dead_time_steps=int(d.get("dead_time_steps", 0)),
                       extra_connected_steps=int(d.get("extra_connected_steps", 0)),
                       level=float(d.get("level", float("nan"))), level_label=d.get("level_label", ""),
                       load_dependent_departure_cap_min=float(d.get("load_dependent_departure_cap_min", 0.0)),
                       energy_scale=float(d.get("energy_scale", 1.0)))


def write_sidecar(config_path: str, spec: ArrivalSpec, extra: dict = None) -> str:
    d = {"arrival_model": ARRIVAL_MODEL, "module": "ev2gym_thesis/demand/station_arrivals.py",
         "arrivals_per_day": dict(spec.arrivals_per_day), "dwell_mean_min": spec.dwell.mean_min,
         "dwell_cv": spec.dwell.cv, "dead_time_steps": spec.dead_time_steps,
         "extra_connected_steps": spec.extra_connected_steps, "level": spec.level,
         "load_dependent_departure_cap_min": spec.load_dependent_departure_cap_min,
         "energy_scale": spec.energy_scale,
         "level_label": spec.level_label, **(extra or {})}
    p = sidecar_path(config_path)
    from ev2gym_thesis.demand.review_configs import write_if_changed
    write_if_changed(p, json.dumps(d, indent=2))
    return p


def day_type(env) -> str:
    return "weekday" if env.sim_date.weekday() < 5 else "weekend"


def _key(seed, dtype, *rest) -> np.random.SeedSequence:
    return np.random.SeedSequence([STREAM_TAG, int(seed), 0 if dtype == "weekday" else 1, *[int(r) for r in rest]])


# doc:begin lambda_profile
def lambda_profile(env, arrivals_per_day: float) -> np.ndarray:
    """Expected arrivals per simulation step: tau at the clock time of each
    step, normalised over the day's 96 quarter-hours, times arrivals/day.
    A step shorter than 15 min gets its quarter-hour's share pro rata."""
    import datetime
    tau_df = env.df_arrival_week if day_type(env) == "weekday" else env.df_arrival_weekend
    tau = tau_df[env.scenario].to_numpy(dtype=float)
    lam = np.zeros(env.simulation_length)
    t = env.sim_date
    for s in range(env.simulation_length):
        lam[s] = tau[t.hour * 4 + t.minute // 15] * (env.timescale / 15.0)
        t = t + datetime.timedelta(minutes=env.timescale)
    return lam / tau.sum() * arrivals_per_day
# doc:end lambda_profile


# doc:begin draw_stream
def draw_stream(env, spec: ArrivalSpec, seed: int) -> dict:
    """The whole day's arrivals for (seed, day type), as EV objects in
    arrival order, before any control. Leaves the global numpy RNG untouched."""
    import datetime
    dtype = day_type(env)
    lam = lambda_profile(env, spec.arrivals_per_day[dtype])
    T = env.simulation_length
    saved = np.random.get_state()
    flag = env.empty_ports_at_end_of_simulation
    env.empty_ports_at_end_of_simulation = False  # horizon rule applied below, on the DC duration
    stream, dropped, t = [], [], env.sim_date
    try:
        for s in range(T):
            u = np.random.default_rng(_key(seed, dtype, s, 0, 0)).random()
            n = max(0, int(poisson.ppf(u, lam[s]))) if lam[s] > 0 else 0
            for j in range(n):
                np.random.seed(int(_key(seed, dtype, s, j, 1).generate_state(1)[0]))
                ev = _LIB_SPAWN_SINGLE_EV(env=env, scenario=env.scenario, cs_id=0, port=0, hour=t.hour,
                                          minute=t.minute, step=s, min_time_of_stay_steps=0)
                if spec.energy_scale != 1.0:  # D3: rescale the requested energy, same draw
                    floor = float(env.config["ev"]["min_battery_capacity"])
                    r = min((ev.battery_capacity - ev.battery_capacity_at_arrival) * spec.energy_scale,
                            ev.battery_capacity - floor)
                    ev.battery_capacity_at_arrival = ev.battery_capacity - r
                z = float(np.random.default_rng(_key(seed, dtype, s, j, 2)).standard_normal())
                n_steps = spec.dwell.steps(z, env.timescale)
                ev.time_of_departure = ev.time_of_arrival + n_steps - 1 + spec.extra_connected_steps
                ev.location, ev.id = -1, -1
                ev._sa_key = (s, j)
                ev._sa_dwell_steps = n_steps
                (dropped if ev.time_of_departure >= T - 1 else stream).append(ev)
            t = t + datetime.timedelta(minutes=env.timescale)
    finally:
        env.empty_ports_at_end_of_simulation = flag
        np.random.set_state(saved)
    return {"stream": stream, "dropped_horizon": dropped, "lambda": lam, "day_type": dtype}
# doc:end draw_stream


def requested_kwh(ev) -> float:
    return float(ev.desired_capacity - ev.battery_capacity_at_arrival)


def _port_list(env):
    return [(i, p) for i, cs in enumerate(env.charging_stations) for p in range(cs.n_ports)]


# doc:begin plan
def plan_assignment(stream, ports, dead_time_steps=0):
    """First-free-port assignment under the stream's own (fixed) departures.
    A port whose EV departs at step d can take an EV arriving at d + 1 +
    dead_time_steps (connected from that step)."""
    free_from = {g: 0 for g in ports}  # earliest arrival step the port can take
    accepted, rejected = [], []
    for ev in stream:
        port = next((g for g in ports if free_from[g] <= ev.time_of_arrival), None)
        if port is None:
            rejected.append(ev)
            continue
        free_from[port] = ev.time_of_departure + 1 + dead_time_steps
        accepted.append((ev, port))
    return accepted, rejected
# doc:end plan


def _station_spawner(env):
    spec = _ACTIVE["spec"]
    if spec.load_dependent_departure_cap_min > 0:
        _ACTIVE["cap_steps"] = int(round(spec.load_dependent_departure_cap_min / env.timescale))
    drawn = draw_stream(env, spec, env.seed)
    ports = _port_list(env)
    accepted, rejected = plan_assignment(drawn["stream"], ports, spec.dead_time_steps)
    for ev, (cs_idx, port) in accepted:
        ev.location = env.charging_stations[cs_idx].id
        ev.id = port
    env._sa = {"spec": spec, "seed": env.seed, "day_type": drawn["day_type"], "stream": drawn["stream"],
               "dropped_horizon": drawn["dropped_horizon"], "lambda": drawn["lambda"],
               "planned": {ev._sa_key: (ev.location, ev.id) for ev, _ in accepted},
               "planned_rejected": {ev._sa_key for ev in rejected},
               "online": {}, "rejected": [], "free_from": {g: 0 for g in ports}, "ports": ports,
               "fixed_departures": not _ACTIVE.get("departures_controlled", False)}
    return [ev for ev, _ in accepted]


# doc:begin online_assign
def _assign(env):
    """Online assignment for the drivers arriving in this step (connected
    from step k + 1), before the library spawns them. Ports are scanned in
    index order; a port is free if its EV departs in this step or earlier
    (charger step departs every EV with departure <= k) and the optional dead
    time has elapsed."""
    sa, k = env._sa, env.current_step
    dt = sa["spec"].dead_time_steps
    cap = _ACTIVE.get("cap_steps") if sa["spec"].load_dependent_departure_cap_min > 0 else None
    for i, cs in enumerate(env.charging_stations):  # departures may be control-dependent (D1): refresh
        for p, ev in enumerate(cs.evs_connected):
            if ev is None:
                continue
            leaving = ev.time_of_departure <= k
            if (cap is not None and leaving and ev.current_capacity < ev.desired_capacity - 0.001
                    and k < ev.time_of_arrival + cap - 1):
                # D1: whether this driver leaves after this step's charge is not known yet; the port
                # is treated as occupied (conservative: if the battery fills this step, the port idles
                # one step). Declared with the D1 results.
                leaving = False
            sa["free_from"][(i, p)] = (k + 1 + dt) if leaving else max(ev.time_of_departure, k + 1) + 1 + dt
    arriving = [ev for ev in sa["stream"] if ev.time_of_arrival == k + 1]
    if not arriving:
        return
    taken, accepted = set(), []
    for ev in arriving:
        port = next((g for g in sa["ports"] if g not in taken and sa["free_from"][g] <= ev.time_of_arrival), None)
        if port is None:
            sa["rejected"].append(ev)
            continue
        taken.add(port)
        sa["free_from"][port] = ev.time_of_departure + 1 + dt
        ev.location, ev.id = env.charging_stations[port[0]].id, port[1]
        sa["online"][ev._sa_key] = (ev.location, ev.id)
        accepted.append(ev)
    if sa["fixed_departures"]:
        assert {e._sa_key: sa["online"][e._sa_key] for e in accepted} == \
            {e._sa_key: sa["planned"][e._sa_key] for e in arriving if e._sa_key in sa["planned"]} and \
            {e._sa_key for e in arriving if e not in accepted} == \
            {e._sa_key for e in arriving if e._sa_key in sa["planned_rejected"]}, \
            f"online assignment differs from the fixed-departure plan at step {k}"
    else:  # departures depend on control (Block D1): the online result replaces the plan
        n = env.total_evs_spawned
        rest = [e for e in env.EVs_profiles[n:] if e.time_of_arrival != k + 1]
        env.EVs_profiles = env.EVs_profiles[:n] + accepted + rest
# doc:end online_assign


def _step(self, actions, visualize=False):
    if getattr(self, "_sa", None) is not None:
        _assign(self)
    return _ACTIVE["inner_step"](self, actions, visualize)


def _setpoints_guarded(env):
    """As dc_sessions._setpoints_guarded (utils.generate_power_setpoints
    needs departure >= arrival + 2), restoring each EV's own departure."""
    short = [(ev, ev.time_of_departure) for ev in env.EVs_profiles
             if ev.time_of_departure - ev.time_of_arrival < 2]
    for ev, _ in short:
        ev.time_of_departure = ev.time_of_arrival + 2
    try:
        return _LIB_GENERATE_POWER_SETPOINTS(env)
    finally:
        for ev, d in short:
            ev.time_of_departure = d


# doc:begin load_dependent_departure
def _is_departing_d1(self, timestep):
    """D1: EV.is_departing is evaluated by the charger AFTER the step's charge
    (ev_charger.py lines 210-213), so the driver sees the energy just
    received: if the sampled departure has come but the battery is not yet at
    the desired level and the cap has not been reached, the driver stays one
    more step (the departure moves to the next step)."""
    cap = _ACTIVE["cap_steps"]
    if (timestep >= self.time_of_departure and self.current_capacity < self.desired_capacity - 0.001
            and timestep < self.time_of_arrival + cap - 1):
        self.time_of_departure = timestep + 1
        return None
    return _LIB_IS_DEPARTING(self, timestep)
# doc:end load_dependent_departure


def enable(spec: ArrivalSpec, departures_controlled: bool = False):
    """Install the generator (do NOT combine with dc_sessions or censoring).
    A spec with load_dependent_departure_cap_min > 0 makes departures depend
    on the control (Block D1): the online assignment then replaces the plan."""
    from ev2gym_thesis.demand import dc_sessions
    assert not dc_sessions.is_enabled(), "disable dc_sessions first: the station generator replaces it"
    _ACTIVE["spec"] = spec
    d1 = spec.load_dependent_departure_cap_min > 0
    _ACTIVE["departures_controlled"] = departures_controlled or d1
    _ACTIVE["inner_step"] = EV2Gym.step  # the library's, or a recorder installed earlier
    _loaders.EV_spawner = _station_spawner
    _loaders.generate_power_setpoints = _setpoints_guarded
    EV2Gym.step = _step
    if d1:
        from ev2gym.models.ev import EV
        _ACTIVE["cap_steps"] = int(round(spec.load_dependent_departure_cap_min / 15.0))  # set again per env below
        EV.is_departing = _is_departing_d1


def disable():
    if "inner_step" in _ACTIVE:
        EV2Gym.step = _ACTIVE["inner_step"]
    from ev2gym.models.ev import EV
    EV.is_departing = _LIB_IS_DEPARTING
    _ACTIVE.clear()
    _loaders.EV_spawner = _LIB_EV_SPAWNER
    _loaders.generate_power_setpoints = _LIB_GENERATE_POWER_SETPOINTS


def is_enabled() -> bool:
    return _loaders.EV_spawner is _station_spawner


# doc:begin episode_demand
def episode_demand(env, e_delivered_kwh: float) -> dict:
    """Offered, served and rejected demand of a finished episode, and the
    exact DNS. Call after the last step."""
    sa = env._sa
    rejected = sa["rejected"]
    served = [ev for ev in sa["stream"] if ev._sa_key in sa["online"]]
    e_rej = sum(requested_kwh(ev) for ev in rejected)
    r_served = sum(requested_kwh(ev) for ev in served)
    denom = e_rej + r_served
    return {"arrival_model": ARRIVAL_MODEL, "day_type": sa["day_type"],
            "arrivals_offered": len(sa["stream"]), "arrivals_served": len(served),
            "arrivals_rejected": len(rejected), "dropped_horizon": len(sa["dropped_horizon"]),
            "energy_offered_kwh": denom, "energy_rejected_kwh": e_rej, "energy_requested_served_kwh": r_served,
            "dns_exact": (denom - e_delivered_kwh) / denom if denom > 0 else 0.0,
            "connected_port_steps": sum(ev.time_of_departure - ev.time_of_arrival + 1 for ev in served)}
# doc:end episode_demand


def offered_energy(env, spec: ArrivalSpec, seed: int) -> tuple:
    """(arrivals, kWh) offered by one (seed, day type) stream -- no episode."""
    d = draw_stream(env, spec, seed)
    return len(d["stream"]), sum(requested_kwh(ev) for ev in d["stream"])
