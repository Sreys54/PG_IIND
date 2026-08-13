# f08_learning_curves

Mean episode reward (SB3's own rolling window over the last <=100 completed episodes) vs. training timesteps, one line per TD3 training seed. Source: each run's own learning_curve.csv (ev2gym_thesis/rl/callbacks.py's LearningCurveCallback), NOT the main registry -- the registry has no reward-vs-timesteps time series column. Reward values use the training reward function (SqTrError_TrPenalty_UserIncentives), not any of the thesis's evaluation metrics -- see thesis_docs/chapters/03_rl_baseline.md S3.4 for why those are not the same thing.

- Runs behind this figure: 3
- Configs: station_v0_bogota
- Algorithms: TD3 (seed 100), TD3 (seed 101), TD3 (seed 102)
- Git commit: 2190ce39ddafeac3a25b4c59437e94459f2a2c57
- Generated: 2026-08-13T04:42:49.330494Z

This is the first figure where seed-to-seed spread across the 3 TD3_vanilla_ts* lines IS the signal, not noise to average away -- see 00_lab_log.md's Week 3 Entregable 7 entry for the cross-training-seed dispersion analysis this figure visualizes.
