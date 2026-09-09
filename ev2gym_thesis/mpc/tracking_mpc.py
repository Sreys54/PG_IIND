"""
Week 5, Part B, Gate 1 deliverable: a receding-horizon, G2V-only,
tracking-objective MPC controller.

Why this exists as new code, not a config on a shipped class: every class
in `ev2gym/baselines/mpc/` minimizes a price-linear objective
(`f @ u`, e.g. `eMPC.py:123`) -- none matches this thesis's Public/PST
tracking objective, the same family the Week 4 oracle
(`PowerTrackingErrorrMin`) was selected for over the price-driven
`V2GProfitMaxOracleGB` (`04_oracle_and_pitd3.md` S4.2). Under Part A's
Colombian flat-tariff finding (`05_algorithm_comparison.md` S5.1), a
price objective is additionally provably inert (maximizing profit
degenerates to maximizing energy delivered), which independently rules
out reusing the shipped price objective even before the family-fit
argument.

Never modifies `ev2gym/baselines/mpc/mpc.py` -- subclasses the unmodified
abstract `MPC` base class (per `CLAUDE.md` rule 1), reusing only its
already-causal machinery: `reconstruct_state` (reads currently-connected
EVs' actual SoC), `update_tr_power` (causal transformer-capacity
forecast), `calculate_XF_G2V`/`g2v_station_models`/
`calculate_InequalityConstraints` (battery-capacity bookkeeping, no
discharge variable -- the same G2V-only structure `eMPC_G2V` uses, so no
`force_g2v`-style fix is needed the way the Gurobi oracle needed one).

Objective matches `PowerTrackingErrorrMin`'s exactly (no
`min(setpoint, charge_power_potential)` clamp, unlike the RL reward
functions) so this arm's optimality gap against `Optimal_Oracle_Tracking`
is measured on the identical quantity both are optimizing --
Sigma_i (station_power_i - power_setpoint_i)^2 over the receding horizon,
station_power_i = sum of all ports' charging power at horizon step i
(single-transformer station; summed per-transformer in general, matching
`tracking_error.py`'s own `power_tr_ch`/`power_tr_dis` summation).

Causality declaration (Week 5 Gate 1 audit, `05_algorithm_comparison.md`
S5.5): like every class inheriting `MPC.__init__`, this controller knows
the exact departure time of every currently-connected EV (not just the
current dwell duration a real operator/PublicPST would see) and the exact
arrival/desired-capacity of any EV that will arrive within the rolling
`control_horizon` window. `env.power_setpoints` is NOT a causality issue
-- it is EV2Gym's own published operational setpoint, already read by
every other arm each step (`RoundRobin`, `PublicPST`'s state, the
Gurobi oracle); reading a few steps of it ahead is a mild extension of
already-causal information, not a new leak on the same order as EV
schedule/price omniscience.
"""
import gurobipy as gp
from gurobipy import GRB
import numpy as np

from ev2gym.baselines.mpc.mpc import MPC

# doc:begin control_horizon_default
# Origin: "set for this project" -- matches the shipped eMPC/OCMF classes'
# own default (eMPC.py:18, ocmf_mpc.py:18), kept as the starting point for
# Gate 2's timing calibration rather than picked independently; the final
# value is chosen in section 14's horizon-sensitivity deliverable, not here.
DEFAULT_CONTROL_HORIZON = 10
# doc:end control_horizon_default


class MPCTrackingG2V(MPC):
    """Receding-horizon MPC, G2V-only (no discharge decision variable),
    minimizing Sigma (station_power - power_setpoint)^2 over the horizon --
    the same objective family as this thesis's chosen Optimal_Oracle_Tracking,
    adapted from an offline single-shot solve to a receding-horizon one.

    Causality: NOT causal on EV arrival/departure information (see module
    docstring) -- registered under the explicit name `MPC_TrackingG2V`,
    never plain "MPC", so this is never mistaken for a deployable
    causal controller in any table or figure.
    """

    def __init__(self, env, control_horizon=DEFAULT_CONTROL_HORIZON,
                 verbose=False, time_limit=200, MIPGap=None, **kwargs):
        super().__init__(env, control_horizon, verbose,
                          time_limit=time_limit, MIPGap=MIPGap)
        self.na = self.n_ports
        self.nb = self.na  # G2V only: one decision variable per port per step

    def get_action(self, env):
        t = env.current_step
        h = self.control_horizon
        n = self.n_ports

        # Causal transformer-capacity forecast (station_v0_bogota's
        # transformer.max_power is constant, so this is inert for the
        # reference config, but the causal path is used regardless of
        # config, per the Gate 1 audit's own distinction).
        self.update_tr_power(t)
        self.reconstruct_state(t)
        self.calculate_XF_G2V(t)
        self.g2v_station_models(t)
        self.calculate_InequalityConstraints(t)
        self.set_power_limits_G2V(t)

        # Power setpoint over the horizon -- EV2Gym's own published
        # operational signal, zero-padded past simulation_length exactly
        # like every other per-step array in this codebase.
        setpoints = np.array(env.power_setpoints[t:t + h], dtype=float)
        if len(setpoints) < h:
            setpoints = np.append(setpoints, np.zeros(h - len(setpoints)))

        model = gp.Model("tracking_mpc")
        model.setParam('OutputFlag', self.output_flag)
        u = model.addMVar(n * h, vtype=GRB.CONTINUOUS, lb=0.0, name="u")

        model.addConstr((self.AU @ u) <= self.bU, name="constr1")
        model.addConstr((0 <= u), name="constr2a")
        model.addConstr((u <= self.UB), name="constr2b")

        # Hard transformer-capacity constraint, matching eMPC_G2V's own
        # (eMPC.py:236-246) -- calculate_InequalityConstraints encodes
        # battery-capacity bounds, not transformer capacity, so this is
        # required separately, exactly as the shipped class does it.
        for tr_index in range(self.number_of_transformers):
            for i in range(h):
                model.addConstr(
                    (gp.quicksum(u[j] for index, j in enumerate(
                        range(i * n, (i + 1) * n))
                        if self.cs_transformers[index] == tr_index) +
                     self.tr_loads[tr_index, i] + self.tr_pv[tr_index, i]
                     <= self.tr_power_limit[tr_index, i]),
                    name=f"constr_tr_{tr_index}_t{i}")

        # Tracking objective: station power at each horizon step vs. the
        # published setpoint, squared -- identical formula to
        # PowerTrackingErrorrMin's power_error term (tracking_error.py:168-170).
        obj = gp.QuadExpr()
        for i in range(h):
            power_i = gp.quicksum(u[i * n:(i + 1) * n])
            obj += (power_i - setpoints[i]) * (power_i - setpoints[i])

        model.setObjective(obj, GRB.MINIMIZE)
        if self.MIPGap is not None:
            model.params.MIPGap = self.MIPGap
        model.params.TimeLimit = self.time_limit
        model.optimize()
        self.total_exec_time += model.Runtime

        if model.status in (GRB.Status.INF_OR_UNBD, GRB.Status.INFEASIBLE):
            print(f"MPCTrackingG2V: INFEASIBLE at step {t}, applying default (0) actions")
            return np.zeros(n)

        a = u.X[:n]
        actions = np.zeros(n)
        for i in range(n):
            actions[i] = a[i] / self.max_ch_power[i] if self.max_ch_power[i] > 0 else 0.0

        return actions
