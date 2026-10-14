# f19_capacity_threshold

Long-dwell regime: EV2Gym's native session durations (mean 300.6 min), the environment the simulator was built for; the DC fast-charging regime is f19_capacity_threshold_dc (two-regime framing, 06 S6.8). Closure brief C1. Left: demand not served, lower bound (rejected arrivals' energy plus shortfall on served EVs, over total requested; ev2gym_thesis/demand/censoring.py). Right: 95th percentile over 50 seeds of the per-seed peak station power. Round Robin breaks the 15% target at 0.733x and never exceeds 100 kW; AFAP and the final RL model exceed 100 kW from 0.5x. Demand not served is nearly identical across arms: the 8 ports set it. 1.0/1.3/1.6x are the Week 7 Step 2 rows (identical to non-grid); the rest are closure rows. Source: results/closure_c1_capacity_by_level.csv.

- Runs behind this figure: 2100
- Configs: station_v0_bogota_sp15/22/60/75, station_v0_bogota_grid[base/spawn1.3/1.6]
- Algorithms: AFAP, Round Robin, TD3 extended seed 102 (final RL)
- Git commit: 34dc0e0d006bf1a6ba010ba73e477eadb400fae6
- Generated: 2026-10-14T05:43:48.088766Z
