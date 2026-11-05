# f07_metric_heatmap

Algorithms (rows) x metrics (columns), color-normalized per column (min-max across algorithms) with direction corrected so green always means 'better performance', not just 'higher raw number' -- total_transformer_overload is inverted since lower is better there. Raw mean value annotated in each cell. A single-glance summary of the algorithms compared on the current grid. Colours are relative within each column, not absolute: a red cell is the worst arm in that column, which can still be close to the best in raw value.

- Runs behind this figure: 2200
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), MPC (tracking), MPC (energy-max), TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102), TD3 extended, last (seed 100), TD3 extended, last (seed 101), TD3 extended, last (seed 102), TD3 new run @60k (seed 100), TD3 new run @60k (seed 101), TD3 new run @60k (seed 102)
- Git commit: 8b2fc5016d2b49fab79de6d11fb985afe5f0d0bc
- Generated: 2026-11-03T19:20:53.279328Z
