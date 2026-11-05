"""
Week 8 advisor review (2026-11-01), C2: MPC and oracle with the operator's
objective, for the DC regime with the station-level arrival generator
(ev2gym_thesis/demand/station_arrivals.py). New code; the library MPC
classes are not edited or subclassed (their hard departure-energy
constraints are what made MPC_TrackingG2V infeasible in 37.7% of DC steps).

Formulation (units: kW, kWh, h; dt = 0.25 h):
  max  sum_k sum_e P[e,k] dt  -  rho * sum_{e in D} sigma[e]
  s.t. 0 <= P[e,k] <= Pmax_e * a[e,k]                     (a = 1 while e is connected)
       sum_e P[e,k] <= B_k = 0.999 x transformer rating    (kW, every k)
       sum_k P[e,k] dt <= Rrem_e                           (no energy beyond the request)
       sum_k P[e,k] dt >= Rrem_e - sigma[e], sigma[e] >= 0 (e in D: departs within the horizon)
  Rrem_e = desired - current capacity (kWh); eta = 1 (config charge_efficiency
  = 1), so E[e,k+1] = E[e,k] + P[e,k] dt and E <= C reduce to the
  cumulative bound above; Pmax_e = min(port rated power, EV max power).
  P = 0, sigma = Rrem is always feasible, so the model is never infeasible;
  every solve status other than OPTIMAL is counted and reported.

rho = 10 (kWh of objective per kWh of shortfall; labelled, set for this
project). Because delivered energy cannot exceed the request, sigma_e =
Rrem_e - sum_k P[e,k] dt at the optimum, so energy to an EV that departs
inside the horizon is worth 1 + rho and energy to any other EV 1: any
rho > 0 gives earliest-departure priority without reducing total energy;
rho = 10 makes the priority dominate numerical ties. With a one-day
horizon (Oracle-E) every EV is in D and the objective is
(1 + rho) x energy - constant: the oracle maximises energy delivered.

Variants (information each one uses at step t):
  MPC-soft      connected EVs with their TRUE departure times + the drivers
                that will connect within the horizon (arrival, requested
                energy, port: the fixed-departure plan); H = 10 steps.
                Not causal.
  MPC-soft-est  connected EVs only; departure ESTIMATED as arrival + 42 min
                (connected round(42/15) = 3 steps, d = a + 2; d = t once the
                EV has stayed longer); no future arrivals; H = 10. Causal.
                MPC-soft minus MPC-soft-est is the value of knowing departure
                times (and the next arrivals), everything else fixed.
  Oracle-E      one solve at step 0 over the whole day, full knowledge of
                every driver the station will accept. Not causal. The upper
                bound on energy delivered for any arm under this arrival
                stream, port assignment and transformer budget.
"""
import gurobipy as gp
import numpy as np
from gurobipy import GRB

from ev2gym_thesis.heuristics import BUDGET_FRACTION
from ev2gym_thesis.rl.safety import port_rated_kw

RHO = 10.0
HORIZON = 10
DWELL_ESTIMATE_MIN = 42.0
STATS = {"solves": 0, "non_optimal": 0}


def _ports(env):
    out = []
    for cs in env.charging_stations:
        for p in range(cs.n_ports):
            out.append((cs, p))
    return out


def _pmax(cs, ev):
    return min(port_rated_kw(cs), float(ev.max_ac_charge_power))


# doc:begin operator_lp
def solve_operator_lp(sessions, t0, horizon, budget_kw, dt_h, rho=RHO):
    """sessions: list of dicts with port index g, first and last connected
    step (inclusive), Rrem (kWh), Pmax (kW) and whether the departure
    constraint applies. Returns {g: kW at step t0} and the model status."""
    m = gp.Model("operator_mpc")
    m.setParam("OutputFlag", 0)
    m.setParam("Threads", 1)
    P, sig = {}, {}
    for j, s in enumerate(sessions):
        for k in range(max(s["first"], t0), min(s["last"], t0 + horizon - 1) + 1):
            P[j, k] = m.addVar(lb=0.0, ub=s["pmax"], name=f"P_{j}_{k}")
        e = gp.quicksum(P[j, k] * dt_h for k in range(t0, t0 + horizon) if (j, k) in P)
        m.addConstr(e <= s["rrem"])
        if s["departs"]:
            sig[j] = m.addVar(lb=0.0, name=f"sigma_{j}")
            m.addConstr(e >= s["rrem"] - sig[j])
    for k in range(t0, t0 + horizon):
        terms = [P[j, k] for j in range(len(sessions)) if (j, k) in P]
        if terms:
            m.addConstr(gp.quicksum(terms) <= budget_kw[k - t0])
    m.setObjective(gp.quicksum(v * dt_h for v in P.values()) - rho * gp.quicksum(sig.values()), GRB.MAXIMIZE)
    m.optimize()
    STATS["solves"] += 1
    ok = m.status == GRB.OPTIMAL
    if not ok:
        STATS["non_optimal"] += 1
    plan = {}
    for (j, k), v in P.items():
        val = v.X if ok else 0.0
        plan.setdefault(k, {})[sessions[j]["g"]] = plan.get(k, {}).get(sessions[j]["g"], 0.0) + val
    return plan, m.status
