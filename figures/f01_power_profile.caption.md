# f01_power_profile

Aggregate station power (kW) over the reference evaluation day, one line per algorithm, with the transformer power limit as a dashed horizontal line and shaded fill where the limit is exceeded.

- Runs behind this figure: 6
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control)
- Git commit: 2190ce39ddafeac3a25b4c59437e94459f2a2c57
- Generated: 2026-08-13T04:42:36.405624Z

Single-day profile: seed=0 only (not averaged across the 5-seed grid), per eval_protocol.REFERENCE_DAY=2022-01-17 -- this is the figure REFERENCE_DAY exists for, per its own docstring.
