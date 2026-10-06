# f16_transformer_sizing

Per scenario seed, the peak power drawn by the station (max over the two day types, from each run's saved timeseries); black bar = 95th percentile over the 50 seeds, i.e. the transformer rating at which the 95th-percentile seed would stop overloading. Dotted = the installed 100 kW. For AFAP the peak does not respond to the rating, so the bar is a valid sizing number; limit-aware arms stay at or below 100 kW by construction. With n = 50 the 95th percentile rests on ~2-3 tail seeds: directional, not a tail estimate. Source: results/week7_transformer_per_seed.csv, results/week7_transformer_sizing.csv.

- Runs behind this figure: 2500
- Configs: station_v0_bogota_grid[base], station_v0_bogota_grid[load1.3], station_v0_bogota_grid[load1.6], station_v0_bogota_grid[spawn1.3], station_v0_bogota_grid[spawn1.6]
- Algorithms: AFAP, Round Robin, MPC (tracking), TD3 extended seed 102 (final RL), Oracle (tracking-only)
- Git commit: ebf3634998ec91a8e99e6aae3a86b812e1c2d681
- Generated: 2026-10-06T05:41:13.377229Z