# doc:end operator_lp


class OperatorMPC:
    """MPC-soft (estimate_departures=False) or MPC-soft-est (True)."""

    def __init__(self, env, estimate_departures=False, horizon=HORIZON, rho=RHO):
        self.est, self.h, self.rho = estimate_departures, horizon, rho
        self.ports = _ports(env)
        self.dt = env.timescale / 60.0
        self.n_est = int(round(DWELL_ESTIMATE_MIN / env.timescale))

    def _budget(self, env, t):
        T = env.simulation_length
        return [BUDGET_FRACTION * float(sum(tr.max_power[min(k, T - 1)] for tr in env.transformers))
                for k in range(t, t + self.h)]

    def get_action(self, env):
        t = env.current_step
        sessions = []
        for g, (cs, p) in enumerate(self.ports):
            ev = cs.evs_connected[p]
            if ev is None:
                continue
            last = ev.time_of_departure
            if self.est:
                last = max(t, ev.time_of_arrival + self.n_est - 1)
            sessions.append({"g": g, "first": t, "last": last, "pmax": _pmax(cs, ev),
                             "rrem": max(0.0, float(ev.desired_capacity - ev.current_capacity)),
                             "departs": last <= t + self.h - 1})
        if not self.est:  # drivers that will connect within the horizon (fixed-departure plan)
            index = {(cs.id, p): g for g, (cs, p) in enumerate(self.ports)}
            for ev in env._sa["stream"]:
                if t < ev.time_of_arrival <= t + self.h - 1 and ev._sa_key in env._sa["planned"]:
                    loc = env._sa["planned"][ev._sa_key]
                    cs = self.ports[index[loc]][0]
                    sessions.append({"g": index[loc], "first": ev.time_of_arrival, "last": ev.time_of_departure,
                                     "pmax": _pmax(cs, ev),
                                     "rrem": float(ev.desired_capacity - ev.battery_capacity_at_arrival),
                                     "departs": ev.time_of_departure <= t + self.h - 1})
        a = np.zeros(len(self.ports))
        if not any(s["first"] <= t for s in sessions):
            return a
        plan, _ = solve_operator_lp(sessions, t, self.h, self._budget(env, t), self.dt, self.rho)
        for g, kw in plan.get(t, {}).items():
            a[g] = min(1.0, kw / port_rated_kw(self.ports[g][0]))
        return np.floor(a * 1e5) / 1e5  # as safety.project_actions: EV2Gym's 5-decimal rounding cannot raise it


class OracleE:
    """Oracle-E: one full-day solve at step 0 with every accepted driver."""

    def __init__(self, env, rho=RHO):
        self.ports = _ports(env)
        index = {(cs.id, p): g for g, (cs, p) in enumerate(self.ports)}
        T = env.simulation_length
        sessions = []
        for ev in env.EVs_profiles:  # the accepted drivers, with their ports (fixed-departure plan)
            g = index[(ev.location, ev.id)]
            sessions.append({"g": g, "first": ev.time_of_arrival, "last": ev.time_of_departure,
                             "pmax": _pmax(self.ports[g][0], ev),
                             "rrem": float(ev.desired_capacity - ev.battery_capacity_at_arrival), "departs": True})
        budget = [BUDGET_FRACTION * float(sum(tr.max_power[k] for tr in env.transformers)) for k in range(T)]
        self.plan, self.status = solve_operator_lp(sessions, 0, T, budget, env.timescale / 60.0, rho)

    def get_action(self, env):
        a = np.zeros(len(self.ports))
        for g, kw in self.plan.get(env.current_step, {}).items():
            if self.ports[g][0].evs_connected[self.ports[g][1]] is not None:
                a[g] = min(1.0, kw / port_rated_kw(self.ports[g][0]))
        return np.floor(a * 1e5) / 1e5
