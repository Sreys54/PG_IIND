# f01_power_profile

Aggregate station power (kW) over the reference evaluation day, one line per algorithm, with the transformer power limit as a dashed horizontal line and shaded fill where the limit is exceeded.

- Runs behind this figure: 11
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), Oracle (tracking-only), Oracle (balanced)
- Git commit: b86e3b3def127c6fc52606036ca65ef84e9b5f5b
- Generated: 2026-08-20T05:34:40.391487Z

Single-day profile: seed=0 only (not averaged across the 5-seed grid), per eval_protocol.REFERENCE_DAY=2022-01-17 -- this is the figure REFERENCE_DAY exists for, per its own docstring.
