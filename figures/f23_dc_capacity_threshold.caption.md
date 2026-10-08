# f23_dc_capacity_threshold

Final capacity brief C1 under the DC session model (primary). Left and middle: 42-minute sessions, four arms. Right: demand not served for EV2Gym's Round Robin and the transformer-aware Round Robin at 32, 42 and 78 minutes. EV2Gym's Round Robin charges ceil(setpoint / port power) EVs, and the setpoint is median-smoothed over 5 steps, which erases short-session spikes: it under-delivers and still exceeds 100 kW where spikes survive. The transformer-aware Round Robin (same allocation, budget = 0.999 x rating; the recommended strategy) never exceeds 100 kW by construction. The final RL model was trained on Dutch durations and is out of its training distribution. Grey dashed: the closure (Dutch-duration) Round Robin, now a declared sensitivity. Source: results/dwell_c1_capacity_by_level.csv.

- Runs behind this figure: 8800
- Configs: station_v0_bogota_dc{32,42,78}_sp{8..150}
- Algorithms: AFAP, Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware, Final RL model (out of training distribution)
- Git commit: dad3f3ecb69b64e7a743809d0729e4b7058b0646
- Generated: 2026-10-07T22:29:20.521370Z
