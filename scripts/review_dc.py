"""
Week 8 advisor review (2026-11-01): one instrumented evaluation case in the
DC regime, under either arrival model, for any arm.

  arrival = "station" : station-level Poisson generator
                        (ev2gym_thesis/demand/station_arrivals.py), demand
                        from the config's .arrivals.json sidecar; DNS exact;
  arrival = "spawner" : EV2Gym's per-port spawner with the DC duration
                        transform (dc_sessions.py) and the censoring
                        reconstruction (censoring.py); DNS lower/upper bound.

Every case also runs the episode recorder (ev2gym_thesis/metrics/service.py):
per-EV energy satisfaction f, EV2Gym's battery-level satisfaction, per-step
power, setpoint, overload and the three post-hoc reward terms.

Arms (article names; Week 8 brief C1):
  AFAP      ChargeAsFastAsPossible (EV2Gym), unmanaged;
  PS        AFAP + the safety layer (rl/safety.py, common scaling factor,
            0.999 x rating) = proportional sharing;
  FIX12.5   every connected port at 100/8 = 12.5 kW (action 12.5 / P_port);
  RR        EV2Gym RoundRobin, unchanged (follows the power setpoint);
  RR+S      RR + the safety layer;
  RR-TA     RoundRobinTransformerCapped (ev2gym_thesis/heuristics.py);
  Random+S  uniform random actions (keyed on the case) + the safety layer.
Further arms (TD3_safe, MPC-soft, MPC-soft-est, Oracle-E) register
themselves in ARMS from their own modules.
"""
import csv
import datetime
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.demand import censoring, dc_sessions, station_arrivals
from ev2gym_thesis.heuristics import RoundRobinTransformerCapped
from ev2gym_thesis.metrics import service
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.registry import REGISTRY_COLUMNS, stats_to_row
from ev2gym_thesis.rl import safety
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

LAST_RECORD = {}  # the last case's per-step / per-EV record (figures)
UNIT_MARGIN_COP_PER_KWH = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
REVIEW_REGISTRY = "results/review_registry.csv"
REVIEW_COLUMNS = REGISTRY_COLUMNS + ["arrival_model", "safety_layer"]
DAY_CONFIG_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), f"w8_review_cfg_{os.getpid()}")


def _fixed_kw_policy(kw):
    def act(env):
        a = []
        for cs in env.charging_stations:
            frac = min(1.0, kw / safety.port_rated_kw(cs))
            a += [frac if ev is not None else 0.0 for ev in cs.evs_connected]
        # floored to 5 decimals: EV2Gym rounds actions to 5 decimals (ev_charger.py line 157), and rounding
        # 12.5 / 49.883 up would put 8 full ports 0.6 W above the 100 kW rating
        return np.floor(np.array(a) * 1e5) / 1e5
    return act


class _Random:
    def __init__(self, env, seed, day):
        self.rng = np.random.default_rng([int(seed), int(day[0]), int(day[1]), int(day[2]), 7])

    def get_action(self, env):
        return self.rng.random(env.number_of_ports)


# name -> (factory(env, seed, day) -> get_action(env), safety layer, family, causal)
ARMS = {
    "AFAP": (lambda env, s, d: ChargeAsFastAsPossible().get_action, "none", "heuristic", True),
    "PS": (lambda env, s, d: ChargeAsFastAsPossible().get_action, "proportional", "heuristic", True),
    "FIX12.5": (lambda env, s, d: _fixed_kw_policy(12.5), "none", "heuristic", True),
    "RR": (lambda env, s, d: RoundRobin(env).get_action, "none", "heuristic", False),
    "RR+S": (lambda env, s, d: RoundRobin(env).get_action, "proportional", "heuristic", False),
    "RR-TA": (lambda env, s, d: RoundRobinTransformerCapped(env).get_action, "none", "heuristic", True),
    "Random+S": (lambda env, s, d: _Random(env, s, d).get_action, "proportional", "heuristic", True),
    "MPC-soft": (lambda env, s, d: _operator(env, "mpc_soft"), "none", "mpc", False),
    "MPC-soft-est": (lambda env, s, d: _operator(env, "mpc_soft_est"), "none", "mpc", True),
    "Oracle-E": (lambda env, s, d: _operator(env, "oracle_e"), "none", "optimal", False),
}


