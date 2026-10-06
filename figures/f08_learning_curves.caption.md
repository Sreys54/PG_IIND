# f08_learning_curves

Mean episode reward (SB3's own rolling window over the last <=100 completed episodes) vs. training timesteps, one line per training seed, in SEPARATE PANELS per arm -- vanilla TD3 (SqTrError_TrPenalty_UserIncentives) and TD3-TrackingOnly (SquaredTrackingErrorReward) train under different reward functions, so their episode-reward magnitudes are not comparable on one shared axis (the assert_total_reward_comparable rule, in figure form). Source: each run's own learning_curve.csv (ev2gym_thesis/rl/callbacks.py's LearningCurveCallback), NOT the main registry -- the registry has no reward-vs-timesteps time series column. Reward values use each arm's OWN training reward function, not any of metrics -- see thesis_docs/chapters/03_rl_baseline.md S3.4 for why those are not the same thing. Week 6 Part 0 adds a third panel: the extended TD3_vanilla run (480k/660k/910k steps), same statistic computed from its per-episode log (experiments/phase2_algorithms/results/week6_part0/*_episodes.csv), sharing the y-axis with the original vanilla panel because the reward function is identical. Dashed: original 60k budget; dotted: convergence declared by the validation rule. The extended run trained on the post-setpoint-fix environment, the original runs before it.

- Runs behind this figure: 9
- Configs: station_v0_bogota
- Algorithms: TD3 (seed 100), TD3 (seed 101), TD3 (seed 102), TD3-TrackingOnly (seed 100), TD3-TrackingOnly (seed 101), TD3-TrackingOnly (seed 102), TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102)
- Git commit: 23468f3dff170f211d33911b79d6e7c1cd6d7d58
- Generated: 2026-09-28T15:51:26.581149Z

Seed-to-seed spread across each panel's 3 lines IS signal, not noise to average away -- see 00_lab_log.md's Week 3 Entregable 7 entry (vanilla) and Week 4's trackingonly_train_seed_dispersion.csv (TD3-TrackingOnly) for the cross-training-seed dispersion analysis this figure visualizes.
