"""
Final capacity brief, Parts A-B: where EV2Gym's session durations come from,
and a DC-fast-charging session-duration transform applied from outside the
library.

Source of the library's durations (read-only, ev2gym/utilities/utils.py at
commit 942122a):
  - spawn_single_EV, lines 232-238: time of stay ~ Normal(m(h), 0.2 m(h))
    hours, where m(h) is the 'public' column of
    ev2gym/data/mean-session-length-per.csv (mean session length per
    half-hour arrival time; loaded by loaders.load_ev_spawn_scenarios, lines
    67-89) -- the same table for every charger, AC or DC: the spawner never
    reads the charger's power or type;
  - line 240: converted to steps as hours x 60 / timescale + 1;
  - lines 251-252: floored at min_time_of_stay // timescale steps (config
    ev.min_time_of_stay = 200 min -> 13 steps);
  - lines 336-338 (homogeneous-fleet branch): time_of_arrival = step + 1, time_of_departure =
    int(time_of_stay + step + 3), so a connection lasts int(stay) + 2 steps,
    at least 15 steps (225 min) in this project's config.
  - Energy requested (lines 203-211): Normal(e(h), 0.5 e(h)) kWh, e(h) from
    ev2gym/data/mean-demand-per-arrival.csv ('public'), redrawn in [5, 10)
    when below 5 kWh, capped by the 70 kWh battery.

The transform (Part B). EV2Gym has no session-duration key and no hook
between "population generated" and "episode runs" other than the spawner
itself. Rewriting departures after EV_spawner returns would leave the port
occupancy that decided which arrivals exist unchanged (arrivals blocked by
a 6-hour Dutch session would stay blocked behind a 42-minute one), which is
not a DC station. So the rewrite happens inside the spawner's own loop,
without editing the library:
  1. loaders.EV_spawner (the name load_ev_profiles calls) is wrapped.
  2. The wrapper first runs the library spawner unchanged (pass 1): this is
     the Dutch-duration population, bitwise the one every registry row used.
  3. It restores the RNG state, and runs the library spawner again (pass 2)
     with utils.spawn_single_EV temporarily replaced by a function that:
       - for an arrival (station, port, step) that pass 1 also produced,
         returns pass 1's EV object itself (arrival time, energy requested,
         battery state bitwise unchanged) with only time_of_departure
         rewritten;
       - for an arrival that exists only because a port is now free, calls
         the library's spawn_single_EV under an RNG seeded from (scenario
         RNG state, station, port, step), so the new EV's energy is drawn by
         the library's own code and is the same in every duration variant;
       - draws the connection duration from a lognormal with the target
         mean and coefficient of variation (CV 0.5, labelled assumption),
         from z ~ N(0,1) keyed on (scenario, station, port, step) -- the
         same z in every variant, so 32/42/78-minute populations are
         comonotone (common random numbers);
       - rounds it to the timestep (floor of 1 step) and applies the
         library's own horizon rule (drop when departure >= T - 1,
         equivalent to utils.py lines 254-256).
     The arrival draw matrix (utils.py line 489, the spawner's first random
     call) is identical in both passes. Neither keyed call advances the
     global RNG.
  4. The global RNG is set to its state after pass 1, so everything EV2Gym
     draws after the spawner during reset is what it would have drawn
     without the transform.
EV2Gym's free-port test (free at t, t-1 and t-2, lines 534-536) is kept: a
port can take a new arrival only 3 steps (45 min) after a departure.
Harmless with 6-hour stays, it caps a 3-step DC session at one per 6 steps;
kept as the library's behaviour (conservative: it overstates the ports
needed), declared in chapter 08.

The transform reads its parameters from a sidecar JSON next to the config
(<config>.dwell.json), never from a new YAML key (EV2Gym does not consume
one; CLAUDE.md config rule).
"""
import json
import math
import os
from dataclasses import dataclass

import numpy as np

import ev2gym.utilities.loaders as _loaders
import ev2gym.utilities.utils as _utils

_LIB_EV_SPAWNER = _utils.EV_spawner
_LIB_SPAWN_SINGLE_EV = _utils.spawn_single_EV
_LIB_GENERATE_POWER_SETPOINTS = _loaders.generate_power_setpoints
_ACTIVE = {}
LAST = {}


@dataclass(frozen=True)
class DwellModel:
    """Lognormal connection duration with a given mean (minutes) and CV."""
    mean_min: float
    cv: float = 0.5

    @property
    def sigma(self) -> float:
        return math.sqrt(math.log(1.0 + self.cv ** 2))

    @property
    def mu(self) -> float:
        return math.log(self.mean_min) - self.sigma ** 2 / 2.0

    def minutes(self, z: float) -> float:
        return math.exp(self.mu + self.sigma * z)

    def steps(self, z: float, timescale: int) -> int:
        """Rounded to the nearest timestep (half up), at least one step."""
        return max(1, int(math.floor(self.minutes(z) / timescale + 0.5)))


def sidecar_path(config_path: str) -> str:
    return os.path.splitext(config_path)[0] + ".dwell.json"


def model_for_config(config_path: str):
    """The DwellModel a config declares through its sidecar, or None."""
    p = sidecar_path(config_path)
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    return DwellModel(float(d["mean_min"]), float(d["cv"]))


def _scenario_key(state) -> list:
    keys, pos = state[1], state[2]
    return [int(x) for x in keys[:4]] + [int(pos)]


def _keyed_seed(base, cs_id, port, step, stream) -> int:
    return int(np.random.SeedSequence(base + [int(cs_id), int(port), int(step), stream]).generate_state(1)[0])


