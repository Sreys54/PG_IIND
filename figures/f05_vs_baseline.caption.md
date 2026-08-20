# f05_vs_baseline

Paired percentage (or absolute, where the AFAP baseline is exactly 0) change relative to the AFAP baseline for each metric, computed with a paired bootstrap matched by (seed, eval_day) cell -- not independent-sample means, since every algorithm is evaluated on the identical scenario grid. A vertical zero line marks 'no change'.

- Runs behind this figure: 550
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102)
- Git commit: b86e3b3def127c6fc52606036ca65ef84e9b5f5b
- Generated: 2026-08-20T05:34:51.391932Z
