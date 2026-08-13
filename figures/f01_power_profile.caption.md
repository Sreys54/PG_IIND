# f01_power_profile

Aggregate station power (kW) over the reference evaluation day, one line per algorithm, with the transformer power limit as a dashed horizontal line and shaded fill where the limit is exceeded.

- Runs behind this figure: 2
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin
- Git commit: 0b098f5e0b7ac8efe19a4369f476e58f917ff06a
- Generated: 2026-08-13T00:18:51.455072Z

Single-day profile: seed=0 only (not averaged across the 5-seed grid), per eval_protocol.REFERENCE_DAY=2022-01-17 -- this is the figure REFERENCE_DAY exists for, per its own docstring.
