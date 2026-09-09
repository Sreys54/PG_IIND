# f10_optimality_gap

Mean absolute gap between each online algorithm and the corresponding oracle variant, restricted to metrics that oracle actually optimizes (tracking_error vs. Optimal_Oracle_Tracking; satisfaction metrics vs. Optimal_Oracle_Balanced) -- no panel for total_transformer_overload, a hard constraint in both oracle variants and trivially zero. The shaded gray band is the tie-break noise floor (results/oracle_tiebreak_noise_floor.csv): the spread between the two oracle variants' own degenerate optima on the same metric -- any online-algorithm gap smaller than this band is within measurement resolution, not a meaningful difference.

- Runs behind this figure: 33
- Configs: station_v0_bogota
- Algorithms: 
- Git commit: 07eb8a4fecac3a57be1571389199f4917c39ca03
- Generated: 2026-09-09T16:11:51.899599Z

Source: results/optimality_gap.csv + results/oracle_tiebreak_noise_floor.csv (scripts/analyze_week4_results.py), not the main registry directly.
