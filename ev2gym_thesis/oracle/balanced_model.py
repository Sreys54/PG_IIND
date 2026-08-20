"""
Week 4, S4.2 Amendment 1: the "Balanced" oracle variant --
PowerTrackingErrorrMin's objective plus a departure-satisfaction penalty.

Design decision -- a near-full copy of
ev2gym.baselines.gurobi_models.tracking_error.PowerTrackingErrorrMin, not a
subclass overriding one method: that class fuses model construction and
solving into a single __init__ with no separate build_model()/objective()
hook to override -- there is no clean seam to inject one additional
objective term without either (a) editing the library file in place
(forbidden, CLAUDE.md rule 1) or (b) reimplementing the whole method.
Rejected alternative (a). Chosen (b), documented here rather than hidden --
the task brief explicitly anticipated this exact tension. Every constraint
block below is copied verbatim from tracking_error.py (same variable names,
same structure, so a future diff against the upstream file stays legible)
except the new user_satisfaction variable/constraint and the objective.

Satisfaction-term correction, found while adapting, not copied blindly:
profit_max.py's own user_satisfaction term is
`(ev_des_energy[p,i,t] * ev_max_energy[p,i,t-1] - energy[p,i,t])**2` --
multiplying two kWh quantities together (ev_des_energy/desired_capacity is
documented in kWh: ev2gym/models/ev.py:23,51 -- "the desired capacity of
the EV at departure time in kWh", not a fraction) produces a kWh^2 - kWh
expression, dimensionally inconsistent. This class uses the dimensionally
consistent form instead: (ev_des_energy - energy)^2, both terms in kWh.
"""
import pickle

import numpy as np
import gurobipy as gp
from gurobipy import GRB

# doc:begin balanced_oracle_penalty_weight
# "Set for this project": adapted from profit_max.py's departure-
# satisfaction penalty in STRUCTURE (a squared kWh gap at departure), not
# in scale -- profit_max.py's weight=100 was calibrated against a profit
# objective (a different unit and magnitude entirely) and would carry no
# transferable meaning here. 1.0 is the starting point (no artificial
# rescaling of either term); the S4.2 sensitivity check (0.5x/1x/2x this
# value, one cell) reports empirically how much the bound moves and
# whether this default needs revising.
SATISFACTION_PENALTY_WEIGHT = 1.0
# doc:end balanced_oracle_penalty_weight