# doc:begin dc_spawner
def _dc_spawner(env):
    model = _ACTIVE["model"]
    s0 = np.random.get_state()
    dutch = _LIB_EV_SPAWNER(env)  # pass 1: the library's population, unchanged
    s_post = np.random.get_state()
    base = _scenario_key(s0)
    from_pass1 = {(ev.location, ev.id, ev.time_of_arrival - 1): ev for ev in dutch}
    counts = {"reused_from_dutch": 0, "new_arrivals": 0, "dropped_horizon": 0}

    def spawn(env, scenario, cs_id, port, hour, minute, step, min_time_of_stay_steps):
        ev = from_pass1.pop((cs_id, port, step), None)
        if ev is not None:
            counts["reused_from_dutch"] += 1
        else:
            saved = np.random.get_state()
            np.random.seed(_keyed_seed(base, cs_id, port, step, 0))
            flag = env.empty_ports_at_end_of_simulation
            env.empty_ports_at_end_of_simulation = False  # horizon rule applied below, on the new duration
            try:
                ev = _LIB_SPAWN_SINGLE_EV(env=env, scenario=scenario, cs_id=cs_id, port=port, hour=hour,
                                          minute=minute, step=step, min_time_of_stay_steps=min_time_of_stay_steps)
            finally:
                env.empty_ports_at_end_of_simulation = flag
                np.random.set_state(saved)
            counts["new_arrivals"] += 1
        z = float(np.random.default_rng(_keyed_seed(base, cs_id, port, step, 1)).standard_normal())
        departure = ev.time_of_arrival + model.steps(z, env.timescale)
        if env.empty_ports_at_end_of_simulation and departure >= env.simulation_length - 1:
            counts["dropped_horizon"] += 1
            return None
        ev.time_of_departure = departure
        return ev

    np.random.set_state(s0)
    _utils.spawn_single_EV = spawn
    try:
        evs = _LIB_EV_SPAWNER(env)  # pass 2: same arrival draws, DC departures drive port occupancy
    finally:
        _utils.spawn_single_EV = _LIB_SPAWN_SINGLE_EV
    np.random.set_state(s_post)
    LAST["result"] = {**counts, "n_dutch": len(dutch), "n_dc": len(evs),
                      "dutch_population": [(e.location, e.id, e.time_of_arrival, e.battery_capacity_at_arrival,
                                            e.desired_capacity) for e in dutch]}
    return evs
# doc:end dc_spawner


# doc:begin setpoint_guard
def _setpoints_guarded(env):
    """utils.generate_power_setpoints (lines 714-718) spreads each EV's energy
    over steps [arrival + 1, departure), so a 1-step connection gives an empty
    slice and min() raises. For the setpoint computation only, a 1-step
    connection is treated as 2 steps, then restored, so its setpoint energy
    sits in the step after arrival -- the library's own placement for every
    EV (its window always starts one step after arrival); the result is then
    median-smoothed over 5 steps as usual. The power setpoint is the tracking
    target AND EV2Gym's Round Robin control signal (heuristics.py lines
    58-60: RR charges setpoint / per-port power EVs; it never reads the
    transformer limit), so this guard does affect Round Robin for the
    1-step sessions (13% at 42 min, 29% at 32 min, 1% at 78 min). Declared
    in chapter 08."""
    short = [ev for ev in env.EVs_profiles if ev.time_of_departure - ev.time_of_arrival < 2]
    for ev in short:
        ev.time_of_departure = ev.time_of_arrival + 2
    try:
        return _LIB_GENERATE_POWER_SETPOINTS(env)
    finally:
        for ev in short:
            ev.time_of_departure = ev.time_of_arrival + 1
# doc:end setpoint_guard


def enable(model: DwellModel):
    """Install the transform. Enable it BEFORE censoring.enable(), so the
    censoring replay wraps (and re-walks) the transformed population."""
    _ACTIVE["model"] = model
    _loaders.EV_spawner = _dc_spawner
    _loaders.generate_power_setpoints = _setpoints_guarded


def disable():
    _ACTIVE.clear()
    _loaders.EV_spawner = _LIB_EV_SPAWNER
    _loaders.generate_power_setpoints = _LIB_GENERATE_POWER_SETPOINTS


def is_enabled() -> bool:
    return _loaders.EV_spawner is _dc_spawner


def session_records(evs, timescale: int) -> list:
    """One record per EV: connection duration (minutes) and energy requested
    (kWh, desired minus at-arrival, as EV2Gym's own required_energy)."""
    return [{"station": ev.location, "port": ev.id, "arrival_step": ev.time_of_arrival,
             "departure_step": ev.time_of_departure,
             "duration_min": (ev.time_of_departure - ev.time_of_arrival) * timescale,
             "energy_requested_kwh": float(ev.desired_capacity - ev.battery_capacity_at_arrival)}
            for ev in evs]


# doc:begin cell_sessions
def cell_sessions(config_path, day, seed, day_config_dir, model=None):
    """(session records, censoring dict, env facts) for one (config, day,
    seed) cell, built exactly as the evaluation runs build it."""
    from ev2gym_thesis.demand import censoring
    from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
    if model is not None:
        enable(model)
    censoring.enable()
    try:
        env = make_env(config_path, day, seed, day_config_dir=day_config_dir)
        reset_for_evaluation(env, seed)
        cens = dict(censoring.LAST["result"])
        recs = session_records(env.EVs_profiles, env.timescale)
        facts = {"timescale": env.timescale, "simulation_length": env.simulation_length,
                 "n_ports": env.number_of_ports}
    finally:
        censoring.disable()
        disable()
    return recs, cens, facts
# doc:end cell_sessions
