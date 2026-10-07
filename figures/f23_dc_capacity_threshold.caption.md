# f23_dc_capacity_threshold

Final capacity brief C1 under the DC session model (primary). Left and middle: 42-minute sessions, four arms. Right: demand not served for EV2Gym's Round Robin and the transformer-capped diagnostic at 32, 42 and 78 minutes. EV2Gym's Round Robin charges ceil(setpoint / port power) EVs, and the setpoint is median-smoothed over 5 steps, which erases short-session spikes: it under-delivers and still exceeds 100 kW where spikes survive. The capped diagnostic (same allocation, budget = 0.999 x rating) never exceeds 100 kW by construction. The final RL model was trained on Dutch durations and is out of its training distribution. Grey dashed: the closure (Dutch-duration) Round Robin, now a declared sensitivity. Source: results/dwell_c1_capacity_by_level.csv.

- Runs behind this figure: 8800
- Configs: station_v0_bogota_dc{32,42,78}_sp{8..150}
- Algorithms: AFAP, Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-capped (diagnostic), Final RL model (out of training distribution)
- Git commit: 942122a9ef92ffece960e3d7270f98c5307131be
- Generated: 2026-10-07T06:17:16.766808Z
