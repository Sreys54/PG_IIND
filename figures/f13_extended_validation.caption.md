# f13_extended_validation

Deterministic (no exploration noise) validation of each saved checkpoint every 10,000 steps on 20 fixed validation cells disjoint from the training draws and from the evaluation grid. Grey band and black line: min-max and mean across the three training seeds, over the range all three seeds reached; coloured lines continue the seeds that trained longer. Left: tracking error, the pre-registered selection criterion; middle/right: secondary metrics. Dashed grey: original 60k budget; dotted: convergence declared per seed; large markers: selected (primary) checkpoint. Source: experiments/phase2_algorithms/results/week6_part0/*_validation.csv and results/week6_part0_convergence.csv.

- Runs behind this figure: 4100
- Configs: station_v0_bogota
- Algorithms: TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102)
- Git commit: 23468f3dff170f211d33911b79d6e7c1cd6d7d58
- Generated: 2026-09-28T15:10:12.094496Z

n_runs counts validation episodes (validation evaluations x 20 cells).
