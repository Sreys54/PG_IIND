# f08_learning_curves

Mean episode reward (SB3's own rolling window over the last <=100 completed episodes) vs. training timesteps, one line per training seed, in SEPARATE PANELS per arm -- vanilla TD3 (SqTrError_TrPenalty_UserIncentives) and TD3-TrackingOnly (SquaredTrackingErrorReward) train under different reward functions, so their episode-reward magnitudes are not comparable on one shared axis (the assert_total_reward_comparable rule, in figure form). Source: each run's own learning_curve.csv (ev2gym_thesis/rl/callbacks.py's LearningCurveCallback), NOT the main registry -- the registry has no reward-vs-timesteps time series column. Reward values use each arm's OWN training reward function, not any of metrics -- see thesis_docs/chapters/03_rl_baseline.md S3.4 for why those are not the same thing.

- Runs behind this figure: 6
- Configs: station_v0_bogota
- Algorithms: TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102)
- Git commit: b86e3b3def127c6fc52606036ca65ef84e9b5f5b
- Generated: 2026-08-20T05:34:53.254596Z

Seed-to-seed spread across each panel's 3 lines IS signal, not noise to average away -- see 00_lab_log.md's Week 3 Entregable 7 entry (vanilla) and Week 4's trackingonly_train_seed_dispersion.csv (TD3-TrackingOnly) for the cross-training-seed dispersion analysis this figure visualizes.
