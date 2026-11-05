"""
Week 8 advisor review, A6: what each arm uses at step t, read from the code
(file and line), and therefore whether it is causal. One row per arm.

Columns: connected EVs (occupancy), transformer rating, energy requested
(remaining need), departure times, future arrivals, EV2Gym power setpoint.
The setpoint (ev2gym/utilities/utils.py, generate_power_setpoints, lines
664-772) is built at reset from EVERY EV of the day: each EV's requested
energy x (100 + flexibility)/100 (line 696, 709) spread over
[arrival + 1, departure) (lines 715-718, 753), then median-smoothed over
steps t-2..t+2 (line 772, window 5 x 15/timescale). An arm that reads
setpoint[t] therefore receives, indirectly, the departure times and energy
of the connected EVs and the arrivals of the next two steps.
"""
YES, NO = "yes", "no"
INDIRECT = "indirect (via setpoint)"

COLUMNS = ["arm", "regimes", "connected_evs", "transformer_rating", "requested_energy", "departure_times",
           "future_arrivals", "power_setpoint", "causal", "code"]

INFORMATION_TABLE = [
    {"arm": "AFAP", "regimes": "both", "connected_evs": YES, "transformer_rating": NO, "requested_energy": NO,
     "departure_times": NO, "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "ev2gym/baselines/heuristics.py, ChargeAsFastAsPossible (action 1 on every port; EV2Gym zeroes empty "
             "ports, ev_charger.py lines 137-140)"},
    {"arm": "RR (EV2Gym Round Robin)", "regimes": "both", "connected_evs": YES, "transformer_rating": NO,
     "requested_energy": "full / not full only (SoC < 1)", "departure_times": INDIRECT,
     "future_arrivals": INDIRECT + ", next 2 steps", "power_setpoint": YES, "causal": NO,
     "code": "ev2gym/baselines/heuristics.py lines 58-77 (total power = power_setpoints[t]); buffer update reads "
             "get_soc() < 1 (lines 40-52)"},
    {"arm": "RR-TA (transformer-aware Round Robin)", "regimes": "both", "connected_evs": YES,
     "transformer_rating": YES, "requested_energy": "full / not full only (SoC < 1)", "departure_times": NO,
     "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "ev2gym_thesis/heuristics.py, RoundRobinTransformerCapped.get_action (replaces setpoint[t] by "
             "0.999 x rating before calling RoundRobin.get_action, restores it after)"},
    {"arm": "PS (AFAP + safety layer)", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": NO, "departure_times": NO, "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "ev2gym_thesis/rl/safety.py, project_actions (common scaling factor, 0.999 x rating)"},
    {"arm": "FIX12.5", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": "design value only",
     "requested_energy": NO, "departure_times": NO, "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "scripts/review_dc.py, _fixed_kw_policy (12.5 kW / port rated power on connected ports)"},
    {"arm": "RR+S", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": "full / not full only", "departure_times": INDIRECT, "future_arrivals": INDIRECT,
     "power_setpoint": YES, "causal": NO, "code": "EV2Gym RoundRobin + ev2gym_thesis/rl/safety.py"},
    {"arm": "Random / Random+S", "regimes": "both / DC", "connected_evs": "only through EV2Gym's zeroing "
     "(Random); the safety layer reads occupancy (Random+S)", "transformer_rating": "Random+S only",
     "requested_energy": NO, "departure_times": NO, "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "scripts/evaluate_rl.py, eval_random_policy; scripts/review_dc.py, _Random"},
    {"arm": "TD3 (Weeks 3-6, PublicPST state)", "regimes": "long-dwell", "connected_evs": YES,
     "transformer_rating": NO, "requested_energy": "full / not full flag and energy exchanged so far",
     "departure_times": INDIRECT, "future_arrivals": INDIRECT, "power_setpoint": YES, "causal": NO,
     "code": "ev2gym/rl_agent/state.py lines 6-60 (PublicPST: t/T, power_setpoints[t], last power; per port "
             "full flag, energy exchanged, steps since arrival)"},
    {"arm": "TD3_safe with ServiceState", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating":
     "yes (safety layer; rating normalises the state)", "requested_energy": "yes (SoC; CCS reports it)",
     "departure_times": INDIRECT, "future_arrivals": INDIRECT, "power_setpoint": YES, "causal": NO,
     "code": "ev2gym_thesis/rl/state_service.py, ServiceState (global entry 2 = power_setpoints[t] / rating)"},
    {"arm": "TD3_safe with ServiceStateCausal", "regimes": "DC (Week 8)", "connected_evs": YES,
     "transformer_rating": "yes (safety layer)", "requested_energy": "yes (SoC)", "departure_times": NO,
     "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "ev2gym_thesis/rl/state_service.py, ServiceStateCausal (ServiceState without the setpoint)"},
    {"arm": "MPC-T (MPC_TrackingG2V)", "regimes": "long-dwell (+ DC in the Final capacity brief)",
     "connected_evs": YES, "transformer_rating": YES, "requested_energy": YES, "departure_times": "yes (exact)",
     "future_arrivals": "yes, within the 10-step horizon", "power_setpoint": "yes, 10 steps ahead",
     "causal": NO, "code": "ev2gym_thesis/mpc/tracking_mpc.py lines 81-150; ev2gym/baselines/mpc/mpc.py "
                           "(MPC.__init__ reads every EV profile; reconstruct_state)"},
    {"arm": "MPC-E (MPC_EnergyMaxG2V)", "regimes": "long-dwell", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": YES, "departure_times": "yes (exact)", "future_arrivals": "yes, within the horizon",
     "power_setpoint": NO, "causal": NO,
     "code": "ev2gym_thesis/mpc/energy_max_mpc.py (eMPC_G2V with ch_prices = 1.0 flat); "
             "ev2gym/baselines/mpc/eMPC.py lines 180-273"},
    {"arm": "Oracle-T / Oracle-B", "regimes": "long-dwell (+ DC Oracle-T)", "connected_evs": YES,
     "transformer_rating": YES, "requested_energy": YES, "departure_times": "yes (exact)",
     "future_arrivals": "yes, whole day", "power_setpoint": "yes, whole day", "causal": NO,
     "code": "ev2gym/baselines/gurobi_models/tracking_error.py; ev2gym_thesis/oracle/balanced_model.py "
             "(EV2Gym replay of the whole day)"},
    {"arm": "MPC-soft", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": YES, "departure_times": "yes (exact)", "future_arrivals": "yes, within 10 steps",
     "power_setpoint": NO, "causal": NO, "code": "ev2gym_thesis/mpc/operator_mpc.py, OperatorMPC"},
    {"arm": "MPC-soft-est", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": "yes (remaining need from SoC)", "departure_times": "estimated (arrival + 42 min)",
     "future_arrivals": NO, "power_setpoint": NO, "causal": YES,
     "code": "ev2gym_thesis/mpc/operator_mpc.py, OperatorMPC(estimate_departures=True)"},
    {"arm": "Oracle-E", "regimes": "DC (Week 8)", "connected_evs": YES, "transformer_rating": YES,
     "requested_energy": YES, "departure_times": "yes (exact)", "future_arrivals": "yes, whole day",
     "power_setpoint": NO, "causal": NO, "code": "ev2gym_thesis/mpc/operator_mpc.py, OracleE"},
]
