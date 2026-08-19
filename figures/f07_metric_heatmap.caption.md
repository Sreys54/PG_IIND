# f07_metric_heatmap

Algorithms (rows) x metrics (columns), color-normalized per column (min-max across algorithms) with direction corrected so green always means 'better performance', not just 'higher raw number' -- total_transformer_overload is inverted since lower is better there. Raw mean value annotated in each cell. A single-glance summary of the cumulative experiment history -- with only 2 algorithms so far, each column is necessarily 0/1; this becomes more informative as more algorithms are added in later weeks.

- Runs behind this figure: 300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control)
- Git commit: 4a82315b68e2a106928ecba523b2cc15ca14e5c9
- Generated: 2026-08-19T03:40:24.839486Z
