# f17_voltage_attribution

Station-attributable voltage effect: each arm's run minus the idle-station (zero-charging) run of the same setting, seed and day (the feeder's background load and PV are identical between the two). Left: extra (bus, step) samples outside 0.95-1.05 p.u.; right: change in the minimum bus voltage. The x labels give how many of the 100 cells already leave the band with the station idle -- the feeder itself is out of band at bus 27, so no absolute compliance claim is made. Source: results/week7_voltage_attribution.csv.

- Runs behind this figure: 2500
- Configs: station_v0_bogota_grid[base], station_v0_bogota_grid[load1.3], station_v0_bogota_grid[load1.6], station_v0_bogota_grid[spawn1.3], station_v0_bogota_grid[spawn1.6]
- Algorithms: AFAP, Round Robin, MPC (tracking), TD3 extended seed 102 (final RL), Oracle (tracking-only)
- Git commit: ebf3634998ec91a8e99e6aae3a86b812e1c2d681
- Generated: 2026-10-06T05:42:09.820226Z
