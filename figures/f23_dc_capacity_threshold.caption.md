# f23_dc_capacity_threshold

Final capacity brief C1 in the DC fast-charging regime (two-regime framing, 06 S6.8). Left and middle: 42-minute sessions, four arms. Right: demand not served for EV2Gym's Round Robin and the transformer-aware Round Robin at 32, 42 and 78 minutes. EV2Gym's Round Robin charges ceil(setpoint / port power) EVs, and the setpoint is median-smoothed over 5 steps, which erases short-session spikes: it under-delivers and still exceeds 100 kW where spikes survive. The transformer-aware Round Robin (same allocation, budget = 0.999 x rating; the recommended strategy) never exceeds 100 kW by construction. The final RL model was trained on Dutch durations and is out of its training distribution. Grey dashed: the closure Round Robin in the long-dwell regime (EV2Gym's native durations). Source: results/dwell_c1_capacity_by_level.csv.

- Runs behind this figure: 8800
- Configs: station_v0_bogota_dc{32,42,78}_sp{8..150}
- Algorithms: AFAP, Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware, Final RL model (out of training distribution)
- Git commit: 34dc0e0d006bf1a6ba010ba73e477eadb400fae6
- Generated: 2026-10-14T05:43:50.667285Z