# TD3_safe checkpoints evaluated on the test grid: arm name -> checkpoint path
# (set by the evaluation driver after training; selection rule in config_safe).
TD3_SAFE_CHECKPOINTS = {}
_TD3_CACHE = {}


def _td3_safe(env, arm):
    """Deterministic TD3_safe policy: frozen VecNormalize, the state function
    it was trained with (config_safe.STATE_FN), the safety layer applied by
    run_case (layer "proportional"), exactly as in training and validation."""
    from ev2gym_thesis.rl.extended_training import load_frozen_checkpoint
    path, state_fn = TD3_SAFE_CHECKPOINTS[arm]
    if path not in _TD3_CACHE:
        import gymnasium
        from stable_baselines3.common.vec_env import DummyVecEnv
        dim = len(state_fn(env))

        class _Spaces(gymnasium.Env):
            observation_space = gymnasium.spaces.Box(-np.inf, np.inf, (dim,), np.float64)
            action_space = gymnasium.spaces.Box(0.0, 1.0, (env.number_of_ports,), np.float64)

            def reset(self, seed=None, options=None):
                return np.zeros(dim), {}

            def step(self, a):
                return np.zeros(dim), 0.0, True, False, {}
        _TD3_CACHE[path] = load_frozen_checkpoint(path, DummyVecEnv([_Spaces]))
    model, vn = _TD3_CACHE[path]

    def act(e):
        obs = vn.normalize_obs(np.asarray(state_fn(e), dtype=np.float64)[None, :])
        return model.predict(obs, deterministic=True)[0][0]
    return act


def register_td3_safe(arm, checkpoint_path, state_fn):
    TD3_SAFE_CHECKPOINTS[arm] = (checkpoint_path, state_fn)
    ARMS[arm] = (lambda env, s, d, _a=arm: _td3_safe(env, _a), "proportional", "rl", True)


def _operator(env, kind):
    from ev2gym_thesis.mpc.operator_mpc import OperatorMPC, OracleE
    if kind == "oracle_e":
        return OracleE(env).get_action
    return OperatorMPC(env, estimate_departures=(kind == "mpc_soft_est")).get_action


def _enable(arrival, config_path):
    if arrival == "station":
        spec = station_arrivals.spec_for_config(config_path)
        assert spec is not None, f"{config_path} has no .arrivals.json sidecar"
        station_arrivals.enable(spec)
    elif arrival == "spawner":
        dc_sessions.enable(dc_sessions.model_for_config(config_path))
        censoring.enable()
    else:
        raise ValueError(arrival)
    service.enable_recording()


def _disable():
    service.disable_recording()
    station_arrivals.disable()
    censoring.disable()
    dc_sessions.disable()


# doc:begin run_case
def run_case(arm, config_path, seed, day, arrival="station", commit="", notes="", policy=None):
    """One (arm, config, seed, day) episode. Returns (registry_row, extras)."""
    name = os.path.splitext(os.path.basename(config_path))[0]
    factory, layer, family, causal = ARMS[arm] if policy is None else policy
    _enable(arrival, config_path)
    t0 = time.perf_counter()
    try:
        env = make_env(config_path, day, seed, day_config_dir=DAY_CONFIG_DIR)
        reset_for_evaluation(env, seed)
        cens = dict(censoring.LAST["result"]) if arrival == "spawner" else None
        act = factory(env, seed, day)
        n_proj = 0
        for _ in range(env.simulation_length):
            a = act(env)
            if layer == "proportional":
                a, info = safety.project_actions(env, a)
                n_proj += int(info["active"])
            _, _, done, _, stats = env.step(a)
        rec = service.LAST.pop("episode")
        LAST_RECORD["episode"] = rec
        e_del = float(stats["total_energy_charged"])
        if arrival == "station":
            dem = station_arrivals.episode_demand(env, e_del)
        else:
            dem = _spawner_demand(cens, e_del, rec)
    finally:
        _disable()
    runtime = time.perf_counter() - t0
    day_str = f"{day[0]:04d}-{day[1]:02d}-{day[2]:02d}"
    n_ports = int(env.number_of_ports)
    kw = float(env.transformers[0].max_power[0])
    row = {c: "" for c in REVIEW_COLUMNS}
    row.update({"run_id": f"{name}__{arm}__seed{seed}__{day_str}",
                "timestamp_utc": datetime.datetime.utcnow().isoformat(), "git_commit": commit,
                "config_name": name, "n_ports": n_ports, "transformer_kw": kw,
                "oversubscription_ratio": round(n_ports * 50 / kw, 3), "algorithm": arm,
                "algorithm_family": family, "seed": seed, "eval_day": day_str,
                "sim_steps": env.simulation_length, "runtime_s": round(runtime, 4), "notes": notes,
                "day_type": "weekday" if datetime.date(*day).weekday() < 5 else "weekend",
                "analysis_row": True, "superseded": False, "simulate_grid": False,
                "arrival_model": station_arrivals.ARRIVAL_MODEL if arrival == "station" else "ev2gym_spawner",
                "safety_layer": layer})
    row["scenario_id"] = f"{seed}_{row['day_type']}"
    row.update(stats_to_row(stats))
    extras = case_extras(rec, dem, e_del, n_ports, kw, env.simulation_length)
    extras.update({"run_id": row["run_id"], "config_name": name, "algorithm": arm, "seed": seed,
                   "eval_day": day_str, "day_type": row["day_type"], "causal": causal,
                   "projection_active_steps": n_proj, "arrival_model": row["arrival_model"],
                   "safety_layer": layer})
    return row, extras
