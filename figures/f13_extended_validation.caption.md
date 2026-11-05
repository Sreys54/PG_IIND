# f13_extended_validation

Deterministic (no exploration noise) validation of each saved checkpoint every 10,000 steps on 20 fixed validation cells disjoint from the training draws and from the evaluation grid. Grey band and black line: min-max and mean across the three training seeds, over the range all three seeds reached; coloured lines continue the seeds that trained longer. Left: tracking error, the pre-registered selection criterion; middle/right: secondary metrics. Dashed grey: original 60k budget; dotted: convergence declared per seed; large markers: selected (primary) checkpoint. Source: experiments/phase2_algorithms/results/week6_part0/*_validation.csv and results/week6_part0_convergence.csv.

- Runs behind this figure: 4100
- Configs: station_v0_bogota
- Algorithms: TD3 extended, primary (seed 100), TD3 extended, primary (seed 101), TD3 extended, primary (seed 102)
- Git commit: 8b2fc5016d2b49fab79de6d11fb985afe5f0d0bc
- Generated: 2026-11-03T19:20:54.090701Z

n_runs counts validation episodes (validation evaluations x 20 cells).
