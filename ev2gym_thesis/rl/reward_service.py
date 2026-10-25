"""
Week 8 (redesigned RL): reward functions for the projected (hard-constraint)
TD3 agent. Drop-in reward_function callables with EV2Gym's signature
(env, total_costs, user_satisfaction_list, *args); EV2Gym calls them after
the step, when env.current_step has already advanced (ev2gym_env.py, step,
lines 418-420), so the step just executed is env.current_step - 1.

Why the old reward is replaced (review of 2026-10-14, chapter 08 item 48).
SqTrError_TrPenalty_UserIncentives mixed three terms on unrelated scales:
squared tracking error of EV2Gym's synthetic power setpoint (~1e2-1e4 per
step), -100 per kW of overload and -1000 x (1 - satisfaction) per departing
EV. The overload term is no longer needed, because the transformer limit is
now a hard constraint (ev2gym_thesis/rl/safety.py). The other two pulled in
different directions, which chapter 05 S5.11 measured: extended training
improved that reward while the evaluation metric (tracking error) got worse.

ServedEnergyReward -- the reward aligned with the thesis's service criterion.
  r_t = E_t / E_budget,
  where E_t is the energy delivered to EVs in step t (kWh) and
  E_budget = transformer rating x step length (kWh), the most the 100 kW
  unit can deliver in one step, so r_t lies in [0, 1].
  Alignment, exact for this project's station (proved in the module test):
  - EV2Gym sets every EV's desired capacity to desired_capacity x battery
    = 1.0 x 70 kWh (station_v0_bogota.yaml, ev.desired_capacity: 1), and an
    EV arrives with battery - requested energy (utils.py, spawn_single_EV,
    lines 220-222). Charging stops at a full battery, so no energy is ever
    delivered beyond what was requested: all delivered energy is useful.
  - The episode return times E_budget therefore equals total_energy_charged.
  - Demand not served (ev2gym_thesis/demand/censoring.py) is
    (E_rejected + R_served - E_delivered) / (E_rejected + R_served), and
    E_rejected and R_served do not depend on the policy (arrivals are drawn
    at reset). Maximising the return is therefore exactly minimising DNS on
    every scenario, with no weight to tune.
  The function refuses to run if desired_capacity != 1, because the
  alignment argument would no longer hold.

CappedTrackingReward -- for the long-dwell regime, if the comparison is to
  be made on chapter 05's tracking metric. The squared tracking term of
  SqTrError_TrPenalty_UserIncentives alone (the same target, min(setpoint,
  charge potential, rating)), normalised by the rating squared. No overload
  term (hard constraint) and no satisfaction term.

Never touches ev2gym/rl_agent/*.py.
"""


def _step_hours(env) -> float:
    return env.timescale / 60.0


def _rating_kw(env, step) -> float:
    return float(sum(tr.max_power[step] for tr in env.transformers))


def _check_desired_is_full(env):
    desired = env.config["ev"]["desired_capacity"]
    if desired != 1:
        raise ValueError(
            f"ServedEnergyReward assumes ev.desired_capacity == 1 (every EV wants a full battery), "
            f"so that all delivered energy is requested energy; this config has {desired}.")


# doc:begin served_energy_reward
def ServedEnergyReward(env, total_costs, user_satisfaction_list, *args):
    _check_desired_is_full(env)
    t = env.current_step - 1
    energy_kwh = float(env.current_power_usage[t]) * _step_hours(env)
    budget_kwh = _rating_kw(env, t) * _step_hours(env)
    return energy_kwh / budget_kwh
# doc:end served_energy_reward


def served_energy_scale_kwh(env) -> float:
    """kWh represented by a reward of 1.0 at the first step (the rating is
    constant in this project's station). Return x scale = energy delivered."""
    return _rating_kw(env, 0) * _step_hours(env)


# doc:begin capped_tracking_reward
def CappedTrackingReward(env, total_costs, user_satisfaction_list, *args):
    t = env.current_step - 1
    rating = _rating_kw(env, t)
    target = min(env.power_setpoints[t], env.charge_power_potential[t], rating)
    return -((target - env.current_power_usage[t]) / rating) ** 2
# doc:end capped_tracking_reward
