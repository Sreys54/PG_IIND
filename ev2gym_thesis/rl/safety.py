"""
Week 8 (redesigned RL): a hard transformer-capacity constraint for the RL
agent, applied as an action projection before every simulator step.

Why (review of 2026-10-14, chapter 08 item 48). The Weeks 3-6 agents
learned the transformer limit only through a penalty term in the reward
(-100 per kW of overload, SqTrError_TrPenalty_UserIncentives). Nothing
stopped their actions from exceeding the rating, so every TD3 checkpoint
overloaded in some runs, while the arm they were compared with in the DC
regime, the transformer-aware Round Robin, cannot exceed the rating by
construction. This module gives the agent the same guarantee, using the
same information that arm uses: the transformer rating at the current step
and the rated power of each port.

Projection (labelled design choice). EV2Gym maps a charging action
a in [0, 1] on a port to a pilot current a * max_charge_current
(ev2gym/models/ev_charger.py, step, lines 167-176). The power the EV then
draws is at most a * P_port, with P_port = max_charge_current * voltage *
sqrt(phases) / 1000 kW (ev2gym/models/ev.py, _charge: the pilot is capped by
the EV's own maximum rate, and charge_efficiency <= 1 can only lower the
energy credited). So sum(a_i * P_port_i) over the ports of a transformer is
an upper bound on that transformer's EV load in the step. If the bound
exceeds the budget (BUDGET_FRACTION x the rating at that step), every
connected port's action is scaled by the same factor budget / bound. A
common factor keeps the policy's relative priorities between EVs; only the
total is cut. Ports with no EV get action 0 (EV2Gym already ignores them,
ev_charger.py lines 137-140; zeroing them here keeps the bound tight).

The bound is conservative: an EV near full, or one whose own maximum rate
is below P_port, draws less than a * P_port, and the budget it leaves
unused is not reallocated. The transformer-aware Round Robin makes the same
assumption (it charges ceil(budget / average port power) EVs at full
pilot), so the comparison between the two is on equal terms.

BUDGET_FRACTION = 0.999 is the transformer-aware Round Robin's own margin
(ev2gym_thesis/heuristics.py), so float rounding cannot register as
overload.

The projection reads only the connected EVs (occupancy) and the rating: no
departure time, no requested energy. It is causal.

Never touches ev2gym/models/*.py or ev2gym/rl_agent/*.py.
"""
import math

import numpy as np

from ev2gym_thesis.heuristics import BUDGET_FRACTION


def port_rated_kw(cs) -> float:
    """Rated power of one port of charging station `cs`, in kW."""
    return cs.max_charge_current * cs.voltage * math.sqrt(cs.phases) / 1000.0


# doc:begin project_actions
def project_actions(env, action, budget_fraction: float = BUDGET_FRACTION):
    """Project a raw policy action onto the transformer-feasible set.

    Returns (projected_action, info) where info holds the bound before
    projection, the budget and the scaling factor applied, summed or taken
    over transformers (one transformer in this project's station).
    The input is not modified.
    """
    a = np.clip(np.asarray(action, dtype=np.float64).reshape(-1), 0.0, 1.0).copy()
    step = env.current_step
    # Group port indices by transformer, in EV2Gym's own action order
    # (charging stations in order, ports in order; ev2gym_env.py, step,
    # lines 356-385).
    groups = {}
    idx = 0
    for cs in env.charging_stations:
        p_kw = port_rated_kw(cs)
        for port in range(cs.n_ports):
            if cs.evs_connected[port] is None:
                a[idx] = 0.0
            groups.setdefault(cs.connected_transformer, []).append((idx, p_kw))
            idx += 1
    assert idx == a.size, f"action has {a.size} entries, the station has {idx} ports"

    bound_total, budget_total, min_scale = 0.0, 0.0, 1.0
    for tr_id, members in groups.items():
        tr = env.transformers[tr_id]
        budget = budget_fraction * float(tr.max_power[step])
        bound = float(sum(a[i] * p for i, p in members))
        scale = 1.0
        if bound > budget:
            scale = budget / bound if bound > 0 else 0.0
            for i, _ in members:
                a[i] *= scale
        bound_total += bound
        budget_total += budget
        min_scale = min(min_scale, scale)
    # EV2Gym rounds every action to 5 decimals before using it
    # (ev_charger.py, step, line 157: action = round(action, 5)), which can
    # raise a scaled action by up to 5e-6. Truncating down to 5 decimals here
    # makes that rounding a no-op, so the bound above still holds on the
    # actions EV2Gym actually applies. Found by test_safe_rl (a float32 cast
    # plus the rounding put one step at 99.9003 kW against a 99.9 kW budget).
    a = np.floor(a * 1e5) / 1e5
    return a, {"bound_kw": bound_total, "budget_kw": budget_total,
               "scale": min_scale, "active": min_scale < 1.0}
# doc:end project_actions


def safe_step(env, action):
    """env.step() on the projected action. Returns EV2Gym's 5-tuple plus the
    projection info."""
    projected, info = project_actions(env, action)
    return env.step(projected) + (info,)
