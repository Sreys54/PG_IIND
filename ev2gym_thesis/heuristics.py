"""
Final capacity brief: a diagnostic Round Robin whose power budget is the
transformer rating instead of EV2Gym's power setpoint.

Why (measured, Part C, 2026-10-06): EV2Gym's RoundRobin
(ev2gym/baselines/heuristics.py, lines 54-93) charges
ceil(setpoint / per-port power) EVs per step, where the setpoint is
utils.generate_power_setpoints: each EV's requested energy x 1.8 spread over
[arrival + 1, departure), then median-smoothed over 5 steps. It never reads
the transformer limit. With 5-hour Dutch stays the setpoint is smooth and
stays below 100 kW, which is why Round Robin showed zero overload in Weeks
1-7. With 1-5-step DC sessions the median filter removes isolated spikes
(one 0.267x cell: 434.5 -> 169.7 kWh of setpoint against 241.4 kWh
requested; 14 of 34 connected steps with a zero setpoint), so Round Robin
both under-delivers and, where spikes survive, overloads.

This class keeps EV2Gym's Round Robin allocation unchanged (same buffer, same
rotation, same per-port action) and replaces only the power budget with
0.999 x the transformer's rated power at the current step (0.1% margin so
float rounding cannot register as overload; labelled). It is a DIAGNOSTIC
arm added by this brief, separating "round-robin load management" from
"EV2Gym's setpoint-coupled implementation"; it was not part of the Weeks 1-7
comparison, and the brief's thresholds are reported for EV2Gym's Round Robin
first.
"""
from ev2gym.baselines.heuristics import RoundRobin

BUDGET_FRACTION = 0.999


# doc:begin rr_capped
class RoundRobinTransformerCapped(RoundRobin):
    algo_name = "Round Robin, transformer-capped (diagnostic)"

    def get_action(self, env):
        budget_kw = BUDGET_FRACTION * min(tr.max_power[env.current_step] for tr in env.transformers)
        saved = env.power_setpoints[env.current_step]
        env.power_setpoints[env.current_step] = budget_kw  # RoundRobin.get_action reads this one value
        try:
            return super().get_action(env)
        finally:
            env.power_setpoints[env.current_step] = saved  # the tracking target itself is left unchanged
# doc:end rr_capped
