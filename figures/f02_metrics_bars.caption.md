# f02_metrics_bars

Grouped bars with 95% CI error bars across algorithms for total_ev_served, total_energy_charged, total_transformer_overload, average_user_satisfaction, and total_profits. The energy-charged panel additionally shows the total energy requested by arriving EVs as a dashed upper-bound reference line (computed from ONE live reference-day run, seed=0 -- a proxy, not an average over all 100 runs).

- Runs behind this figure: 300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control)
- Git commit: 4a82315b68e2a106928ecba523b2cc15ca14e5c9
- Generated: 2026-08-19T03:40:20.897446Z
