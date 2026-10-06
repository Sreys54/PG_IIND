# f12_extended_training_reward

Raw training-episode reward (faint) and its rolling mean over the last 100 episodes (black) for the three extended TD3_vanilla training seeds, one panel per seed; same reward function throughout, so a shared y-axis is valid. Dashed grey: the original 60,000-step budget. Dotted: the step at which the pre-registered validation rule declared convergence. Episodes use exploration noise and a different random scenario each, so this curve oscillates even for a stable policy. Source: experiments/phase2_algorithms/results/week6_part0/*_episodes.csv.

- Runs behind this figure: 3
- Configs: station_v0_bogota
- Algorithms: TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102)
- Git commit: 23468f3dff170f211d33911b79d6e7c1cd6d7d58
- Generated: 2026-09-28T15:10:11.256147Z
