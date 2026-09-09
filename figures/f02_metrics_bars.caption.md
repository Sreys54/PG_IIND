# f02_metrics_bars

Grouped bars with 95% CI error bars across algorithms for total_ev_served, total_energy_charged, total_transformer_overload, average_user_satisfaction, and gross_margin_cop (Colombian-peso economics, results/economics_cop.csv -- NOT EV2Gym's own total_profits column, which is a negated ENTSO-E-priced purchase cost, not a profit figure; see registry.py's total_profits_semantics doc comment). Gross margin does not discriminate control quality under this project's flat Colombian tariff (05_algorithm_comparison.md S5.1) -- reported for Objective 1's revenue question, never used to rank algorithms. The energy-charged panel additionally shows the total energy requested by arriving EVs as a dashed upper-bound reference line (computed from ONE live reference-day run, seed=0 -- a proxy, not an average over all runs).

- Runs behind this figure: 1300
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), Random (control), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), MPC (tracking), MPC (energy-max)
- Git commit: 07eb8a4fecac3a57be1571389199f4917c39ca03
- Generated: 2026-09-09T16:11:39.878224Z