class PowerTrackingErrorMinBalanced:
    """Optimal_Oracle_Balanced: PowerTrackingErrorrMin's tracking objective
    plus a departure-satisfaction penalty. See module docstring for why
    this duplicates most of PowerTrackingErrorrMin's __init__ rather than
    subclassing it. Interface (get_action, get_actions, algo_name) is kept
    identical so it drops into evaluate_oracle.py the same way."""

    algo_name = 'Optimal (Offline, Balanced)'

    def __init__(self, replay_path=None, satisfaction_weight=SATISFACTION_PENALTY_WEIGHT, **kwargs):

        replay = pickle.load(open(replay_path, 'rb'))

        self.sim_length = replay.sim_length
        self.n_cs = replay.n_cs
        self.number_of_ports_per_cs = replay.max_n_ports
        self.n_transformers = replay.n_transformers
        self.timescale = replay.timescale
        dt = replay.timescale / 60

        tra_max_amps = replay.tra_max_amps
        tra_min_amps = replay.tra_min_amps
        cs_transformer = replay.cs_transformer
        port_max_charge_current = replay.port_max_charge_current
        port_min_charge_current = replay.port_min_charge_current
        port_max_discharge_current = replay.port_max_discharge_current
        port_min_discharge_current = replay.port_min_discharge_current
        voltages = replay.voltages / 1000

        power_setpoints = replay.power_setpoints

        cs_ch_efficiency = replay.cs_ch_efficiency
        cs_dis_efficiency = replay.cs_dis_efficiency

        ev_max_energy = replay.ev_max_energy
        ev_des_energy = replay.ev_des_energy  # NEW vs. tracking_error.py: needed for the satisfaction term

        ev_max_ch_power = replay.ev_max_ch_power
        ev_max_dis_power = replay.ev_max_dis_power
        u = replay.u
        energy_at_arrival = replay.energy_at_arrival
        ev_arrival = replay.ev_arrival
        t_dep = replay.t_dep

        self.m = gp.Model("ev_city_balanced")

        energy = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                 vtype=GRB.CONTINUOUS, name='energy')
        current_ev_dis = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                         vtype=GRB.CONTINUOUS, name='current_ev_dis')
        current_ev_ch = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                        vtype=GRB.CONTINUOUS, name='current_ev_ch')
        act_current_ev_dis = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                             vtype=GRB.CONTINUOUS, name='act_current_ev_dis')
        act_current_ev_ch = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                            vtype=GRB.CONTINUOUS, name='act_current_ev_ch')
        current_cs_ch = self.m.addVars(self.n_cs, self.sim_length, vtype=GRB.CONTINUOUS, name='current_cs_ch')
        current_cs_dis = self.m.addVars(self.n_cs, self.sim_length, vtype=GRB.CONTINUOUS, name='current_cs_dis')
        omega_ch = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                   vtype=GRB.BINARY, name='omega_ch')
        omega_dis = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                    vtype=GRB.BINARY, name='omega_dis')
        power_cs_ch = self.m.addVars(self.n_cs, self.sim_length, vtype=GRB.CONTINUOUS, name='power_cs_ch')
        power_cs_dis = self.m.addVars(self.n_cs, self.sim_length, vtype=GRB.CONTINUOUS, name='power_cs_dis')
        power_tr_ch = self.m.addVars(self.n_transformers, self.sim_length, vtype=GRB.CONTINUOUS, name='power_tr_ch')
        power_tr_dis = self.m.addVars(self.n_transformers, self.sim_length, vtype=GRB.CONTINUOUS, name='power_tr_dis')
        current_tr_ch = self.m.addVars(self.n_transformers, self.sim_length, vtype=GRB.CONTINUOUS, name='current_tr_ch')
        current_tr_dis = self.m.addVars(self.n_transformers, self.sim_length, vtype=GRB.CONTINUOUS, name='current_tr_dis')
        power_error = self.m.addVars(self.sim_length, vtype=GRB.CONTINUOUS, name='power_error')

        # NEW vs. tracking_error.py: departure-satisfaction penalty variable.
        user_satisfaction = self.m.addVars(self.number_of_ports_per_cs, self.n_cs, self.sim_length,
                                            vtype=GRB.CONTINUOUS, name='user_satisfaction')

        for t in range(self.sim_length):
            for i in range(self.n_transformers):
                self.m.addConstr(current_tr_ch[i, t] == gp.quicksum(
                    current_cs_ch[m, t] for m in range(self.n_cs) if cs_transformer[m] == i))
                self.m.addConstr(current_tr_dis[i, t] == gp.quicksum(
                    current_cs_dis[m, t] for m in range(self.n_cs) if cs_transformer[m] == i))
                self.m.addConstr(power_tr_ch[i, t] == gp.quicksum(
                    power_cs_ch[m, t] for m in range(self.n_cs) if cs_transformer[m] == i),
                    name=f'power_tr_ch.{i}.{t}')
                self.m.addConstr(power_tr_dis[i, t] == gp.quicksum(
                    power_cs_dis[m, t] for m in range(self.n_cs) if cs_transformer[m] == i),
                    name=f'power_tr_dis.{i}.{t}')

            power_error[t] = (gp.quicksum(power_tr_ch[i, t] - power_tr_dis[i, t]
                               for i in range(self.n_transformers)) - power_setpoints[t]) ** 2

        self.m.addConstrs(power_cs_ch[i, t] == (current_cs_ch[i, t] * voltages[i])
                           for i in range(self.n_cs) for t in range(self.sim_length))
        self.m.addConstrs(power_cs_dis[i, t] == (current_cs_dis[i, t] * voltages[i])
                           for i in range(self.n_cs) for t in range(self.sim_length))

        self.m.addConstrs((current_tr_ch[i, t] - current_tr_dis[i, t] <= tra_max_amps[i, t]
                            for i in range(self.n_transformers) for t in range(self.sim_length)),
                           name='tr_current_limit_max')
        self.m.addConstrs((current_tr_ch[i, t] - current_tr_dis[i, t] >= tra_min_amps[i, t]
                            for i in range(self.n_transformers) for t in range(self.sim_length)),
                           name='tr_current_limit_min')

        self.m.addConstrs((current_cs_ch[i, t] == act_current_ev_ch.sum('*', i, t)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='cs_ch_current_output')
        self.m.addConstrs((current_cs_dis[i, t] == act_current_ev_dis.sum('*', i, t)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='cs_dis_current_output')

        self.m.addConstrs((-current_cs_dis[i, t] + current_cs_ch[i, t] >= port_max_discharge_current[i]
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='cs_current_dis_limit_max')
        self.m.addConstrs((-current_cs_dis[i, t] + current_cs_ch[i, t] <= port_max_charge_current[i]
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='cs_curent_ch_limit_max')

        self.m.addConstrs((act_current_ev_ch[p, i, t] == current_ev_ch[p, i, t] * omega_ch[p, i, t]
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='act_ev_current_ch')
        self.m.addConstrs((act_current_ev_dis[p, i, t] == current_ev_dis[p, i, t] * omega_dis[p, i, t]
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='act_ev_current_dis')

        self.m.addConstrs((current_ev_ch[p, i, t] >= port_min_charge_current[i]
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='ev_current_ch_limit_min')
        self.m.addConstrs((current_ev_dis[p, i, t] >= -port_min_discharge_current[i]
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='ev_current_dis_limit_min')

        self.m.addConstrs((current_ev_ch[p, i, t] <= min(ev_max_ch_power[p, i, t] / voltages[i], port_max_charge_current[i])
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)
                            if u[p, i, t] == 1 and ev_arrival[p, i, t] == 0),
                           name='ev_current_ch_limit_max')
        self.m.addConstrs((current_ev_dis[p, i, t] <= min(-ev_max_dis_power[p, i, t] / voltages[i], -port_max_discharge_current[i])
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)
                            if u[p, i, t] == 1 and ev_arrival[p, i, t] == 0),
                           name='ev_current_dis_limit_max')

        for t in range(self.sim_length):
            for i in range(self.n_cs):
                for p in range(self.number_of_ports_per_cs):
                    if u[p, i, t] == 0 or ev_arrival[p, i, t] == 1:
                        self.m.addLConstr((omega_ch[p, i, t] == 0), name=f'omega_empty_port_ch.{p}.{i}.{t}')
                        self.m.addLConstr((omega_dis[p, i, t] == 0), name=f'omega_empty_port_dis.{p}.{i}.{t}')
                    if u[p, i, t] == 0 and t_dep[p, i, t] == 0:
                        self.m.addLConstr(energy[p, i, t] == 0, name=f'ev_empty_port_energy.{p}.{i}.{t}')

        for t in range(1, self.sim_length):
            for i in range(self.n_cs):
                for p in range(self.number_of_ports_per_cs):
                    if ev_arrival[p, i, t] == 1:
                        self.m.addLConstr(energy[p, i, t] == energy_at_arrival[p, i, t],
                                           name=f'ev_arrival_energy.{p}.{i}.{t}')
                    if u[p, i, t - 1] == 1:
                        self.m.addConstr(energy[p, i, t] == (
                            energy[p, i, t - 1]
                            + act_current_ev_ch[p, i, t] * voltages[i] * cs_ch_efficiency[i, t] * dt
                            - act_current_ev_dis[p, i, t] * voltages[i] * cs_dis_efficiency[i, t] * dt),
                            name=f'ev_energy.{p}.{i}.{t}')

        self.m.addConstrs((energy[p, i, t] >= 0
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='ev_energy_level_min')
        self.m.addConstrs((energy[p, i, t] <= ev_max_energy[p, i, t]
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)
                            if t_dep[p, i, t] != 1),
                           name='ev_energy_level_max')

        self.m.addConstrs((omega_dis[p, i, t] * omega_ch[p, i, t] == 0
                            for p in range(self.number_of_ports_per_cs)
                            for i in range(self.n_cs) for t in range(self.sim_length)),
                           name='ev_power_mode_2')

        # NEW vs. tracking_error.py: departure-satisfaction penalty
        # constraint, dimensionally-corrected form -- see module docstring.
        for t in range(self.sim_length):
            for i in range(self.n_cs):
                for p in range(self.number_of_ports_per_cs):
                    if t_dep[p, i, t] == 1:
                        self.m.addConstr(
                            user_satisfaction[p, i, t] == (ev_des_energy[p, i, t] - energy[p, i, t]) ** 2,
                            name=f'ev_user_satisfaction.{p}.{i}.{t}')

        # Objective: tracking error plus the satisfaction penalty -- both
        # minimized (unlike profit_max.py, which maximizes profit minus the
        # penalty; this model has no profit term to maximize).
        self.m.setObjective(power_error.sum() + satisfaction_weight * user_satisfaction.sum(),
                             GRB.MINIMIZE)

        self.m.params.NonConvex = 2
        self.m.optimize()

        self.act_current_ev_ch = act_current_ev_ch
        self.act_current_ev_dis = act_current_ev_dis
        self.port_max_charge_current = port_max_charge_current
        self.port_max_discharge_current = port_max_discharge_current

        if self.m.status != GRB.Status.OPTIMAL:
            print(f'Optimization ended with status {self.m.status}')
            exit()

        self.get_actions()

    def get_actions(self):
        self.actions = np.zeros([self.number_of_ports_per_cs, self.n_cs, self.sim_length])
        for t in range(self.sim_length):
            for i in range(self.n_cs):
                for p in range(self.number_of_ports_per_cs):
                    if self.act_current_ev_ch[p, i, t].x > 0:
                        self.actions[p, i, t] = self.act_current_ev_ch[p, i, t].x / self.port_max_charge_current[i]
                    elif self.act_current_ev_dis[p, i, t].x > 0:
                        self.actions[p, i, t] = self.act_current_ev_dis[p, i, t].x / self.port_max_discharge_current[i]
        return self.actions

    def get_action(self, env, **kwargs):
        step = env.current_step
        return self.actions[:, :, step].T.reshape(-1)
