# f20_port_options

Closure brief C2, Round Robin on the 100 kW transformer. EV2Gym draws arrivals per port, so adding ports at an unchanged spawn multiplier also adds demand (grey); the constant-demand variants scale the spawn multiplier by 8/ports so only the port count changes (blue, the primary reading). 10 ports meet the 15% target at 0.733x and 12 ports at 1.0x. The 112.5 and 150 kVA variants (not plotted) leave Round Robin's values identical. Censoring recomputed for each port count. Source: results/closure_c2_options.csv.

- Runs behind this figure: 1000
- Configs: station_v0_bogota_sp22/sp30[_p10|_p12]_tx100[_cd]
- Algorithms: Round Robin
- Git commit: 6f42b02fd5e17cca0db3f2e9b52ce01865c1da10
- Generated: 2026-10-06T23:36:11.394591Z
