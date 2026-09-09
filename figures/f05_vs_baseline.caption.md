# f05_vs_baseline

Paired percentage (or absolute, where the AFAP baseline is exactly 0) change relative to the AFAP baseline for each metric, computed with a paired bootstrap matched by (seed, eval_day) cell -- not independent-sample means, since every algorithm is evaluated on the identical scenario grid. A vertical zero line marks 'no change'.

- Runs behind this figure: 1300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), MPC (tracking), MPC (energy-max)
- Git commit: 07eb8a4fecac3a57be1571389199f4917c39ca03
- Generated: 2026-09-09T16:11:47.659708Z
