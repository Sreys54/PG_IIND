"""
Bogota-calibrated calendar-aging wrapper for EV2Gym's battery degradation
model (Week 2, Deliverable 6.2-6.4). Does NOT modify ev2gym/models/ev.py.

Scope, as approved:
- Recomputes ONLY calendar aging (d_cal). Cycling aging (d_cyc) is passed
  through unchanged from the simulator's own EV.get_battery_degradation()
  output: beta() has no temperature term in the implemented model (verified
  by inspection, see thesis_docs/chapters/00_lab_log.md), so recomputing it
  here would be redundant.
- Substitutes ONLY theta (fixed at 298.15 K in ev.py) with a time-varying
  ambient temperature integrated over the EV's actual session, using the
  per-step data the simulator already exposes on the EV object
  (historic_soc, active_steps, time_of_arrival, time_of_departure) --
  nothing here reaches into EV2Gym's internals or changes simulation
  dynamics.
- Verified NOT to feed back into any reward function (grep over
  ev2gym/rl_agent/reward.py: zero references to battery/degradation/stats).
  Recomputing degradation post-hoc is therefore exactly equivalent to
  computing it inside the simulator, not an approximation.

Reported absolute degradation figures are NOT physical predictions for a
Colombian fleet: T_acc, b_cap_kwh, d_dist and G below are hard-coded
European-fleet usage assumptions (see EXPOSED_DEFAULTS) carried over
unchanged from ev2gym/models/ev.py. Only RELATIVE differences -- between
algorithms, or between ambient scenarios, under the same fixed assumptions
-- are reportable claims.
"""
import datetime
import math

import numpy as np

# doc:begin exposed_defaults
# These four are ev.py's hard-coded assumptions about a REFERENCE vehicle's
# annual usage pattern (15,000 km/year at 0.186 kWh/km, a 78 kWh battery,
# 2-year-old at simulation time), used only to build the normalizing
# denominator Q_acc for cycling aging -- they describe a generic European
# EV usage pattern, not the specific EV being simulated (whose own
# battery_capacity may differ, e.g. our station configs use 70 kWh).
# Exposed here as parameters (current values = ev.py's defaults) so a
# future run can vary them explicitly instead of editing buried literals.
EXPOSED_DEFAULTS = dict(
    T_acc_days=2 * 365,   # battery age assumed at simulation time (days)
    b_cap_kwh=78,         # reference vehicle battery capacity (kWh)
    d_dist_km_year=15000, # reference vehicle annual distance (km/year)
    G_kwh_per_km=0.186,   # reference vehicle energy consumption (kWh/km)
)

# Battery-chemistry coefficients from ev.py's implemented model (Xu et al.
# 2018 -type semi-empirical form -- citation pending verification, see
# thesis_docs/chapters/00_lab_log.md). These are NOT usage-pattern
# assumptions, so they are not exposed as calibration parameters here.
E0 = 7.543e6
E1 = 23.75e6
E2 = 6976
K = 0.8263
V_MIN = 3.3324
B_CAP_AH = 2.05
# doc:end exposed_defaults


# doc:begin arrhenius_factor
def arrhenius_factor(theta_kelvin: float) -> float:
    """exp(-E2/theta), the temperature term inside ev.py's alpha(V,theta).
    Verified against 4 closed-form reference values -- see
    tests/test_degradation_bogota.py.
    """
    return math.exp(-E2 / theta_kelvin)
# doc:end arrhenius_factor


def _session_hours_and_charging_flags(ev, sim_starting_date, timescale_min):
    """Reconstruct (hour_of_day, is_charging) for each entry already
    recorded in ev.historic_soc/ev.active_steps during the session. These
    lists are populated per-step by EV.step() (and one extra trailing
    entry by EV.get_battery_degradation(), which must have already run so
    this wrapper sees the exact same data the original calendar/cycling
    computation used).
    """
    n = len(ev.historic_soc)
    if n == 0:
        return [], []
    hours, charging = [], []
    for i in range(n):
        abs_step = min(ev.time_of_arrival + i, ev.time_of_departure)
        t = sim_starting_date + datetime.timedelta(minutes=abs_step * timescale_min)
        hours.append(t.hour + t.minute / 60.0)
        is_charging = ev.active_steps[i] == 1 if i < len(ev.active_steps) else False
        charging.append(is_charging)
    return hours, charging


