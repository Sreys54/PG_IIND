"""
Week 8 advisor review (2026-11-01), A1: energy satisfaction per driver, and a
per-step / per-EV episode recorder used to compute it (and the A4 reward
decomposition) without editing the library.

Definitions (advisor 3.3):
  - energy satisfaction of driver i: f_i = min(1, e_i / R_i), e_i the energy
    delivered, R_i the energy requested (desired minus at-arrival capacity);
    a rejected driver has f_i = 0;
  - EV2Gym's own metric (ev2gym/models/ev.py lines 204-214,
    get_user_satisfaction) is current/desired battery level, renamed here
    `ev2gym_battery_level_satisfaction`. With desired = C (this project's
    desired_capacity = 1) it equals s_i = 1 - (R_i / C)(1 - f_i): with a 70 kWh
    battery and R/C around 0.23, an EV that received nothing still scores
    s = 0.77, which is why the old satisfaction numbers looked high;
  - service level: the share of drivers with f_i >= 0.9.
Both are reported over served drivers only and over all drivers including
rejected ones (f = 0). Labelled assumption (Week 8 brief, A1): the 90%
satisfaction target applies to the mean of f INCLUDING rejected drivers.

Recorder. `enable_recording()` wraps EV2Gym.step (chained: it wraps
whatever step is installed, e.g. the station arrival generator's). After
every step it stores, for step k = current_step - 1:
  setpoint, charge-power potential (as the reward reads them), transformer
  rating, station power, overload kW, connected EVs, and the three terms of
  SqTrError_TrPenalty_UserIncentives (ev2gym/rl_agent/reward.py lines 16-32)
  computed post hoc for ANY arm:
    tracking = -(min(setpoint, potential, rating) - power)^2
    overload = -100 * sum_tr overload kW
    user     = -1000 * sum_departing (1 - s_i)
and, for every departing EV, (R_i, e_i, s_i, f_i, arrival, departure, port).
When the last step is taken, the finished episode is left in LAST["episode"].
"""
import numpy as np

from ev2gym.models.ev2gym_env import EV2Gym

LAST = {}
_ACTIVE = {}
SERVICE_LEVEL_THRESHOLD = 0.9
SATISFACTION_TARGET = 0.9  # applied to the mean of f including rejected drivers (labelled assumption)


def energy_satisfaction(delivered_kwh: float, requested_kwh: float) -> float:
    if requested_kwh <= 1e-9:
        return 1.0
    return float(min(1.0, max(0.0, delivered_kwh) / requested_kwh))


def ev2gym_battery_level_satisfaction(requested_kwh: float, capacity_kwh: float, f: float) -> float:
    """s = 1 - (R/C)(1 - f): EV2Gym's metric written in terms of f."""
    return float(1.0 - (requested_kwh / capacity_kwh) * (1.0 - f))


def ev_record(ev) -> dict:
    """Delivered energy is ev.total_energy_exchanged (the sum of the per-step
    energy the station also sums), not current - arrival capacity: EV2Gym
    rounds current_capacity UP to 0.01 kWh after every step (ev.py, step,
    my_ceil), which overstates the delivered energy by up to 0.01 kWh per
    charging step (found by test_station_arrivals, 0.18 kWh on one day).
    EV2Gym's own satisfaction s_i still uses the rounded capacity."""
    r = float(ev.desired_capacity - ev.battery_capacity_at_arrival)
    e = float(ev.total_energy_exchanged)
    return {"station": ev.location, "port": ev.id, "arrival": ev.time_of_arrival,
            "departure": ev.time_of_departure, "requested_kwh": r, "delivered_kwh": e,
            "battery_kwh": float(ev.battery_capacity), "f": energy_satisfaction(e, r),
            "s_ev2gym": float(ev.get_user_satisfaction())}


# doc:begin service_summary
def service_summary(f_served, n_rejected: float = 0.0) -> dict:
    """Mean f and service level, over served drivers and including
    n_rejected drivers with f = 0 (n_rejected may be a non-integer bound)."""
    f = np.asarray(list(f_served), dtype=float)
    n = len(f)
    tot = n + n_rejected
    ok = float((f >= SERVICE_LEVEL_THRESHOLD - 1e-12).sum())
    return {"n_served": n, "n_rejected": n_rejected,
            "mean_f_served": float(f.mean()) if n else float("nan"),
            "mean_f_all": float(f.sum() / tot) if tot else float("nan"),
            "service_level_served": ok / n if n else float("nan"),
            "service_level_all": ok / tot if tot else float("nan"),
            "sum_f": float(f.sum()), "n_f_ge_09": ok}
# doc:end service_summary


def _post_step(env):
    rec = env._rec
    k = env.current_step - 1
    rating = float(sum(tr.max_power[k] for tr in env.transformers))
    sp = float(env.power_setpoints[k])
    pot = float(env.charge_power_potential[k])
    power = float(env.current_power_usage[k])
    over = float(sum(tr.get_how_overloaded() for tr in env.transformers))
    deps = [ev_record(ev) for ev in env.departing_evs]
    rec["steps"].append({"k": k, "setpoint_kw": sp, "potential_kw": pot, "rating_kw": rating,
                         "power_kw": power, "overload_kw": over,
                         "n_connected": int(sum(cs.n_evs_connected for cs in env.charging_stations)),
                         "r_tracking": -(min(sp, pot, rating) - power) ** 2,
                         "r_overload": -100.0 * over,
                         "r_user": -1000.0 * sum(1.0 - d["s_ev2gym"] for d in deps)})
    rec["evs"].extend(deps)
    if env.current_step >= env.simulation_length:
        rec["connected_at_end"] = [ev_record(ev) for cs in env.charging_stations
                                   for ev in cs.evs_connected if ev is not None]
        LAST["episode"] = rec


def _step(self, actions, visualize=False):
    if self.current_step == 0 or getattr(self, "_rec", None) is None:
        self._rec = {"seed": self.seed, "sim_date": str(self.sim_date), "timescale": self.timescale,
                     "steps": [], "evs": []}
    out = _ACTIVE["inner_step"](self, actions, visualize)
    _post_step(self)
    return out


def enable_recording():
    assert not _ACTIVE, "recording already enabled"
    _ACTIVE["inner_step"] = EV2Gym.step
    EV2Gym.step = _step


def disable_recording():
    if "inner_step" in _ACTIVE:
        EV2Gym.step = _ACTIVE["inner_step"]
    _ACTIVE.clear()


def episode_totals(rec: dict) -> dict:
    """Reward terms and step totals of one recorded episode."""
    st, h = rec["steps"], rec["timescale"] / 60.0
    return {"r_tracking": sum(s["r_tracking"] for s in st), "r_overload": sum(s["r_overload"] for s in st),
            "r_user": sum(s["r_user"] for s in st),
            "energy_kwh": sum(s["power_kw"] for s in st) * h,
            "overload_kwh_from_steps": sum(s["overload_kw"] for s in st) * h}
