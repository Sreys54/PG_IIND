# f19_capacity_threshold_dc

Last run: f19 in the DC fast-charging regime, 42-minute sessions (the long-dwell regime is f19_capacity_threshold; two-regime framing, 06 S6.8). The transformer-aware Round Robin (the recommended strategy) holds every criterion through 1.3x (47 offered arrivals/day, 763 kWh/day) and never exceeds 100 kW; AFAP, EV2Gym's setpoint-following Round Robin and the final RL model (out of its training distribution) exceed 100 kW from 0.267x. Source: results/dwell_c1_capacity_by_level.csv.

- Runs behind this figure: 4400
- Configs: station_v0_bogota_dc42_sp{8..150}
- Algorithms: AFAP, Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware, Final RL model (out of training distribution)
- Git commit: 34dc0e0d006bf1a6ba010ba73e477eadb400fae6
- Generated: 2026-10-14T05:43:51.511312Z
