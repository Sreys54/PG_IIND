# f05_vs_baseline

Paired percentage (or absolute, where the AFAP baseline is exactly 0) change relative to the AFAP baseline for each metric, computed with a paired bootstrap matched by (seed, eval_day) cell -- not independent-sample means, since every algorithm is evaluated on the identical scenario grid. A vertical zero line marks 'no change'.

- Runs behind this figure: 300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control)
- Git commit: 2190ce39ddafeac3a25b4c59437e94459f2a2c57
- Generated: 2026-08-13T04:42:47.643151Z
