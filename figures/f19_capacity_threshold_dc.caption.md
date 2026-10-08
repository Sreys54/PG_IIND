# f19_capacity_threshold_dc

Last run: f19 regenerated under the primary 42-minute DC session model (the Dutch-duration f19 is kept as a sensitivity). The transformer-aware Round Robin (the recommended strategy) holds every criterion through 1.3x (47 offered arrivals/day, 763 kWh/day) and never exceeds 100 kW; AFAP, EV2Gym's setpoint-following Round Robin and the final RL model (out of its training distribution) exceed 100 kW from 0.267x. Source: results/dwell_c1_capacity_by_level.csv.

- Runs behind this figure: 4400
- Configs: station_v0_bogota_dc42_sp{8..150}
- Algorithms: AFAP, Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware, Final RL model (out of training distribution)
- Git commit: dad3f3ecb69b64e7a743809d0729e4b7058b0646
- Generated: 2026-10-07T22:30:17.550215Z
