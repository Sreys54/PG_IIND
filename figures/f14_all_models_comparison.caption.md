# f14_all_models_comparison

Every arm evaluated on the current statistical grid (analysis_row=True, 50 scenario seeds x 2 day types = 100 cells per arm), from the Week 1 heuristics through the Week 6 Part 0 extended TD3_vanilla run, in four small-multiple panels (one metric per panel, never a shared axis). Points are 100-cell means; bars are 95% normal CIs over the 50 seed-level means (the seed is the independent unit), except ENS_rel, which uses the S5.7 definition and its cluster-bootstrap CI from results/week5_ens_compliance.csv and results/week6_part0_ens_compliance.csv. Dashed blue: Round Robin, the recommended strategy (S5.8). Dotted: the 15% ENS_rel target. Groups are shaded alternately. MPC and oracle arms are non-causal (know departure times) and are value-of-information bounds, not deployable candidates. The original TD3 rows were trained before the Week 5 power-setpoint fix and evaluated after it; the new-run and extended rows were trained and evaluated on the fixed environment.

- Runs behind this figure: 2200
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin, Random (control), MPC (tracking), MPC (energy-max), Oracle (tracking-only), Oracle (balanced), TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), TD3 new run @60k (seed 100), TD3 new run @60k (seed 101), TD3 new run @60k (seed 102), TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102), TD3 extended, last (seed 100), TD3 extended, last (seed 101), TD3 extended, last (seed 102)
- Git commit: 23468f3dff170f211d33911b79d6e7c1cd6d7d58
- Generated: 2026-09-28T15:51:28.381114Z