def recompute_calendar_degradation(ev, sim_starting_date, timescale_min,
                                    ambient_profile_fn, delta_t_charging_c=0.0,
                                    T_acc_days=EXPOSED_DEFAULTS["T_acc_days"]):
    """Recompute calendar-aging capacity loss (d_cal) with a time-varying
    ambient temperature in place of ev.py's fixed theta=298.15K.

    Uses the effective Arrhenius factor
        A_eff = mean_t( exp(-E2/theta(t)) )
    over the EV's actual per-step session data (a discrete Riemann-sum
    approximation of the continuous integral, at simulation-step
    resolution), rather than substituting the session-mean temperature into
    a single evaluation. exp(-E2/theta) is convex in theta over this range,
    so by Jensen's inequality the point-estimate (mean-temperature)
    approximation UNDERESTIMATES A_eff, and therefore underestimates
    degradation -- see also_compute_point_estimate below, used to quantify
    that gap.

    delta_t_charging_c: flat, UNVALIDATED sensitivity bump (deg C) added to
    ambient temperature only at steps where the EV is actively charging
    (active_steps[i] == 1), standing in for DC-charging self-heating at
    altitude. Per the approved scope, this is NOT a calibrated thermal
    model -- no validated thermal model for 50kW DC charging at 2600m was
    available. Intended usage: run with delta_t_charging_c=0 and =5 as a
    declared sensitivity bracket, not as a point prediction.

    Returns None if the EV never had a session (no historic_soc data).
    """
    # doc:begin recompute_calendar
    hours, charging_flags = _session_hours_and_charging_flags(ev, sim_starting_date, timescale_min)
    if not hours:
        return None

    avg_soc = float(np.mean(ev.historic_soc))
    v_avg = V_MIN + K * avg_soc

    T_sim_days = (ev.time_of_departure - ev.time_of_arrival + 1) * timescale_min / (60 * 24)

    exp_terms = []
    ambient_temps_c = []
    for hour, is_charging in zip(hours, charging_flags):
        ambient_c = ambient_profile_fn(hour)
        bump = delta_t_charging_c if is_charging else 0.0
        theta_t = 273.15 + ambient_c + bump
        exp_terms.append(arrhenius_factor(theta_t))
        ambient_temps_c.append(ambient_c + bump)

    A_eff = float(np.mean(exp_terms))
    alpha_eff = (E0 * v_avg - E1) * A_eff
    d_cal = alpha_eff * 0.75 * T_sim_days / (T_acc_days ** 0.25)

    # Point-estimate comparison: single evaluation at the session's mean
    # experienced temperature, to quantify the Jensen's-inequality gap.
    theta_mean = 273.15 + float(np.mean(ambient_temps_c))
    A_point = arrhenius_factor(theta_mean)
    alpha_point = (E0 * v_avg - E1) * A_point
    d_cal_point_estimate = alpha_point * 0.75 * T_sim_days / (T_acc_days ** 0.25)

    return {
        "d_cal": d_cal,
        "d_cal_point_estimate": d_cal_point_estimate,
        "jensen_gap_pct": (d_cal - d_cal_point_estimate) / d_cal * 100 if d_cal else float("nan"),
        "A_eff": A_eff,
        "A_point": A_point,
        "T_sim_days": T_sim_days,
        "v_avg": v_avg,
        "mean_ambient_c": float(np.mean(ambient_temps_c)),
        "n_session_steps": len(hours),
    }
# doc:end recompute_calendar
