# f18_two_city_margin

Gross margin each arm concedes against AFAP (COP/day), recomputed from the registry's energy with Bogota's Week 5 constants (retail 1,450; CU 865.7615) and Medellin's EPM September 2026 Nivel II CU (923.92, Punta, with contribution) with Bogota's retail price as a labelled sensitivity (EPM publishes no EV charging price). Under a flat price the two cities differ by the constant factor 0.900; the ranking is identical (results/week7_ranking_invariance.csv). Source: results/week7_replicability_margin.csv.

- Runs behind this figure: 700
- Configs: station_v0_bogota
- Algorithms: Round Robin, MPC (tracking), Oracle (tracking-only), TD3 extended seed 102 (final RL), Random (control), MPC (energy-max), Oracle (balanced)
- Git commit: ebf3634998ec91a8e99e6aae3a86b812e1c2d681
- Generated: 2026-10-06T05:41:14.876039Z
