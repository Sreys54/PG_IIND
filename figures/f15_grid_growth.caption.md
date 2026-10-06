# f15_grid_growth

The five fixed Objective 4 arms on the grid-enabled station, along two one-at-a-time growth axes (top: station demand, spawn_multiplier 30/39/48; bottom: feeder background load, load_multiplier 1.0/1.3/1.6). Point = mean over 100 cells (50 scenario seeds x weekday/weekend); bar = 95% cluster-bootstrap CI resampling the seed (ENS_rel: S5.7 definition and its seed bootstrap). Round Robin is drawn dashed as the reference; dotted lines are the anteproyecto targets. Source: results/week7_grid_master_comparison.csv, results/week7_grid_ens_compliance.csv.

- Runs behind this figure: 2500
- Configs: station_v0_bogota_grid[base], station_v0_bogota_grid[load1.3], station_v0_bogota_grid[load1.6], station_v0_bogota_grid[spawn1.3], station_v0_bogota_grid[spawn1.6]
- Algorithms: AFAP, Round Robin, MPC (tracking), TD3 extended seed 102 (final RL), Oracle (tracking-only)
- Git commit: ebf3634998ec91a8e99e6aae3a86b812e1c2d681
- Generated: 2026-10-06T05:42:33.006609Z

MPC_TrackingG2V and the oracle are non-causal (know departure times); they bound, not compete.