# doc:end run_case


def _spawner_demand(cens, e_del, rec):
    r_served = float(cens["requested_served_kwh"])
    out = {"arrival_model": "ev2gym_spawner", "arrivals_served": int(cens["n_spawned"]),
           "dropped_horizon": int(cens["dropped_late_horizon"]),
           "energy_requested_served_kwh": r_served,
           "connected_port_steps": sum(e["departure"] - e["arrival"] + 1 for e in rec["evs"] + rec["connected_at_end"])}
    for b in ("lower", "upper"):
        e_rej = float(cens[f"energy_rejected_{b}_kwh"])
        out[f"arrivals_rejected_{b}"] = int(cens[f"rejected_{b}"])
        out[f"energy_rejected_{b}_kwh"] = e_rej
        out[f"energy_offered_{b}_kwh"] = e_rej + r_served
        out[f"arrivals_offered_{b}"] = int(cens["n_spawned"]) + int(cens[f"rejected_{b}"])
        out[f"dns_{b}"] = (e_rej + r_served - e_del) / (e_rej + r_served)
    return out


def case_extras(rec, dem, e_del, n_ports, kw, T):
    evs = rec["evs"] + rec["connected_at_end"]
    f = [e["f"] for e in evs]
    steps = rec["steps"]
    power = np.array([s["power_kw"] for s in steps])
    over = np.array([s["overload_kw"] for s in steps])
    out = dict(dem)
    tot = service.episode_totals(rec)
    out.update({"energy_delivered_kwh": e_del, "gross_margin_cop": e_del * UNIT_MARGIN_COP_PER_KWH,
                "peak_station_kw": float(power.max()), "overload_kwh": float(over.sum() * rec["timescale"] / 60),
                "overload_steps": int((over > 1e-9).sum()), "overload_day": bool((over > 1e-9).any()),
                # from the departing EVs' own departure step (D1 extends it online)
                "port_occupancy": sum(e["departure"] - e["arrival"] + 1 for e in evs) / (n_ports * T),
                "mean_s_ev2gym_served": float(np.mean([e["s_ev2gym"] for e in evs])) if evs else float("nan"),
                "max_identity_error_s": max((abs(e["s_ev2gym"] - service.ev2gym_battery_level_satisfaction(
                    e["requested_kwh"], e["battery_kwh"], e["f"])) for e in evs), default=0.0),
                "r_tracking": tot["r_tracking"], "r_overload": tot["r_overload"], "r_user": tot["r_user"]})
    if "arrivals_rejected" in dem:
        out.update({f"{k}": v for k, v in service.service_summary(f, dem["arrivals_rejected"]).items()})
    else:
        for b in ("lower", "upper"):
            s = service.service_summary(f, dem[f"arrivals_rejected_{b}"])
            out.update({"n_served": s["n_served"], "mean_f_served": s["mean_f_served"],
                        "service_level_served": s["service_level_served"],
                        f"mean_f_all_{b}": s["mean_f_all"], f"service_level_all_{b}": s["service_level_all"]})
    return out


def append_csv(path, rec, fields=None):
    fields = fields or list(rec)
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(rec)


def process_hooks():
    """Per-process setup shared by every Week 8 runner: one torch thread,
    the output-identical price-data cache, keep-awake."""
    from scripts import run_week7_grid as w7
    w7.enable_process_hooks()
