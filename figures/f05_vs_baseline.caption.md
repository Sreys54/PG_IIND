# f05_vs_baseline

Paired percentage (or absolute, where the AFAP baseline is exactly 0) change relative to the AFAP baseline for each metric, computed with a paired bootstrap matched by (seed, eval_day) cell -- not independent-sample means, since every algorithm is evaluated on the identical scenario grid. A vertical zero line marks 'no change'.

- Runs behind this figure: 300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control)
- Git commit: 4a82315b68e2a106928ecba523b2cc15ca14e5c9
- Generated: 2026-08-19T03:40:23.974538Z
