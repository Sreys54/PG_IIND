# f20_port_options

Long-dwell regime: EV2Gym's native session durations (mean 300.6 min), the environment the simulator was built for; the DC fast-charging regime is f20_port_options_dc (two-regime framing, 06 S6.8). Closure brief C2, Round Robin on the 100 kW transformer. EV2Gym draws arrivals per port, so adding ports at an unchanged spawn multiplier also adds demand (grey); the constant-demand variants scale the spawn multiplier by 8/ports so only the port count changes (blue, the primary reading). 10 ports meet the 15% target at 0.733x and 12 ports at 1.0x. The 112.5 and 150 kVA variants (not plotted) leave Round Robin's values identical. Censoring recomputed for each port count. Source: results/closure_c2_options.csv.

- Runs behind this figure: 1000
- Configs: station_v0_bogota_sp22/sp30[_p10|_p12]_tx100[_cd]
- Algorithms: Round Robin
- Git commit: 34dc0e0d006bf1a6ba010ba73e477eadb400fae6
- Generated: 2026-10-14T05:43:49.207838Z
